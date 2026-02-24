# backend/app/main.py
import asyncio
import os
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi.middleware.cors import CORSMiddleware
import re
import unicodedata
from sqlalchemy.orm import sessionmaker

from app.nlp import classify_order, MENU_ITEMS, build_override_rules  # Greek-capable classifier + menu lookup
from app.storage import Storage, InMemoryStorage, SQLiteStorage, SQLAlchemyStorage  # Storage abstraction
from app.api.menu_router import router as menu_router
from app.api.receipts_router import router as receipts_router
from app.api.nlp_router import router as nlp_router
from app.api.auth_router import router as auth_router
from app.api.users_router import router as users_router
from app.api.workstations_router import router as workstations_router
from app.db.dependencies import get_db_session
from app.db.models import NLPTrainingSample
from app.db import order_utils  # Helper functions for normalized Order/OrderItem domain
from app.utils.time_utils import iso_athens

app = FastAPI(title="Tavern Ordering Backend (MVP)")

# Allow CORS for local dev (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage backend based on environment variable
# Options: "inmemory", "sqlite" (legacy), "sqlalchemy" (normalized models)
storage_backend = os.getenv("STORAGE_BACKEND", "inmemory").lower()
print(f"[main] STORAGE_BACKEND environment variable: {os.getenv('STORAGE_BACKEND', 'NOT SET')}")
print(f"[main] Selected storage backend: {storage_backend}")

if storage_backend == "sqlalchemy":
    # Use normalized Order/OrderItem models
    restaurant_id = os.getenv("RESTAURANT_ID", "default")
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Construct database path: data/{restaurant_id}.db
    # Use forward slashes for SQLite URLs (works on all platforms)
    db_path = os.path.join(data_dir, f"{restaurant_id}.db").replace("\\", "/")
    db_url = f"sqlite:///{db_path}"
    
    print(f"[main] Initializing SQLAlchemy storage with: {db_url}")
    app.state.storage = SQLAlchemyStorage(db_url)
elif storage_backend == "sqlite":
    # Legacy SQLite storage (flat OrderModel)
    restaurant_id = os.getenv("RESTAURANT_ID", "default")
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Construct database path: data/{restaurant_id}.db
    # Use forward slashes for SQLite URLs (works on all platforms)
    db_path = os.path.join(data_dir, f"{restaurant_id}.db").replace("\\", "/")
    db_url = f"sqlite:///{db_path}"
    
    print(f"[main] Initializing SQLite storage with: {db_url}")
    app.state.storage = SQLiteStorage(db_url)
else:
    # Default to in-memory (inmemory or any unrecognized value)
    print(f"[main] Initializing InMemory storage (no persistence)")
    app.state.storage = InMemoryStorage()

print(f"[main] [OK] Storage backend initialized: {storage_backend}")



# ---------- Register API routers ----------
# Wire in the menu management router
app.include_router(menu_router)
# Wire in the receipts and history router
app.include_router(receipts_router)
# Wire in the NLP training router
app.include_router(nlp_router)
# Wire in the auth router
app.include_router(auth_router)
# Wire in the users router
app.include_router(users_router)
# Wire in the workstations router
app.include_router(workstations_router)


# ---------- Startup and Shutdown Events ----------
@app.on_event("startup")
async def startup_event():
    """Ensure storage is properly initialized on app startup."""
    # For SQLiteStorage, tables are created in __init__
    # For InMemoryStorage, no initialization needed
    
    # Seed menu if enabled
    seed_on_startup = os.getenv("SEED_MENU_ON_STARTUP", "false").lower() == "true"
    if seed_on_startup and isinstance(app.state.storage, SQLiteStorage):
        try:
            _seed_menu_on_startup()
        except Exception as e:
            print(f"Warning: Menu seeding failed: {e}")
            # Don't fail startup if seeding fails; log and continue


