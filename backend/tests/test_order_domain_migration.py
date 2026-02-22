"""Tests for Order domain migration to normalized models.

Verifies that Order/OrderItem models work correctly while maintaining
backward compatibility with existing API contracts.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Order, OrderItem, TableSession
from app.storage.sqlalchemy_adapter import SQLAlchemyStorage


@pytest.fixture
def normalized_storage():
    """Create SQLAlchemyStorage with in-memory database."""
    storage = SQLAlchemyStorage("sqlite:///:memory:")
    yield storage
    storage.close()


@pytest.fixture
def normalized_db_session(normalized_storage):
    """Get a database session from the storage."""
    return normalized_storage._get_session()


@pytest.fixture
async def client_with_normalized_storage(normalized_storage):
    """Create async HTTP client with normalized storage."""
    import httpx
    from httpx import ASGITransport
    from app.main import app
    
    # Override app storage
    app.state.storage = normalized_storage
    
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ============================================================================
# POST /order/ - Create orders with normalized models
# ============================================================================

@pytest.mark.asyncio
async def test_post_order_creates_normalized_models(client_with_normalized_storage, normalized_db_session):
    """Test POST /order/ creates Order and OrderItem rows in database."""
    # Submit an order
    payload = {
        "table": 1,
        "order_text": "2 Μύθος\n1 Χωριάτικη",
        "people": 2,
        "bread": True
    }
    
    response = await client_with_normalized_storage.post("/order/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["created"]) == 2
    
    # Verify TableSession created
    sessions = normalized_db_session.execute(select(TableSession)).scalars().all()
    assert len(sessions) >= 1
    assert sessions[0].table_label == "1"
    
    # Verify Orders created
    orders = normalized_db_session.execute(select(Order)).scalars().all()
    assert len(orders) >= 1
    
    # Verify OrderItems created
    order_items = normalized_db_session.execute(select(OrderItem)).scalars().all()
    assert len(order_items) >= 2
    
    # Verify items have correct data
    item_names = [item.name for item in order_items]
    assert any("Μύθος" in name or "μυθος" in name.lower() for name in item_names)


@pytest.mark.asyncio
async def test_post_order_returns_correct_json_format(client_with_normalized_storage):
    """Test POST /order/ returns items in expected JSON format."""
    payload = {
        "table": 5,
        "order_text": "1 Μύθος",
        "people": 1,
        "bread": False
    }
    
    response = await client_with_normalized_storage.post("/order/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "status" in data
    assert "created" in data
    assert len(data["created"]) > 0
    
    # Check item structure (API compatibility)
    item = data["created"][0]
    assert "id" in item
    assert "table" in item
    assert "text" in item
    assert "category" in item
    assert "status" in item
    assert item["table"] == 5
    assert item["status"] == "pending"


# ============================================================================
# GET /orders/ - List orders from normalized models
# ============================================================================

@pytest.mark.asyncio
async def test_get_orders_returns_normalized_data(client_with_normalized_storage):
    """Test GET /orders/ returns orders from normalized models."""
    # Create some orders first
    payload = {
        "table": 3,
        "order_text": "1 Μύθος\n2 Σουβλάκι",
        "people": 2,
        "bread": True
    }
    
    await client_with_normalized_storage.post("/order/", json=payload)
    
    # Get all orders
    response = await client_with_normalized_storage.get("/orders/")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have table "3" with items
    assert "3" in data
    assert len(data["3"]) >= 2
    
    # Verify JSON structure
    item = data["3"][0]
    assert "id" in item
    assert "table" in item
    assert "text" in item
    assert "menu_name" in item
    assert "status" in item
    assert item["table"] == 3
    assert item["status"] == "pending"


@pytest.mark.asyncio
async def test_get_orders_pending_only(client_with_normalized_storage, normalized_db_session):
    """Test GET /orders/ returns only pending items by default."""
    # Create orders
    payload = {
        "table": 7,
        "order_text": "1 Μύθος",
        "people": 1,
        "bread": False
    }
    
    create_response = await client_with_normalized_storage.post("/order/", json=payload)
    item_id = create_response.json()["created"][0]["id"]
    
    # Mark one as done
    await client_with_normalized_storage.post(f"/item/{item_id}/done")
    
    # Get pending orders
    response = await client_with_normalized_storage.get("/orders/")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should not include done items
    if "7" in data:
        assert all(item["status"] == "pending" for item in data["7"])


# ============================================================================
# POST /item/{item_id}/done - Mark items as done
# ============================================================================

@pytest.mark.asyncio
async def test_mark_item_done_updates_database(client_with_normalized_storage, normalized_db_session):
    """Test POST /item/{item_id}/done updates OrderItem status in DB."""
    # Create an order
    payload = {
        "table": 10,
        "order_text": "1 Μύθος",
        "people": 1,
        "bread": False
    }
    
    create_response = await client_with_normalized_storage.post("/order/", json=payload)
    item_id = create_response.json()["created"][0]["id"]
    
    # Mark as done
    response = await client_with_normalized_storage.post(f"/item/{item_id}/done")
    
    assert response.status_code == 200
    
    # Verify in database
    order_items = normalized_db_session.execute(select(OrderItem)).scalars().all()
    done_items = [item for item in order_items if item.status == "done"]
    assert len(done_items) >= 1


@pytest.mark.asyncio
async def test_mark_item_done_broadcasts_update(client_with_normalized_storage):
    """Test POST /item/{item_id}/done broadcasts WebSocket update."""
    # Create an order
    payload = {
        "table": 11,
        "order_text": "1 Χωριάτικη",
        "people": 1,
        "bread": False
    }
    
    create_response = await client_with_normalized_storage.post("/order/", json=payload)
    item_id = create_response.json()["created"][0]["id"]
    
    # Patch broadcast function at the module level
    with patch("app.main.broadcast_to_station", new_callable=AsyncMock) as mock_broadcast:
        with patch("app.main.broadcast_to_all", new_callable=AsyncMock) as mock_broadcast_all:
            # Mark as done
            await client_with_normalized_storage.post(f"/item/{item_id}/done")
            
            # Verify broadcast was called (either broadcast_to_station or broadcast_to_all)
            assert mock_broadcast.called or mock_broadcast_all.called


# ============================================================================
# POST /purge_done - Remove done items
# ============================================================================

@pytest.mark.asyncio
async def test_purge_done_removes_from_database(client_with_normalized_storage, normalized_db_session):
    """Test POST /purge_done removes done OrderItems from database."""
    # Create orders
    payload = {
        "table": 15,
        "order_text": "1 Μύθος\n1 Χωριάτικη",
        "people": 1,
        "bread": False
    }
    
    create_response = await client_with_normalized_storage.post("/order/", json=payload)
    items = create_response.json()["created"]
    
    # Mark first as done
    await client_with_normalized_storage.post(f"/item/{items[0]['id']}/done")
    
    # Count items before purge
    items_before = normalized_db_session.execute(select(OrderItem)).scalars().all()
    count_before = len(items_before)
    
    # Purge done items
    await client_with_normalized_storage.post("/purge_done")
    
    # Count items after purge
    normalized_db_session.expire_all()  # Refresh session
    items_after = normalized_db_session.execute(select(OrderItem)).scalars().all()
    count_after = len(items_after)
    
    # Should have removed done items
    assert count_after < count_before or count_after == 0


# ============================================================================
# PUT /order/{table} - Smart replace with matching
# ============================================================================

@pytest.mark.asyncio
async def test_replace_order_preserves_matching_semantics(client_with_normalized_storage, normalized_db_session):
    """Test PUT /order/{table} preserves smart matching logic."""
    # Create initial order
    initial = {
        "table": 20,
        "order_text": "2 Μύθος\n1 Χωριάτικη",
        "people": 2,
        "bread": True
    }
    
    await client_with_normalized_storage.post("/order/", json=initial)
    
    # Get initial items
    orders_before = await client_with_normalized_storage.get("/orders/")
    items_before = orders_before.json().get("20", [])
    initial_count = len(items_before)
    
    # Replace with modified order (changed quantity)
    updated = {
        "table": 20,
        "order_text": "3 Μύθος\n1 Χωριάτικη",  # Changed from 2 to 3
        "people": 2,
        "bread": True
    }
    
    response = await client_with_normalized_storage.put("/order/20", json=updated)
    
    assert response.status_code == 200
    
    # Verify items in database
    orders_after = await client_with_normalized_storage.get("/orders/")
    items_after = orders_after.json().get("20", [])
    
    # Should still have 2 items (matched and updated)
    assert len(items_after) == 2


@pytest.mark.asyncio
async def test_replace_order_cancels_unmatched_items(client_with_normalized_storage, normalized_db_session):
    """Test PUT /order/{table} cancels items not in new order."""
    # Create initial order
    initial = {
        "table": 25,
        "order_text": "2 Μύθος\n1 Χωριάτικη\n1 Σουβλάκι",
        "people": 3,
        "bread": True
    }
    
    await client_with_normalized_storage.post("/order/", json=initial)
    
    # Replace with smaller order (remove Σουβλάκι)
    updated = {
        "table": 25,
        "order_text": "2 Μύθος\n1 Χωριάτικη",
        "people": 2,
        "bread": True
    }
    
    await client_with_normalized_storage.put("/order/25", json=updated)
    
    # Verify cancelled items in database
    order_items = normalized_db_session.execute(select(OrderItem)).scalars().all()
    cancelled = [item for item in order_items if item.status == "cancelled"]
    
    # Should have at least one cancelled item
    assert len(cancelled) >= 1


@pytest.mark.asyncio
async def test_replace_order_creates_new_items(client_with_normalized_storage, normalized_db_session):
    """Test PUT /order/{table} creates new items when added."""
    # Create initial order
    initial = {
        "table": 30,
        "order_text": "2 Μύθος",
        "people": 1,
        "bread": False
    }
    
    await client_with_normalized_storage.post("/order/", json=initial)
    
    # Get initial count
    items_before = normalized_db_session.execute(select(OrderItem)).scalars().all()
    count_before = len(items_before)
    
    # Replace with expanded order
    updated = {
        "table": 30,
        "order_text": "2 Μύθος\n1 Χωριάτικη\n1 Σουβλάκι",  # Added new items
        "people": 2,
        "bread": True
    }
    
    await client_with_normalized_storage.put("/order/30", json=updated)
    
    # Get new count
    normalized_db_session.expire_all()
    items_after = normalized_db_session.execute(select(OrderItem)).scalars().all()
    count_after = len(items_after)
    
    # Should have more items now
    assert count_after > count_before


# ============================================================================
# Integration tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_order_lifecycle(client_with_normalized_storage, normalized_db_session):
    """Test complete order lifecycle: create -> modify -> mark done -> purge."""
    table = 50
    
    # 1. Create order
    create_payload = {
        "table": table,
        "order_text": "2 Μύθος\n1 Χωριάτικη",
        "people": 2,
        "bread": True
    }
    
    create_resp = await client_with_normalized_storage.post("/order/", json=create_payload)
    assert create_resp.status_code == 200
    items = create_resp.json()["created"]
    assert len(items) == 2
    
    # Verify in database
    order_items = normalized_db_session.execute(select(OrderItem)).scalars().all()
    assert len(order_items) >= 2
    
    # 2. Modify order
    modify_payload = {
        "table": table,
        "order_text": "3 Μύθος\n1 Χωριάτικη",  # Changed quantity
        "people": 2,
        "bread": True
    }
    
    modify_resp = await client_with_normalized_storage.put(f"/order/{table}", json=modify_payload)
    assert modify_resp.status_code == 200
    
    # 3. Get orders
    orders_resp = await client_with_normalized_storage.get("/orders/")
    orders = orders_resp.json()
    assert str(table) in orders
    
    # 4. Mark one item as done
    item_to_mark = orders[str(table)][0]["id"]
    done_resp = await client_with_normalized_storage.post(f"/item/{item_to_mark}/done")
    assert done_resp.status_code == 200
    
    # Verify status changed in DB
    normalized_db_session.expire_all()
    done_items = normalized_db_session.execute(
        select(OrderItem).where(OrderItem.status == "done")
    ).scalars().all()
    assert len(done_items) >= 1
    
    # 5. Purge done items
    purge_resp = await client_with_normalized_storage.post("/purge_done")
    assert purge_resp.status_code == 200
    
    # Verify purged from DB
    normalized_db_session.expire_all()
    remaining_items = normalized_db_session.execute(select(OrderItem)).scalars().all()
    # Should have fewer items (done ones removed)
    assert all(item.status != "done" for item in remaining_items)


# ============================================================================
# Backward compatibility tests
# ============================================================================

@pytest.mark.asyncio
async def test_api_responses_unchanged(client_with_normalized_storage):
    """Test that API response format is unchanged with normalized models."""
    # Create order
    payload = {
        "table": 100,
        "order_text": "1 Μύθος",
        "people": 1,
        "bread": False
    }
    
    response = await client_with_normalized_storage.post("/order/", json=payload)
    
    # Verify response structure matches legacy format
    data = response.json()
    assert "status" in data
    assert "created" in data
    
    item = data["created"][0]
    required_fields = ["id", "table", "text", "menu_name", "name", "qty", 
                      "unit_price", "line_total", "category", "status", "created_at"]
    
    for field in required_fields:
        assert field in item, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_multiple_tables_isolation(client_with_normalized_storage):
    """Test that orders for different tables are properly isolated."""
    # Create orders for different tables
    for table_num in [1, 2, 3]:
        payload = {
            "table": table_num,
            "order_text": f"{table_num} Μύθος",
            "people": table_num,
            "bread": False
        }
        await client_with_normalized_storage.post("/order/", json=payload)
    
    # Verify each table has its own orders
    response = await client_with_normalized_storage.get("/orders/")
    orders = response.json()
    
    assert "1" in orders
    assert "2" in orders
    assert "3" in orders
    
    # Verify quantities match
    assert len(orders["1"]) == 1
    assert len(orders["2"]) == 1
    assert len(orders["3"]) == 1
