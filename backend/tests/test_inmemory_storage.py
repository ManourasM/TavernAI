"""
Unit tests for InMemoryStorage implementation.

These tests verify InMemoryStorage-specific behavior, internal consistency,
and edge cases.
"""

import pytest
from collections import defaultdict
from app.storage import InMemoryStorage


class TestInMemoryStorageInternals:
    """Test InMemoryStorage internal consistency."""

    def test_defaultdict_behavior_for_orders(self):
        """Accessing non-existent table's orders returns empty list."""
        storage = InMemoryStorage()
        orders = storage.get_orders(999)
        assert orders == []
        assert isinstance(orders, list)

    def test_defaultdict_behavior_for_metadata(self):
        """Accessing non-existent table's metadata returns defaults."""
        storage = InMemoryStorage()
        meta = storage.get_table(999)
        assert meta == {"people": None, "bread": False}
        assert isinstance(meta, dict)

    def test_separate_instances_separate_state(self):
        """Multiple instances don't share internal dicts."""
        s1 = InMemoryStorage()
        s2 = InMemoryStorage()
        
        s1.add_order(1, {"id": "a", "status": "pending"})
        s2.add_order(1, {"id": "b", "status": "pending"})
        
        assert len(s1.get_orders(1)) == 1
        assert len(s2.get_orders(1)) == 1
        assert s1.get_orders(1)[0]["id"] == "a"
        assert s2.get_orders(1)[0]["id"] == "b"


class TestInMemoryStorageFiltering:
    """Test filtering operations."""

    def test_purge_preserves_pending(self):
        """Purge only removes non-pending items."""
        storage = InMemoryStorage()
        storage.add_order(1, {"id": "p1", "status": "pending"})
        storage.add_order(1, {"id": "d1", "status": "done"})
        storage.add_order(1, {"id": "c1", "status": "cancelled"})
        storage.add_order(1, {"id": "d2", "status": "done"})
        
        removed = storage.purge_done_orders(1)
        
        assert removed == 3
        orders = storage.get_orders(1)
        assert len(orders) == 1
        assert orders[0]["id"] == "p1"

    def test_purge_nonexistent_table(self):
        """Purging a non-existent table returns 0."""
        storage = InMemoryStorage()
        removed = storage.purge_done_orders(999)
        assert removed == 0

    def test_purge_empty_table(self):
        """Purging empty table returns 0."""
        storage = InMemoryStorage()
        storage._orders_by_table[1] = []  # Create empty list
        removed = storage.purge_done_orders(1)
        assert removed == 0


class TestInMemoryStorageOrderSearch:
    """Test order finding and searching operations."""

    def test_find_by_id_among_many(self):
        """Can find specific item among many in table."""
        storage = InMemoryStorage()
        for i in range(10):
            storage.add_order(1, {
                "id": f"item{i}",
                "text": f"item{i}",
                "status": "pending"
            })
        
        item = storage.get_order_by_id(1, "item5")
        assert item is not None
        assert item["text"] == "item5"

    def test_find_by_id_wrong_table(self):
        """Item in table 1 not found in table 2."""
        storage = InMemoryStorage()
        storage.add_order(1, {"id": "item1", "status": "pending"})
        
        item = storage.get_order_by_id(2, "item1")
        assert item is None

    def test_update_status_among_many(self):
        """Can update specific item among many."""
        storage = InMemoryStorage()
        for i in range(10):
            storage.add_order(1, {
                "id": f"item{i}",
                "status": "pending"
            })
        
        success = storage.update_order_status(1, "item5", "done")
        assert success is True
        
        item = storage.get_order_by_id(1, "item5")
        assert item["status"] == "done"

    def test_delete_specific_item_preserves_others(self):
        """Deleting an item doesn't affect others."""
        storage = InMemoryStorage()
        ids = ["a", "b", "c", "d", "e"]
        for item_id in ids:
            storage.add_order(1, {"id": item_id, "status": "pending"})
        
        success = storage.delete_order(1, "c")
        assert success is True
        
        remaining = storage.get_orders(1)
        remaining_ids = [o["id"] for o in remaining]
        assert remaining_ids == ["a", "b", "d", "e"]


