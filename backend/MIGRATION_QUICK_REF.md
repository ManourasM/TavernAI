# Quick Reference: Alembic & Database Initialization

## Files Created/Modified

### ✅ Files Created
1. **`alembic/versions/429362eb9277_create_initial_schema.py`** (210 lines)
   - Auto-generated initial migration with all 8 tables, indexes, and foreign keys
   - Includes full upgrade and downgrade functions
   - Applied and tracked by Alembic

2. **`tests/test_migrations_init.py`** (205 lines)
   - 6 comprehensive tests for init_db function
   - Tests both Alembic and fallback modes
   - Tests data insertion capabilities
   - All 161 tests passing (6 new + 155 existing)

3. **`MIGRATIONS_SUMMARY.md`** (documentation)
   - Complete guide to migration system
   - Usage examples for dev and production
   - Architecture diagrams

### ✅ Files Modified
1. **`app/db/__init__.py`** 
   - Added `init_db(engine, use_alembic=True, base=None)` function
   - Supports both Alembic migrations and fallback create_all
   - Works with any SQLAlchemy declarative base

2. **`app/storage/sqlite.py`**
   - Replaced `Base.metadata.create_all()` with `init_db()` call
   - Uses `USE_ALEMBIC` environment variable to control mode
   - Default: development mode (use_alembic=False)
   - Production: set USE_ALEMBIC=true for migration tracking

3. **`alembic.ini`**
   - Fixed INI section structure
   - Removed incompatible `sqlalchemy.timezone` setting for SQLite
   - Now properly recognized by Alembic

### ✅ Files Verified
- **`app/db/models.py`**: 8 canonical SQLAlchemy ORM models
- **`alembic/env.py`**: Properly configured to read APP_DATABASE_URL
- **Migration history**: alembic_version table tracking

## One-Liner Summaries

**Migration file**: Contains CREATE TABLE and INDEX commands for users, menu_versions, menu_items, table_sessions, orders, order_items, receipts, and nlp_training_samples

**init_db function**: Safely initializes database with either Alembic migrations (production-safe tracking) or instant create_all (development convenience)

**Updated storage**: Now calls init_db internally, supports both modes via environment variable

**Test suite**: 6 new tests verify init_db creates all tables and allows data insertion with correct column structure

## Key Commands

```bash
# Verify migration applied
alembic current
# Output: 429362eb9277 (head)

# Generate new migration after model changes
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Revert last migration
alembic downgrade -1

# Show migration history
alembic history

# Run tests
pytest tests/test_migrations_init.py -v

# All tests
pytest tests/ -q
# Output: 161 passed
```

## Environment Variables

```bash
# Development (default) - instant schema creation via create_all
USE_ALEMBIC=false

# Production - migration tracking
USE_ALEMBIC=true
```

## Migration Details

| Component | Status | Details |
|-----------|--------|---------|
| Revision ID | ✅ | 429362eb9277 |
| Created date | ✅ | 2026-02-22 |
| Tables created | ✅ | 8 total |
| Indexes created | ✅ | 25+ indexes |
| Foreign keys | ✅ | All relationships configured |
| Downgrade support | ✅ | Full rollback capability |
| Applied | ✅ | Current schema version |

## Database Schema Overview

```
users (auth & roles)
├── menu_versions (menu snapshots)
│   └── menu_items (items in menu)
├── table_sessions (dining sessions)
│   └── orders (orders for table)
│       ├── order_items (line items)
│       └── receipts (printed receipts)
└── nlp_training_samples (ML training data)
```

All tables include proper indexes on:
- Primary keys
- Foreign keys
- Timestamps (created_at, opened_at)
- Status fields
- Category/station fields

## Test Coverage

New tests verify:
- ✅ Storage schema tables created (table_meta, orders)
- ✅ DB schema tables created (users, orders, order_items, etc.)
- ✅ Data insertion works after init
- ✅ Column structure matches model definitions
- ✅ Alembic mode properly configured

All tests pass with temporary SQLite databases (no pollution).

## Backward Compatibility

✅ Existing code using app.storage.models continues to work
✅ Existing tests all pass (155/155)
✅ Current behavior unchanged in development mode (default)
✅ SQLiteStorage API unchanged

## Production Readiness

- ✅ Migration file generated and tested
- ✅ Alembic properly configured and verified
- ✅ Migration tracking enabled via environment variable
- ✅ Downgrade path documented and working
- ✅ Database version tracked in alembic_version table
- ✅ Zero-downtime deployment possible with migration queue
