"""
Tests for concurrent write operations on SQLiteStorage.

Basic thread test to ensure concurrent inserts succeed without corruption.
"""

import os
import tempfile
import threading

import pytest

from app.storage import SQLiteStorage


@pytest.fixture
def temp_sqlite_db():
    """Create a temporary SQLite database."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_concurrent.db")
    db_url = f"sqlite:///{db_path}"

    storage = SQLiteStorage(db_url)
    yield storage

    try:
        storage.close()
    except Exception:
        pass

    if os.path.exists(temp_dir):
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestConcurrentWrites:
    """Basic concurrent writes test."""

    def test_concurrent_add_orders_same_table(self, temp_sqlite_db):
        """Multiple threads add orders to the same table without errors."""
        storage = temp_sqlite_db
        table_id = 1
        num_threads = 4
        orders_per_thread = 15
        errors = []
        error_lock = threading.Lock()

        def add_orders(thread_id: int) -> None:
            try:
                for i in range(orders_per_thread):
                    order_id = f"t{thread_id}-o{i}"
                    order = {
                        "id": order_id,
                        "text": f"Item {order_id}",
                        "menu_name": f"Menu {order_id}",
                        "qty": 1.0,
                        "unit_price": 10.0,
                        "line_total": 10.0,
                        "category": "kitchen",
                        "status": "pending",
                        "menu_id": f"menu-{order_id}",
                        "name": f"Item {order_id}",
                    }
                    storage.add_order(table_id, order)
            except Exception as exc:
                with error_lock:
                    errors.append(exc)

        threads = [
            threading.Thread(target=add_orders, args=(thread_id,))
            for thread_id in range(num_threads)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Concurrent writes raised {len(errors)} errors"

        orders = storage.get_orders(table_id)
        expected = num_threads * orders_per_thread
        assert len(orders) == expected, f"Expected {expected} orders, got {len(orders)}"

        order_ids = [order["id"] for order in orders]
        assert len(order_ids) == len(set(order_ids)), "Duplicate order IDs detected"