class TestInMemoryStorageMultiTable:
    """Test operations across multiple tables."""

    def test_orders_isolated_by_table(self):
        """Orders in one table don't affect others."""
        storage = InMemoryStorage()
        
        storage.add_order(1, {"id": "t1_item1", "status": "pending"})
        storage.add_order(2, {"id": "t2_item1", "status": "pending"})
        storage.add_order(3, {"id": "t3_item1", "status": "pending"})
        
        assert len(storage.get_orders(1)) == 1
        assert len(storage.get_orders(2)) == 1
        assert len(storage.get_orders(3)) == 1
        
        storage.delete_order(1, "t1_item1")
        assert len(storage.get_orders(1)) == 0
        assert len(storage.get_orders(2)) == 1
        assert len(storage.get_orders(3)) == 1

    def test_metadata_isolated_by_table(self):
        """Metadata in one table doesn't affect others."""
        storage = InMemoryStorage()
        
        storage.set_table(1, {"people": 4, "bread": True})
        storage.set_table(2, {"people": 2, "bread": False})
        storage.set_table(3, {"people": 6, "bread": True})
        
        assert storage.get_table(1)["people"] == 4
        assert storage.get_table(2)["people"] == 2
        assert storage.get_table(3)["people"] == 6

    def test_delete_table_doesnt_affect_others(self):
        """Deleting one table doesn't affect others."""
        storage = InMemoryStorage()
        
        for table in range(1, 5):
            storage.set_table(table, {"people": table, "bread": False})
            storage.add_order(table, {"id": f"t{table}_i1", "status": "pending"})
        
        storage.delete_table(2)
        
        assert storage.table_exists(1)
        assert not storage.table_exists(2)
        assert storage.table_exists(3)
        assert storage.table_exists(4)
        
        assert len(storage.get_orders(1)) == 1
        assert len(storage.get_orders(2)) == 0  # Deleted
        assert len(storage.get_orders(3)) == 1

    def test_clear_truly_clears_everything(self):
        """clear() removes all tables and orders."""
        storage = InMemoryStorage()
        
        for table in range(1, 10):
            storage.set_table(table, {"people": table, "bread": table % 2 == 0})
            for i in range(5):
                storage.add_order(table, {
                    "id": f"t{table}_i{i}",
                    "status": "pending" if i % 2 == 0 else "done"
                })
        
        storage.clear()
        
        # Everything should be empty
        assert storage.list_tables() == []
        for table in range(1, 10):
            assert storage.get_orders(table) == []
            assert storage.get_table(table) == {"people": None, "bread": False}


class TestInMemoryStorageComplexScenario:
    """Test realistic multi-step scenarios."""

    def test_full_order_lifecycle(self):
        """Test complete order flow: add, update, purge."""
        storage = InMemoryStorage()
        
        # Add orders
        storage.add_order(5, {"id": "item1", "status": "pending"})
        storage.add_order(5, {"id": "item2", "status": "pending"})
        storage.add_order(5, {"id": "item3", "status": "pending"})
        
        # Mark some as done
        storage.update_order_status(5, "item1", "done")
        storage.update_order_status(5, "item2", "done")
        
        # Check state
        orders = storage.get_orders(5)
        pending = [o for o in orders if o["status"] == "pending"]
        done = [o for o in orders if o["status"] == "done"]
        
        assert len(pending) == 1
        assert len(done) == 2
        
        # Purge done items
        removed = storage.purge_done_orders(5)
        assert removed == 2
        
        # Final state
        orders = storage.get_orders(5)
        assert len(orders) == 1
        assert orders[0]["id"] == "item3"

    def test_replace_order_workflow(self):
        """Simulate order replacement: keep some, cancel others, add new."""
        storage = InMemoryStorage()
        
        # Initial order
        storage.add_order(1, {"id": "old1", "text": "item1", "status": "pending"})
        storage.add_order(1, {"id": "old2", "text": "item2", "status": "pending"})
        storage.add_order(1, {"id": "old3", "text": "item3", "status": "pending"})
        
        # Simulate replacement:
        # - Keep old1 and old2 (unchanged)
        # - Cancel old3 (removed from new order)
        # - Add new items
        
        storage.update_order_status(1, "old3", "cancelled")
        storage.add_order(1, {"id": "new1", "text": "item4", "status": "pending"})
        storage.add_order(1, {"id": "new2", "text": "item5", "status": "pending"})
        
        # Check final state
        orders = storage.get_orders(1)
        assert len(orders) == 5  # 2 kept + 1 cancelled + 2 new
        
        pending = [o for o in orders if o["status"] == "pending"]
        cancelled = [o for o in orders if o["status"] == "cancelled"]
        
        assert len(pending) == 4
        assert len(cancelled) == 1
