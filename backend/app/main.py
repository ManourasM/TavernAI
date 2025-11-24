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
import unicodedata

from app.nlp import classify_order, MENU_ITEMS  # Greek-capable classifier + menu lookup

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

# Keep websocket clients per station (kitchen, grill, drinks, waiter)
station_connections: Dict[str, List[WebSocket]] = {"kitchen": [], "grill": [], "drinks": [], "waiter": []}
lock = asyncio.Lock()  # ensure atomic updates when multiple requests come in


# ---------- Pydantic models ----------
class SubmitOrder(BaseModel):
    table: int
    order_text: str
    people: int = None      # optional number of people
    bread: bool = False     # wants bread?


# ---------- Helper utilities ----------
def _normalize_text_for_match(s: str) -> str:
    """
    Normalize a dish line for matching:
    - Strip parentheses content (e.g., "2 μυθος (χωρίς σάλτσα)" -> "2 μυθος")
    - Strip quantity prefix with units (e.g., "2 μυθος" -> "μυθος", "2λ κρασι" -> "κρασι", "500ml ρακι" -> "ρακι")
    - lowercase
    - remove accents/diacritics
    - remove punctuation except Greek letters/numbers
    - collapse whitespace

    This ensures "2 μυθος" and "3 μυθος" match as the same item.
    Also ensures "2λ κρασι" and "3λ κρασι" match, and "2kg παιδακια" and "3kg παιδακια" match.
    Also ensures "2 μυθος (χωρίς σάλτσα)" and "3 μυθος" match.
    """
    if not s:
        return ""

    text = s.strip()

    # Strip parentheses content (e.g., "(χωρίς σάλτσα)")
    # This ensures "2 μυθος (χωρίς σάλτσα)" matches "2 μυθος"
    parentheses_pattern = r'\s*\([^)]*\)\s*'
    text = re.sub(parentheses_pattern, ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # Strip quantity prefix patterns (must match the parsing logic in nlp.py):
    # - "2 μυθος" -> "μυθος"
    # - "2λ κρασι" -> "κρασι"
    # - "2kg παιδακια" -> "παιδακια"
    # - "500ml ρακι" -> "ρακι"
    # - "2.5kg παιδακια" -> "παιδακια"
    # Pattern: number (int or decimal) + optional unit (NO SPACE) + space + item text
    quantity_pattern = r'^\d+(?:\.\d+)?(λτ|λ|lt|l|kg|κιλα|κιλο|κ|ml)?\s+'
    text = re.sub(quantity_pattern, '', text, flags=re.IGNORECASE)

    # strip accents
    nfkd = unicodedata.normalize("NFD", str(text))
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    t = no_accents.strip().lower()
    # keep Greek letters, latin, digits and spaces
    t = re.sub(r"[^\w\sάέήίόύώϊϋΐΰΆΈΉΊΌΎΏΑ-Ωα-ω0-9]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _strip_accents(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _parse_qty_and_name(line_text: str):
    """
    Parse leading quantity and return (qty:int, name:str).
    If no leading number is found assume qty=1 and return original text as name.
    Example:
      "2 Σουβλάκι χοιρινό" -> (2, "Σουβλάκι χοιρινό")
      "Σουβλάκι" -> (1, "Σουβλάκι")
    """
    if not line_text or not str(line_text).strip():
        return 1, ""
    s = str(line_text).strip()
    m = re.match(r"^\s*(\d+)\s+(.+)$", s)
    if m:
        try:
            qty = int(m.group(1))
            name = m.group(2).strip()
            if qty <= 0:
                qty = 1
            return qty, name
        except Exception:
            return 1, s
    return 1, s


def _levenshtein(a: str, b: str) -> int:
    """
    Basic Levenshtein distance (iterative, O(len(a)*len(b))). Implemented here to avoid extra deps.
    """
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)

    # ensure a is the shorter
    if len(a) > len(b):
        a, b = b, a

    previous_row = list(range(len(a) + 1))
    for i, cb in enumerate(b, start=1):
        current_row = [i]
        for j, ca in enumerate(a, start=1):
            insertions = previous_row[j] + 1
            deletions = current_row[j - 1] + 1
            substitutions = previous_row[j - 1] + (0 if ca == cb else 1)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _tokenize(s: str) -> List[str]:
    """Split normalized string into tokens, dropping very short tokens."""
    if not s:
        return []
    parts = [tok for tok in s.split() if len(tok) > 1]
    return parts


def _find_menu_price_for_name(name: str):
    """
    Fuzzy match an order-line name against MENU_ITEMS and return (unit_price_float_or_None, matched_menu_id_or_None).
    Strategy (prefix-aware):
      - normalize both input and menu item names with _normalize_text_for_match
      - substring matches are treated as very strong signals
      - do per-token scoring: if an order token matches the start of a menu token (startswith) score = 1.0
        otherwise use normalized token-level Levenshtein ratio
      - final score is the average of per-order-token best token matches, combined with a full-string
        levenshtein ratio as a secondary signal. Preference is given to longer menu entries when scores tie.
    """
    if not name:
        return None, None

    norm = _normalize_text_for_match(name)
    if not norm:
        return None, None

    # Build normalized menu mapping (normalize menu entry names)
    normalized_menu = {}
    for k, entry in MENU_ITEMS.items():
        entry_name = entry.get("name") or ""
        nk = _normalize_text_for_match(entry_name)
        if not nk:
            nk = _normalize_text_for_match(k)
        # if duplicates appear, keep the first — we'll use length-breaker later if needed
        normalized_menu.setdefault(nk, entry)

    best_key = None
    best_score = 0.0

    # pre-tokenize the order name
    order_tokens = _tokenize(norm)
    # if no tokens, fallback to whole-string only
    if not order_tokens:
        order_tokens = [norm]

    for menu_norm, entry in normalized_menu.items():
        if not menu_norm:
            continue

        # immediate strong signal: substring either way
        if menu_norm in norm or norm in menu_norm:
            score = 1.0
        else:
            menu_tokens = _tokenize(menu_norm) or [menu_norm]

            # For each order token, find the best matching menu token score:
            # - startswith (prefix) gets 1.0 (strong)
            # - else compute token-level levenshtein ratio (1 - dist / max_len)
            per_token_scores = []
            for ot in order_tokens:
                best_tok_score = 0.0
                for mt in menu_tokens:
                    if mt.startswith(ot) or ot.startswith(mt):
                        # prefix or reverse-prefix match -> treat as exact
                        tok_score = 1.0
                    else:
                        max_l = max(len(ot), len(mt))
                        if max_l == 0:
                            tok_score = 0.0
                        else:
                            d = _levenshtein(ot, mt)
                            tok_score = 1.0 - (d / max_l)
                            if tok_score < 0:
                                tok_score = 0.0
                    if tok_score > best_tok_score:
                        best_tok_score = tok_score
                per_token_scores.append(best_tok_score)

            # average per-order-token score (so short user token that matches prefix boosts score)
            token_match_score = sum(per_token_scores) / len(per_token_scores) if per_token_scores else 0.0

            # also compute full-string levenshtein ratio as secondary signal
            max_len = max(len(norm), len(menu_norm))
            if max_len > 0:
                full_dist = _levenshtein(norm, menu_norm)
                full_lev_ratio = 1.0 - (full_dist / max_len)
                if full_lev_ratio < 0:
                    full_lev_ratio = 0.0
            else:
                full_lev_ratio = 0.0

            # prefix-length bonus: length of common prefix between strings normalized
            common_pref = 0
            for a_ch, b_ch in zip(norm, menu_norm):
                if a_ch == b_ch:
                    common_pref += 1
                else:
                    break
            prefix_bonus = (common_pref / max_len) if max_len > 0 else 0.0

            # Combine scores — token match is primary, full-string and prefix bonus secondary.
            score = (0.65 * token_match_score) + (0.25 * full_lev_ratio) + (0.10 * prefix_bonus)

        # prefer longer menu_norm (more specific) when scores tie closely
        if score > best_score or (abs(score - best_score) < 1e-6 and len(menu_norm) > (len(best_key) if best_key else 0)):
            best_score = score
            best_key = menu_norm

    # threshold to avoid false positives; adjust if needed
    THRESHOLD = 0.50
    if best_key and best_score >= THRESHOLD:
        entry = normalized_menu.get(best_key)
        if entry:
            price = entry.get("price")
            return (float(price) if (price is not None) else None, entry.get("id"))
    return None, None


def _make_item(line_text: str, table: int, category: str, menu_id: str = None,
               menu_name: str = None, price: float = None, multiplier: float = None) -> Dict:
    """Create a standardized item object for storage & messages.

    Now includes:
      - text: original user text (preserved exactly as written)
      - menu_name: matched menu item name (for pricing display in waiter UI)
      - qty: quantity multiplier (can be float for kg/liters)
      - unit_price: unit price from menu
      - line_total: qty * unit_price
      - menu_id: matched menu item ID
    """
    # Use provided values from classification, or fall back to old parsing
    if menu_id is not None and price is not None and multiplier is not None:
        qty = multiplier
        unit_price = price
        matched_id = menu_id
        parsed_name = menu_name or line_text
    else:
        # Fallback to old parsing (for backwards compatibility)
        qty, parsed_name = _parse_qty_and_name(line_text)
        unit_price, matched_id = _find_menu_price_for_name(parsed_name)

    line_total = None
    if unit_price is not None and qty is not None:
        try:
            line_total = round(qty * float(unit_price), 2)
        except Exception:
            line_total = None

    return {
        "id": str(uuid4()),
        "table": table,
        "text": line_text.strip(),  # Original user text
        "menu_name": menu_name,  # Matched menu name for pricing display
        "name": parsed_name,  # For backwards compatibility
        "qty": qty,
        "unit_price": unit_price,  # float or None
        "line_total": line_total,  # float or None
        "menu_id": matched_id,
        "category": category,  # 'kitchen'|'grill'|'drinks'
        "status": "pending",  # pending / done / cancelled
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def _meta_for(table_key):
    """
    Safely return table meta for a table id that may be an int or None (or other).
    This avoids type-checker complaints where callers might have 'int | None'.
    """
    try:
        if table_key is None:
            return {"people": None, "bread": False}
        # coerce to int if possible
        return table_meta.get(int(table_key), {"people": None, "bread": False})
    except Exception:
        return {"people": None, "bread": False}


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
    """Broadcast to kitchen, grill, drinks and waiter."""
    await broadcast_to_station("kitchen", message)
    await broadcast_to_station("grill", message)
    await broadcast_to_station("drinks", message)
    await broadcast_to_station("waiter", message)


def _pending_items_only(table_items: List[Dict]) -> List[Dict]:
    """Return only items with status == 'pending' in chronological order."""
    pending = [it for it in table_items if it.get("status") == "pending"]
    pending.sort(key=lambda x: x["created_at"])
    return pending


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

        # classify_order now returns: {text, category, menu_id, menu_name, price, multiplier}
        classified = classify_order(payload.order_text)
        created_items = []
        for entry in classified:
            item = _make_item(
                entry["text"],
                payload.table,
                entry["category"],
                menu_id=entry.get("menu_id"),
                menu_name=entry.get("menu_name"),
                price=entry.get("price"),
                multiplier=entry.get("multiplier")
            )
            orders_by_table[payload.table].append(item)
            created_items.append(item)

        # Broadcast each new item to its station; include table meta in the message
        meta_for_table = _meta_for(payload.table)
        for item in created_items:
            msg = {"action": "new", "item": item, "meta": meta_for_table}
            # Route to appropriate station based on category
            if item["category"] == "grill":
                target_station = "grill"
            elif item["category"] == "drinks":
                target_station = "drinks"
            else:
                target_station = "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, msg))

        # Notify waiter clients about each new item & meta
        for item in created_items:
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": item, "meta": meta_for_table}))

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
        msg_meta = {"action": "meta_update", "table": table, "meta": table_meta[table]}

        # Broadcast meta update to all stations and waiter
        asyncio.create_task(broadcast_to_station("kitchen", msg_meta))
        asyncio.create_task(broadcast_to_station("grill", msg_meta))
        asyncio.create_task(broadcast_to_station("drinks", msg_meta))
        asyncio.create_task(broadcast_to_station("waiter", msg_meta))

        # classify new payload
        classified = classify_order(payload.order_text)

        new_items_created = []
        updated_items = []
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
                existing_item = existing_records[match_idx]["item"]

                # Check if the text actually changed (e.g., "2 μυθος" -> "3 μυθος")
                if existing_item["text"] != new_text:
                    # Update the existing item with new text and pricing
                    existing_item["text"] = new_text

                    # Only update pricing if new classification has a price
                    # Otherwise preserve existing pricing (important for unmatched items)
                    if entry.get("price") is not None:
                        existing_item["menu_name"] = entry.get("menu_name")
                        existing_item["qty"] = entry.get("multiplier", 1)
                        existing_item["unit_price"] = entry.get("price")
                        if entry.get("multiplier"):
                            existing_item["line_total"] = round(entry["price"] * entry["multiplier"], 2)
                        else:
                            existing_item["line_total"] = entry.get("price")
                    # If no new price but we have existing price, recalculate with new quantity
                    elif existing_item.get("unit_price") is not None and entry.get("multiplier"):
                        existing_item["qty"] = entry.get("multiplier", 1)
                        existing_item["line_total"] = round(existing_item["unit_price"] * entry["multiplier"], 2)

                    updated_items.append(existing_item)
                else:
                    kept_items.append(existing_item)
            else:
                item = _make_item(
                    new_text,
                    table,
                    new_cat,
                    menu_id=entry.get("menu_id"),
                    menu_name=entry.get("menu_name"),
                    price=entry.get("price"),
                    multiplier=entry.get("multiplier")
                )
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
            # Route to appropriate station based on category
            if it["category"] == "grill":
                target_station = "grill"
            elif it["category"] == "drinks":
                target_station = "drinks"
            else:
                target_station = "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, msg))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": _meta_for(table)}))

        # Broadcast updated items (quantity/text changed) to stations and waiter
        meta_for_table = _meta_for(table)
        for it in updated_items:
            # Route to appropriate station based on category
            if it["category"] == "grill":
                target_station = "grill"
            elif it["category"] == "drinks":
                target_station = "drinks"
            else:
                target_station = "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "update", "item": it, "meta": meta_for_table}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": meta_for_table}))

        # Broadcast new items (with meta) and notify waiter
        for it in new_items_created:
            # Route to appropriate station based on category
            if it["category"] == "grill":
                target_station = "grill"
            elif it["category"] == "drinks":
                target_station = "drinks"
            else:
                target_station = "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "new", "item": it, "meta": meta_for_table}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": meta_for_table}))

        # Broadcast update for remaining pending items (kept + new) so stations refresh table header
        remaining_pending = [it for it in orders_by_table.get(table, []) if it["status"] == "pending"]
        for it in remaining_pending:
            # Route to appropriate station based on category
            if it["category"] == "grill":
                target_station = "grill"
            elif it["category"] == "drinks":
                target_station = "drinks"
            else:
                target_station = "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "update", "item": it, "meta": meta_for_table}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": meta_for_table}))

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
                # Route to appropriate station based on category
                if it["category"] == "grill":
                    target_station = "grill"
                elif it["category"] == "drinks":
                    target_station = "drinks"
                else:
                    target_station = "kitchen"
                asyncio.create_task(broadcast_to_station(target_station, msg))
                # also notify waiter (so UI can update and show cancelled)
                asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": _meta_for(table)}))
                break
        if not found:
            raise HTTPException(status_code=404, detail="item not found or not pending")

        # If no pending items left, do NOT auto-clear meta here (waiter must finalize).
        pending_left = [x for x in orders_by_table.get(table, []) if x["status"] == "pending"]
        if not pending_left:
            # Inform clients that pending are gone (meta remains until waiter finalizes)
            meta_msg = {"action": "meta_update", "table": table, "meta": _meta_for(table)}
            asyncio.create_task(broadcast_to_station("waiter", meta_msg))
            asyncio.create_task(broadcast_to_station("kitchen", meta_msg))
            asyncio.create_task(broadcast_to_station("grill", meta_msg))
            asyncio.create_task(broadcast_to_station("drinks", meta_msg))

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
        asyncio.create_task(broadcast_to_all({"action": "update", "item": found, "meta": _meta_for(found_table)}))

        # also notify waiter: update & short notification
        asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": found, "meta": _meta_for(found_table)}))
        # Greek notification: e.g. "ετοιμα <text> τραπέζι <table>"
        try:
            note_text = f"ετοιμα {found.get('text','')} τραπέζι {found.get('table')}"
            asyncio.create_task(broadcast_to_station("waiter", {"action": "notify", "message": note_text, "id": str(uuid4())}))
        except Exception:
            pass

        # If no pending left, notify clients (meta remains until waiter finalizes)
        pending_left = [x for x in orders_by_table.get(found_table, []) if x.get("status") == "pending"]
        if not pending_left:
            meta_msg = {"action": "meta_update", "table": found_table, "meta": _meta_for(found_table)}
            asyncio.create_task(broadcast_to_station("waiter", meta_msg))
            asyncio.create_task(broadcast_to_station("kitchen", meta_msg))
            asyncio.create_task(broadcast_to_station("grill", meta_msg))
            asyncio.create_task(broadcast_to_station("drinks", meta_msg))

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
    Register a kitchen, grill, drinks or waiter websocket. The station will receive JSON messages of the form:
      { action: "new"|"delete"|"update", item: {...} } or {action:"delete", item_id: "..."}

    Waiter sockets may send:
      { action: "finalize_table", table: <int> }  -> finalize table (only allowed when no pending items)
    Stations may send:
      { action: "mark_done", item_id: "..." } to mark item as done
    """
    station = station.lower()
    if station not in ("kitchen", "grill", "drinks", "waiter"):
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
            # For kitchen/grill/drinks: send current pending items for that station in chronological order, attach meta to each item
            pending = []
            for table_items in orders_by_table.values():
                for it in table_items:
                    if it["status"] == "pending":
                        # Route items to appropriate station based on category
                        if station == "grill" and it["category"] == "grill":
                            item_copy = dict(it)
                            item_copy["meta"] = _meta_for(it["table"])
                            pending.append(item_copy)
                        elif station == "drinks" and it["category"] == "drinks":
                            item_copy = dict(it)
                            item_copy["meta"] = _meta_for(it["table"])
                            pending.append(item_copy)
                        elif station == "kitchen" and it["category"] not in ("grill", "drinks"):
                            item_copy = dict(it)
                            item_copy["meta"] = _meta_for(it["table"])
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

                # Ensure we have an int table id (websocket JSON may provide string/number)
                try:
                    table_to_finalize = int(table_to_finalize)
                except Exception:
                    await websocket.send_json({"action": "finalize_failed", "table": table_to_finalize, "reason": "invalid_table"})
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
                        pending_items = [dict(it, meta=_meta_for(it["table"])) for table_items in orders_by_table.values() for it in table_items if it["status"] == "pending"]
                        await websocket.send_json({"action": "init", "items": pending_items})
                        continue

                    # No pending items -> perform finalization: broadcast deletes and remove table & meta
                    items_to_remove = list(orders_by_table.get(table_to_finalize, []))
                    for it in items_to_remove:
                        # send delete to stations
                        msg = {"action": "delete", "item_id": it["id"], "table": table_to_finalize}
                        # Route to appropriate station based on category
                        if it["category"] == "grill":
                            target_station = "grill"
                        elif it["category"] == "drinks":
                            target_station = "drinks"
                        else:
                            target_station = "kitchen"
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
                        asyncio.create_task(broadcast_to_all({"action": "update", "item": found_item, "meta": _meta_for(found_table)}))

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
