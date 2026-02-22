# Database and Migration Notes

## Migrations

### Alembic (recommended for production)

From the backend directory:

```bash
alembic upgrade head
```

### Fast init (dev/test)

This creates tables directly without Alembic:

```bash
python -c "from sqlalchemy import create_engine; from app.db import init_db; engine=create_engine('sqlite:///data/dev.db'); init_db(engine, use_alembic=False)"
```

## Seeding menu data

```bash
python -m scripts.seed_menu --menu-file data/menu.json --user-id 1
```

Environment option:

```bash
APP_DATABASE_URL=sqlite:///data/dev.db python -m scripts.seed_menu --menu-file data/menu.json
```

## STORAGE_BACKEND options

Set the storage backend with `STORAGE_BACKEND`:

- `inmemory` (default)
- `sqlite` (legacy flat orders)
- `sqlalchemy` (normalized Order/OrderItem)

Example:

```bash
STORAGE_BACKEND=sqlalchemy RESTAURANT_ID=default
```

For SQLite and SQLAlchemy backends, the DB file is:

```
data/{RESTAURANT_ID}.db
```

## Backfill legacy data

Use the backfill helper to migrate legacy dumps:

```bash
python -m scripts.backfill_orders --dump path/to/dump.json --db sqlite:///data/default.db
```

The dump format and idempotency notes are documented in
[backend/scripts/backfill_orders.py](scripts/backfill_orders.py).

## Create admin user

Auth is minimal and supports a dev bootstrap path:

```bash
# In dev mode (default), signup is allowed
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secret123","roles":["admin"]}'

# Login and get token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secret123"}'
```

Set a stronger JWT secret in production:

```bash
JWT_SECRET_KEY=your-strong-secret
```
