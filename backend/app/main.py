# backend/app/main.py
import asyncio
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi.middleware.cors import CORSMiddleware
import re
import unicodedata
from uuid import uuid4 as _uuid4

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
def _normalize_text_for_match(s: str) -> str:
    """
    Normalize a dish line for matching:
    - lowercase
    - remove accents/diacritics
    - remove punctuation except letters/numbers/space
    - collapse whitespace
    """
    if not s:
        return ""
    # strip accents
    nfkd = unicodedata.normalize("NFD", str(s))
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    t = no_accents.strip().lower()
    # keep letters, digits and spaces (Greek letters included)
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _strip_accents(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _parse_qty_and_name(line_text: str) -> Tuple[float, str, Optional[float]]:
    """
    Parse leading quantity and detect weight tokens (kg, κ, g, γρ).
    Returns: (count_or_weight_number, parsed_name_without_leading_qty, weight_kg_or_None)

    Important: per rule, a number followed IMMEDIATELY (no space) by letters like "kg" or "κ" or "g"/"γρ"
    will be considered a weight. If there's a space between the number and letters ("2 kg" or "2 kg ...")
    we treat it as a plain count (2 portions).
    """
    if not line_text or not str(line_text).strip():
        return 1.0, "", None
    s = str(line_text).strip()

    # 1) Leading number immediately followed by unit (no space) -> weight
    # Examples matched: "1kgπαϊδάκια", "1kg παϊδάκια", "1κπαϊδάκια", "500gμπριζόλα", "500γρ μπριζόλα"
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)(kg|κ|κιλ|κιλό|g|γρ|gr)(?:\b)?\s*(.*)$", s, flags=re.IGNORECASE)
    if m:
        num_raw = m.group(1)
        unit = (m.group(2) or "").lower()
        rest = (m.group(3) or "").strip()
        num = float(num_raw.replace(",", ".")) if num_raw else 1.0
        if unit in ("kg", "κ", "κιλ", "κιλό"):
            # user gave kilos (e.g. "2κπαϊδάκια" or "2κ παϊδάκια")
            return num, rest or "", float(num)
        elif unit in ("g", "γρ", "gr"):
            # grams -> convert to kg; treat qty as 1 piece with weight
            return 1.0, rest or "", float(num) / 1000.0

    # 2) Trailing inline grams anywhere like "500g" or "500 γρ" (catch even with a space)
    m2 = re.search(r"(\d+(?:[.,]\d+)?)\s*(g|γρ|gr)\b", s, flags=re.IGNORECASE)
    if m2:
        grams = float(m2.group(1).replace(",", "."))
        kg = grams / 1000.0
        cleaned = re.sub(r"(\d+(?:[.,]\d+)?)\s*(g|γρ|gr)\b", " ", s, flags=re.IGNORECASE).strip()
        return 1.0, cleaned, kg

    # 3) Leading number with optional space but NO adjacent unit captured above -> treat as portions
    # Examples: "2 παιδάκια", "2 kg παιδάκια" -> here we treat as qty=2 (portions), not weight
    m3 = re.match(r"^\s*(\d+(?:[.,]\d+)?)(?:\b|\s+)(.*)$", s, flags=re.IGNORECASE)
    if m3:
        num_raw = m3.group(1)
        rest = (m3.group(2) or "").strip()
        num = float(num_raw.replace(",", ".")) if num_raw else 1.0
        # It's a plain count (no immediate unit attached)
        return float(num), rest or "", None

    # fallback: no leading number, simple text order -> qty 1
    return 1.0, s, None


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


def _score_strings(order_norm: str, menu_norm: str) -> float:
    """prefix-aware scoring between two normalized strings (same logic as frontends)."""
    if not order_norm or not menu_norm:
        return 0.0
    if menu_norm in order_norm or order_norm in menu_norm:
        return 1.0

    order_tokens = _tokenize(order_norm)
    menu_tokens = _tokenize(menu_norm) or [menu_norm]

    per_token_scores = []
    for ot in order_tokens or [order_norm]:
        best_tok = 0.0
        for mt in menu_tokens:
            if mt.startswith(ot) or ot.startswith(mt):
                best_tok = max(best_tok, 1.0)
                if best_tok == 1.0:
                    break
            else:
                maxl = max(len(ot), len(mt))
                if maxl == 0:
                    continue
                d = _levenshtein(ot, mt)
                tok_score = 1.0 - (d / maxl)
                if tok_score < 0:
                    tok_score = 0.0
                best_tok = max(best_tok, tok_score)
        per_token_scores.append(best_tok)

    token_match_score = (sum(per_token_scores) / len(per_token_scores)) if per_token_scores else 0.0

    maxlen = max(len(order_norm), len(menu_norm))
    full_ratio = 0.0
    if maxlen > 0:
        dist = _levenshtein(order_norm, menu_norm)
        full_ratio = 1.0 - (dist / maxlen)
        if full_ratio < 0:
            full_ratio = 0.0

    # prefix bonus
    common_pref = 0
    for a_ch, b_ch in zip(order_norm, menu_norm):
        if a_ch == b_ch:
            common_pref += 1
        else:
            break
    pref_bonus = (common_pref / maxlen) if maxlen > 0 else 0.0

    score = (0.65 * token_match_score) + (0.25 * full_ratio) + (0.10 * pref_bonus)
    return score


