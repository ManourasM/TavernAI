# Alembic Migration & Safe Initialization Summary

## Deliverables Completed

### 1. Generated Alembic Migration File ✅
**File**: `alembic/versions/429362eb9277_create_initial_schema.py`

The initial migration was generated via `alembic revision --autogenerate` and comprehensively defines:
- **8 tables**: users, menu_versions, menu_items, table_sessions, orders, order_items, receipts, nlp_training_samples
- **Foreign keys and constraints**: Proper relationships between tables with cascading deletes
- **Indexes**: Created for performance (category, station, created_at, user_id, table_id, etc.)
- **Upgrade path**: SQL operations to create all tables and indexes
- **Downgrade path**: Automated rollback support

### 2. Safe Initialization Function ✅
**File**: `app/db/__init__.py`

```python
def init_db(engine: Engine, use_alembic: bool = True, base: Optional[Any] = None) -> None:
```

**Features**:
- **Alembic mode** (`use_alembic=True`): Runs `alembic upgrade head` to apply migrations safely
- **Fallback mode** (`use_alembic=False`): Calls `Base.metadata.create_all(engine)` for development convenience
- **Flexible base support**: Works with both `app.db.models.Base` (new schema) and `app.storage.models.Base` (legacy)
- **Error handling**: Clear error messages if Alembic configuration missing or import fails

### 3. Updated Storage Layer ✅
**File**: `app/storage/sqlite.py`

```python
# Uses environment variable to control initialization mode
use_alembic = os.getenv("USE_ALEMBIC", "false").lower() == "true"
init_db(self.engine, use_alembic=use_alembic, base=Base)
```

**Behavior**:
- **Development**: `USE_ALEMBIC=false` (default) → instant schema creation via `create_all()`
- **Production**: `USE_ALEMBIC=true` → migration tracking via Alembic
- Backward compatible: Works with existing `app.storage.models.Base`

### 4. Comprehensive Test Suite ✅
**File**: `tests/test_migrations_init.py`

**6 new tests** covering:
- ✅ `test_init_db_creates_storage_schema`: Verifies storage tables created
- ✅ `test_init_db_enables_data_insertion`: Tests data insertion after init
- ✅ `test_init_db_creates_db_schema`: Verifies new db schema tables created
- ✅ `test_init_db_alembic_mode_requires_alembic`: Validates Alembic setup
- ✅ `test_storage_order_table_exists_after_init`: Orders table in storage schema
- ✅ `test_db_order_table_exists_after_init`: Orders table in db schema

**All tests use temporary SQLite files and verify column structure**

## Verification Results

### Migration Application
```
$ alembic upgrade head
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 429362eb9277, create initial schema
✅ SUCCESS
```

### Current Migration Status
```
$ alembic current
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
429362eb9277 (head)
✅ CURRENT: Initial schema migration applied and tracked
```

### Test Suite Results
```
$ pytest tests/ -q
✅ 161 passed (155 original + 6 new) in 27.58s
```

## Usage Guide

### Development (Instant Schema Creation)
```bash
# Default behavior - uses fallback mode for instant schema
python -m app.main  # No setup needed, database auto-created
```

### Production (Migration Tracking)
```bash
# With migration tracking
export USE_ALEMBIC=true
python -m app.main  # Runs alembic upgrade head on startup
```

### Manual Database Initialization
```python
from sqlalchemy import create_engine
from app.db import init_db

engine = create_engine("sqlite:///tavern.db")

# Fallback mode (dev)
init_db(engine, use_alembic=False)

# Alembic mode (production)
init_db(engine, use_alembic=True)
```

### Running Tests
```bash
# All tests including new migration tests
pytest tests/ -v

# Only migration tests
pytest tests/test_migrations_init.py -v
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Application Startup                                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SQLiteStorage.__init__()                                  │
│    ↓                                                         │
│  Engine created                                            │
│    ↓                                                         │
│  init_db(engine, use_alembic=USE_ALEMBIC_env_var)        │
│    ↓                                                         │
│  ┌─────────────────────────────────┐                       │
│  │ if use_alembic:                 │                       │
│  │   alembic.command.upgrade()     │ (Tracks migrations)  │
│  │ else:                            │                       │
│  │   Base.metadata.create_all()    │ (Fast, no tracking)  │
│  └─────────────────────────────────┘                       │
│    ↓                                                         │
│  Database ready                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Migration Files Reference

- **Migration script**: `alembic/versions/429362eb9277_create_initial_schema.py`
- **Alembic config**: `alembic.ini` (stores version and SQL dialect info)
- **Alembic environment**: `alembic/env.py` (reads APP_DATABASE_URL env var)
- **Alembic template**: `alembic/script.py.mako` (template for future migrations)

## Next Steps (After This Phase)

1. **Generate subsequent migrations**:
   ```bash
   alembic revision --autogenerate -m "add column X to table Y"
   ```

2. **Downgrade if needed**:
   ```bash
   alembic downgrade -1  # Revert last migration
   ```

3. **Check migration history**:
   ```bash
   alembic history
   ```

4. **Switch between modes**: Change `USE_ALEMBIC` environment variable

## Production Deployment Checklist

- [ ] Set `USE_ALEMBIC=true` in production environment
- [ ] Backup database before running migrations
- [ ] Test migrations in staging first
- [ ] Monitor alembic_version table for migration history
- [ ] Keep migration files under version control
- [ ] Document any manual migrations or data transformations

## Notes

- **Backward Compatible**: Existing `app.storage.models` still work and can be initialized via init_db
- **Two Schemas**: The codebase now has two database schemas:
  - Legacy: `app.storage.models` (simple in-memory compatible)
  - New: `app.db.models` (relational with full schema, used by Alembic)
- **Reserved Keywords**: Column name `metadata` → renamed to `extra_data` (SQLAlchemy reserved word)
- **SQLite Timezone**: Removed unsupported `sqlalchemy.timezone` config from `alembic.ini`
