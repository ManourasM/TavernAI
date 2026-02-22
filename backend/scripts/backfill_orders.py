"""Backfill legacy in-memory orders into normalized database schema.

CLI usage:
    python -m scripts.backfill_orders --dump path/to/dump.json --db sqlite:///data/default.db

Dump format (minimal):
    {
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
                }
            ]
        },
        "table_meta": {"1": {"people": 2, "bread": true}},
        "migrated_item_ids": ["legacy-1"]
    }

Notes:
    - Only "orders_by_table" is required; "table_meta" is ignored.
    - "migrated_item_ids" is updated in-place for idempotency.
"""

import argparse
import json
from typing import Dict, Any, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.db import order_utils
from app.db.models import Order, OrderItem, MenuItem


def _load_dump(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_dump(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def _lookup_menu_item_id(session, menu_id: str) -> int | None:
    if not menu_id:
        return None
    menu_item = session.query(MenuItem).filter(MenuItem.external_id == menu_id).first()
    return menu_item.id if menu_item else None


def _item_qty(item: Dict[str, Any]) -> int:
    return int(item.get("qty") or item.get("multiplier") or 1)


def _item_unit_price(item: Dict[str, Any]) -> float:
    price = item.get("unit_price")
    if price is None:
        price = item.get("price")
    return float(price or 0)


def _item_line_total(item: Dict[str, Any], qty: int, unit_price: float) -> float:
    line_total = item.get("line_total")
    if line_total is None:
        line_total = unit_price * qty
    return float(line_total or 0)


def backfill_from_dump(dump_path: str, db_url: str) -> Dict[str, int]:
    """Backfill orders from a legacy in-memory dump into normalized DB.

    The dump should include:
    - orders_by_table: {table_id: [item, ...]}
    - migrated_item_ids: [legacy_item_id, ...] (optional)
    """
    data = _load_dump(dump_path)
    orders_by_table = data.get("orders_by_table", {})
    migrated_ids = set(data.get("migrated_item_ids", []))

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    migrated_count = 0

    session = SessionLocal()
    try:
        for table_label, items in orders_by_table.items():
            if not isinstance(items, list):
                continue
            new_items = [it for it in items if it.get("id") not in migrated_ids]
            if not new_items:
                continue

            table_session = order_utils.get_or_create_table_session(session, str(table_label))

            order = Order(
                table_session_id=table_session.id,
                created_by_user_id=0,
                status="pending",
                total=0
            )
            session.add(order)
            session.flush()

            order_total_cents = 0
            for item in new_items:
                item_id = item.get("id")
                qty = _item_qty(item)
                unit_price = _item_unit_price(item)
                line_total = _item_line_total(item, qty, unit_price)
                status = item.get("status") or "pending"

                menu_item_id = _lookup_menu_item_id(session, item.get("menu_id"))
                name = item.get("menu_name") or item.get("name") or item.get("text") or "Unknown"

                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item_id,
                    name=name,
                    qty=qty,
                    unit=item.get("unit"),
                    unit_price=int(round(unit_price * 100)),
                    line_total=int(round(line_total * 100)),
                    status=status
                )
                session.add(order_item)
                session.flush()

                if status != "cancelled":
                    order_total_cents += int(round(line_total * 100))

                if item_id:
                    migrated_ids.add(item_id)
                    migrated_count += 1

            order.total = order_total_cents

        session.commit()
    finally:
        session.close()

    data["migrated_item_ids"] = sorted(migrated_ids)
    _save_dump(dump_path, data)

    return {"migrated": migrated_count}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill legacy orders into normalized DB")
    parser.add_argument("--dump", required=True, help="Path to legacy dump JSON")
    parser.add_argument("--db", default="sqlite:///data/default.db", help="Target DB URL")
    args = parser.parse_args()

    stats = backfill_from_dump(args.dump, args.db)
    print(f"Migrated items: {stats['migrated']}")


if __name__ == "__main__":
    main()
