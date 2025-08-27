# backend/app/main.py
import asyncio
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi.middleware.cors import CORSMiddleware
import re

from app.nlp import classify_order  # Greek-capable classifier

app = FastAPI(title="Tavern Ordering Backend (MVP)")

# Allow CORS for local dev (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (MVP). Replace with DB (SQLite/Postgres) for production.
orders_by_table: Dict[int, List[Dict]] = defaultdict(list)
# Table-level metadata (people count, bread preference)
table_meta: Dict[int, Dict] = defaultdict(lambda: {"people": None, "bread": False})

# Keep websocket clients per station (kitchen, grill, waiter)
station_connections: Dict[str, List[WebSocket]] = {"kitchen": [], "grill": [], "waiter": []}
lock = asyncio.Lock()  # ensure atomic updates when multiple requests come in


# ---------- Pydantic models ----------
class SubmitOrder(BaseModel):
    table: int
    order_text: str
    people: int = None      # optional number of people
    bread: bool = False     # wants bread?


# ---------- Helper utilities ----------
def _make_item(line_text: str, table: int, category: str) -> Dict:
    """Create a standardized item object for storage & messages."""
    return {
        "id": str(uuid4()),
        "table": table,
        "text": line_text.strip(),
        "category": category,  # 'kitchen'|'grill'|'drinks'
        "status": "pending",  # pending / done / cancelled
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


async def broadcast_to_station(station: str, message: Dict):
    """Send JSON message to all connected clients of a station, remove dead connections."""
    conns = station_connections.get(station, [])
    alive = []
    for ws in conns:
        try:
            await ws.send_json(message)
            alive.append(ws)
        except Exception:
            # Connection closed/errored — drop it
            pass
    station_connections[station] = alive


async def broadcast_to_all(message: Dict):
    """Broadcast to kitchen, grill and waiter."""
    await broadcast_to_station("kitchen", message)
    await broadcast_to_station("grill", message)
    await broadcast_to_station("waiter", message)


def _pending_items_only(table_items: List[Dict]) -> List[Dict]:
    """Return only items with status == 'pending' in chronological order."""
    pending = [it for it in table_items if it.get("status") == "pending"]
    pending.sort(key=lambda x: x["created_at"])
    return pending


def _normalize_text_for_match(s: str) -> str:
    """
    Normalize a dish line for matching:
    - lowercase
    - remove punctuation except Greek letters/numbers
    - collapse whitespace
    """
    if not s:
        return ""
    t = s.strip().lower()
    t = re.sub(r"[^\w\sάέήίόύώϊϋΐΰΆΈΉΊΌΎΏΑ-Ωα-ω0-9]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


# ---------- Config endpoint (convenience for frontends) ----------
@app.get("/config", summary="Return backend URL info for frontends")
async def get_config(request: Request):
    scheme = request.url.scheme or "http"
    host = request.url.hostname or "localhost"
    port = request.url.port or 8000
    base = f"{scheme}://{host}:{port}"
    ws_base = f"{'wss' if scheme == 'https' else 'ws'}://{host}:{port}"
    return {"backend_base": base, "ws_base": ws_base, "backend_port": port}


# ---------- API Endpoints ----------
@app.post("/order/", summary="Submit a new order (table + free-text lines)")
async def submit_order(payload: SubmitOrder):
    """
    Accept table number, multi-line order_text (one dish per line) and optional table metadata.
    Classify each line, store items, push them to the proper station(s), and save table meta.
    """
    async with lock:
        # save table-level metadata
        table_meta[payload.table] = {"people": payload.people, "bread": bool(payload.bread)}

        classified = classify_order(payload.order_text)  # returns list of {text, category}
        created_items = []
        for entry in classified:
            item = _make_item(entry["text"], payload.table, entry["category"])
            orders_by_table[payload.table].append(item)
            created_items.append(item)

        # Broadcast each new item to its station; include table meta in the message
        for item in created_items:
            msg = {"action": "new", "item": item, "meta": table_meta.get(payload.table, {})}
            target_station = "grill" if item["category"] == "grill" else "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, msg))

        # Notify waiter clients about each new item & meta
        for item in created_items:
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": item, "meta": table_meta.get(payload.table, {})}))

    return {"status": "ok", "created": created_items}


@app.get("/table_meta/{table}")
async def get_table_meta(table: int):
    return table_meta.get(table, {"people": None, "bread": False})


@app.get("/orders/", summary="List all tables and their current orders")
async def list_orders(include_history: bool = Query(False, description="If true return full history including cancelled/done")):
    """
    Return all orders grouped by table.
    By default (include_history=false) return only pending items for each table.
    If include_history=true return the full list (pending/done/cancelled) per table.
    """
    if include_history:
        return {str(table): orders_by_table[table] for table in orders_by_table}
    else:
        # return only pending items to keep frontend clean
        return {str(table): _pending_items_only(orders_by_table[table]) for table in orders_by_table}


@app.put("/order/{table}", summary="Replace/Update the active order for a table")
async def replace_table_order(table: int, payload: SubmitOrder):
    """
    Smarter replace: only replace the changed lines.
    - Reuse pending items that match (normalized text + category) to avoid duplication.
    - Cancel unmatched old pending items.
    - Create new items for unmatched new lines.
    """
    async with lock:
        # existing pending items available for matching
        existing_pending = [it for it in orders_by_table.get(table, []) if it["status"] == "pending"]
        existing_records = []
        for it in existing_pending:
            existing_records.append({
                "item": it,
                "norm": _normalize_text_for_match(it.get("text", "")),
                "category": it.get("category"),
                "used": False
            })

        # Save table meta
        table_meta[table] = {"people": payload.people, "bread": bool(payload.bread)}

        # Broadcast meta update to all stations and waiter
        msg_meta = {"action": "meta_update", "table": table, "meta": table_meta[table]}
        asyncio.create_task(broadcast_to_station("kitchen", msg_meta))
        asyncio.create_task(broadcast_to_station("grill", msg_meta))
        asyncio.create_task(broadcast_to_station("waiter", msg_meta))

        # classify new payload
        classified = classify_order(payload.order_text)

        new_items_created = []
        kept_items = []
        for entry in classified:
            new_text = entry["text"].strip()
            new_cat = entry["category"]
            new_norm = _normalize_text_for_match(new_text)

            match_idx = None
            for idx, rec in enumerate(existing_records):
                if not rec["used"] and rec["norm"] == new_norm and rec["category"] == new_cat:
                    match_idx = idx
                    break

            if match_idx is not None:
                existing_records[match_idx]["used"] = True
                kept_items.append(existing_records[match_idx]["item"])
            else:
                item = _make_item(new_text, table, new_cat)
                orders_by_table[table].append(item)
                new_items_created.append(item)

        # Cancel unmatched old pending items
        cancelled_items = []
        for rec in existing_records:
            if not rec["used"]:
                rec["item"]["status"] = "cancelled"
                cancelled_items.append(rec["item"])

        # Broadcast deletes for cancelled items and notify waiter
        for it in cancelled_items:
            msg = {"action": "delete", "item_id": it["id"], "table": table}
            target_station = "grill" if it["category"] == "grill" else "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, msg))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": table_meta.get(table, {})}))

        # Broadcast new items (with meta) and notify waiter
        for it in new_items_created:
            target_station = "grill" if it["category"] == "grill" else "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "new", "item": it, "meta": table_meta.get(table, {})}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": table_meta.get(table, {})}))

        # Broadcast update for remaining pending items (kept + new) so stations refresh table header
        remaining_pending = [it for it in orders_by_table.get(table, []) if it["status"] == "pending"]
        for it in remaining_pending:
            target_station = "grill" if it["category"] == "grill" else "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "update", "item": it, "meta": table_meta.get(table, {})}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": table_meta.get(table, {})}))

    return {"status": "ok", "replaced_count": len(new_items_created), "kept_count": len(kept_items), "cancelled_count": len(cancelled_items)}


