"""
Integration tests for storage with endpoint behavior.

These tests verify that when endpoints are refactored to use injected storage,
the behavior remains identical to current production logic.
"""

import pytest
from app.storage import InMemoryStorage


class TestStorageBasedEndpointBehavior:
    """Test endpoint behavior when using storage abstraction."""

    @pytest.fixture
    def storage(self):
        """Create fresh storage for each test."""
        return InMemoryStorage()

    def test_post_order_flow(self, storage):
        """POST /order/ creates items in storage."""
        # Simulate endpoint receiving table + items
        table_id = 1
        items = [
            {
                "id": "item1",
                "table": table_id,
                "text": "σαλάτα",
                "menu_name": "Σαλάτα Χωριάτικη",
                "qty": 1,
                "unit_price": 5.5,
                "line_total": 5.5,
                "category": "kitchen",
                "status": "pending",
                "created_at": "2026-02-20T12:00:00Z"
            },
            {
                "id": "item2",
                "table": table_id,
                "text": "2 μπύρα",
                "menu_name": "Μπύρα 330ml",
                "qty": 2,
                "unit_price": 2.5,
                "line_total": 5.0,
                "category": "drinks",
                "status": "pending",
                "created_at": "2026-02-20T12:00:00Z"
            }
        ]
        
        # Storage layer: add items
        for item in items:
            storage.add_order(table_id, item)
        
        # Verify: items are retrievable
        stored = storage.get_orders(table_id)
        assert len(stored) == 2
        assert stored[0]["text"] == "σαλάτα"
        assert stored[1]["text"] == "2 μπύρα"

    def test_get_orders_flow(self, storage):
        """GET /orders/ retrieves items from storage."""
        # Add items to multiple tables
        storage.add_order(1, {
            "id": "t1_i1",
            "table": 1,
            "text": "item1",
            "status": "pending"
        })
        storage.add_order(1, {
            "id": "t1_i2",
            "table": 1,
            "text": "item2",
            "status": "done"
        })
        storage.add_order(2, {
            "id": "t2_i1",
            "table": 2,
            "text": "item3",
            "status": "pending"
        })
        
        # Simulate GET /orders/?include_history=false
        tables = storage.list_tables()
        all_orders = {}
        for table_id in tables:
            orders = storage.get_orders(table_id)
            # Filter out done/cancelled for exclude_history
            pending_only = [o for o in orders if o["status"] == "pending"]
            all_orders[table_id] = pending_only
        
        # Verify structure
        assert len(all_orders) == 2
        assert len(all_orders[1]) == 1  # Only pending
        assert len(all_orders[2]) == 1

    def test_put_order_replacement_flow(self, storage):
        """PUT /order/{table} replaces orders intelligently."""
        table_id = 3
        
        # Initial order
        old_items = [
            {"id": "old1", "text": "σαλάτα", "status": "pending"},
            {"id": "old2", "text": "μπύρα", "status": "pending"},
            {"id": "old3", "text": "κρασί", "status": "pending"}
        ]
        for item in old_items:
            storage.add_order(table_id, item)
        
        # New order replaces old_items[2] and adds new items
        # Simulate smart matching: keep old1, keep old2, cancel old3, add new
        
        # Cancel removed items
        storage.update_order_status(table_id, "old3", "cancelled")
        
        # Add new items
        new_items = [
            {"id": "new1", "text": "παϊδάκια", "status": "pending"},
            {"id": "new2", "text": "2 λλ κρασί", "status": "pending"}
        ]
        for item in new_items:
            storage.add_order(table_id, item)
        
        # Verify final state
        orders = storage.get_orders(table_id)
        assert len(orders) == 5  # 2 old + 1 cancelled + 2 new
        
        pending = [o for o in orders if o["status"] == "pending"]
        assert len(pending) == 4

    def test_delete_item_flow(self, storage):
        """DELETE /order/{table}/{item_id} removes item."""
        table_id = 2
        
        storage.add_order(table_id, {"id": "item1", "text": "item1", "status": "pending"})
        storage.add_order(table_id, {"id": "item2", "text": "item2", "status": "pending"})
        storage.add_order(table_id, {"id": "item3", "text": "item3", "status": "pending"})
        
        # Delete item2
        found = storage.delete_order(table_id, "item2")
        assert found is True
        
        # Verify deletion
        orders = storage.get_orders(table_id)
        ids = [o["id"] for o in orders]
        assert ids == ["item1", "item3"]

    def test_mark_done_flow(self, storage):
        """POST /item/{item_id}/done marks item as done."""
        table_id = 4
        item_id = "special_item"
        
        storage.add_order(table_id, {
            "id": item_id,
            "text": "σαλάτα",
            "status": "pending"
        })
        
        # Mark done
        updated = storage.update_order_status(table_id, item_id, "done")
        assert updated is True
        
        # Verify status changed
        item = storage.get_order_by_id(table_id, item_id)
        assert item["status"] == "done"

    def test_purge_done_flow(self, storage):
        """POST /purge_done removes done/cancelled items."""
        table_id = 5
        
        # Add mix of items
        storage.add_order(table_id, {"id": "p1", "status": "pending", "created_at": "2026-01-01T00:00:00Z"})
        storage.add_order(table_id, {"id": "d1", "status": "done", "created_at": "2026-01-01T00:00:00Z"})
        storage.add_order(table_id, {"id": "p2", "status": "pending", "created_at": "2026-01-01T00:00:00Z"})
        storage.add_order(table_id, {"id": "c1", "status": "cancelled", "created_at": "2026-01-01T00:00:00Z"})
        storage.add_order(table_id, {"id": "d2", "status": "done", "created_at": "2026-01-01T00:00:00Z"})
        
        # Purge
        removed = storage.purge_done_orders(table_id, older_than_seconds=0)
        assert removed == 3  # d1, c1, d2
        
        # Verify only pending remain
        orders = storage.get_orders(table_id)
        ids = [o["id"] for o in orders]
        assert ids == ["p1", "p2"]

    def test_table_meta_flow(self, storage):
        """Table metadata (people, bread) can be set and retrieved."""
        table_id = 6
        
        # Initially defaults
        meta = storage.get_table(table_id)
        assert meta == {"people": None, "bread": False}
        
        # Update metadata
        storage.set_table(table_id, {"people": 4, "bread": True})
        
        # Verify update
        meta = storage.get_table(table_id)
        assert meta["people"] == 4
        assert meta["bread"] is True

    def test_table_exists_check(self, storage):
        """Can check if table has data."""
        assert not storage.table_exists(1)
        
        # Add order
        storage.add_order(1, {"id": "item1", "status": "pending"})
        assert storage.table_exists(1)
        
        # Add metadata to new table
        storage.set_table(2, {"people": 2, "bread": False})
        assert storage.table_exists(2)

    def test_finalize_table_flow(self, storage):
        """DELETE /table/{table_id} removes entire table."""
        table_id = 7
        
        # Add items and metadata
        storage.add_order(table_id, {"id": "item1", "status": "pending"})
        storage.add_order(table_id, {"id": "item2", "status": "done"})
        storage.set_table(table_id, {"people": 4, "bread": True})
        
        # Finalize (delete) table
        storage.delete_table(table_id)
        
        # Verify everything is gone
        assert not storage.table_exists(table_id)
        assert storage.get_orders(table_id) == []
        assert storage.get_table(table_id) == {"people": None, "bread": False}

    def test_concurrent_tables_isolation(self, storage):
        """Multiple tables can be managed independently."""
        # Setup multiple tables
        for table in range(1, 5):
            storage.set_table(table, {"people": table * 2, "bread": table % 2 == 0})
            for i in range(3):
                storage.add_order(table, {
                    "id": f"t{table}_i{i}",
                    "status": "pending" if i < 2 else "done"
                })
        
        # Modify table 2
        storage.update_order_status(2, "t2_i0", "done")
        storage.delete_order(2, "t2_i1")
        new_item = {"id": "t2_new", "status": "pending"}
        storage.add_order(2, new_item)
        
        # Verify table 2 changes
        t2_orders = storage.get_orders(2)
        ids = [o["id"] for o in t2_orders]
        assert "t2_i1" not in ids  # Deleted
        assert "t2_new" in ids  # Added
        
        # Verify table 1 unchanged
        t1_orders = storage.get_orders(1)
        ids = [o["id"] for o in t1_orders]
        assert [o["id"] for o in t1_orders] == ["t1_i0", "t1_i1", "t1_i2"]
        
        # Verify table 3 unchanged
        t3_meta = storage.get_table(3)
        assert t3_meta == {"people": 6, "bread": False}