def _seed_menu_on_startup():
    """Seed menu from menu.json if SEED_MENU_ON_STARTUP is true."""
    import json
    from pathlib import Path
    from sqlalchemy.orm import sessionmaker
    from scripts.seed_menu import seed_menu
    
    # Find menu.json
    menu_file = Path(__file__).parent.parent / "data" / "menu.json"
    if not menu_file.exists():
        print(f"Warning: menu.json not found at {menu_file}, skipping menu seeding")
        return
    
    # Load menu
    with open(menu_file, 'r', encoding='utf-8') as f:
        menu_dict = json.load(f)
    
    # Get database session
    engine = app.state.storage.engine
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Seed menu
        stats = seed_menu(session, menu_dict, force=False)
        print(
            f"Menu seeding: Version {stats['version_id']}, "
            f"Created: {stats['items_created']}, Updated: {stats['items_updated']}"
        )
    finally:
        session.close()


@app.on_event("shutdown")
async def shutdown_event():
    """Properly dispose of resources on app shutdown."""
    # Gracefully close database connections if using SQLiteStorage
    if isinstance(app.state.storage, SQLiteStorage):
        try:
            app.state.storage.close()
        except Exception as e:
            # Log error but don't raise; allow shutdown to proceed
            print(f"Warning: Error closing SQLiteStorage: {e}")


# Keep websocket clients per station (dynamic + waiter)
station_connections: Dict[str, List[WebSocket]] = {"waiter": []}
lock = asyncio.Lock()  # ensure atomic updates when multiple requests come in


# ---------- Pydantic models ----------
class SubmitOrder(BaseModel):
    table: int
    order_text: str
    people: int = None      # optional number of people
    bread: bool = False     # wants bread?


# ---------- Dependency injection ----------
def get_storage() -> Storage:
    """Get the storage instance from app state."""
    return app.state.storage


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
        # When we have a menu match, use menu_name for display (cleaner name without quantity)
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

    # Ensure parsed_name doesn't have quantity prefix
    # If menu_name wasn't provided but we have classification, parse it from text
    if not menu_name and parsed_name == line_text:
        _, parsed_name = _parse_qty_and_name(line_text)

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
        "category": category,  # station category slug (e.g., 'kitchen', 'grill', 'drinks', or custom)
        "status": "pending",  # pending / done / cancelled
        "created_at": iso_athens(),
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
    """Broadcast to all connected stations (including waiter)."""
    for station in list(station_connections.keys()):
        await broadcast_to_station(station, message)


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


# Helper function to check if unclassified order lines match hidden items
def check_for_hidden_items_in_order(order_text: str, menu_dict: Dict[str, Any]) -> List[str]:
    """
    Check if order lines match hidden menu items, using fuzzy matching.
    This catches attempts to order items that have been hidden.
    
    Uses keyword-based fuzzy matching to handle variations like:
    - "κατσικι" matching "Κατσικάκι λεμονάτο" 
    - "2 Ντακος" matching "Ντάκος"
    
    Args:
        order_text: Raw user order text
        menu_dict: Full menu dictionary (including hidden items)
        
    Returns:
        List of hidden item names matched, or empty list if none
    """
    from app.nlp import _normalize_text_basic, _strip_accents
    
    hidden_items = []
    
    if not menu_dict or not order_text:
        return hidden_items
    
    # Parse order lines
    lines = [ln.strip() for ln in order_text.splitlines() if ln.strip()]
    
    # Build set of all hidden items
    hidden_items_list = []
    for section_items in menu_dict.values():
        if isinstance(section_items, list):
            for item in section_items:
                if isinstance(item, dict) and item.get("hidden") is True:
                    if item.get("name"):
                        hidden_items_list.append(item.get("name"))
                        print(f"[check_for_hidden_items] Found hidden item: {item.get('name')}")
    
    print(f"[check_for_hidden_items] Total hidden items: {len(hidden_items_list)}")
    print(f"[check_for_hidden_items] Order lines: {lines}")
    
    def normalize_and_tokenize(text):
        """Normalize text and return tokens (keywords)."""
        normalized = _normalize_text_basic(text).lower()
        no_accents = _strip_accents(normalized).lower()
        # Split into tokens and filter out single chars and numbers
        tokens = [t for t in no_accents.split() if len(t) > 1 and not t.isdigit()]
        return tokens
    
    def token_similarity(tokens1, tokens2):
        """
        Check if tokens from text1 have similar matches in text2.
        Returns True if any token from text1 is similar to any token in text2.
        """
        for t1 in tokens1:
            for t2 in tokens2:
                # Calculate Levenshtein distance
                dist = _levenshtein(t1, t2)
                # Consider match if distance is < 2 or similarity > 80%
                max_len = max(len(t1), len(t2))
                if max_len == 0:
                    continue
                similarity = 1 - (dist / max_len)
                if similarity > 0.75:  # 75% match threshold
                    print(f"[check_for_hidden_items]   Token match: '{t1}' ~ '{t2}' (sim={similarity:.2f})")
                    return True
        return False
    
    # For each order line, check if it matches any hidden item
    for line in lines:
        line_tokens = normalize_and_tokenize(line)
        
        if not line_tokens:
            continue
        
        for hidden_name in hidden_items_list:
            hidden_tokens = normalize_and_tokenize(hidden_name)
            
            # Check if line tokens are similar to hidden item tokens
            if token_similarity(line_tokens, hidden_tokens):
                if hidden_name not in hidden_items:
                    hidden_items.append(hidden_name)
                    print(f"[check_for_hidden_items] MATCH! '{line}' matches hidden item '{hidden_name}'")
    
    return hidden_items


