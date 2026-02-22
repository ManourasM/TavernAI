# Deployment Checklist (Restaurant Owners)

Use this checklist before going live.

## 1) Prepare folders

- Create a `data/` folder in the backend working directory.
- Ensure the process has read/write permissions.

## 2) Set environment variables

- `RESTAURANT_ID` (unique per location, e.g., `taverna_athens`)
- `STORAGE_BACKEND=sqlalchemy`
- `JWT_SECRET_KEY` (strong random value)

Optional:

- `ENVIRONMENT=production`

## 3) Run migrations

From the backend directory:

```bash
alembic upgrade head
```

If you do not use Alembic in dev mode:

```bash
python -c "from sqlalchemy import create_engine; from app.db import init_db; engine=create_engine('sqlite:///data/{RESTAURANT_ID}.db'); init_db(engine, use_alembic=False)"
```

## 4) Seed menu

```bash
python -m scripts.seed_menu --menu-file data/menu.json --user-id 1
```

## 5) (Optional) Backfill legacy orders

```bash
python -m scripts.backfill_orders --dump path/to/dump.json --db sqlite:///data/{RESTAURANT_ID}.db
```

## 6) Create admin user

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secret123","roles":["admin"]}'
```

## 7) Start backend

Use your preferred command (Docker or manual scripts). Verify the API at:

- `http://localhost:8000/docs`

## 8) Verify stations

- Confirm all UIs connect to the backend.
- Place a test order and confirm it appears in all stations.
- Confirm receipts and history load in the admin views.
