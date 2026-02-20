"""
Tests for Storage interface contract.

These tests verify that any Storage implementation meets the basic contract:
- Tables can be created and retrieved
- Orders can be added and retrieved
- Orders can be updated and deleted
- State can be cleared
"""

import pytest
from app.storage import InMemoryStorage


class TestStorageTableOperations:
    """Test table metadata operations."""

    @pytest.fixture
    def storage(self):
        """Create fresh storage instance for each test."""
        return InMemoryStorage()

    def test_get_default_table_metadata(self, storage):
        """Getting a non-existent table returns default metadata."""
        meta = storage.get_table(1)
        assert meta == {"people": None, "bread": False}

    def test_set_and_get_table_metadata(self, storage):
        """Can set and retrieve table metadata."""
        storage.set_table(1, {"people": 4, "bread": True})
        meta = storage.get_table(1)
        assert meta == {"people": 4, "bread": True}

    def test_set_table_updates_existing(self, storage):
        """Setting table metadata overwrites previous value."""
        storage.set_table(1, {"people": 4, "bread": True})
        storage.set_table(1, {"people": 2, "bread": False})
        meta = storage.get_table(1)
        assert meta == {"people": 2, "bread": False}

    def test_delete_table_removes_all(self, storage):
        """Deleting a table removes both metadata and orders."""
        storage.set_table(1, {"people": 4, "bread": True})
        storage.add_order(1, {"id": "item1", "text": "σαλάτα", "status": "pending"})
        storage.delete_table(1)
        
        # After delete, should get defaults
        assert storage.get_table(1) == {"people": None, "bread": False}
        assert storage.get_orders(1) == []

    def test_list_tables_empty(self, storage):
        """Listing tables when empty returns empty list."""
        assert storage.list_tables() == []

    def test_list_tables_contains_all_tables(self, storage):
        """list_tables() returns all tables with orders or metadata."""
        storage.add_order(1, {"id": "a", "text": "item", "status": "pending"})
        storage.set_table(2, {"people": 4, "bread": False})
        storage.add_order(3, {"id": "b", "text": "item", "status": "pending"})
        
        tables = storage.list_tables()
        assert set(tables) == {1, 2, 3}

    def test_table_exists(self, storage):
        """table_exists detects tables with orders or metadata."""
        assert not storage.table_exists(1)
        
        storage.add_order(1, {"id": "a", "text": "item", "status": "pending"})
        assert storage.table_exists(1)
        
        storage2 = InMemoryStorage()
        assert not storage2.table_exists(1)
        storage2.set_table(2, {"people": 4, "bread": False})
        assert storage2.table_exists(2)


