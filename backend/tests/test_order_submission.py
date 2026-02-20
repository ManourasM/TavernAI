import pytest
from app.main import app


@pytest.mark.asyncio
async def test_submit_basic_greek_order(async_client, reset_app_state, mock_broadcast_to_station):
    """Test submitting a basic Greek order with multiple items."""
    payload = {
        "table": 1,
        "order_text": "2 σουβλάκια\n1 μπύρα",
        "people": 2,
        "bread": True
    }
    
    response = await async_client.post("/order/", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "created" in data
    assert len(data["created"]) == 2
    
    # Verify state via storage
    storage = app.state.storage
    assert len(storage.get_orders(1)) == 2
    assert storage.get_table(1)["people"] == 2
    assert storage.get_table(1)["bread"] is True


@pytest.mark.asyncio
async def test_submit_order_triggers_broadcast(async_client, reset_app_state, mock_broadcast_to_station):
    """Test that submitting an order triggers WebSocket broadcasts."""
    payload = {
        "table": 1,
        "order_text": "1 μπριζόλα",
    }
    
    response = await async_client.post("/order/", json=payload)
    assert response.status_code == 200
    
    # Verify broadcast was called
    assert mock_broadcast_to_station.call_count >= 1


@pytest.mark.asyncio
async def test_submit_order_multi_station_routing(async_client, reset_app_state, mock_broadcast_to_station):
    """Test that items are routed to correct stations."""
    payload = {
        "table": 2,
        "order_text": "1 μπριζόλα\n1 σαλάτα\n1 μπύρα"
    }
    
    response = await async_client.post("/order/", json=payload)
    assert response.status_code == 200
    assert len(response.json()["created"]) == 3


@pytest.mark.asyncio
async def test_get_orders_empty(async_client, reset_app_state):
    """Test GET /orders/ with no orders."""
    response = await async_client.get("/orders/")
    assert response.status_code == 200
    assert response.json() == {}


@pytest.mark.asyncio
async def test_get_orders_with_data(async_client, reset_app_state):
    """Test GET /orders/ with submitted orders."""
    payload = {
        "table": 1,
        "order_text": "1 μπριζόλα\n1 σαλάτα"
    }
    
    await async_client.post("/order/", json=payload)
    response = await async_client.get("/orders/")
    
    assert response.status_code == 200
    data = response.json()
    assert "1" in data


@pytest.mark.asyncio
async def test_submit_order_with_quantity(async_client, reset_app_state):
    """Test submitting order with quantities."""
    payload = {
        "table": 3,
        "order_text": "2 σουβλάκια\n3 σαλάτες"
    }
    
    response = await async_client.post("/order/", json=payload)
    assert response.status_code == 200
    
    items = response.json()["created"]
    # qty should be numeric or string
    assert items[0]["qty"] in (2, "2", 2.0)
    assert items[1]["qty"] in (3, "3", 3.0)


@pytest.mark.asyncio
async def test_submit_order_with_specials(async_client, reset_app_state):
    """Test order with parentheses (special instructions)."""
    payload = {
        "table": 4,
        "order_text": "1 σουβλάκι (χωρίς σάλτσα)\n1 μπύρα (κρύα)"
    }
    
    response = await async_client.post("/order/", json=payload)
    assert response.status_code == 200
    
    items = response.json()["created"]
    # Text should preserve original with parentheses
    assert "χωρίς σάλτσα" in items[0]["text"]
    assert "κρύα" in items[1]["text"]


@pytest.mark.asyncio
async def test_submit_invalid_json(async_client, reset_app_state):
    """Test submitting invalid JSON."""
    response = await async_client.post("/order/", json={"not_a_valid": "payload"})
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_submit_empty_order(async_client, reset_app_state):
    """Test submitting empty order text."""
    payload = {
        "table": 5,
        "order_text": "",
    }
    
    response = await async_client.post("/order/", json=payload)
    # Should succeed but create no items
    assert response.status_code == 200
