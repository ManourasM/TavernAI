"""
Tests for menu seeding and menu utilities.

Covers idempotent seeding from menu.json, version tracking,
and item creation/update logic.
"""

import json
import tempfile
import os
from pathlib import Path
from copy import deepcopy

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from app.db import init_db, Base
from app.db.models import MenuVersion, MenuItem
from app.db.menu_utils import (
    hash_menu_json,
    menu_version_exists,
    normalize_item_name,
    upsert_menu_item,
    create_menu_version
)
from scripts.seed_menu import seed_menu, load_menu_json, get_menu_file_path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = tmp.name
    
    try:
        engine = create_engine(f"sqlite:///{tmp_db_path}")
        init_db(engine, use_alembic=False, base=Base)
        
        yield engine
        
    finally:
        engine.dispose()
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)


@pytest.fixture
def db_session(temp_db):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=temp_db)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_menu():
    """Create a sample menu for testing."""
    return {
        "Salads": [
            {
                "id": "salads_01",
                "name": "Greek Salad",
                "price": 9.99,
                "category": "kitchen"
            },
            {
                "id": "salads_02",
                "name": "Tomato Salad",
                "price": 7.50,
                "category": "kitchen"
            }
        ],
        "Grilled": [
            {
                "id": "grill_01",
                "name": "Lamb Chops",
                "price": 25.00,
                "category": "grill"
            }
        ],
        "Drinks": [
            {
                "id": "drinks_01",
                "name": "Retsina",
                "price": 5.50,
                "category": "drinks"
            }
        ]
    }


class TestMenuUtilities:
    """Test menu utility functions."""
    
    def test_hash_menu_json_deterministic(self, sample_menu):
        """Test that menu hashing is deterministic."""
        hash1 = hash_menu_json(sample_menu)
        hash2 = hash_menu_json(sample_menu)
        
        assert hash1 == hash2, "Menu hash should be deterministic"
        assert len(hash1) == 64, "SHA256 hash should be 64 hex characters"
    
    def test_hash_menu_json_changes_with_content(self, sample_menu):
        """Test that hash changes when menu content changes."""
        hash1 = hash_menu_json(sample_menu)
        
        # Modify menu
        modified_menu = deepcopy(sample_menu)
        modified_menu["Salads"][0]["price"] = 10.00
        hash2 = hash_menu_json(modified_menu)
        
        assert hash1 != hash2, "Hash should change when menu content changes"
    
    def test_normalize_item_name(self):
        """Test item name normalization."""
        assert normalize_item_name("Greek Salad") == "greek salad"
        assert normalize_item_name("  LAMB CHOPS  ") == "lamb chops"
        assert normalize_item_name("Grilled-Fish") == "grilled-fish"
    
    def test_menu_version_exists_returns_none_when_empty(self, db_session):
        """Test that menu_version_exists returns None on empty database."""
        result = menu_version_exists(db_session, {"test": "menu"})
        assert result is None
    
    def test_menu_version_exists_returns_version_when_identical(self, db_session, sample_menu):
        """Test that menu_version_exists returns MenuVersion when identical."""
        # Create a version
        version = create_menu_version(db_session, sample_menu)
        db_session.commit()
        
        # Check it exists
        result = menu_version_exists(db_session, sample_menu)
        assert result is not None
        assert result.id == version.id
    
    def test_menu_version_exists_returns_none_when_different(self, db_session, sample_menu):
        """Test that menu_version_exists returns None when JSON differs."""
        # Create a version
        create_menu_version(db_session, sample_menu)
        db_session.commit()
        
        # Modify menu
        modified_menu = deepcopy(sample_menu)
        modified_menu["Salads"][0]["price"] = 10.00
        
        # Check it doesn't exist
        result = menu_version_exists(db_session, modified_menu)
        assert result is None


