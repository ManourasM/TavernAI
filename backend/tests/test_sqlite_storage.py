"""
Tests for SQLiteStorage implementation.

Tests persistence, interface compliance, and multi-instance data durability.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

from app.storage.sqlite import SQLiteStorage
from app.storage.inmemory import InMemoryStorage
from app.storage.models import Base


@pytest.fixture
def temp_db():
    """Create a temporary database file for testing."""
    import time
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    db_url = f"sqlite:///{db_path}"
    yield db_url
    
    # Cleanup
    time.sleep(0.1)  # Allow time for file handles to be released
    
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except (OSError, PermissionError):
        # File may still be locked on Windows, let it be
        pass


@pytest.fixture
def sqlite_storage(temp_db):
    """Create a SQLiteStorage instance with temp database."""
    storage = SQLiteStorage(temp_db)
    yield storage
    # Cleanup
    try:
        storage.close()
    except Exception:
        pass


@pytest.fixture
def inmemory_storage():
    """Create an InMemoryStorage instance for comparison testing."""
    return InMemoryStorage()


class TestSQLiteStorageBasics:
    """Test basic SQLiteStorage functionality."""
    
    def test_initialization_creates_tables(self, temp_db):
        """Test that init creates the database and tables."""
        storage = SQLiteStorage(temp_db)
        try:
            # If we got here without error, tables were created
            assert storage.engine is not None
            assert storage.SessionLocal is not None
        finally:
            storage.close()
    
    def test_get_table_nonexistent_returns_default(self, sqlite_storage):
        """Test getting a non-existent table returns default metadata."""
        result = sqlite_storage.get_table(999)
        assert result == {"people": None, "bread": False}
    
    def test_set_and_get_table(self, sqlite_storage):
        """Test setting and retrieving table metadata."""
        sqlite_storage.set_table(5, {"people": 4, "bread": True})
        result = sqlite_storage.get_table(5)
        assert result["people"] == 4
        assert result["bread"] is True
    
    def test_get_nonexistent_order_returns_none(self, sqlite_storage):
        """Test getting a non-existent order returns None."""
        result = sqlite_storage.get_order_by_id(1, "fake-id")
        assert result is None
    
    def test_add_and_get_order(self, sqlite_storage):
        """Test adding and retrieving an order."""
        order = {
            "id": "item-001",
            "text": "2 coffees",
            "menu_name": "Coffee",
            "qty": 2,
            "unit_price": 3.50,
            "line_total": 7.0,
            "category": "drinks",
            "status": "pending",
            "menu_id": "coffee-01",
            "name": "Coffee",
        }
        
        sqlite_storage.add_order(1, order)
        result = sqlite_storage.get_order_by_id(1, "item-001")
        
        assert result is not None
        assert result["id"] == "item-001"
        assert result["text"] == "2 coffees"
        assert result["qty"] == 2
        assert result["status"] == "pending"
    
    def test_update_order_status(self, sqlite_storage):
        """Test updating an order's status."""
        order = {
            "id": "item-002",
            "text": "1 soup",
            "menu_name": "Soup",
            "qty": 1,
            "unit_price": 5.0,
            "line_total": 5.0,
            "category": "kitchen",
            "status": "pending",
            "menu_id": "soup-01",
            "name": "Soup",
        }
        
        sqlite_storage.add_order(2, order)
        
        # Update status
        success = sqlite_storage.update_order_status(2, "item-002", "done")
        assert success is True
        
        # Verify update
        result = sqlite_storage.get_order_by_id(2, "item-002")
        assert result["status"] == "done"
    
    def test_delete_order(self, sqlite_storage):
        """Test deleting an order."""
        order = {
            "id": "item-003",
            "text": "1 steak",
            "menu_name": "Steak",
            "qty": 1,
            "unit_price": 15.0,
            "line_total": 15.0,
            "category": "grill",
            "status": "pending",
            "menu_id": "steak-01",
            "name": "Steak",
        }
        
        sqlite_storage.add_order(3, order)
        assert sqlite_storage.get_order_by_id(3, "item-003") is not None
        
        # Delete
        success = sqlite_storage.delete_order(3, "item-003")
        assert success is True
        assert sqlite_storage.get_order_by_id(3, "item-003") is None
    
    def test_get_orders_for_table(self, sqlite_storage):
        """Test retrieving all orders for a table."""
        # Add multiple orders
        for i in range(3):
            order = {
                "id": f"item-{i:03d}",
                "text": f"Item {i}",
                "menu_name": f"Item {i}",
                "qty": 1,
                "unit_price": 10.0,
                "line_total": 10.0,
                "category": "kitchen",
                "status": "pending",
                "menu_id": f"item-{i}",
                "name": f"Item {i}",
            }
            sqlite_storage.add_order(5, order)
        
        orders = sqlite_storage.get_orders(5)
        assert len(orders) == 3
        assert all(order["table"] == 5 for order in orders)
    
    def test_list_tables(self, sqlite_storage):
        """Test listing all table IDs."""
        # Add orders to different tables
        sqlite_storage.set_table(1, {"people": 2, "bread": False})
        sqlite_storage.set_table(2, {"people": 4, "bread": True})
        
        order = {
            "id": "item-001",
            "text": "test",
            "menu_name": "test",
            "qty": 1,
            "unit_price": 1.0,
            "line_total": 1.0,
            "category": "kitchen",
            "status": "pending",
            "menu_id": "test",
            "name": "test",
        }
        sqlite_storage.add_order(3, order)
        
        tables = sqlite_storage.list_tables()
        assert sorted(tables) == [1, 2, 3]
    
    def test_table_exists(self, sqlite_storage):
        """Test checking if a table exists."""
        assert not sqlite_storage.table_exists(99)
        
        sqlite_storage.set_table(10, {"people": 2, "bread": False})
        assert sqlite_storage.table_exists(10)
    
    def test_delete_table(self, sqlite_storage):
        """Test deleting a table and all its orders."""
        # Setup
        sqlite_storage.set_table(7, {"people": 3, "bread": True})
        order = {
            "id": "item-del",
            "text": "test",
            "menu_name": "test",
            "qty": 1,
            "unit_price": 1.0,
            "line_total": 1.0,
            "category": "kitchen",
            "status": "pending",
            "menu_id": "test",
            "name": "test",
        }
        sqlite_storage.add_order(7, order)
        
        # Verify exists
        assert sqlite_storage.table_exists(7)
        assert len(sqlite_storage.get_orders(7)) == 1
        
        # Delete
        sqlite_storage.delete_table(7)
        
        # Verify deleted
        assert not sqlite_storage.table_exists(7)
        assert len(sqlite_storage.get_orders(7)) == 0


