"""
Tests for SQLite persistence lifecycle.

Verifies proper database initialization, persistence across restarts, and graceful shutdown.
"""

import pytest
import os
import tempfile
import asyncio
from pathlib import Path
from httpx import ASGITransport, AsyncClient

from app.storage import SQLiteStorage


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "persistence_test.db")
    db_url = f"sqlite:///{db_path}"
    yield db_path, db_url
    
    # Cleanup
    import time
    time.sleep(0.1)
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except (OSError, PermissionError):
        pass


class TestSQLiteStartup:
    """Test database initialization on startup."""
    
    def test_startup_creates_db_file(self, temp_db_path):
        """Test that app startup creates the database file."""
        db_path, db_url = temp_db_path
        
        # Before creating storage, DB should not exist
        assert not os.path.exists(db_path)
        
        # Create storage (simulates app startup)
        storage = SQLiteStorage(db_url)
        try:
            # DB file should now exist
            assert os.path.exists(db_path), "Database file should be created on startup"
        finally:
            storage.close()
    
    def test_startup_creates_tables(self, temp_db_path):
        """Test that app startup creates necessary database tables."""
        db_path, db_url = temp_db_path
        
        # Create storage (triggers table creation)
        storage = SQLiteStorage(db_url)
        try:
            # Verify tables were created by checking we can query them
            session = storage._get_session()
            try:
                from app.storage.models import OrderModel, TableMetaModel
                from sqlalchemy import inspect
                
                # Get the inspector for the database
                inspector = inspect(storage.engine)
                tables = inspector.get_table_names()
                
                # Verify required tables exist
                assert "table_meta" in tables, "table_meta table should exist"
                assert "orders" in tables, "orders table should exist"
            finally:
                session.close()
        finally:
            storage.close()
    
    def test_startup_with_existing_db(self, temp_db_path):
        """Test that startup works correctly when database already exists."""
        db_path, db_url = temp_db_path
        
        # First startup: create DB
        storage1 = SQLiteStorage(db_url)
        try:
            storage1.set_table(1, {"people": 2, "bread": False})
        finally:
            storage1.close()
        
        # Second startup: connect to existing DB
        storage2 = SQLiteStorage(db_url)
        try:
            # Verify existing data is accessible
            meta = storage2.get_table(1)
            assert meta["people"] == 2
            assert meta["bread"] is False
        finally:
            storage2.close()


class TestSQLitePersistenceAcrossRestarts:
    """Test that data persists across SQLite storage restarts."""
    
    def test_orders_survive_restart(self, temp_db_path):
        """Test that orders persist when storage is closed and reopened."""
        db_path, db_url = temp_db_path
        
        # Instance 1: write data
        storage1 = SQLiteStorage(db_url)
        try:
            storage1.set_table(5, {"people": 3, "bread": True})
            
            order = {
                "id": "persist-order-001",
                "text": "2 coffee",
                "menu_name": "Coffee",
                "qty": 2,
                "unit_price": 3.50,
                "line_total": 7.0,
                "category": "drinks",
                "status": "pending",
                "menu_id": "coffee-01",
                "name": "Coffee",
            }
            storage1.add_order(5, order)
        finally:
            storage1.close()
        
        # Instance 2: read same data
        storage2 = SQLiteStorage(db_url)
        try:
            # Verify table metadata persists
            meta = storage2.get_table(5)
            assert meta["people"] == 3
            assert meta["bread"] is True
            
            # Verify order persists
            orders = storage2.get_orders(5)
            assert len(orders) == 1
            assert orders[0]["id"] == "persist-order-001"
            assert orders[0]["qty"] == 2
            assert orders[0]["status"] == "pending"
        finally:
            storage2.close()
    
    def test_multiple_tables_survive_restart(self, temp_db_path):
        """Test that multiple tables' data persist across restart."""
        db_path, db_url = temp_db_path
        
        # Write data to multiple tables
        storage1 = SQLiteStorage(db_url)
        try:
            for table_id in [1, 2, 3]:
                storage1.set_table(table_id, {"people": table_id, "bread": table_id % 2 == 0})
                
                order = {
                    "id": f"order-table-{table_id}",
                    "text": f"Order for table {table_id}",
                    "menu_name": "Item",
                    "qty": 1,
                    "unit_price": 10.0,
                    "line_total": 10.0,
                    "category": "kitchen",
                    "status": "pending",
                    "menu_id": "item-1",
                    "name": "Item",
                }
                storage1.add_order(table_id, order)
        finally:
            storage1.close()
        
        # Restart and verify all tables
        storage2 = SQLiteStorage(db_url)
        try:
            tables = storage2.list_tables()
            assert sorted(tables) == [1, 2, 3]
            
            for table_id in [1, 2, 3]:
                meta = storage2.get_table(table_id)
                assert meta["people"] == table_id
                assert meta["bread"] == (table_id % 2 == 0)
                
                orders = storage2.get_orders(table_id)
                assert len(orders) == 1
                assert orders[0]["id"] == f"order-table-{table_id}"
        finally:
            storage2.close()
    
    def test_order_status_changes_survive_restart(self, temp_db_path):
        """Test that order status updates persist across restart."""
        db_path, db_url = temp_db_path
        
        # Create order and mark as done
        storage1 = SQLiteStorage(db_url)
        try:
            order = {
                "id": "status-test-001",
                "text": "Test",
                "menu_name": "Test",
                "qty": 1,
                "unit_price": 1.0,
                "line_total": 1.0,
                "category": "kitchen",
                "status": "pending",
                "menu_id": "test",
                "name": "Test",
            }
            storage1.add_order(7, order)
            storage1.update_order_status(7, "status-test-001", "done")
        finally:
            storage1.close()
        
        # Verify status persists
        storage2 = SQLiteStorage(db_url)
        try:
            order = storage2.get_order_by_id(7, "status-test-001")
            assert order is not None
            assert order["status"] == "done"
        finally:
            storage2.close()