def _entry_is_kg(entry: Dict) -> bool:
    n = (entry.get("name") or "").lower()
    return bool(re.search(r"(^|\s)(kg|κ|κιλ|κιλο|κιλα|κιλ\.)", n))


def _find_menu_price_for_name(name: str, weight_kg: Optional[float]) -> Tuple[Optional[float], Optional[str], bool, Optional[str], Optional[float]]:
    """
    Given parsed name (name without leading qty) and optional weight_kg,
    fuzzy-match to MENU_ITEMS and return best candidate.

    Returns: (unit_price_or_None, matched_menu_id_or_None, is_kg_bool, matched_menu_name_or_None, matched_score_or_None)

    Rules:
     - Score all MENU_ITEMS and pick the best-scoring entry.
     - Special-case for 'παϊδάκια' family: if name contains 'παιδ'/'παϊδ', and weight_kg is not None
       -> forcibly look for kg-variant among paidakia items and pick best of those (if none, fall back).
       If weight_kg is None -> prefer portion (non-kg) paidakia candidates.
     - If weight_kg provided, bias toward kg entries; if not, penalize kg entries.
     - Return matched score for debugging.
    """
    if not name:
        return None, None, False, None, None

    order_norm = _normalize_text_for_match(name)
    if not order_norm:
        return None, None, False, None, None

    # Flatten MENU_ITEMS (dict id->entry) into list of entries, keep ids
    all_entries = []
    for mid, ent in MENU_ITEMS.items():
        e = dict(ent)
        e["id"] = mid
        all_entries.append(e)

    # detect paidakia family tokens
    order_no_tonos = order_norm.replace("ϊ", "ι").replace("ΐ", "ι")
    is_paidakia_order = "παιδ" in order_no_tonos or "παϊδ" in order_no_tonos

    # compute scores for all entries
    scored = []
    for e in all_entries:
        menu_name = e.get("name", "") or ""
        en = _normalize_text_for_match(menu_name)
        if not en:
            continue
        score = _score_strings(order_norm, en)

        # bias according to weight preference
        is_kg_name = _entry_is_kg(e)
        if weight_kg is not None:
            # user asked for weight -> boost kg entries
            if is_kg_name:
                score += 0.20
        else:
            # user didn't ask weight -> penalize kg entries slightly
            if is_kg_name:
                score -= 0.15

        # small prefix boost when menu starts with same token
        toks = _tokenize(order_norm)
        if toks:
            ot0 = toks[0]
            if en.startswith(ot0):
                score += 0.03

        scored.append((score, e))

    # If this is a paidakia order and weight_kg indicates weight, *restrict* to paidakia-kg candidates if any
    best_entry = None
    best_score = -1.0
    chosen_candidate_set = scored

    if is_paidakia_order:
        # build family-specific lists
        paidakia_candidates = [(s, e) for (s, e) in scored if ("παιδ" in _normalize_text_for_match(e.get("name","")) or "παϊδ" in _normalize_text_for_match(e.get("name","")))]
        if weight_kg is not None:
            # prefer kg named variants strictly: filter further by kg in menu name
            paid_kg = [(s, e) for (s, e) in paidakia_candidates if _entry_is_kg(e)]
            if paid_kg:
                chosen_candidate_set = paid_kg
            elif paidakia_candidates:
                # no explicit kg entry; fallback to family candidates (we'll rely on score)
                chosen_candidate_set = paidakia_candidates
        else:
            # weight not asked -> prefer non-kg paidakia entries (portions)
            paid_portions = [(s, e) for (s, e) in paidakia_candidates if not _entry_is_kg(e)]
            if paid_portions:
                chosen_candidate_set = paid_portions
            elif paidakia_candidates:
                chosen_candidate_set = paidakia_candidates
        # if family specific returned empty, we'll fall back to all entries (chosen_candidate_set remains scored)

    # pick best score among chosen_candidate_set (if empty, fallback to full scored)
    if not chosen_candidate_set:
        chosen_candidate_set = scored

    for score, e in chosen_candidate_set:
        if score > best_score:
            best_score = score
            best_entry = e
        elif abs(score - best_score) < 1e-9 and best_entry:
            # tie-breaker: prefer longer/more specific name
            if len(_normalize_text_for_match(e.get("name",""))) > len(_normalize_text_for_match(best_entry.get("name",""))):
                best_entry = e

    # threshold
    THRESH = 0.45
    if best_entry and best_score >= THRESH:
        price = best_entry.get("price")
        is_kg_flag = _entry_is_kg(best_entry)
        return (float(price) if price is not None else None, best_entry.get("id"), bool(is_kg_flag), best_entry.get("name"), float(best_score))
    return None, None, False, None, None