class TestSQLitePersistence:
    """Test that data persists across SQLiteStorage instances."""
    
    def test_data_persists_across_instances(self, temp_db):
        """Test that data written by one instance is readable by another."""
        # First instance: write data
        storage1 = SQLiteStorage(temp_db)
        try:
            storage1.set_table(1, {"people": 5, "bread": True})
            
            order = {
                "id": "persist-001",
                "text": "Persisted order",
                "menu_name": "Menu Item",
                "qty": 3,
                "unit_price": 5.0,
                "line_total": 15.0,
                "category": "kitchen",
                "status": "pending",
                "menu_id": "menu-01",
                "name": "Menu Item",
            }
            storage1.add_order(1, order)
        finally:
            storage1.close()
        
        # Second instance: read same database
        storage2 = SQLiteStorage(temp_db)
        try:
            meta = storage2.get_table(1)
            assert meta["people"] == 5
            assert meta["bread"] is True
            
            orders = storage2.get_orders(1)
            assert len(orders) == 1
            assert orders[0]["id"] == "persist-001"
            assert orders[0]["qty"] == 3
        finally:
            storage2.close()
    
    def test_multiple_instances_concurrent_access(self, temp_db):
        """Test that multiple instances can access the same database."""
        storage1 = SQLiteStorage(temp_db)
        storage2 = SQLiteStorage(temp_db)
        try:
            # First instance writes
            storage1.set_table(10, {"people": 2, "bread": False})
            
            # Second instance reads
            meta = storage2.get_table(10)
            assert meta["people"] == 2
            
            # Add order with first instance
            order = {
                "id": "concurrent-001",
                "text": "Order 1",
                "menu_name": "Menu",
                "qty": 1,
                "unit_price": 10.0,
                "line_total": 10.0,
                "category": "kitchen",
                "status": "pending",
                "menu_id": "m1",
                "name": "Menu",
            }
            storage1.add_order(10, order)
            
            # Second instance sees it
            orders = storage2.get_orders(10)
            assert len(orders) == 1
            assert orders[0]["id"] == "concurrent-001"
        finally:
            storage1.close()
            storage2.close()


