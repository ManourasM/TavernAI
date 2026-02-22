"""Tests for Menu CRUD API endpoints."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.db.models import MenuVersion, MenuItem
from app.db.dependencies import require_admin


@pytest.fixture
def test_db_session():
    """Create a temporary SQLite database session for testing."""
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_menu_dict():
    """Sample menu dictionary for testing."""
    return {
        "Salads": [
            {"id": "salads_01", "name": "Greek Salad", "price": 9.50, "category": "kitchen"},
            {"id": "salads_02", "name": "Tomato Salad", "price": 7.50, "category": "kitchen"},
        ],
        "Grill": [
            {"id": "grill_01", "name": "Pork Chop", "price": 15.00, "category": "grill"},
            {"id": "grill_02", "name": "Lamb Chops", "price": 40.00, "category": "grill"},
        ],
        "Drinks": [
            {"id": "drinks_01", "name": "Mythos Beer", "price": 4.00, "category": "drinks"},
        ],
    }


@pytest.fixture
def seeded_menu(test_db_session, sample_menu_dict):
    """Seed a menu version into the test database."""
    from scripts.seed_menu import seed_menu
    
    stats = seed_menu(
        session=test_db_session,
        menu_dict=sample_menu_dict,
        force=True,
        created_by_user_id=1
    )
    test_db_session.commit()
    
    # Return the version that was created
    from app.db.models import MenuVersion
    version = test_db_session.query(MenuVersion).filter_by(id=stats['version_id']).first()
    return version


@pytest.fixture
async def client_with_db(test_db_session):
    """Create async HTTP client with database session mocked."""
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.db.dependencies import get_db_session
    
    # Override dependency to use test session
    async def override_get_db_session():
        yield test_db_session
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def admin_override():
    """Override admin dependency for menu endpoints."""
    from app.main import app

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_admin] = lambda: {"id": 1, "roles": ["admin"]}
    yield
    app.dependency_overrides = original_overrides


# ============================================================================
# GET /api/menu - Get latest menu
# ============================================================================

@pytest.mark.asyncio
async def test_get_latest_menu_from_db(client_with_db, seeded_menu):
    """Test GET /api/menu returns menu from database when seeded."""
    response = await client_with_db.get("/api/menu")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return the seeded menu structure
    assert "Salads" in data
    assert "Grill" in data
    assert "Drinks" in data
    assert len(data["Salads"]) == 2
    assert len(data["Grill"]) == 2
    assert len(data["Drinks"]) == 1


@pytest.mark.asyncio
async def test_get_latest_menu_fallback_to_file(async_client):
    """Test GET /api/menu falls back to menu.json when no DB menu exists."""
    # This uses the default in-memory storage (no DB)
    response = await async_client.get("/api/menu")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return menu from file (menu.json in data/ directory)
    # Just verify it's a valid menu structure
    assert isinstance(data, dict)
    # Should have some categories (exact structure depends on menu.json)
    assert len(data) > 0


# ============================================================================
# GET /api/menu/versions - List versions
# ============================================================================

@pytest.mark.asyncio
async def test_list_menu_versions(client_with_db, test_db_session, sample_menu_dict):
    """Test GET /api/menu/versions returns list of menu versions."""
    from scripts.seed_menu import seed_menu
    
    # Create 3 versions
    for i in range(3):
        seed_menu(test_db_session, sample_menu_dict, force=True, created_by_user_id=i+1)
        test_db_session.commit()
    
    response = await client_with_db.get("/api/menu/versions")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 3
    # Should be ordered newest first
    assert data[0]["id"] >= data[1]["id"]
    assert data[1]["id"] >= data[2]["id"]
    
    # Check structure
    assert "id" in data[0]
    assert "created_at" in data[0]
    assert "item_count" in data[0]


@pytest.mark.asyncio
async def test_list_menu_versions_pagination(client_with_db, test_db_session, sample_menu_dict):
    """Test GET /api/menu/versions with limit parameter."""
    from scripts.seed_menu import seed_menu
    
    # Create 10 versions
    for i in range(10):
        seed_menu(test_db_session, sample_menu_dict, force=True, created_by_user_id=i+1)
        test_db_session.commit()
    
    # Request only 5
    response = await client_with_db.get("/api/menu/versions?limit=5")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 5


@pytest.mark.asyncio
async def test_list_menu_versions_limit_validation(client_with_db):
    """Test GET /api/menu/versions validates limit range (1-100)."""
    # Test limit too low
    response = await client_with_db.get("/api/menu/versions?limit=0")
    assert response.status_code == 422  # Validation error
    
    # Test limit too high
    response = await client_with_db.get("/api/menu/versions?limit=101")
    assert response.status_code == 422


# ============================================================================
# GET /api/menu/{version_id} - Get specific version
# ============================================================================

@pytest.mark.asyncio
async def test_get_menu_by_version_id(client_with_db, seeded_menu):
    """Test GET /api/menu/{version_id} returns specific version."""
    version_id = seeded_menu.id
    
    response = await client_with_db.get(f"/api/menu/{version_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return menu structure
    assert "Salads" in data
    assert "Grill" in data


@pytest.mark.asyncio
async def test_get_menu_by_version_id_not_found(client_with_db):
    """Test GET /api/menu/{version_id} returns 404 for non-existent version."""
    response = await client_with_db.get("/api/menu/99999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# POST /api/menu - Create new menu version
# ============================================================================

@pytest.mark.asyncio
async def test_create_menu_version(client_with_db, sample_menu_dict, admin_override):
    """Test POST /api/menu creates new menu version."""
    response = await client_with_db.post(
        "/api/menu",
        json={
            "menu_dict": sample_menu_dict,
            "created_by_user_id": 1
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["version_id"] is not None
    assert data["items_created"] == 5  # 2 salads + 2 grill + 1 drink
    assert data["items_updated"] == 0


@pytest.mark.asyncio
async def test_create_menu_version_force_flag(client_with_db, test_db_session, sample_menu_dict, admin_override):
    """Test POST /api/menu with force=True always creates new version."""
    from app.db.menu_utils import create_menu_version
    
    # Create initial version
    create_menu_version(test_db_session, sample_menu_dict, created_by_user_id=1)
    test_db_session.commit()
    
    # Create again with force=True (should create new version even with same data)
    response = await client_with_db.post(
        "/api/menu",
        json={
            "menu_dict": sample_menu_dict,
            "created_by_user_id": 1
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Should have created new version
    assert data["version_id"] > 1


@pytest.mark.asyncio
async def test_create_menu_version_requires_admin(client_with_db, sample_menu_dict):
    """Test POST /api/menu requires admin auth."""
    response = await client_with_db.post(
        "/api/menu",
        json={
            "menu_dict": sample_menu_dict,
            "created_by_user_id": 1
        }
    )
    
    assert response.status_code == 401


# ============================================================================
# PUT /api/menu/item/{item_id} - Update menu item
# ============================================================================

@pytest.mark.asyncio
async def test_update_menu_item(client_with_db, test_db_session, seeded_menu, admin_override):
    """Test PUT /api/menu/item/{item_id} updates menu item."""
    # Get an item to update
    item = test_db_session.query(MenuItem).filter_by(external_id="salads_01").first()
    assert item is not None
    
    new_price = 12.50
    new_name = "Updated Greek Salad"
    
    response = await client_with_db.put(
        f"/api/menu/item/{item.id}",
        json={
            "name": new_name,
            "price": new_price
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == new_name
    assert data["price"] == new_price
    
    # Verify in database
    test_db_session.refresh(item)
    assert item.name == new_name
    assert item.price == int(new_price * 100)  # Stored as cents


@pytest.mark.asyncio
async def test_update_menu_item_partial(client_with_db, test_db_session, seeded_menu, admin_override):
    """Test PUT /api/menu/item/{item_id} allows partial updates."""
    item = test_db_session.query(MenuItem).filter_by(external_id="grill_01").first()
    original_name = item.name
    original_price = item.price
    
    # Update only price
    new_price = 18.00
    
    response = await client_with_db.put(
        f"/api/menu/item/{item.id}",
        json={"price": new_price}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Name should be unchanged
    assert data["name"] == original_name
    # Price should be updated
    assert data["price"] == new_price


@pytest.mark.asyncio
async def test_update_menu_item_not_found(client_with_db, admin_override):
    """Test PUT /api/menu/item/{item_id} returns 404 for non-existent item."""
    response = await client_with_db.put(
        "/api/menu/item/99999",
        json={"name": "Test"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_menu_item_requires_admin(client_with_db, test_db_session, seeded_menu):
    """Test PUT /api/menu/item/{item_id} requires admin auth."""
    item = test_db_session.query(MenuItem).first()
    
    response = await client_with_db.put(
        f"/api/menu/item/{item.id}",
        json={"name": "Test"}
    )
    
    assert response.status_code == 401


# ============================================================================
# DELETE /api/menu/item/{item_id} - Soft-delete menu item
# ============================================================================

@pytest.mark.asyncio
async def test_delete_menu_item_soft_delete(client_with_db, test_db_session, seeded_menu, admin_override):
    """Test DELETE /api/menu/item/{item_id} marks item as inactive."""
    item = test_db_session.query(MenuItem).filter_by(external_id="drinks_01").first()
    assert item.is_active is True
    
    response = await client_with_db.delete(f"/api/menu/item/{item.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "marked as inactive" in data["message"].lower()
    
    # Verify in database
    test_db_session.refresh(item)
    assert item.is_active is False


@pytest.mark.asyncio
async def test_delete_menu_item_not_found(client_with_db, admin_override):
    """Test DELETE /api/menu/item/{item_id} returns 404 for non-existent item."""
    response = await client_with_db.delete("/api/menu/item/99999")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_menu_item_requires_admin(client_with_db, test_db_session, seeded_menu):
    """Test DELETE /api/menu/item/{item_id} requires admin auth."""
    item = test_db_session.query(MenuItem).first()
    
    response = await client_with_db.delete(f"/api/menu/item/{item.id}")
    
    assert response.status_code == 401


# ============================================================================
# GET /api/menu/active/latest - Get active items
# ============================================================================

@pytest.mark.asyncio
async def test_get_active_items_filters_inactive(client_with_db, test_db_session, seeded_menu):
    """Test GET /api/menu/active/latest returns only active items."""
    # Mark one item as inactive
    item = test_db_session.query(MenuItem).filter_by(external_id="salads_02").first()
    item.is_active = False
    test_db_session.commit()
    
    response = await client_with_db.get("/api/menu/active/latest")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only return active items
    assert len(data["Salads"]) == 1  # Only 1 active salad
    assert data["Salads"][0]["id"] == "salads_01"


@pytest.mark.asyncio
async def test_get_active_items_empty_category(client_with_db, test_db_session, seeded_menu):
    """Test GET /api/menu/active/latest excludes empty categories."""
    # Mark all items in Drinks as inactive
    items = test_db_session.query(MenuItem).filter_by(category="drinks").all()
    for item in items:
        item.is_active = False
    test_db_session.commit()
    
    response = await client_with_db.get("/api/menu/active/latest")
    
    assert response.status_code == 200
    data = response.json()
    
    # Drinks category should not exist (all items inactive)
    assert "Drinks" not in data


# ============================================================================
# Price conversion tests
# ============================================================================

@pytest.mark.asyncio
async def test_price_conversion_decimal_to_cents(client_with_db, test_db_session, admin_override):
    """Test that prices are correctly converted from decimal to cents."""
    menu = {
        "Test": [
            {"id": "test_01", "name": "Test Item", "price": 9.99, "category": "kitchen"}
        ]
    }
    
    response = await client_with_db.post(
        "/api/menu",
        json={"menu_dict": menu, "created_by_user_id": 1}
    )
    
    assert response.status_code == 201
    
    # Check in database
    item = test_db_session.query(MenuItem).filter_by(external_id="test_01").first()
    assert item.price == 999  # 9.99 * 100


@pytest.mark.asyncio
async def test_price_conversion_cents_to_decimal(client_with_db, test_db_session, seeded_menu):
    """Test that prices are correctly converted from cents to decimal in responses."""
    response = await client_with_db.get("/api/menu/active/latest")
    
    assert response.status_code == 200
    data = response.json()
    
    # Prices should be in decimal format
    salad = data["Salads"][0]
    assert isinstance(salad["price"], (int, float))
    assert salad["price"] == 9.50  # Not 950


# ============================================================================
# Integration tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_crud_workflow(client_with_db, test_db_session, sample_menu_dict, admin_override):
    """Test complete CRUD workflow: create -> read -> update -> delete."""
    # 1. Create menu
    create_response = await client_with_db.post(
        "/api/menu",
        json={"menu_dict": sample_menu_dict, "created_by_user_id": 1}
    )
    assert create_response.status_code == 201
    version_id = create_response.json()["version_id"]
    
    # 2. Read menu
    read_response = await client_with_db.get(f"/api/menu/{version_id}")
    assert read_response.status_code == 200
    menu_data = read_response.json()
    assert "Salads" in menu_data
    
    # 3. Update item
    item = test_db_session.query(MenuItem).filter_by(external_id="salads_01").first()
    update_response = await client_with_db.put(
        f"/api/menu/item/{item.id}",
        json={"price": 11.00}
    )
    assert update_response.status_code == 200
    assert update_response.json()["price"] == 11.00
    
    # 4. Delete (soft-delete) item
    delete_response = await client_with_db.delete(f"/api/menu/item/{item.id}")
    assert delete_response.status_code == 200
    
    # 5. Verify item is inactive
    active_response = await client_with_db.get("/api/menu/active/latest")
    assert active_response.status_code == 200
    active_data = active_response.json()
    # Should have only 1 salad left (the other is inactive)
    assert len(active_data["Salads"]) == 1
    assert active_data["Salads"][0]["id"] != "salads_01"
