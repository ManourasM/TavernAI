"""Export database snapshot as JSON."""

import argparse
import json
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.db.models import (
    User,
    MenuVersion,
    MenuItem,
    TableSession,
    Order,
    OrderItem,
    Receipt,
    NLPTrainingSample
)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _serialize_rows(rows: list[Any], fields: list[str]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        item = {field: _serialize_value(getattr(row, field)) for field in fields}
        result.append(item)
    return result


def export_snapshot(db_url: str, output_path: str) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()
    try:
        snapshot = {
            "users": _serialize_rows(
                session.query(User).all(),
                ["id", "username", "roles", "pin", "created_at"]
            ),
            "menu_versions": _serialize_rows(
                session.query(MenuVersion).all(),
                ["id", "created_at", "created_by_user_id", "json_blob"]
            ),
            "menu_items": _serialize_rows(
                session.query(MenuItem).all(),
                [
                    "id",
                    "menu_version_id",
                    "external_id",
                    "name",
                    "price",
                    "category",
                    "station",
                    "extra_data",
                    "is_active"
                ]
            ),
            "table_sessions": _serialize_rows(
                session.query(TableSession).all(),
                ["id", "table_label", "opened_at", "closed_at", "waiter_user_id"]
            ),
            "orders": _serialize_rows(
                session.query(Order).all(),
                ["id", "table_session_id", "created_by_user_id", "status", "created_at", "total"]
            ),
            "order_items": _serialize_rows(
                session.query(OrderItem).all(),
                ["id", "order_id", "menu_item_id", "name", "qty", "unit", "unit_price", "line_total", "status"]
            ),
            "receipts": _serialize_rows(
                session.query(Receipt).all(),
                ["id", "order_id", "printed_at", "content"]
            ),
            "nlp_training_samples": _serialize_rows(
                session.query(NLPTrainingSample).all(),
                [
                    "id",
                    "raw_text",
                    "predicted_menu_item_id",
                    "corrected_menu_item_id",
                    "corrected_by_user_id",
                    "created_at"
                ]
            )
        }

        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export DB snapshot as JSON")
    parser.add_argument("--db", default="sqlite:///data/default.db", help="Database URL")
    parser.add_argument("--out", required=True, help="Output JSON file path")
    args = parser.parse_args()

    export_snapshot(args.db, args.out)
    print(f"Snapshot written to {args.out}")


if __name__ == "__main__":
    main()