class TestUpsertMenuItem:
    """Test the upsert_menu_item functionality."""
    
    def test_upsert_menu_item_creates_new(self, db_session, sample_menu):
        """Test that upsert_menu_item creates new item when not exists."""
        # Create version first
        version = create_menu_version(db_session, sample_menu)
        db_session.flush()
        
        # Upsert new item
        item_dict = {
            "id": "test_01",
            "name": "Test Item",
            "price": 12.50,
            "category": "kitchen"
        }
        
        result = upsert_menu_item(db_session, item_dict, version.id)
        db_session.flush()  # Flush to assign ID
        
        assert result.id is not None  # ID assigned after flush
        assert result.external_id == "test_01"
        assert result.name == "Test Item"
        assert result.price == 1250  # 12.50 * 100 cents
        assert result.category == "kitchen"
    
    def test_upsert_menu_item_updates_by_external_id(self, db_session, sample_menu):
        """Test that upsert updates existing item by external_id."""
        # Create first version and item
        version1 = create_menu_version(db_session, sample_menu)
        db_session.flush()
        
        item_dict = {
            "id": "item_01",
            "name": "Original Item",
            "price": 10.00,
            "category": "kitchen"
        }
        item1 = upsert_menu_item(db_session, item_dict, version1.id)
        db_session.commit()
        
        item1_id = item1.id
        
        # Create new version
        modified_menu = deepcopy(sample_menu)
        modified_menu["Salads"][0]["price"] = 12.00
        version2 = create_menu_version(db_session, modified_menu)
        db_session.flush()
        
        # Upsert same item with new version
        updated_item_dict = {
            "id": "item_01",
            "name": "Updated Item",
            "price": 12.50,
            "category": "grill"
        }
        
        item2 = upsert_menu_item(db_session, updated_item_dict, version2.id)
        db_session.commit()
        
        # Should be same item (same ID)
        assert item2.id == item1_id
        assert item2.name == "Updated Item"
        assert item2.price == 1250
        assert item2.category == "grill"
        assert item2.menu_version_id == version2.id
    
    def test_upsert_menu_item_price_conversion(self, db_session, sample_menu):
        """Test that prices are correctly converted to cents."""
        version = create_menu_version(db_session, sample_menu)
        db_session.flush()
        
        test_cases = [
            (9.99, 999),
            (10.00, 1000),
            (0.50, 50),
            (100.00, 10000),
            (25.55, 2555),
        ]
        
        for price_decimal, expected_cents in test_cases:
            item_dict = {
                "id": f"price_test_{price_decimal}",
                "name": f"Item {price_decimal}",
                "price": price_decimal,
                "category": "kitchen"
            }
            
            result = upsert_menu_item(db_session, item_dict, version.id)
            assert result.price == expected_cents, f"Price {price_decimal} should be {expected_cents} cents"


class TestSeedMenu:
    """Test the complete seed_menu function."""
    
    def test_seed_menu_creates_version_and_items(self, db_session, sample_menu):
        """Test that seed_menu creates MenuVersion and MenuItems."""
        stats = seed_menu(db_session, sample_menu)
        
        # Check statistics
        assert stats['created_version'] is True
        assert stats['version_id'] is not None
        assert stats['items_created'] == 4  # 2 salads + 1 grill + 1 drink
        assert stats['items_updated'] == 0
        
        # Verify in database
        stmt = select(MenuVersion).where(MenuVersion.id == stats['version_id'])
        version = db_session.execute(stmt).scalar_one()
        
        assert version is not None
        assert version.json_blob == sample_menu
        
        # Check items
        stmt = select(MenuItem).where(MenuItem.menu_version_id == version.id)
        items = db_session.execute(stmt).scalars().all()
        
        assert len(items) == 4
        
        # Verify item details
        salad_items = [i for i in items if i.category == "kitchen"]
        assert len(salad_items) == 2
        
        grill_items = [i for i in items if i.category == "grill"]
        assert len(grill_items) == 1
        assert grill_items[0].price == 2500  # 25.00 * 100
    
    def test_seed_menu_idempotent_same_json(self, db_session, sample_menu):
        """Test that seed_menu is idempotent with same JSON."""
        # Seed first time
        stats1 = seed_menu(db_session, sample_menu)
        version_id_1 = stats1['version_id']
        assert stats1['created_version'] is True
        
        # Seed second time with same menu
        stats2 = seed_menu(db_session, sample_menu)
        
        # Should not create new version
        assert stats2['created_version'] is False
        assert stats2['version_id'] == version_id_1
        assert stats2['items_created'] == 0
        
        # Verify only one version exists
        stmt = select(MenuVersion)
        versions = db_session.execute(stmt).scalars().all()
        assert len(versions) == 1
    
    def test_seed_menu_creates_new_version_on_change(self, db_session, sample_menu):
        """Test that seed_menu creates new version when menu changes."""
        # Seed first time
        stats1 = seed_menu(db_session, sample_menu)
        version_id_1 = stats1['version_id']
        
        # Modify menu
        modified_menu = deepcopy(sample_menu)
        modified_menu["Salads"][0]["price"] = 12.00  # Changed from 9.99
        
        # Seed with modified menu
        stats2 = seed_menu(db_session, modified_menu)
        
        # Should create new version
        assert stats2['created_version'] is True
        assert stats2['version_id'] != version_id_1
        
        # Verify both versions exist
        stmt = select(MenuVersion)
        versions = db_session.execute(stmt).scalars().all()
        assert len(versions) == 2
    
    def test_seed_menu_force_flag(self, db_session, sample_menu):
        """Test that force=True creates new version even if identical."""
        # Seed first time
        stats1 = seed_menu(db_session, sample_menu, force=False)
        version_id_1 = stats1['version_id']
        
        # Seed with force=True but same menu
        stats2 = seed_menu(db_session, sample_menu, force=True)
        
        # Should create new version despite identical JSON
        assert stats2['created_version'] is True
        assert stats2['version_id'] != version_id_1
        
        # Verify both versions exist
        stmt = select(MenuVersion)
        versions = db_session.execute(stmt).scalars().all()
        assert len(versions) == 2
    
    def test_seed_menu_with_user_id(self, db_session, sample_menu):
        """Test that created_by_user_id is stored correctly."""
        stats = seed_menu(db_session, sample_menu, created_by_user_id=42)
        
        # Verify user_id in database
        stmt = select(MenuVersion).where(MenuVersion.id == stats['version_id'])
        version = db_session.execute(stmt).scalar_one()
        
        assert version.created_by_user_id == 42