# ---------- API Endpoints ----------
@app.post("/order/", summary="Submit a new order (table + free-text lines)")
async def submit_order(payload: SubmitOrder, storage: Storage = Depends(get_storage), db_session = Depends(get_db_session)):
    """
    Accept table number, multi-line order_text (one dish per line) and optional table metadata.
    Classify each line, store items, push them to the proper station(s), and save table meta.
    """
    async with lock:
        # save table-level metadata
        storage.set_table(payload.table, {"people": payload.people, "bread": bool(payload.bread)})

        # Get the full menu (including hidden items)
        from app.db.menu_access import get_latest_menu
        latest_menu = get_latest_menu(db_session)
        print(f"[submit_order] Menu loaded, db_session: {db_session}")
        
        # Check if order contains hidden items (before classification)
        hidden_items = check_for_hidden_items_in_order(payload.order_text, latest_menu)
        if hidden_items:
            print(f"[submit_order] Hidden items found: {hidden_items}")
            raise HTTPException(
                status_code=400,
                detail={"error": "Order contains unavailable items", "hidden_items": hidden_items}
            )

        # Build NLP override rules from corrections (latest per raw text)
        override_rules = {}
        if db_session:
            try:
                samples = (
                    db_session.query(NLPTrainingSample)
                    .filter(NLPTrainingSample.corrected_menu_item_id.isnot(None))
                    .order_by(NLPTrainingSample.created_at.desc())
                    .all()
                )
                override_rules = build_override_rules(samples, latest_menu)
            except Exception as e:
                print(f"[submit_order] Failed to load NLP override rules: {e}")

        # classify_order now returns: {text, category, menu_id, menu_name, price, multiplier}
        classified = classify_order(payload.order_text, override_rules=override_rules)
        
        # Check for unclassified items (items that couldn't be matched to menu)
        unclassified_items = [item["text"] for item in classified if item.get("menu_name") is None]
        if unclassified_items:
            print(f"[submit_order] Unclassified items found: {unclassified_items}")
            raise HTTPException(
                status_code=400,
                detail={"error": "Order contains unidentified items", "unclassified_items": unclassified_items}
            )
        
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
            storage.add_order(payload.table, item)
            created_items.append(item)

        # Broadcast each new item to its station; include table meta in the message
        meta_for_table = storage.get_table(payload.table)
        for item in created_items:
            msg = {"action": "new", "item": item, "meta": meta_for_table}
            # Route to station based on category slug
            target_station = item.get("category") or "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, msg))

        # Notify waiter clients about each new item & meta
        for item in created_items:
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": item, "meta": meta_for_table}))

    return {"status": "ok", "created": created_items}


