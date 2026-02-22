#Persistent Menu Versioning & Idempotent Seeding

## Deliverables Summary

### 1. ✅ Menu Utility Helpers
**File**: [app/db/menu_utils.py](app/db/menu_utils.py) (142 lines)

**Functions**:
- `hash_menu_json()`: Deterministic SHA256 hash of menu for detecting changes
- `menu_version_exists()`: Check if identical menu version already exists (idempotency)
- `normalize_item_name()`: Normalize names for matching/deduplication
- `upsert_menu_item()`: Create or update menu item by external_id or name
- `create_menu_version()`: Create new MenuVersion with JSON blob snapshot

**Key Features**:
- Price converted from decimal to cents (int) for accuracy
- External_id matching for tracking items across versions
- Fallback to normalized name if no external_id
- Handles both new items and updates properly

### 2. ✅ Seed Script
**File**: [scripts/seed_menu.py](scripts/seed_menu.py) (200 lines)

**Usage**:
```bash
# Seed from menu.json
python -m scripts.seed_menu

# With options
python -m scripts.seed_menu --menu-file custom_menu.json --user-id 42 --database-url sqlite:///tavern.db

# Force new version ignoring duplicates
python -m scripts.seed_menu --force
```

**Features**:
- Reads menu.json from flexibly located paths
- Creates MenuVersion with full JSON snapshot
- Creates MenuItem records from flattened menu structure
- Detects and skips identical versions (idempotent)
- Creates new version when JSON changes
- Tracks created_by_user_id for audit trail
- Command-line interface with clear error messages
- Clean result reporting with statistics

**Idempotency Logic**:
```
Run 1: menu.json → hash matches nothing → CREATE MenuVersion + MenuItems
Run 2: menu.json → hash matches current → SKIP (idempotent)
Run 3: menu.json (modified) → hash differs → CREATE new MenuVersion + update Items
Run 4: menu.json (same as Run 3) → hash matches → SKIP (idempotent)
```

### 3. ✅ Startup Hook
**File**: [app/main.py](app/main.py) (lines 50-99)

**Features**:
- Added `_seed_menu_on_startup()` function
- Only runs if `SEED_MENU_ON_STARTUP=true` environment variable set
- Only for SQLiteStorage (not InMemoryStorage)
- Gracefully handles failures without crashing startup
- Logs seeding results (version ID, items created/updated)

**Integration**:
```python
@app.on_event("startup")
async def startup_event():
    # ... existing code ...
    if seed_on_startup and isinstance(app.state.storage, SQLiteStorage):
        try:
            _seed_menu_on_startup()
        except Exception as e:
            print(f"Warning: Menu seeding failed: {e}")
```

### 4. ✅ Database Model Fixes
**File**: [app/db/models.py](app/db/models.py)

**Changes**:
- Fixed menu_items.metadata → menu_items.extra_data (SQLAlchemy reserved word)
- Fixed NLPTrainingSample relationships:
  - Removed problematic back_populates (ambiguous FK paths)
  - Added explicit foreign_keys specification
  - Added corrected_item relationship for corrected_menu_item_id
- Now supports multiple FK paths to MenuItem

**Note**: MenuItem still accessible from NLPTrainingSample via predicted_item and corrected_item relationships, just not bidirectional back_populates.

### 5. ✅ Comprehensive Test Suite
**File**: [tests/test_seed_menu.py](tests/test_seed_menu.py) (394 lines)

**19 Tests Organized in 5 Classes**:

#### TestMenuUtilities (6 tests)
- ✅ `test_hash_menu_json_deterministic`: Hash consistency
- ✅ `test_hash_menu_json_changes_with_content`: Hash changes on modification
- ✅ `test_normalize_item_name`: Name normalization
- ✅ `test_menu_version_exists_returns_none_when_empty`: Empty DB check
- ✅ `test_menu_version_exists_returns_version_when_identical`: Finds duplicates
- ✅ `test_menu_version_exists_returns_none_when_different`: Detects changes

#### TestUpsertMenuItem (3 tests)
- ✅ `test_upsert_menu_item_creates_new`: Create functionality
- ✅ `test_upsert_menu_item_updates_by_external_id`: Update by ID
- ✅ `test_upsert_menu_item_price_conversion`: Price to cents conversion

#### TestSeedMenu (5 tests)
- ✅ `test_seed_menu_creates_version_and_items`: Full seeding
- ✅ `test_seed_menu_idempotent_same_json`: Idempotency verification
- ✅ `test_seed_menu_creates_new_version_on_change`: Version on change
- ✅ `test_seed_menu_force_flag`: Force flag override
- ✅ `test_seed_menu_with_user_id`: Audit trail tracking

#### TestSeedMenuIntegration (2 tests)
- ✅ `test_load_actual_menu_json`: Load real menu.json
- ✅ `test_seed_actual_menu`: Seed real menu (66 items)

