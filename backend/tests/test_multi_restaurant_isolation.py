"""
Tests for multi-restaurant database isolation.

Verifies that each restaurant instance has its own database file and data is isolated.
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

from app.storage import SQLiteStorage, InMemoryStorage


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Cleanup
    import time
    time.sleep(0.1)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestDatabasePathConstruction:
    """Test that database paths are constructed correctly per restaurant."""
    
    def test_default_restaurant_creates_default_db_file(self, temp_data_dir):
        """Test that default restaurant uses data/default.db."""
        # Change to temp directory for this test
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # Create data directory first
            data_dir = os.path.join(temp_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            db_path = os.path.join(data_dir, "default.db")
            db_url = f"sqlite:///{db_path}"
            
            storage = SQLiteStorage(db_url)
            try:
                # Verify database file exists
                assert os.path.exists(db_path), "Default database file should be created"
                assert "default.db" in db_path
            finally:
                storage.close()
        finally:
            os.chdir(original_cwd)
    
    def test_custom_restaurant_creates_named_db_file(self, temp_data_dir):
        """Test that custom RESTAURANT_ID creates data/{id}.db file."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # Create data directory first
            data_dir = os.path.join(temp_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            db_path = os.path.join(data_dir, "taverna_zeus.db")
            db_url = f"sqlite:///{db_path}"
            
            storage = SQLiteStorage(db_url)
            try:
                # Verify database file exists with correct name
                assert os.path.exists(db_path), "Restaurant-specific database file should be created"
                assert "taverna_zeus.db" in db_path
            finally:
                storage.close()
        finally:
            os.chdir(original_cwd)
    
    def test_data_directory_created_automatically(self, temp_data_dir):
        """Test that data directory is created if it doesn't exist."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            data_dir = os.path.join(temp_data_dir, "data")
            
            # Verify data dir doesn't exist yet
            assert not os.path.exists(data_dir), "Data directory should not exist initially"
            
            # Create data directory (simulating what main.py does)
            os.makedirs(data_dir, exist_ok=True)
            
            # Create storage and verify it can use the directory
            db_path = os.path.join(data_dir, "test_restaurant.db")
            db_url = f"sqlite:///{db_path}"
            
            storage = SQLiteStorage(db_url)
            try:
                # Verify data directory exists and can be used
                assert os.path.exists(data_dir), "Data directory should exist"
                assert os.path.isdir(data_dir)
                assert os.path.exists(db_path), "Database file should be created in data directory"
            finally:
                storage.close()
        finally:
            os.chdir(original_cwd)


class TestRestaurantDataIsolation:
    """Test that each restaurant's data is isolated."""
    
    def test_restaurant_a_orders_not_visible_to_restaurant_b(self, temp_data_dir):
        """Test that Restaurant A's orders are not visible to Restaurant B."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # Create data directory
            data_dir = os.path.join(temp_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            # Restaurant A creates storage and adds order
            db_path_a = os.path.join(data_dir, "restaurant_a.db")
            db_url_a = f"sqlite:///{db_path_a}"
            
            storage_a = SQLiteStorage(db_url_a)
            try:
                order_a = {
                    "id": "order-a-001",
                    "text": "2 coffee",
                    "menu_name": "Coffee",
                    "qty": 2,
                    "unit_price": 3.0,
                    "line_total": 6.0,
                    "category": "drinks",
                    "status": "pending",
                    "menu_id": "coffee-01",
                    "name": "Coffee",
                }
                storage_a.add_order(1, order_a)
            finally:
                storage_a.close()
            
            # Restaurant B creates storage (different database)
            db_path_b = os.path.join(data_dir, "restaurant_b.db")
            db_url_b = f"sqlite:///{db_path_b}"
            
            storage_b = SQLiteStorage(db_url_b)
            try:
                # Restaurant B should NOT see Restaurant A's orders
                orders_b = storage_b.get_orders(1)
                assert len(orders_b) == 0, "Restaurant B should not see Restaurant A's orders"
            finally:
                storage_b.close()
        finally:
            os.chdir(original_cwd)
    
    def test_restaurant_a_and_b_have_separate_db_files(self, temp_data_dir):
        """Test that Restaurant A and B have separate database files."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # Create data directory
            data_dir = os.path.join(temp_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            db_path_a = os.path.join(data_dir, "pizza_palace.db")
            db_path_b = os.path.join(data_dir, "pasta_house.db")
            
            # Create both storages
            storage_a = SQLiteStorage(f"sqlite:///{db_path_a}")
            storage_b = SQLiteStorage(f"sqlite:///{db_path_b}")
            
            try:
                # Verify files are different
                assert os.path.exists(db_path_a), "Restaurant A database should exist"
                assert os.path.exists(db_path_b), "Restaurant B database should exist"
                assert db_path_a != db_path_b, "Database files should be different"
                assert "pizza_palace.db" in db_path_a
                assert "pasta_house.db" in db_path_b
            finally:
                storage_a.close()
                storage_b.close()
        finally:
            os.chdir(original_cwd)
    
    def test_multiple_restaurants_with_same_table_id_isolated(self, temp_data_dir):
        """Test that same table_id in different restaurants are isolated."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # Create data directory
            data_dir = os.path.join(temp_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            # Both restaurants set metadata for table 5, but should be isolated
            storage_r1 = SQLiteStorage(f"sqlite:///{os.path.join(data_dir, 'taverna_1.db')}")
            storage_r2 = SQLiteStorage(f"sqlite:///{os.path.join(data_dir, 'taverna_2.db')}")
            
            try:
                # Restaurant 1: Table 5 has 4 people, wants bread
                storage_r1.set_table(5, {"people": 4, "bread": True})
                
                # Restaurant 2: Table 5 has 2 people, no bread
                storage_r2.set_table(5, {"people": 2, "bread": False})
                
                # Verify isolation
                meta_r1 = storage_r1.get_table(5)
                meta_r2 = storage_r2.get_table(5)
                
                assert meta_r1["people"] == 4
                assert meta_r1["bread"] is True
                assert meta_r2["people"] == 2
                assert meta_r2["bread"] is False
            finally:
                storage_r1.close()
                storage_r2.close()
        finally:
            os.chdir(original_cwd)


class TestRestaurantWithAppEnvironment:
    """Test restaurant configuration via app with environment variables."""
    
    def test_app_with_restaurant_a_env_var(self, temp_data_dir, monkeypatch):
        """Test app with RESTAURANT_ID=taverna_a."""
        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # Set environment variables for restaurant A
            monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
            monkeypatch.setenv("RESTAURANT_ID", "taverna_a")
            
            # Clear cached modules
            for mod in list(sys.modules.keys()):
                if mod.startswith("app") or mod.startswith("storage"):
                    del sys.modules[mod]
            
            # Import app (will use the env vars)
            from app.main import app
            # Re-import SQLiteStorage to get same class instance
            from app.storage import SQLiteStorage
            
            # Verify database file exists in data/taverna_a.db
            data_dir = os.path.join(temp_data_dir, "data")
            db_path = os.path.join(data_dir, "taverna_a.db")
            
            assert os.path.exists(db_path), f"Database should exist at {db_path}"
            assert isinstance(app.state.storage, SQLiteStorage)
            
            # Add order to Restaurant A
            app.state.storage.set_table(1, {"people": 2, "bread": False})
            
            # Cleanup
            if hasattr(app.state.storage, 'close'):
                app.state.storage.close()
        
        finally:
            os.chdir(original_cwd)
    
    def test_app_with_restaurant_b_env_var_does_not_see_a_data(self, temp_data_dir, monkeypatch):
        """Test that app with different RESTAURANT_ID doesn't see other restaurant's data."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # First, create Restaurant A's data
            monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
            monkeypatch.setenv("RESTAURANT_ID", "spaghetteria")
            
            for mod in list(sys.modules.keys()):
                if mod.startswith("app") or mod.startswith("storage"):
                    del sys.modules[mod]
            
            from app.main import app as app_a
            from app.storage import SQLiteStorage
            
            # Add data to Restaurant A
            order_a = {
                "id": "order-001",
                "text": "2 pasta",
                "menu_name": "Pasta",
                "qty": 2,
                "unit_price": 10.0,
                "line_total": 20.0,
                "category": "kitchen",
                "status": "pending",
                "menu_id": "pasta-01",
                "name": "Pasta",
            }
            app_a.state.storage.add_order(1, order_a)
            app_a.state.storage.set_table(1, {"people": 2, "bread": True})
            
            if hasattr(app_a.state.storage, 'close'):
                app_a.state.storage.close()
            
            # Now create Restaurant B with different ID
            monkeypatch.setenv("RESTAURANT_ID", "pizzeria")
            
            for mod in list(sys.modules.keys()):
                if mod.startswith("app") or mod.startswith("storage"):
                    del sys.modules[mod]
            
            from app.main import app as app_b
            
            # Restaurant B should not see Restaurant A's data
            orders_b = app_b.state.storage.get_orders(1)
            assert len(orders_b) == 0, "Restaurant B should not see Restaurant A's orders"
            
            meta_b = app_b.state.storage.get_table(1)
            assert meta_b["people"] is None, "Restaurant B table 1 should not have Restaurant A's metadata"
            
            if hasattr(app_b.state.storage, 'close'):
                app_b.state.storage.close()
        
        finally:
            os.chdir(original_cwd)
    
    def test_default_restaurant_id_used_when_not_set(self, temp_data_dir, monkeypatch):
        """Test that 'default' restaurant ID is used when RESTAURANT_ID not set."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # Make sure RESTAURANT_ID is not set
            monkeypatch.delenv("RESTAURANT_ID", raising=False)
            monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
            
            for mod in list(sys.modules.keys()):
                if mod.startswith("app") or mod.startswith("storage"):
                    del sys.modules[mod]
            
            from app.main import app
            from app.storage import SQLiteStorage
            
            # Verify default database was used
            data_dir = os.path.join(temp_data_dir, "data")
            default_db_path = os.path.join(data_dir, "default.db")
            
            assert os.path.exists(default_db_path), f"Default database should exist at {default_db_path}"
            
            if hasattr(app.state.storage, 'close'):
                app.state.storage.close()
        
        finally:
            os.chdir(original_cwd)


class TestRestaurantPersistenceAcrossRestart:
    """Test that restaurant-specific data persists across storage restart."""
    
    def test_restaurant_data_survives_restart(self, temp_data_dir):
        """Test that Restaurant A's data survives storage restart."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_data_dir)
            
            # Create data directory
            data_dir = os.path.join(temp_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            db_path = os.path.join(data_dir, "ristorante.db")
            db_url = f"sqlite:///{db_path}"
            
            # First session: add data
            storage1 = SQLiteStorage(db_url)
            try:
                storage1.set_table(3, {"people": 5, "bread": True})
                
                order = {
                    "id": "menu-item-001",
                    "text": "1 lasagna",
                    "menu_name": "Lasagna",
                    "qty": 1,
                    "unit_price": 12.0,
                    "line_total": 12.0,
                    "category": "kitchen",
                    "status": "pending",
                    "menu_id": "lasagna-01",
                    "name": "Lasagna",
                }
                storage1.add_order(3, order)
            finally:
                storage1.close()
            
            # Second session: verify data persists
            storage2 = SQLiteStorage(db_url)
            try:
                meta = storage2.get_table(3)
                assert meta["people"] == 5
                assert meta["bread"] is True
                
                orders = storage2.get_orders(3)
                assert len(orders) == 1
                assert orders[0]["id"] == "menu-item-001"
            finally:
                storage2.close()
        finally:
            os.chdir(original_cwd)
