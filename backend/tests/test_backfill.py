"""Tests for backfill_orders migration helper."""

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.db.models import Order, OrderItem, TableSession
from scripts import backfill_orders


def _dump_path(tmp_path, name: str) -> str:
    return str(tmp_path / name)


def _db_url(tmp_path, name: str) -> str:
    return f"sqlite:///{tmp_path / name}"


def test_backfill_idempotent(tmp_path):
    dump_data = {
        "orders_by_table": {
            "1": [
                {
                    "id": "legacy-1",
                    "text": "1 Salad",
                    "menu_name": "Salad",
                    "menu_id": "salads_01",
                    "qty": 1,
                    "unit_price": 5.0,
                    "line_total": 5.0,
                    "status": "pending"
                },
                {
                    "id": "legacy-2",
                    "text": "2 Beers",
                    "menu_name": "Beer",
                    "menu_id": "drinks_01",
                    "qty": 2,
                    "unit_price": 4.0,
                    "line_total": 8.0,
                    "status": "done"
                }
            ]
        },
        "table_meta": {
            "1": {"people": 2, "bread": True}
        }
    }

    dump_path = _dump_path(tmp_path, "dump.json")
    with open(dump_path, "w", encoding="utf-8") as handle:
        json.dump(dump_data, handle, ensure_ascii=False, indent=2)

    db_url = _db_url(tmp_path, "backfill.db")

    # First backfill
    stats1 = backfill_orders.backfill_from_dump(dump_path, db_url)
    assert stats1["migrated"] == 2

    # Second backfill should be idempotent
    stats2 = backfill_orders.backfill_from_dump(dump_path, db_url)
    assert stats2["migrated"] == 0

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        assert session.query(TableSession).count() == 1
        assert session.query(Order).count() == 1
        assert session.query(OrderItem).count() == 2
    finally:
        session.close()

    with open(dump_path, "r", encoding="utf-8") as handle:
        updated = json.load(handle)
    assert set(updated["migrated_item_ids"]) == {"legacy-1", "legacy-2"}