@app.delete("/order/{table}/{item_id}", summary="Cancel a specific item from a table's order")
async def cancel_item(table: int, item_id: str):
    """
    Mark item as cancelled (if found) and notify stations to remove it.
    """
    async with lock:
        found = False
        for it in orders_by_table.get(table, []):
            if it["id"] == item_id and it["status"] == "pending":
                it["status"] = "cancelled"
                found = True
                msg = {"action": "delete", "item_id": item_id, "table": table}
                target_station = "grill" if it["category"] == "grill" else "kitchen"
                asyncio.create_task(broadcast_to_station(target_station, msg))
                # also notify waiter (so UI can update and show cancelled)
                asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": table_meta.get(table, {})}))
                break
        if not found:
            raise HTTPException(status_code=404, detail="item not found or not pending")

        # If no pending items left, do NOT auto-clear meta here (waiter must finalize).
        pending_left = [x for x in orders_by_table.get(table, []) if x["status"] == "pending"]
        if not pending_left:
            # Inform clients that pending are gone (meta remains until waiter finalizes)
            meta_msg = {"action": "meta_update", "table": table, "meta": table_meta.get(table, {"people": None, "bread": False})}
            asyncio.create_task(broadcast_to_station("waiter", meta_msg))
            asyncio.create_task(broadcast_to_station("kitchen", meta_msg))
            asyncio.create_task(broadcast_to_station("grill", meta_msg))

    return {"status": "ok", "cancelled": item_id}