def _make_item(line_text: str, table: int, category: str) -> Dict:
    """Create a standardized item object for storage & messages.

    Now includes:
      - qty: parsed leading integer quantity (default 1)
      - weight_kg: when parsed as weight (e.g. leading "2kg..." or "2κ...")
      - unit_price: looked up from MENU_ITEMS when possible (None otherwise)
      - line_total: qty * unit_price (or computed from weight_kg * per-kg price)
      - name: parsed name without quantity prefix (for easier display/matching)
      - menu_id/menu_name: matched menu entry id/name when available
    """
    qty, parsed_name, parsed_weight = _parse_qty_and_name(line_text)
    unit_price, matched_id, is_kg_flag, matched_name, matched_score = _find_menu_price_for_name(parsed_name, parsed_weight)

    line_total = None

    # If we matched unit_price and have qty/weight, compute sensible line_total:
    try:
        if parsed_weight is not None:
            # weight-ordered: unit_price expected to be per-kg
            if unit_price is not None:
                line_total = round(float(unit_price) * float(parsed_weight), 2)
            # qty for weight items is set to 1 logically (we keep qty=1 but set weight_kg)
            qty_for_storage = 1
        else:
            # portion-ordered: qty * unit_price
            qty_for_storage = int(qty) if isinstance(qty, (int, float)) else qty
            if unit_price is not None:
                try:
                    line_total = round(float(unit_price) * float(qty_for_storage), 2)
                except Exception:
                    line_total = None
    except Exception:
        line_total = None
        qty_for_storage = qty

    # make item
    item = {
        "id": str(_uuid4()),
        "table": table,
        "text": line_text.strip(),
        "name": parsed_name,
        "qty": int(qty) if (isinstance(qty, (int, float)) and (float(qty).is_integer())) else qty,
        "weight_kg": parsed_weight if parsed_weight is not None else None,
        "unit_price": unit_price,  # float or None
        "line_total": line_total,  # float or None
        "menu_id": matched_id,
        "menu_name": matched_name,
        "category": category,  # 'kitchen'|'grill'|'drinks'
        "status": "pending",  # pending / done / cancelled
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    return item


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
    """Broadcast to kitchen, grill and waiter."""
    await broadcast_to_station("kitchen", message)
    await broadcast_to_station("grill", message)
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

        classified = classify_order(payload.order_text)  # returns list of {text, category}
        created_items = []
        for entry in classified:
            item = _make_item(entry["text"], payload.table, entry["category"])
            orders_by_table[payload.table].append(item)
            created_items.append(item)

        # Broadcast each new item to its station; include table meta in the message
        meta_for_table = _meta_for(payload.table)
        for item in created_items:
            msg = {"action": "new", "item": item, "meta": meta_for_table}
            target_station = "grill" if item["category"] == "grill" else "kitchen"
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
            best_score = 0.0
            for idx, rec in enumerate(existing_records):
                if not rec["used"] and rec["category"] == new_cat:
                    score = _score_strings(new_norm, rec["norm"])
                    if score > 0.95:  # consider it the same line
                        match_idx = idx
                        best_score = score
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
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": _meta_for(table)}))

        # Broadcast new items (with meta) and notify waiter
        meta_for_table = _meta_for(table)
        for it in new_items_created:
            target_station = "grill" if it["category"] == "grill" else "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "new", "item": it, "meta": meta_for_table}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": meta_for_table}))

        # Broadcast update for remaining pending items (kept + new) so stations refresh table header
        remaining_pending = [it for it in orders_by_table.get(table, []) if it["status"] == "pending"]
        for it in remaining_pending:
            target_station = "grill" if it["category"] == "grill" else "kitchen"
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
                target_station = "grill" if it["category"] == "grill" else "kitchen"
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
            asyncio.create_task(broadcast_to_station("waiter", {"action": "notify", "message": note_text, "id": str(_uuid4())}))
        except Exception:
            pass

        # If no pending left, notify clients (meta remains until waiter finalizes)
        pending_left = [x for x in orders_by_table.get(found_table, []) if x.get("status") == "pending"]
        if not pending_left:
            meta_msg = {"action": "meta_update", "table": found_table, "meta": _meta_for(found_table)}
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
                        asyncio.create_task(broadcast_to_all({"action": "update", "item": found_item, "meta": _meta_for(found_table)}))

                        # also notify waiter with short notification text
                        try:
                            note_text = f"ετοιμα {found_item.get('text','')} τραπέζι {found_item.get('table')}"
                            asyncio.create_task(broadcast_to_station("waiter", {"action": "notify", "message": note_text, "id": str(_uuid4())}))
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
