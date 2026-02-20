import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
from typing import Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app import main as main_module
import httpx
from httpx import ASGITransport


@pytest.fixture
def reset_app_state():
    """Reset in-memory storage and station connections before each test."""
    # Clear storage
    app.state.storage.clear()
    # Clear station connections
    main_module.station_connections.clear()
    main_module.station_connections["kitchen"] = []
    main_module.station_connections["grill"] = []
    main_module.station_connections["drinks"] = []
    main_module.station_connections["waiter"] = []
    yield
    # Cleanup after test
    app.state.storage.clear()
    main_module.station_connections.clear()


@pytest_asyncio.fixture
async def async_client(reset_app_state):
    """Create async HTTP client for testing."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_broadcast_to_station(monkeypatch):
    """Mock broadcast_to_station to avoid WebSocket calls."""
    mock = AsyncMock()
    monkeypatch.setattr(main_module, "broadcast_to_station", mock)
    return mock


@pytest.fixture
def mock_broadcast_to_all(monkeypatch):
    """Mock broadcast_to_all to avoid WebSocket calls."""
    mock = AsyncMock()
    monkeypatch.setattr(main_module, "broadcast_to_all", mock)
    return mock


@pytest.fixture
def greek_menu_data():
    """Sample Greek menu items for testing."""
    return {
        "Salads": [
            {"id": "salads_01", "name": "Χωριάτικη", "price": 9.5, "category": "kitchen"},
            {"id": "salads_02", "name": "Ντοματοσαλάτα", "price": 7.5, "category": "kitchen"},
        ],
        "From the grill": [
            {"id": "grill_01", "name": "Χοιρινή μπριζόλα", "price": 15.0, "category": "grill"},
            {"id": "grill_02", "name": "κ Αρνίσια παϊδάκια", "price": 40.0, "category": "grill"},
        ],
        "Beers": [
            {"id": "beer_01", "name": "Μύθος", "price": 4.0, "category": "drinks"},
            {"id": "beer_02", "name": "Κρασί λευκό (1lt)", "price": 10.0, "category": "drinks"},
        ],
    }