class TestSeedMenuIntegration:
    """Integration tests with real menu.json file."""
    
    def test_load_actual_menu_json(self):
        """Test that actual menu.json can be loaded."""
        try:
            menu_file = get_menu_file_path()
            menu_dict = load_menu_json(menu_file)
            
            # Verify structure
            assert isinstance(menu_dict, dict)
            assert len(menu_dict) > 0
            
            # Check for expected categories
            assert any(cat in menu_dict for cat in ["Salads", "Appetizers", "Cheese"])
            
        except FileNotFoundError:
            pytest.skip("Actual menu.json not found in expected location")
    
    def test_seed_actual_menu(self, db_session):
        """Test seeding with actual menu.json."""
        try:
            menu_file = get_menu_file_path()
            menu_dict = load_menu_json(menu_file)
        except FileNotFoundError:
            pytest.skip("Actual menu.json not found in expected location")
        
        # Seed menu
        stats = seed_menu(db_session, menu_dict)
        
        # Verify basic statistics
        assert stats['created_version'] is True
        assert stats['version_id'] is not None
        assert stats['items_created'] > 10  # Real menu has many items
        
        # Verify items in database
        stmt = select(MenuItem).where(
            MenuItem.menu_version_id == stats['version_id']
        )
        items = db_session.execute(stmt).scalars().all()
        
        assert len(items) == stats['items_created']
        
        # Verify items have proper data
        for item in items:
            assert item.name is not None and len(item.name) > 0
            assert item.price > 0
            assert item.category is not None
            assert item.station is not None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_upsert_item_without_external_id(self, db_session, sample_menu):
        """Test upserting item without external_id."""
        version = create_menu_version(db_session, sample_menu)
        db_session.flush()
        
        item_dict = {
            "name": "No ID Item",
            "price": 8.00,
            "category": "kitchen"
        }
        
        result = upsert_menu_item(db_session, item_dict, version.id)
        
        assert result.external_id is None
        assert result.name == "No ID Item"
        assert result.price == 800
    
    def test_seed_empty_menu(self, db_session):
        """Test seeding with empty menu."""
        empty_menu = {}
        
        stats = seed_menu(db_session, empty_menu)
        
        assert stats['created_version'] is True
        assert stats['items_created'] == 0
        
        # Verify version was created
        stmt = select(MenuVersion).where(MenuVersion.id == stats['version_id'])
        version = db_session.execute(stmt).scalar_one()
        assert version.json_blob == empty_menu
    
    def test_seed_menu_with_special_characters(self, db_session):
        """Test seeding with special characters in menu."""
        special_menu = {
            "Ελληνικά": [
                {
                    "id": "greek_01",
                    "name": "Χωριάτικη Σαλάτα",
                    "price": 9.50,
                    "category": "kitchen"
                }
            ],
            "Café": [
                {
                    "id": "cafe_01",
                    "name": "Café au lait",
                    "price": 3.50,
                    "category": "drinks"
                }
            ]
        }
        
        stats = seed_menu(db_session, special_menu)
        
        assert stats['created_version'] is True
        assert stats['items_created'] == 2
        
        # Verify items were created
        stmt = select(MenuItem).where(MenuItem.menu_version_id == stats['version_id'])
        items = db_session.execute(stmt).scalars().all()
        
        assert any(i.name == "Χωριάτικη Σαλάτα" for i in items)
        assert any(i.name == "Café au lait" for i in items)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