@app.post("/order/preview", summary="Preview order classification without sending")
async def preview_order(payload: SubmitOrder, db_session = Depends(get_db_session)):
    """
    Preview classification results without creating items or broadcasting.
    Returns classification along with hidden/unclassified lists for confirmation UI.
    """
    # Get the full menu (including hidden items)
    from app.db.menu_access import get_latest_menu
    latest_menu = get_latest_menu(db_session)

    # Build NLP override rules from corrections (latest per raw text)
    override_rules = {}
    if db_session:
        try:
            samples = (
                db_session.query(NLPTrainingSample)
                .filter(NLPTrainingSample.corrected_menu_item_id.isnot(None))
                .order_by(NLPTrainingSample.created_at.desc())
                .all()
            )
            override_rules = build_override_rules(samples, latest_menu)
        except Exception as e:
            print(f"[preview_order] Failed to load NLP override rules: {e}")

    classified = classify_order(payload.order_text, override_rules=override_rules)

    hidden_items = check_for_hidden_items_in_order(payload.order_text, latest_menu)
    unclassified_items = [item["text"] for item in classified if item.get("menu_name") is None]

    return {
        "classified": classified,
        "hidden_items": hidden_items,
        "unclassified_items": unclassified_items
    }


@app.get("/table_meta/{table}")
async def get_table_meta(table: int, storage: Storage = Depends(get_storage)):
    return storage.get_table(table)


@app.get("/orders/", summary="List all tables and their current orders")
async def list_orders(include_history: bool = Query(False, description="If true return full history including cancelled/done"), storage: Storage = Depends(get_storage)):
    """
    Return all orders grouped by table.
    By default (include_history=false) return only pending items for each table.
    If include_history=true return the full list (pending/done/cancelled) per table.
    """
    if include_history:
        tables = storage.list_tables()
        return {str(table): storage.get_orders(table) for table in tables}
    else:
        # return only pending items to keep frontend clean
        tables = storage.list_tables()
        return {str(table): _pending_items_only(storage.get_orders(table)) for table in tables}


