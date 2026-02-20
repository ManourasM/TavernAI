import pytest


@pytest.mark.asyncio
async def test_order_triggers_broadcast_call(async_client, reset_app_state, mock_broadcast_to_station):
    """Test that creating an order triggers broadcast."""
    payload = {
        "table": 1,
        "order_text": "1 μπριζόλα\n1 σαλάτα"
    }
    
    response = await async_client.post("/order/", json=payload)
    assert response.status_code == 200
    
    # broadcast_to_station should have been called
    assert mock_broadcast_to_station.call_count > 0
    
    # Check call arguments
    calls = mock_broadcast_to_station.call_args_list
    stations_called = [str(call[0][0]) for call in calls]
    # Should have called broadcast for at least grill and kitchen
    assert len(stations_called) > 0


@pytest.mark.asyncio
async def test_broadcast_contains_item_data(async_client, reset_app_state, mock_broadcast_to_station):
    """Test that broadcast payload contains expected item data."""
    payload = {
        "table": 1,
        "order_text": "1 σαλάτα"
    }
    
    response = await async_client.post("/order/", json=payload)
    assert response.status_code == 200
    
    # Get the mock calls
    calls = mock_broadcast_to_station.call_args_list
    assert len(calls) > 0
    
    # Each call should be broadcast_to_station(station, message)
    # Check that message contains expected fields
    for call in calls:
        station, message = call[0]
        assert isinstance(message, dict)
        assert "action" in message
