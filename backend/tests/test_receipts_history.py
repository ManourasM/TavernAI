"""Tests for receipts and order history functionality.

Tests TableSession lifecycle, receipt generation, and history API endpoints.
"""

import importlib
import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta
from app.utils.time_utils import now_athens_naive

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.models import TableSession, Order, OrderItem, Receipt
from app.storage.sqlalchemy_adapter import SQLAlchemyStorage


@pytest.fixture
def receipts_storage():
    """Create SQLAlchemyStorage with in-memory database for receipts tests."""
    storage = SQLAlchemyStorage("sqlite:///:memory:")
    yield storage
    storage.close()


@pytest.fixture
def receipts_db_session(receipts_storage):
    """Get a database session from the receipts storage."""
    return receipts_storage._get_session()


@pytest_asyncio.fixture
async def receipts_client(receipts_storage, monkeypatch):
    """Create async HTTP client with receipts storage using proper dependency override."""
    import httpx
    from httpx import ASGITransport
    import app.main as main_module
    import app.api.receipts_router as receipts_router
    from app.api.receipts_router import get_storage_dependency

    # Reload main module to isolate app state across test suites
    main_module = importlib.reload(main_module)
    app = main_module.app
    get_storage = main_module.get_storage

    # Save original storage and dependency overrides
    original_storage = app.state.storage
    original_overrides = app.dependency_overrides.copy()

    # Ensure app uses SQLAlchemy storage for receipts
    app.state.storage = receipts_storage

    # Force receipts router to use the test storage session directly
    monkeypatch.setattr(receipts_router, "_get_db_session", lambda _storage: receipts_storage._get_session())
    
    # Create a dependency override function that returns our test storage
    def override_get_storage():
        return receipts_storage
    
    # Override both main get_storage and receipts router dependency
    app.dependency_overrides[get_storage] = override_get_storage
    app.dependency_overrides[get_storage_dependency] = override_get_storage
    
    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        # Restore original state
        app.state.storage = original_storage
        app.dependency_overrides = original_overrides


# ============================================================================
# POST /api/orders/close - Close table session and generate receipt
# ============================================================================

@pytest.mark.asyncio
async def test_close_table_creates_receipt(receipts_client, receipts_db_session):
    """Test closing a table creates a Receipt record."""
    # Create an order first
    payload = {
        "table": 1,
        "order_text": "2 Μύθος\n1 Χωριάτικη",
        "people": 2,
        "bread": True
    }
    
    create_response = await receipts_client.post("/order/", json=payload)
    assert create_response.status_code == 200
    
    # Verify TableSession exists and is open
    sessions = receipts_db_session.execute(select(TableSession)).scalars().all()
    assert len(sessions) >= 1
    open_session = [s for s in sessions if s.table_label == "1" and s.closed_at is None]
    assert len(open_session) == 1
    
    # Close the table
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "1"}
    )
    
    assert close_response.status_code == 200
    data = close_response.json()
    
    # Verify response structure
    assert data["status"] == "closed"
    assert "session_id" in data
    assert "receipt_id" in data
    assert "closed_at" in data
    assert "total" in data
    assert data["total"] > 0
    
    # Verify TableSession.closed_at is set
    receipts_db_session.expire_all()
    session = receipts_db_session.execute(
        select(TableSession).where(TableSession.id == data["session_id"])
    ).scalar_one()
    assert session.closed_at is not None
    
    # Verify Receipt was created
    receipt = receipts_db_session.execute(
        select(Receipt).where(Receipt.id == data["receipt_id"])
    ).scalar_one()
    assert receipt is not None
    assert receipt.content is not None
    assert len(receipt.content) > 0


@pytest.mark.asyncio
async def test_close_table_receipt_content_format(receipts_client, receipts_db_session):
    """Test receipt content has correct JSON format."""
    # Create order with multiple items
    payload = {
        "table": 5,
        "order_text": "2 Μύθος\n1 Χωριάτικη\n1 Σουβλάκι",
        "people": 3,
        "bread": True
    }
    
    await receipts_client.post("/order/", json=payload)
    
    # Close table
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "5"}
    )
    
    receipt_id = close_response.json()["receipt_id"]
    
    # Get receipt from database
    receipt = receipts_db_session.execute(
        select(Receipt).where(Receipt.id == receipt_id)
    ).scalar_one()
    
    # Parse receipt content
    content = json.loads(receipt.content)
    
    # Verify content structure
    assert "table_label" in content
    assert content["table_label"] == "5"
    assert "opened_at" in content
    assert "closed_at" in content
    assert "items" in content
    assert isinstance(content["items"], list)
    assert len(content["items"]) >= 3
    assert "subtotal" in content
    assert "total" in content
    assert content["total"] > 0
    
    # Verify item structure
    for item in content["items"]:
        assert "name" in item
        assert "qty" in item
        assert "unit_price" in item
        assert "line_total" in item
        assert "status" in item