@app.put("/order/{table}", summary="Replace/Update the active order for a table")
async def replace_table_order(table: int, payload: SubmitOrder, storage: Storage = Depends(get_storage), db_session = Depends(get_db_session)):
    """
    Smarter replace: only replace the changed lines.
    - Reuse pending items that match (normalized text + category) to avoid duplication.
    - Cancel unmatched old pending items.
    - Create new items for unmatched new lines.
    
    For SQLAlchemyStorage, uses order_utils.replace_table_orders() which handles DB persistence properly.
    For other storage backends (InMemoryStorage, SQLiteStorage), uses the original in-memory matching logic.
    """
    async with lock:
        # Save table meta
        storage.set_table(table, {"people": payload.people, "bread": bool(payload.bread)})
        msg_meta = {"action": "meta_update", "table": table, "meta": storage.get_table(table)}

        # Broadcast meta update to all stations and waiter
        asyncio.create_task(broadcast_to_all(msg_meta))

        # Get full menu and check for hidden items
        from app.db.menu_access import get_latest_menu
        latest_menu = get_latest_menu(db_session)

        # Classify new payload with NLP override rules
        override_rules = {}
        if db_session:
            try:
                samples = (
                    db_session.query(NLPTrainingSample)
                    .filter(NLPTrainingSample.corrected_menu_item_id.isnot(None))
                    .order_by(NLPTrainingSample.created_at.desc())
                    .all()
                )
                override_rules = build_override_rules(samples, latest_menu)
            except Exception as e:
                print(f"[replace_table_order] Failed to load NLP override rules: {e}")

        classified = classify_order(payload.order_text, override_rules=override_rules)
        hidden_items = check_for_hidden_items_in_order(payload.order_text, latest_menu)
        
        if hidden_items:
            raise HTTPException(
                status_code=400,
                detail={"error": "Order contains unavailable items", "hidden_items": hidden_items}
            )
        
        # Check for unclassified items
        unclassified_items = [item["text"] for item in classified if item.get("menu_name") is None]
        if unclassified_items:
            print(f"[replace_table_order] Unclassified items found: {unclassified_items}")
            raise HTTPException(
                status_code=400,
                detail={"error": "Order contains unidentified items", "unclassified_items": unclassified_items}
            )

        # Use different logic based on storage backend
        if isinstance(storage, SQLAlchemyStorage):
            # For normalized storage, use order_utils helper which handles DB persistence
            SessionLocal = sessionmaker(bind=storage.engine)
            session = SessionLocal()
            try:
                result = order_utils.replace_table_orders(
                    session=session,
                    table_label=str(table),
                    new_classified_items=classified,
                    created_by_user_id=None  # TODO: Add user context when authentication is implemented
                )
                session.commit()
                
                new_items_created = result["new"]
                updated_items = result["updated"]
                kept_items = result["kept"]
                cancelled_items = result["cancelled"]
            finally:
                session.close()
        else:
            # For other storage (InMemoryStorage, SQLiteStorage), use original in-memory logic
            all_items = storage.get_orders(table)
            existing_pending = [it for it in all_items if it["status"] == "pending"]
            existing_records = []
            for it in existing_pending:
                existing_records.append({
                    "item": it,
                    "norm": _normalize_text_for_match(it.get("text", "")),
                    "category": it.get("category"),
                    "used": False
                })

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
                    storage.add_order(table, item)
                    new_items_created.append(item)

            # Cancel unmatched old pending items
            cancelled_items = []
            for rec in existing_records:
                if not rec["used"]:
                    # For InMemoryStorage, in-place modification works
                    # For SQLiteStorage, we need to call update_order_status
                    storage.update_order_status(table, rec["item"]["id"], "cancelled")
                    rec["item"]["status"] = "cancelled"
                    cancelled_items.append(rec["item"])

        # Broadcast deletes for cancelled items and notify waiter
        for it in cancelled_items:
            msg = {"action": "delete", "item_id": it["id"], "table": table}
            target_station = it.get("category") or "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, msg))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": storage.get_table(table)}))

        # Broadcast updated items (quantity/text changed) to stations and waiter
        meta_for_table = storage.get_table(table)
        for it in updated_items:
            target_station = it.get("category") or "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "update", "item": it, "meta": meta_for_table}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": meta_for_table}))

        # Broadcast new items (with meta) and notify waiter
        for it in new_items_created:
            target_station = it.get("category") or "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "new", "item": it, "meta": meta_for_table}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": meta_for_table}))

        # Broadcast update for remaining pending items (kept + new) so stations refresh table header
        remaining_pending = [it for it in storage.get_orders(table) if it["status"] == "pending"]
        for it in remaining_pending:
            target_station = it.get("category") or "kitchen"
            asyncio.create_task(broadcast_to_station(target_station, {"action": "update", "item": it, "meta": meta_for_table}))
            asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": it, "meta": meta_for_table}))

    return {"status": "ok", "replaced_count": len(new_items_created), "kept_count": len(kept_items), "cancelled_count": len(cancelled_items)}


@app.delete("/order/{table}/{item_id}", summary="Cancel a specific item from a table's order")
async def cancel_item(table: int, item_id: str, storage: Storage = Depends(get_storage)):
    """
    Mark item as cancelled (if found) and notify stations to remove it.
    """
    async with lock:
        # Find the item and mark it as cancelled
        item = storage.get_order_by_id(table, item_id)
        if item is None or item["status"] != "pending":
            raise HTTPException(status_code=404, detail="item not found or not pending")
        
        storage.update_order_status(table, item_id, "cancelled")
        
        msg = {"action": "delete", "item_id": item_id, "table": table}
        target_station = item.get("category") or "kitchen"
        asyncio.create_task(broadcast_to_station(target_station, msg))
        # also notify waiter (so UI can update and show cancelled)
        asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": item, "meta": storage.get_table(table)}))

        # If no pending items left, do NOT auto-clear meta here (waiter must finalize).
        pending_left = [x for x in storage.get_orders(table) if x["status"] == "pending"]
        if not pending_left:
            # Inform clients that pending are gone (meta remains until waiter finalizes)
            meta_msg = {"action": "meta_update", "table": table, "meta": storage.get_table(table)}
            asyncio.create_task(broadcast_to_all(meta_msg))

    return {"status": "ok", "cancelled": item_id}


