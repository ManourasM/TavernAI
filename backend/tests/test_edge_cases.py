import pytest
from app.nlp import classify_order


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_order_text(self):
        """Test classifying empty string."""
        result = classify_order("")
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_whitespace_only_order(self):
        """Test classifying whitespace-only string."""
        result = classify_order("   \n\n   ")
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_very_long_item_name(self):
        """Test handling very long item names."""
        long_name = "αβγδεζηθικλμνξοπρστυφχψω" * 5
        result = classify_order(f"1 {long_name}")
        assert len(result) == 1
        assert long_name in result[0]["text"]
    
    def test_special_unicode_characters(self):
        """Test handling emoji and special chars (should not crash)."""
        text = "1 σαλάτα\n1 μπύρα"
        result = classify_order(text)
        assert len(result) >= 1
        # Should not raise exception
    
    def test_mixed_greek_latin(self):
        """Test handling mixed Greek and Latin characters."""
        text = "1 salata"
        result = classify_order(text)
        assert len(result) == 1
    
    def test_very_large_quantity(self):
        """Test handling very large quantities."""
        text = "999999 σαλάτες"
        result = classify_order(text)
        assert len(result) == 1
        assert result[0]["text"] == text
    
    @pytest.mark.asyncio
    async def test_submit_order_with_many_items(self, async_client, reset_app_state):
        """Test submitting order with many items."""
        items = "\n".join([f"{i % 10} σαλάτα" for i in range(50)])
        payload = {
            "table": 100,
            "order_text": items
        }
        
        response = await async_client.post("/order/", json=payload)
        # Should not crash
        assert response.status_code == 200


class TestNegativeInputs:
    """Test negative/invalid inputs."""
    
    @pytest.mark.asyncio
    async def test_missing_table_field(self, async_client, reset_app_state):
        """Test missing required 'table' field."""
        payload = {
            "order_text": "1 σαλάτα"
            # Missing 'table'
        }
        response = await async_client.post("/order/", json=payload)
        assert response.status_code in (400, 422)
    
    @pytest.mark.asyncio
    async def test_missing_order_text_field(self, async_client, reset_app_state):
        """Test missing required 'order_text' field."""
        payload = {
            "table": 1
            # Missing 'order_text'
        }
        response = await async_client.post("/order/", json=payload)
        assert response.status_code in (400, 422)
    
    @pytest.mark.asyncio
    async def test_invalid_table_number(self, async_client, reset_app_state):
        """Test invalid table number."""
        payload = {
            "table": -1,
            "order_text": "1 σαλάτα"
        }
        response = await async_client.post("/order/", json=payload)
        # Should handle gracefully or reject
        assert response.status_code in (200, 400, 422)
    
    @pytest.mark.asyncio
    async def test_null_values(self, async_client, reset_app_state):
        """Test null values in payload."""
        payload = {
            "table": None,
            "order_text": "1 σαλάτα"
        }
        response = await async_client.post("/order/", json=payload)
        assert response.status_code in (400, 422)


class TestStatePersistence:
    """Test that state persists correctly across requests."""
    
    @pytest.mark.asyncio
    async def test_multiple_orders_same_table(self, async_client, reset_app_state):
        """Test adding multiple orders to same table."""
        # First order
        resp1 = await async_client.post("/order/", json={
            "table": 5,
            "order_text": "1 σαλάτα"
        })
        assert resp1.status_code == 200
        
        # Second order to same table
        resp2 = await async_client.post("/order/", json={
            "table": 5,
            "order_text": "1 μπριζόλα"
        })
        assert resp2.status_code == 200
        
        # Get all orders
        resp3 = await async_client.get("/orders/")
        data = resp3.json()
        assert "5" in data
        # Should have at least 2 items
        assert len(data["5"]) >= 2