#### TestEdgeCases (3 tests)
- ✅ `test_upsert_item_without_external_id`: Handles missing IDs
- ✅ `test_seed_empty_menu`: Handles empty menus
- ✅ `test_seed_menu_with_special_characters`: Unicode/special chars

**All 19 tests PASS** ✅

## Test Results

```
$ pytest tests/test_seed_menu.py -v
19 passed in 2.40s
```

Real menu seeding test:
```
Loaded: 10 categories
Created: 66 menu items
MenuVersion: 1
```

Idempotency verification:
```
Run 1: Version Created=True, ID=1, Items=66
Run 2: Version Created=False, ID=1 (skipped - identical)
```

## Usage Examples

### Programmatic Usage
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scripts.seed_menu import seed_menu, load_menu_json

engine = create_engine ("sqlite:///tavern.db")
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# Load and seed
menu = load_menu_json("data/menu.json")
stats = seed_menu(session, menu, force=False, created_by_user_id=None)

print(f"Version: {stats['version_id']}")
print(f"New: {stats['items_created']}, Updated: {stats['items_updated']}")
```

### Command Line Usage
```bash
# Basic seeding
python -m scripts.seed_menu

# With custom menu file
python -m scripts.seed_menu --menu-file custom/menu.json

# With user tracking
python -m scripts.seed_menu --user-id 42

# Force new version
python -m scripts.seed_menu --force

# Custom database
python -m scripts.seed_menu --database-url postgresql://owner:password@localhost/tavern
```

### Startup Auto-Seeding
```bash
# Enable auto-seeding on app startup
SEED_MENU_ON_STARTUP=true python -m app.main

# Or in .env
SEED_MENU_ON_STARTUP=true
STORAGE_BACKEND=sqlite
```

## Database Schema

### MenuVersion Table
```
id (PK)
created_at (indexed, auto-timestamp)
created_by_user_id (FK to users, indexed, nullable)
json_blob (JSON column - full menu snapshot)
```

### MenuItem Table
```
id (PK)
menu_version_id (FK to menu_versions, indexed)
external_id (VARCHAR 255, indexed, nullable) - for tracking across versions
name (VARCHAR 255)
price (INTEGER as cents)
category (VARCHAR 100, indexed) - kitchen, grill, drinks, etc.
station (VARCHAR 100) - destination kitchen
extra_data (JSON, nullable) - allergens, prep_time, etc.
```

## Key Design Decisions

1. **Price Storage as Cents**: All prices stored as `INTEGER * 100` to avoid floating-point precision issues
2. **JSON Snapshot**: Full menu structure stored in MenuVersion.json_blob for audit trail and version comparison
3. **Idempotent by Design**: Hash-based detection prevents duplicate versions on repeated runs
4. **Flexible ID Matching**: Supports external_id (preferred) and normalized name fallback
5. **Optional Startup Hook**: Seeding only on explicit opt-in (`SEED_MENU_ON_STARTUP=true`) for safety
6. **Relationship Direction**: NLPTrainingSample → MenuItem (two FK paths handled explicitly)

## Verification Checklist

- ✅ Menu utilities created (hash, exists, normalize, upsert, create_version)
- ✅ Seed script created with CLI interface
- ✅ Startup hook integrated (optional via env var)
- ✅ Idempotency verified (run twice = no duplicate versions)
- ✅ Version tracking works (JSON change = new version)
- ✅ Price conversion to cents working
- ✅ External_id matching works
- ✅ Real menu.json seeding successful (66 items)
- ✅ All 19 tests pass
- ✅ Model relationship fixes applied
- ✅ Backward compatibility maintained (no breaking changes to existing tests)

## Files Modified

1. **Created**: [app/db/menu_utils.py](app/db/menu_utils.py) - Menu utility functions (142 lines)
2. **Created**: [scripts/seed_menu.py](scripts/seed_menu.py) - Seed script (200 lines)
3. **Created**: [scripts/__init__.py](scripts/__init__.py) - Package marker
4. **Created**: [tests/test_seed_menu.py](tests/test_seed_menu.py) - Test suite (394 lines)
5. **Modified**: [app/main.py](app/main.py) - Added startup hook (50 lines added)
6. **Modified**: [app/db/models.py](app/db/models.py) - Fixed relationships and reserved word

## Next Steps (Beyond This Phase)

1. **Menu API Endpoints**: Add REST endpoints to GET current MenuVersion, query MenuItems
2. **Menu History**: Query past MenuVersions for audit trail
3. **Menu Updates**: API to update menu items and create new versions
4. **Menu Search**: Full-text search of menu by name/category
5. **Analytics**: Track which items are most ordered
6. **Sync**: Sync menu with external sources (POS systems, suppliers)

---

**Summary**: Idempotent menu seeding system is production-ready with comprehensive testing, flexible deployment options, and full audit trail support.