@pytest.mark.asyncio
async def test_close_table_calculates_totals(receipts_client, receipts_db_session):
    """Test closing table correctly calculates order totals."""
    # Create order
    payload = {
        "table": 7,
        "order_text": "3 Μύθος",  # 3 beers
        "people": 1,
        "bread": False
    }
    
    create_response = await receipts_client.post("/order/", json=payload)
    created_items = create_response.json()["created"]
    
    # Close table
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "7"}
    )
    
    total_from_response = close_response.json()["total"]
    
    # Verify total matches sum of items
    expected_total = sum(item.get("line_total", 0) for item in created_items)
    assert abs(total_from_response - expected_total) < 0.01  # Float comparison
    
    # Verify Order.total is set in database
    session_id = close_response.json()["session_id"]
    orders = receipts_db_session.execute(
        select(Order).where(Order.table_session_id == session_id)
    ).scalars().all()
    
    assert len(orders) >= 1
    for order in orders:
        assert order.total is not None
        assert order.total > 0


@pytest.mark.asyncio
async def test_close_nonexistent_table_fails(receipts_client):
    """Test closing a non-existent table returns 404."""
    response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "999"}
    )
    
    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "no open session" in detail or "not found" in detail


@pytest.mark.asyncio
async def test_close_already_closed_table_fails(receipts_client):
    """Test closing an already-closed table returns 404."""
    # Create and close table
    payload = {
        "table": 10,
        "order_text": "1 Μύθος",
        "people": 1,
        "bread": False
    }
    
    await receipts_client.post("/order/", json=payload)
    
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "10"}
    )
    assert close_response.status_code == 200
    
    # Try to close again
    second_close = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "10"}
    )
    
    assert second_close.status_code == 404
    detail = second_close.json()["detail"].lower()
    assert "no open session" in detail or "not found" in detail


# ============================================================================
# GET /api/orders/history - List receipts
# ============================================================================

@pytest.mark.asyncio
async def test_get_history_returns_receipts(receipts_client):
    """Test GET /api/orders/history returns closed sessions."""
    # Create and close multiple tables
    for table_num in [20, 21, 22]:
        payload = {
            "table": table_num,
            "order_text": "1 Μύθος",
            "people": 1,
            "bread": False
        }
        await receipts_client.post("/order/", json=payload)
        await receipts_client.post(
            "/api/orders/close",
            json={"table_label": str(table_num)}
        )
    
    # Get history
    response = await receipts_client.get("/api/orders/history")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 3
    
    # Verify item structure
    for item in data["items"]:
        assert "receipt_id" in item
        assert "order_id" in item
        assert "table_label" in item
        assert "closed_at" in item
        assert "total" in item
        assert "printed" in item
        assert isinstance(item["printed"], bool)


@pytest.mark.asyncio
async def test_get_history_pagination(receipts_client):
    """Test history pagination with limit and offset."""
    # Create and close multiple tables
    for table_num in range(30, 36):  # 6 tables
        payload = {
            "table": table_num,
            "order_text": "1 Χωριάτικη",
            "people": 1,
            "bread": False
        }
        await receipts_client.post("/order/", json=payload)
        await receipts_client.post(
            "/api/orders/close",
            json={"table_label": str(table_num)}
        )
    
    # First page (limit 3)
    page1 = await receipts_client.get("/api/orders/history?limit=3&offset=0")
    assert page1.status_code == 200
    data1 = page1.json()
    assert len(data1["items"]) == 3
    assert data1["limit"] == 3
    assert data1["offset"] == 0
    
    # Second page (limit 3, offset 3)
    page2 = await receipts_client.get("/api/orders/history?limit=3&offset=3")
    assert page2.status_code == 200
    data2 = page2.json()
    assert len(data2["items"]) == 3
    assert data2["offset"] == 3
    
    # Verify different items on each page
    ids_page1 = {item["receipt_id"] for item in data1["items"]}
    ids_page2 = {item["receipt_id"] for item in data2["items"]}
    assert len(ids_page1.intersection(ids_page2)) == 0