@app.post("/item/{item_id}/done", summary="Mark an item as done (from station via HTTP)")
async def mark_item_done(item_id: str):
    """Mark item done and broadcast update so UIs refresh status."""
    async with lock:
        found = None
        found_table = None
        for table, items in orders_by_table.items():
            for it in items:
                if it["id"] == item_id and it["status"] == "pending":
                    it["status"] = "done"
                    found = it
                    found_table = table
                    break
            if found:
                break
        if not found:
            raise HTTPException(status_code=404, detail="item not found or not pending")

        # notify both kitchen/grill about status change
        asyncio.create_task(broadcast_to_all({"action": "update", "item": found, "meta": table_meta.get(found_table, {})}))

        # also notify waiter: update & short notification
        asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": found, "meta": table_meta.get(found_table, {})}))
        # Greek notification: e.g. "ετοιμα <text> τραπέζι <table>"
        try:
            note_text = f"ετοιμα {found.get('text','')} τραπέζι {found.get('table')}"
            asyncio.create_task(broadcast_to_station("waiter", {"action": "notify", "message": note_text, "id": str(uuid4())}))
        except Exception:
            pass

        # If no pending left, notify clients (meta remains until waiter finalizes)
        pending_left = [x for x in orders_by_table.get(found_table, []) if x.get("status") == "pending"]
        if not pending_left:
            meta_msg = {"action": "meta_update", "table": found_table, "meta": table_meta.get(found_table, {"people": None, "bread": False})}
            asyncio.create_task(broadcast_to_station("waiter", meta_msg))
            asyncio.create_task(broadcast_to_station("kitchen", meta_msg))
            asyncio.create_task(broadcast_to_station("grill", meta_msg))

    return {"status": "ok", "item": found}


# ---------- Optional maintenance: purge endpoint ----------
@app.post("/purge_done", summary="Permanently remove done/cancelled items (optional maintenance)")
async def purge_done(older_than_seconds: int = 0):
    async with lock:
        now = datetime.utcnow()
        removed = 0
        for table in list(orders_by_table.keys()):
            kept = []
            for it in orders_by_table[table]:
                to_remove = False
                if it["status"] in ("done", "cancelled"):
                    if older_than_seconds > 0:
                        try:
                            created = datetime.fromisoformat(it["created_at"].replace("Z", ""))
                            if (now - created) > timedelta(seconds=older_than_seconds):
                                to_remove = True
                        except Exception:
                            to_remove = True
                    else:
                        to_remove = True
                if to_remove:
                    removed += 1
                else:
                    kept.append(it)
            orders_by_table[table] = kept
    return {"status": "ok", "removed": removed}