@app.post("/item/{item_id}/done", summary="Mark an item as done (from station via HTTP)")
async def mark_item_done(item_id: str, storage: Storage = Depends(get_storage)):
    """Mark item done and broadcast update so UIs refresh status."""
    async with lock:
        # Find the item in any table
        found_item = None
        found_table = None
        for table in storage.list_tables():
            item = storage.get_order_by_id(table, item_id)
            if item and item["status"] == "pending":
                found_item = item
                found_table = table
                break
        
        if not found_item:
            raise HTTPException(status_code=404, detail="item not found or not pending")

        storage.update_order_status(found_table, item_id, "done")

        # notify all stations about status change
        asyncio.create_task(broadcast_to_all({"action": "update", "item": found_item, "meta": storage.get_table(found_table)}))

        # also notify waiter: update & short notification
        asyncio.create_task(broadcast_to_station("waiter", {"action": "update", "item": found_item, "meta": storage.get_table(found_table)}))
        # Greek notification: e.g. "ετοιμα <text> τραπέζι <table>"
        try:
            note_text = f"ετοιμα {found_item.get('text','')} τραπέζι {found_item.get('table')}"
            asyncio.create_task(broadcast_to_station("waiter", {"action": "notify", "message": note_text, "id": str(uuid4())}))
        except Exception:
            pass

        # If no pending left, notify clients (meta remains until waiter finalizes)
        pending_left = [x for x in storage.get_orders(found_table) if x.get("status") == "pending"]
        if not pending_left:
            meta_msg = {"action": "meta_update", "table": found_table, "meta": storage.get_table(found_table)}
            asyncio.create_task(broadcast_to_all(meta_msg))

    return {"status": "ok", "item": found_item}


# ---------- History endpoints for receipts ----------
# ===== HISTORY ENDPOINTS MOVED TO receipts_router =====
# These endpoints are now handled by app/api/receipts_router.py
# The receipts_router is included above with app.include_router(receipts_router)
# and provides the same /api/orders/history and /api/orders/history/{receipt_id} routes

# @app.get("/api/orders/history", summary="Get order history (closed sessions)")
# async def get_order_history(...):
#     ...

# @app.get("/api/orders/history/{session_id}", summary="Get a specific receipt by session ID")
# async def get_receipt(...):
#     ...


# ---------- Optional maintenance: purge endpoint ----------
@app.post("/purge_done", summary="Permanently remove done/cancelled items (optional maintenance)")
async def purge_done(older_than_seconds: int = 0, storage: Storage = Depends(get_storage)):
    async with lock:
        removed = 0
        for table in storage.list_tables():
            removed += storage.purge_done_orders(table, older_than_seconds)
    return {"status": "ok", "removed": removed}