@pytest.mark.asyncio
async def test_get_history_filter_by_table(receipts_client):
    """Test filtering history by table label."""
    # Create and close tables
    for table_num in [40, 41, 42]:
        payload = {
            "table": table_num,
            "order_text": "1 Μύθος",
            "people": 1,
            "bread": False
        }
        await receipts_client.post("/order/", json=payload)
        await receipts_client.post(
            "/api/orders/close",
            json={"table_label": str(table_num)}
        )
    
    # Get history for specific table
    response = await receipts_client.get("/api/orders/history?table=41")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify only table 41 is returned
    assert all(item["table_label"] == "41" for item in data["items"])
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_history_filter_by_date(receipts_client, receipts_db_session):
    """Test filtering history by date range."""
    # Create and close a table
    payload = {
        "table": 50,
        "order_text": "1 Μύθος",
        "people": 1,
        "bread": False
    }
    await receipts_client.post("/order/", json=payload)
    
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "50"}
    )
    
    session_id = close_response.json()["session_id"]
    
    # Get the closed_at timestamp
    session_obj = receipts_db_session.execute(
        select(TableSession).where(TableSession.id == session_id)
    ).scalar_one()
    closed_at = session_obj.closed_at
    
    # Query with date filter (yesterday to tomorrow)
    yesterday = (closed_at - timedelta(days=1)).isoformat()
    tomorrow = (closed_at + timedelta(days=1)).isoformat()
    
    response = await receipts_client.get(
        f"/api/orders/history?from_date={yesterday}&to_date={tomorrow}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_history_empty_result(receipts_client):
    """Test history with no matching results."""
    # Query for future date
    future_date = (now_athens_naive() + timedelta(days=365)).isoformat()
    
    response = await receipts_client.get(
        f"/api/orders/history?from_date={future_date}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# ============================================================================
# GET /api/orders/history/{receipt_id} - Get receipt details
# ============================================================================

@pytest.mark.asyncio
async def test_get_receipt_details(receipts_client):
    """Test GET /api/orders/history/{receipt_id} returns full receipt."""
    # Create and close table
    payload = {
        "table": 60,
        "order_text": "2 Μύθος\n1 Χωριάτικη",
        "people": 2,
        "bread": True
    }
    
    await receipts_client.post("/order/", json=payload)
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "60"}
    )
    
    receipt_id = close_response.json()["receipt_id"]
    
    # Get receipt details
    response = await receipts_client.get(f"/api/orders/history/{receipt_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert data["id"] == receipt_id
    assert "order_id" in data
    assert "table_label" in data
    assert data["table_label"] == "60"
    assert "opened_at" in data
    assert "closed_at" in data
    assert "printed_at" in data
    assert "content" in data
    assert "total" in data
    
    # Verify content is valid JSON
    content = json.loads(data["content"])
    assert "items" in content
    assert len(content["items"]) >= 2


@pytest.mark.asyncio
async def test_get_receipt_details_consistent_with_close(receipts_client):
    """Test receipt details match the close response."""
    # Create and close table
    payload = {
        "table": 65,
        "order_text": "3 Μύθος",
        "people": 1,
        "bread": False
    }
    
    await receipts_client.post("/order/", json=payload)
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "65"}
    )
    
    close_data = close_response.json()
    receipt_id = close_data["receipt_id"]
    
    # Get receipt details
    details_response = await receipts_client.get(f"/api/orders/history/{receipt_id}")
    details_data = details_response.json()
    
    # Verify consistency
    assert details_data["id"] == receipt_id
    assert details_data["table_label"] == "65"
    assert abs(details_data["total"] - close_data["total"]) < 0.01


@pytest.mark.asyncio
async def test_get_nonexistent_receipt_fails(receipts_client):
    """Test getting non-existent receipt returns 404."""
    response = await receipts_client.get("/api/orders/history/99999")
    
    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "receipt" in detail or "not found" in detail


# ============================================================================
# POST /api/orders/{order_id}/finalize_print - Mark receipt as printed
# ============================================================================

@pytest.mark.asyncio
async def test_finalize_print_marks_printed(receipts_client, receipts_db_session):
    """Test POST /api/orders/{order_id}/finalize_print sets printed_at."""
    # Create and close table
    payload = {
        "table": 70,
        "order_text": "1 Μύθος",
        "people": 1,
        "bread": False
    }
    
    await receipts_client.post("/order/", json=payload)
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "70"}
    )
    
    order_id = close_response.json()["order_id"] if "order_id" in close_response.json() else None
    receipt_id = close_response.json()["receipt_id"]
    
    # Get order_id from receipt if not in close response
    if not order_id:
        receipt = receipts_db_session.execute(
            select(Receipt).where(Receipt.id == receipt_id)
        ).scalar_one()
        order_id = receipt.order_id
    
    # Verify receipt is not marked as printed initially
    receipt_before = receipts_db_session.execute(
        select(Receipt).where(Receipt.order_id == order_id)
    ).scalar_one()
    assert receipt_before.printed_at is None
    
    # Mark as printed
    print_response = await receipts_client.post(f"/api/orders/{order_id}/finalize_print")
    
    assert print_response.status_code == 200
    data = print_response.json()
    assert data["status"] == "ok"
    assert "printed_at" in data
    
    # Verify printed_at is set in database
    receipts_db_session.expire_all()
    receipt_after = receipts_db_session.execute(
        select(Receipt).where(Receipt.order_id == order_id)
    ).scalar_one()
    assert receipt_after.printed_at is not None