# ---------- WebSocket endpoints for stations & waiter ----------
@app.websocket("/ws/{station}")
async def station_ws(websocket: WebSocket, station: str):
    """
    Register a kitchen, grill or waiter websocket. The station will receive JSON messages of the form:
      { action: "new"|"delete"|"update", item: {...} } or {action:"delete", item_id: "..."}

    Waiter sockets may send:
      { action: "finalize_table", table: <int> }  -> finalize table (only allowed when no pending items)
    Stations may send:
      { action: "mark_done", item_id: "..." } to mark item as done
    """
    station = station.lower()
    if station not in ("kitchen", "grill", "waiter"):
        await websocket.close(code=4001)
        return

    await websocket.accept()
    station_connections.setdefault(station, []).append(websocket)

    try:
        # When a station connects, send an initialization message:
        if station == "waiter":
            # waiter wants the full view (include_history=true) — send full orders_by_table and meta
            orders_snapshot = {str(t): orders_by_table[t] for t in orders_by_table}
            await websocket.send_json({"action": "init", "orders": orders_snapshot, "meta": {str(k): table_meta[k] for k in table_meta}})
        else:
            # For kitchen/grill: send current pending items for that station in chronological order, attach meta to each item
            pending = []
            for table_items in orders_by_table.values():
                for it in table_items:
                    if it["status"] == "pending":
                        if (station == "grill" and it["category"] == "grill") or (station == "kitchen" and it["category"] != "grill"):
                            item_copy = dict(it)
                            item_copy["meta"] = table_meta.get(it["table"], {"people": None, "bread": False})
                            pending.append(item_copy)
            pending.sort(key=lambda x: x["created_at"])
            await websocket.send_json({"action": "init", "items": pending})

        # receive loop
        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict) or "action" not in data:
                await websocket.send_json({"error": "invalid message"})
                continue

            # ---------- Waiter actions ----------
            if station == "waiter" and data.get("action") == "finalize_table":
                # waiter asked to finalize (per business rule: only allowed when no pending items)
                table_to_finalize = data.get("table")
                if table_to_finalize is None:
                    await websocket.send_json({"action": "finalize_failed", "table": None, "reason": "missing_table"})
                    continue

                async with lock:
                    # Confirm table exists
                    if table_to_finalize not in orders_by_table:
                        await websocket.send_json({"action": "finalize_failed", "table": table_to_finalize, "reason": "table_not_found"})
                        continue

                    # Check pending items for this table
                    pending_left = [x for x in orders_by_table.get(table_to_finalize, []) if x.get("status") == "pending"]
                    if pending_left:
                        # refuse finalize, include number of pending items
                        await websocket.send_json({"action": "finalize_failed", "table": table_to_finalize, "pending": len(pending_left), "reason": "items_pending"})
                        # also send an updated set of pending items back so waiter UI can refresh
                        pending_items = [dict(it, meta=table_meta.get(it["table"], {"people": None, "bread": False})) for table_items in orders_by_table.values() for it in table_items if it["status"] == "pending"]
                        await websocket.send_json({"action": "init", "items": pending_items})
                        continue

                    # No pending items -> perform finalization: broadcast deletes and remove table & meta
                    items_to_remove = list(orders_by_table.get(table_to_finalize, []))
                    for it in items_to_remove:
                        # send delete to stations
                        msg = {"action": "delete", "item_id": it["id"], "table": table_to_finalize}
                        target_station = "grill" if it["category"] == "grill" else "kitchen"
                        asyncio.create_task(broadcast_to_station(target_station, msg))
                        # notify waiters as well
                        asyncio.create_task(broadcast_to_station("waiter", msg))

                    # remove the table from storage & meta
                    if table_to_finalize in orders_by_table:
                        del orders_by_table[table_to_finalize]
                    if table_to_finalize in table_meta:
                        del table_meta[table_to_finalize]

                    # broadcast table_finalized to everyone so UIs remove any remaining traces
                    tf_msg = {"action": "table_finalized", "table": table_to_finalize}
                    asyncio.create_task(broadcast_to_all(tf_msg))

                    # also broadcast meta reset for UI sync
                    meta_msg = {"action": "meta_update", "table": table_to_finalize, "meta": {"people": None, "bread": False}}
                    asyncio.create_task(broadcast_to_all(meta_msg))

                    # reply to the waiting websocket client (immediate confirmation)
                    try:
                        await websocket.send_json({"action": "finalized_ok", "table": table_to_finalize})
                    except Exception:
                        pass

                continue

            # ---------- Station (kitchen/grill) action: mark_done ----------
            if data.get("action") == "mark_done" and "item_id" in data:
                item_id = data["item_id"]
                async with lock:
                    found_item = None
                    found_table = None
                    for table, table_items in orders_by_table.items():
                        for it in table_items:
                            if it["id"] == item_id and it["status"] == "pending":
                                it["status"] = "done"
                                found_item = it
                                found_table = table
                                break
                        if found_item:
                            break
                    if found_item:
                        # broadcast update (include meta for convenience)
                        asyncio.create_task(broadcast_to_all({"action": "update", "item": found_item, "meta": table_meta.get(found_table, {})}))

                        # also notify waiter with short notification text
                        try:
                            note_text = f"ετοιμα {found_item.get('text','')} τραπέζι {found_item.get('table')}"
                            asyncio.create_task(broadcast_to_station("waiter", {"action": "notify", "message": note_text, "id": str(uuid4())}))
                        except Exception:
                            pass

                        try:
                            await websocket.send_json({"status": "ok", "item": found_item})
                        except Exception:
                            pass
                    else:
                        try:
                            await websocket.send_json({"error": "item not found or already processed"})
                        except Exception:
                            pass
                continue

            # Unknown action
            try:
                await websocket.send_json({"error": "unknown action"})
            except Exception:
                pass

    except WebSocketDisconnect:
        # cleanup: remove websocket from list
        if websocket in station_connections.get(station, []):
            station_connections[station].remove(websocket)
    except Exception:
        # on any other error clean up
        if websocket in station_connections.get(station, []):
            station_connections[station].remove(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