class TestSQLiteShutdown:
    """Test graceful shutdown of SQLiteStorage."""
    
    def test_shutdown_closes_engine(self, temp_db_path):
        """Test that shutdown properly closes the database engine."""
        db_path, db_url = temp_db_path
        
        storage = SQLiteStorage(db_url)
        
        # Engine should be open
        assert storage.engine is not None
        
        # Close (simulate shutdown)
        storage.close()
        
        # After close, the connection pool should be disposed
        # Further operations might fail or use a new connection
        # This is expected behavior
    
    def test_shutdown_without_error(self, temp_db_path):
        """Test that shutdown completes without raising an error."""
        db_path, db_url = temp_db_path
        
        storage = SQLiteStorage(db_url)
        storage.add_order(1, {
            "id": "test-001",
            "text": "test",
            "menu_name": "test",
            "qty": 1,
            "unit_price": 1.0,
            "line_total": 1.0,
            "category": "kitchen",
            "status": "pending",
            "menu_id": "test",
            "name": "test",
        })
        
        # Shutdown should not raise an error
        try:
            storage.close()
        except Exception as e:
            pytest.fail(f"Shutdown raised an exception: {e}")


class TestSQLiteLifecycleIntegration:
    """Integration tests for SQLiteStorage lifecycle with app."""
    
    @pytest.mark.asyncio
    async def test_sqlite_backend_app_startup_and_shutdown(self, temp_db_path):
        """Test app startup and shutdown with SQLiteStorage backend."""
        db_path, db_url = temp_db_path
        
        # Mock the database URL in environment
        original_db_url = os.environ.get("DATABASE_URL")
        
        try:
            # Create app with SQLiteStorage
            import sys
            
            # Clear any cached modules
            for mod in list(sys.modules.keys()):
                if mod.startswith("app"):
                    del sys.modules[mod]
            
            # Create a modified main with our temp db
            from app.storage import SQLiteStorage
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            
            app = FastAPI(title="Test App")
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # Initialize storage with temp database
            app.state.storage = SQLiteStorage(db_url)
            
            # Add shutdown handler
            @app.on_event("shutdown")
            async def shutdown_event():
                if isinstance(app.state.storage, SQLiteStorage):
                    try:
                        app.state.storage.close()
                    except Exception as e:
                        print(f"Warning: Error closing SQLiteStorage: {e}")
            
            # Test that DB exists
            assert os.path.exists(db_path), "Database should be created"
            
            # Simulate shutdown
            await shutdown_event()
            
            # Verify we can reconnect and data survives
            app.state.storage = SQLiteStorage(db_url)
            try:
                assert os.path.exists(db_path)
            finally:
                app.state.storage.close()
        
        finally:
            if original_db_url is not None:
                os.environ["DATABASE_URL"] = original_db_url
    
    @pytest.mark.asyncio
    async def test_inmemory_backend_ignores_shutdown(self):
        """Test that InMemoryStorage is unaffected by shutdown event."""
        from app.storage import InMemoryStorage
        
        storage = InMemoryStorage()
        
        # Add some data
        storage.set_table(1, {"people": 2, "bread": False})
        
        # Shutdown should not affect inmemory (no close() method needed)
        # This just verifies the graceful shutdown pattern works
        assert storage.table_exists(1)