# ---------- WebSocket endpoints for stations & waiter ----------
@app.websocket("/ws/{station}")
async def station_ws(websocket: WebSocket, station: str):
    """
    Register a station or waiter websocket. The station will receive JSON messages of the form:
      { action: "new"|"delete"|"update", item: {...} } or {action:"delete", item_id: "..."}

    Waiter sockets may send:
      { action: "finalize_table", table: <int> }  -> finalize table (only allowed when no pending items)
    Stations may send:
      { action: "mark_done", item_id: "..." } to mark item as done
    """
    station = station.lower()
    if not station:
        await websocket.close(code=4001)
        return
    
    await websocket.accept()
    station_connections.setdefault(station, []).append(websocket)
    storage = get_storage()

    try:
        # When a station connects, send an initialization message:
        if station == "waiter":
            # waiter wants the full view (include_history=true) — send full orders and meta
            orders_snapshot = {}
            for table_id in storage.list_tables():
                orders_snapshot[str(table_id)] = storage.get_orders(table_id)
            
            meta_snapshot = {}
            for table_id in storage.list_tables():
                meta_snapshot[str(table_id)] = storage.get_table(table_id)
            
            await websocket.send_json({"action": "init", "orders": orders_snapshot, "meta": meta_snapshot})
        else:
            # For stations: send current pending items for that station in chronological order, attach meta to each item
            pending = []
            for table_id in storage.list_tables():
                table_items = storage.get_orders(table_id)
                for it in table_items:
                    if it["status"] == "pending" and it.get("category") == station:
                        item_copy = dict(it)
                        item_copy["meta"] = storage.get_table(it["table"])
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
                    if not storage.table_exists(table_to_finalize):
                        print(f"[finalize_table] Table {table_to_finalize} not found")
                        await websocket.send_json({"action": "finalize_failed", "table": table_to_finalize, "reason": "table_not_found"})
                        continue

                    # Check pending items for this table
                    all_items = storage.get_orders(table_to_finalize)
                    print(f"[finalize_table] Table {table_to_finalize} has {len(all_items)} items total")
                    for idx, item in enumerate(all_items):
                        print(f"[finalize_table]   Item {idx}: id={item.get('id')}, status={item.get('status')}, text={item.get('text', '')[:50]}")
                    pending_left = [x for x in all_items if x.get("status") == "pending"]
                    print(f"[finalize_table] Table {table_to_finalize} has {len(pending_left)} pending items")
                    
                    if pending_left:
                        # refuse finalize, include number of pending items
                        print(f"[finalize_table] REJECTED - {len(pending_left)} pending items remain")
                        await websocket.send_json({"action": "finalize_failed", "table": table_to_finalize, "pending": len(pending_left), "reason": "items_pending"})
                        # also send an updated set of pending items back so waiter UI can refresh
                        pending_items = []
                        for tbl_id in storage.list_tables():
                            for it in storage.get_orders(tbl_id):
                                if it["status"] == "pending":
                                    pending_items.append(dict(it, meta=storage.get_table(it["table"])))
                        await websocket.send_json({"action": "init", "items": pending_items})
                        continue

                    # No pending items -> perform finalization: broadcast deletes and remove table & meta
                    print(f"[finalize_table] SUCCESS - Finalizing table {table_to_finalize}")
                    items_to_remove = list(storage.get_orders(table_to_finalize))
                    for it in items_to_remove:
                        # send delete to stations
                        msg = {"action": "delete", "item_id": it["id"], "table": table_to_finalize}
                        # Route to appropriate station based on category slug
                        target_station = it.get("category") or "kitchen"
                        asyncio.create_task(broadcast_to_station(target_station, msg))
                        # notify waiters as well
                        asyncio.create_task(broadcast_to_station("waiter", msg))

                    # remove the table from storage & meta, get the receipt_id
                    receipt_id = storage.delete_table(table_to_finalize)
                    print(f"[finalize_table] Closed table and created receipt_id: {receipt_id}, type: {type(receipt_id)}")

                    # broadcast table_finalized to everyone so UIs remove any remaining traces
                    tf_msg = {"action": "table_finalized", "table": table_to_finalize, "receipt_id": receipt_id}
                    print(f"[finalize_table] Broadcasting table_finalized: {tf_msg}")
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

            # ---------- Station action: mark_done ----------
            if data.get("action") == "mark_done" and "item_id" in data:
                item_id = data["item_id"]
                async with lock:
                    found_item = None
                    found_table = None
                    # Search all tables for the item
                    for table_id in storage.list_tables():
                        item = storage.get_order_by_id(table_id, item_id)
                        if item and item["status"] == "pending":
                            storage.update_order_status(table_id, item_id, "done")
                            found_item = item
                            found_table = table_id
                            break
                    
                    if found_item:
                        # broadcast update (include meta for convenience)
                        asyncio.create_task(broadcast_to_all({"action": "update", "item": found_item, "meta": storage.get_table(found_table)}))

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
        print(f"[WebSocket] {station} disconnected normally")
        if websocket in station_connections.get(station, []):
            station_connections[station].remove(websocket)
    except Exception as e:
        # on any other error clean up
        print(f"[WebSocket] ERROR in {station} connection: {e}")
        import traceback
        traceback.print_exc()
        if websocket in station_connections.get(station, []):
            station_connections[station].remove(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
