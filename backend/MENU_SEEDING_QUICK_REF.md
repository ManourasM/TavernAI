# Menu Seeding - Quick Reference

## What Was Built

### 1. Menu Utility Functions (`app/db/menu_utils.py`)
- `hash_menu_json()` - Detect menu changes
- `menu_version_exists()` - Check for duplicates (idempotency)
- `normalize_item_name()` - Name matching
- `upsert_menu_item()` - Create/update items
- `create_menu_version()` - Create version snapshots

### 2. Seed Script (`scripts/seed_menu.py`)
- Reads menu.json
- Creates MenuVersion with JSON snapshot
- Creates/updates MenuItems from menu structure
- Detects and skips identical versions (idempotent)
- Command-line interface with statistics

### 3. Startup Hook (`app/main.py`)
- Auto-seed on startup when `SEED_MENU_ON_STARTUP=true`
- Only for SQLiteStorage
- Graceful error handling (doesn't crash startup)

### 4. Test Suite (`tests/test_seed_menu.py`)
- 19 comprehensive tests covering:
  - Hash functions (3 tests)
  - Upsert logic (3 tests)
  - Seed idempotency (5 tests)
  - Real menu.json integration (2 tests)
  - Edge cases (3 tests)
- All 19 tests PASS ✅

## Quick Commands

```bash
# Seed from command line
python -m scripts.seed_menu

# Force new version
python -m scripts.seed_menu --force

# With custom menu
python -m scripts.seed_menu --menu-file custom_menu.json

# With user ID (audit trail)
python -m scripts.seed_menu --user-id 42

# Run tests
pytest tests/test_seed_menu.py -v
```

## Environment Variables

```bash
# Auto-seed on app startup
SEED_MENU_ON_STARTUP=true

# Custom database
APP_DATABASE_URL=sqlite:///tavern.db

# Storage backend
STORAGE_BACKEND=sqlite
```

## How It Works

**Idempotency**: 
```
Hash menu.json
├─ Hash matches existing version? → Skip (idempotent)
└─ Hash differs? → Create new MenuVersion + update MenuItems
```

**Storage**:
```
MenuVersion
├─ Stores full JSON snapshot of menu
├─ Timestamp (created_at)
└─ User ID (created_by_user_id, nullable)

MenuItem (per MenuVersion)
├─ external_id (for tracking across versions)
├─ name, price (as cents), category, station
└─ extra_data (JSON for allergens, etc.)
```

## Test Results

```
Menu utilities:     6 tests ✅
Upsert functions:   3 tests ✅  
Seed idempotency:   5 tests ✅
Real menu integration: 2 tests ✅ (66 items seeded)
Edge cases:         3 tests ✅

Total: 19 tests PASSED
Migration tests:    6 tests PASSED (from Prompt 2)
Overall: 25 tests PASSED ✅
```

## Files Changed

**Created** (3 files, 736 lines):
- `app/db/menu_utils.py` - Utility functions (142 lines)
- `scripts/seed_menu.py` - Seed script (200 lines)
- `tests/test_seed_menu.py` - Test suite (394 lines)

**Modified** (3 files):
- `app/main.py` - Added startup hook (50 lines)
- `app/db/models.py` - Fixed relationships (2 changes)
- `scripts/__init__.py` - Package marker

## Key Features

✅ **Idempotent**: Run multiple times safely, no duplicates  
✅ **Versioned**: Full audit trail with timestamps and user IDs  
✅ **Flexible**: Command-line or programmatic usage  
✅ **Tested**: 19 tests covering normal + edge cases  
✅ **Production-safe**: Graceful error handling  
✅ **Real menu**: Tested with actual menu.json (66 items)  
✅ **Special chars**: Unicode/internationalization support  

## Example Output

```bash
$ python -m scripts.seed_menu

2026-02-22 15:34:04,859 - INFO - Loaded menu from data/menu.json with 10 categories
2026-02-22 15:34:10,480 - INFO - Created new MenuVersion (ID: 1)
2026-02-22 15:34:10,574 - INFO - Processed 66 items: 66 created, 0 updated
2026-02-22 15:34:10,708 - INFO - MenuVersion 1 committed successfully

============================================================
SEED RESULTS
============================================================
Version ID:       1
Version Created:  True
Items Created:    66
Items Updated:    0
============================================================

$ python -m scripts.seed_menu  # Run again - idempotent

2026-02-22 15:34:17,287 - INFO - Identical menu version already exists (ID: 1).
Skipping (idempotent). Use --force to override.

Version ID:       1
Version Created:  False
Items Created:    0
Items Updated:    0
```

## Database State After Seeding

```sql
SELECT COUNT(*) FROM menu_versions;
-- 1 (one version created)

SELECT COUNT(*) FROM menu_items 
WHERE menu_version_id = 1;
-- 66 (all items from menu.json)

SELECT * FROM menu_versions WHERE id = 1;
-- {id: 1, created_by_user_id: null, created_at: 2026-02-22..., json_blob: {...full menu...}}
```

## Next Steps

1. **Use in production**: `SEED_MENU_ON_STARTUP=true` on server start
2. **Add menu API**: GET /menu, GET /menu/items endpoints
3. **Track changes**: Subscribe to MenuVersion changes for POS sync
4. **Analytics**: Which items were ordered most frequently
5. **Menu updates**: Allow authenticated users to modify menu through UI

---

**Status**: ✅ COMPLETE - All deliverables met, tested, and production-ready.
