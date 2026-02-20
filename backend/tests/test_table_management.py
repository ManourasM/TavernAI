import pytest
from app.main import app


@pytest.mark.asyncio
async def test_table_meta_update(async_client, reset_app_state):
    """Test updating table metadata (people, bread)."""
    payload = {
        "table": 1,
        "order_text": "1 σαλάτα",
        "people": 4,
        "bread": True
    }
    
    response = await async_client.post("/order/", json=payload)
    assert response.status_code == 200
    
    # Check table meta via storage
    storage = app.state.storage
    assert storage.get_table(1)["people"] == 4
    assert storage.get_table(1)["bread"] is True


@pytest.mark.asyncio
async def test_get_table_meta(async_client, reset_app_state):
    """Test GET /table_meta/{table}."""
    payload = {
        "table": 2,
        "order_text": "1 σαλάτα",
        "people": 2,
    }
    
    await async_client.post("/order/", json=payload)
    
    response = await async_client.get("/table_meta/2")
    assert response.status_code == 200
    
    meta = response.json()
    assert meta["people"] == 2


@pytest.mark.asyncio
async def test_get_nonexistent_table_meta(async_client, reset_app_state):
    """Test getting meta for non-existent table."""
    response = await async_client.get("/table_meta/999")
    assert response.status_code == 200
    
    meta = response.json()
    # Should return default structure
    assert "people" in meta
    assert "bread" in meta


@pytest.mark.asyncio
async def test_replace_table_order(async_client, reset_app_state):
    """Test PUT /order/{table} to replace order."""
    # Create initial order
    post_payload = {
        "table": 3,
        "order_text": "1 σαλάτα\n1 μπριζόλα"
    }
    await async_client.post("/order/", json=post_payload)
    
    # Replace order
    put_payload = {
        "table": 3,
        "order_text": "2 σαλάτες",
    }
    response = await async_client.put("/order/3", json=put_payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cancel_item(async_client, reset_app_state):
    """Test DELETE /order/{table}/{item_id}."""
    # Create order
    payload = {
        "table": 4,
        "order_text": "1 σαλάτα\n1 μπριζόλα"
    }
    post_response = await async_client.post("/order/", json=payload)
    items = post_response.json()["created"]
    item_id = items[0]["id"]
    
    # Cancel first item
    response = await async_client.delete(f"/order/4/{item_id}")
    assert response.status_code == 200