class TestStorageOrderOperations:
    """Test order CRUD operations."""

    @pytest.fixture
    def storage(self):
        return InMemoryStorage()

    def test_add_and_get_orders(self, storage):
        """Can add and retrieve orders for a table."""
        order = {"id": "item1", "text": "σαλάτα", "status": "pending"}
        storage.add_order(1, order)
        
        orders = storage.get_orders(1)
        assert len(orders) == 1
        assert orders[0]["id"] == "item1"

    def test_get_orders_empty_table(self, storage):
        """Getting orders from non-existent table returns empty list."""
        orders = storage.get_orders(99)
        assert orders == []

    def test_add_multiple_orders(self, storage):
        """Can add multiple orders to same table."""
        storage.add_order(1, {"id": "a", "text": "item1", "status": "pending"})
        storage.add_order(1, {"id": "b", "text": "item2", "status": "pending"})
        storage.add_order(1, {"id": "c", "text": "item3", "status": "pending"})
        
        orders = storage.get_orders(1)
        assert len(orders) == 3
        assert [o["id"] for o in orders] == ["a", "b", "c"]

    def test_get_order_by_id(self, storage):
        """Can retrieve single order by item_id."""
        order = {"id": "item1", "text": "σαλάτα", "qty": 2, "status": "pending"}
        storage.add_order(1, order)
        
        retrieved = storage.get_order_by_id(1, "item1")
        assert retrieved is not None
        assert retrieved["text"] == "σαλάτα"
        assert retrieved["qty"] == 2

    def test_get_order_by_id_not_found(self, storage):
        """Getting non-existent order returns None."""
        assert storage.get_order_by_id(1, "nonexistent") is None

    def test_update_order_status(self, storage):
        """Can update order status by item_id."""
        storage.add_order(1, {"id": "item1", "text": "σαλάτα", "status": "pending"})
        
        result = storage.update_order_status(1, "item1", "done")
        assert result is True
        
        order = storage.get_order_by_id(1, "item1")
        assert order["status"] == "done"

    def test_update_order_status_not_found(self, storage):
        """Updating non-existent order returns False."""
        result = storage.update_order_status(1, "nonexistent", "done")
        assert result is False

    def test_delete_order(self, storage):
        """Can delete order by item_id."""
        storage.add_order(1, {"id": "item1", "text": "σαλάτα", "status": "pending"})
        storage.add_order(1, {"id": "item2", "text": "μπύρα", "status": "pending"})
        
        result = storage.delete_order(1, "item1")
        assert result is True
        
        orders = storage.get_orders(1)
        assert len(orders) == 1
        assert orders[0]["id"] == "item2"

    def test_delete_order_not_found(self, storage):
        """Deleting non-existent order returns False."""
        result = storage.delete_order(1, "nonexistent")
        assert result is False

    def test_purge_done_orders(self, storage):
        """Purging removes done items and cancellations."""
        storage.add_order(1, {"id": "a", "text": "pending", "status": "pending", "created_at": "2026-01-01T00:00:00Z"})
        storage.add_order(1, {"id": "b", "text": "done", "status": "done", "created_at": "2026-01-01T00:00:00Z"})
        storage.add_order(1, {"id": "c", "text": "cancelled", "status": "cancelled", "created_at": "2026-01-01T00:00:00Z"})
        
        removed = storage.purge_done_orders(1)
        assert removed == 2  # Removed 2 items (done + cancelled)
        
        orders = storage.get_orders(1)
        assert len(orders) == 1
        assert orders[0]["id"] == "a"


class TestStorageClear:
    """Test clear operation."""

    def test_clear_resets_all_state(self):
        """clear() removes all orders and metadata."""
        storage = InMemoryStorage()
        
        # Add data to multiple tables
        storage.set_table(1, {"people": 4, "bread": True})
        storage.add_order(1, {"id": "a", "text": "item", "status": "pending"})
        storage.add_order(2, {"id": "b", "text": "item", "status": "pending"})
        storage.set_table(2, {"people": 2, "bread": False})
        
        # Clear
        storage.clear()
        
        # Verify everything is gone
        assert storage.list_tables() == []
        assert storage.get_orders(1) == []
        assert storage.get_orders(2) == []
        assert storage.get_table(1) == {"people": None, "bread": False}
        assert storage.get_table(2) == {"people": None, "bread": False}

    def test_clear_twice(self):
        """Calling clear() twice is safe."""
        storage = InMemoryStorage()
        storage.add_order(1, {"id": "a", "text": "item", "status": "pending"})
        
        storage.clear()
        storage.clear()  # Should not raise
        
        assert storage.list_tables() == []


class TestStorageIsolation:
    """Test that storage instances are isolated."""

    def test_separate_instances_dont_share_state(self):
        """Different Storage instances maintain separate state."""
        storage1 = InMemoryStorage()
        storage2 = InMemoryStorage()
        
        storage1.add_order(1, {"id": "a", "text": "item", "status": "pending"})
        storage1.set_table(1, {"people": 4, "bread": True})
        
        # storage2 should be unaffected
        assert storage2.get_orders(1) == []
        assert storage2.get_table(1) == {"people": None, "bread": False}