class TestSQLiteInterfaceCompliance:
    """Test that SQLiteStorage implements Storage interface correctly."""
    
    def test_clear_removes_all_data(self, sqlite_storage):
        """Test that clear() removes all orders and metadata."""
        # Add data
        sqlite_storage.set_table(1, {"people": 2, "bread": True})
        sqlite_storage.set_table(2, {"people": 3, "bread": False})
        
        order1 = {
            "id": "item-clear-1",
            "text": "test",
            "menu_name": "test",
            "qty": 1,
            "unit_price": 1.0,
            "line_total": 1.0,
            "category": "kitchen",
            "status": "pending",
            "menu_id": "test",
            "name": "test",
        }
        order2 = {
            "id": "item-clear-2",
            "text": "test",
            "menu_name": "test",
            "qty": 1,
            "unit_price": 1.0,
            "line_total": 1.0,
            "category": "kitchen",
            "status": "pending",
            "menu_id": "test",
            "name": "test",
        }
        sqlite_storage.add_order(1, order1)
        sqlite_storage.add_order(2, order2)
        
        # Clear
        sqlite_storage.clear()
        
        # Verify all cleared
        assert sqlite_storage.list_tables() == []
        assert len(sqlite_storage.get_orders(1)) == 0
        assert len(sqlite_storage.get_orders(2)) == 0
    
    def test_purge_done_orders_removes_only_done(self, sqlite_storage):
        """Test that purge_done_orders removes only done/cancelled items."""
        # Add orders with different statuses
        statuses = ["pending", "done", "pending", "cancelled"]
        for i, status in enumerate(statuses):
            order = {
                "id": f"item-purge-{i}",
                "text": f"Item {status}",
                "menu_name": "Menu",
                "qty": 1,
                "unit_price": 1.0,
                "line_total": 1.0,
                "category": "kitchen",
                "status": status,
                "menu_id": "m1",
                "name": "Menu",
            }
            sqlite_storage.add_order(8, order)
        
        # Purge done items
        removed = sqlite_storage.purge_done_orders(8)
        assert removed == 2  # "done" and "cancelled"
        
        # Verify only pending remain
        orders = sqlite_storage.get_orders(8)
        assert len(orders) == 2
        assert all(order["status"] == "pending" for order in orders)
    
    def test_purge_done_with_time_filter(self, sqlite_storage):
        """Test that purge_done_orders respects older_than_seconds."""
        # Add old order (manually set created_at)
        session = sqlite_storage._get_session()
        try:
            from app.storage.models import OrderModel
            old_order = OrderModel(
                table_id=9,
                item_id="item-old",
                text="Old",
                menu_name="Menu",
                qty=1,
                unit_price=1.0,
                line_total=1.0,
                category="kitchen",
                status="done",
                menu_id="m1",
                name="Menu",
                created_at=datetime.utcnow() - timedelta(hours=2),
            )
            session.add(old_order)
            session.commit()
        finally:
            session.close()
        
        # Add recent order
        new_order = {
            "id": "item-new",
            "text": "New",
            "menu_name": "Menu",
            "qty": 1,
            "unit_price": 1.0,
            "line_total": 1.0,
            "category": "kitchen",
            "status": "done",
            "menu_id": "m1",
            "name": "Menu",
        }
        sqlite_storage.add_order(9, new_order)
        
        # Purge only items older than 1 hour
        removed = sqlite_storage.purge_done_orders(9, older_than_seconds=3600)
        assert removed == 1  # Only the old one
        
        # Verify new one remains
        orders = sqlite_storage.get_orders(9)
        assert len(orders) == 1
        assert orders[0]["id"] == "item-new"


class TestSQLiteVsInMemory:
    """Parametrized tests comparing SQLiteStorage and InMemoryStorage behavior."""
    
    @pytest.fixture(params=["sqlite", "inmemory"])
    def storage(self, request, sqlite_storage, inmemory_storage, temp_db):
        """Parametrized fixture providing both storage types."""
        if request.param == "sqlite":
            return sqlite_storage
        else:
            return inmemory_storage
    
    def test_both_support_table_operations(self, storage):
        """Test that both storage types support table operations."""
        storage.set_table(1, {"people": 3, "bread": True})
        meta = storage.get_table(1)
        
        assert meta["people"] == 3
        assert meta["bread"] is True
    
    def test_both_support_order_operations(self, storage):
        """Test that both storage types support order operations."""
        order = {
            "id": "test-id",
            "text": "Test",
            "menu_name": "Menu",
            "qty": 2,
            "unit_price": 5.0,
            "line_total": 10.0,
            "category": "kitchen",
            "status": "pending",
            "menu_id": "m1",
            "name": "Menu",
        }
        
        storage.add_order(1, order)
        retrieved = storage.get_order_by_id(1, "test-id")
        
        assert retrieved is not None
        assert retrieved["qty"] == 2
        assert retrieved["status"] == "pending"
    
    def test_both_handle_status_updates(self, storage):
        """Test that both storage types handle status updates."""
        order = {
            "id": "update-test",
            "text": "Test",
            "menu_name": "Menu",
            "qty": 1,
            "unit_price": 1.0,
            "line_total": 1.0,
            "category": "kitchen",
            "status": "pending",
            "menu_id": "m1",
            "name": "Menu",
        }
        
        storage.add_order(1, order)
        success = storage.update_order_status(1, "update-test", "done")
        
        assert success is True
        retrieved = storage.get_order_by_id(1, "update-test")
        assert retrieved["status"] == "done"