@pytest.mark.asyncio
async def test_finalize_print_nonexistent_order_fails(receipts_client):
    """Test marking non-existent order as printed returns 404."""
    response = await receipts_client.post("/api/orders/99999/finalize_print")
    
    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "no receipt" in detail or "not found" in detail


@pytest.mark.asyncio
async def test_finalize_print_updates_history_printed_flag(receipts_client):
    """Test printed flag appears in history after finalize_print."""
    # Create and close table
    payload = {
        "table": 75,
        "order_text": "1 Χωριάτικη",
        "people": 1,
        "bread": False
    }
    
    await receipts_client.post("/order/", json=payload)
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": "75"}
    )
    
    receipt_id = close_response.json()["receipt_id"]
    
    # Get order_id from receipt details
    details_response = await receipts_client.get(f"/api/orders/history/{receipt_id}")
    order_id = details_response.json()["order_id"]
    
    # Check history before print
    history_before = await receipts_client.get("/api/orders/history?table=75")
    item_before = history_before.json()["items"][0]
    assert item_before["printed"] is False
    
    # Mark as printed
    await receipts_client.post(f"/api/orders/{order_id}/finalize_print")
    
    # Check history after print
    history_after = await receipts_client.get("/api/orders/history?table=75")
    item_after = history_after.json()["items"][0]
    assert item_after["printed"] is True


# ============================================================================
# Integration Test - Full lifecycle
# ============================================================================

@pytest.mark.asyncio
async def test_full_receipt_lifecycle(receipts_client, receipts_db_session):
    """Test complete lifecycle: open session, add items, close, get history."""
    table_label = "100"
    
    # Step 1: Create order (opens TableSession)
    payload = {
        "table": 100,
        "order_text": "2 Μύθος\n1 Χωριάτικη\n1 Σουβλάκι",
        "people": 4,
        "bread": True
    }
    
    create_response = await receipts_client.post("/order/", json=payload)
    assert create_response.status_code == 200
    created_items = create_response.json()["created"]
    assert len(created_items) >= 3
    
    # Verify session is open
    sessions = receipts_db_session.execute(
        select(TableSession).where(TableSession.table_label == table_label)
    ).scalars().all()
    open_sessions = [s for s in sessions if s.closed_at is None]
    assert len(open_sessions) == 1
    
    # Step 2: Close session
    close_response = await receipts_client.post(
        "/api/orders/close",
        json={"table_label": table_label}
    )
    assert close_response.status_code == 200
    close_data = close_response.json()
    receipt_id = close_data["receipt_id"]
    
    # Step 3: Verify session is closed
    receipts_db_session.expire_all()
    closed_session = receipts_db_session.execute(
        select(TableSession).where(TableSession.id == close_data["session_id"])
    ).scalar_one()
    assert closed_session.closed_at is not None
    
    # Step 4: Get history and verify receipt appears
    history_response = await receipts_client.get(f"/api/orders/history?table={table_label}")
    assert history_response.status_code == 200
    history_data = history_response.json()
    assert len(history_data["items"]) >= 1
    assert any(item["receipt_id"] == receipt_id for item in history_data["items"])
    
    # Step 5: Get receipt details
    details_response = await receipts_client.get(f"/api/orders/history/{receipt_id}")
    assert details_response.status_code == 200
    details_data = details_response.json()
    
    # Parse and verify content
    content = json.loads(details_data["content"])
    assert content["table_label"] == table_label
    assert len(content["items"]) >= 3
    assert content["total"] > 0
    
    # Step 6: Mark as printed
    order_id = details_data["order_id"]
    print_response = await receipts_client.post(f"/api/orders/{order_id}/finalize_print")
    assert print_response.status_code == 200
    
    # Step 7: Verify printed flag in history
    final_history = await receipts_client.get(f"/api/orders/history?table={table_label}")
    final_item = final_history.json()["items"][0]
    assert final_item["printed"] is True
