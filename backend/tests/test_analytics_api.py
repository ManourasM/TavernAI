"""Tests for analytics API — GET /api/analytics/summary."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from app.db import Base
from app.db.models import Order, OrderItem, TableSession, User
from app.storage.sqlalchemy_adapter import SQLAlchemyStorage


# ---------- Fixtures ----------

@pytest.fixture
def analytics_storage(tmp_path):
    db_path = tmp_path / "analytics.db"
    storage = SQLAlchemyStorage(f"sqlite:///{db_path}")
    Base.metadata.create_all(storage.engine)
    yield storage
    storage.close()


@pytest_asyncio.fixture
async def analytics_client(analytics_storage, monkeypatch):
    import httpx
    from httpx import ASGITransport
    from app.main import app, get_storage
    from app.db.dependencies import get_sqlalchemy_session
    import app.api.analytics_router as analytics_router
    import app.api.auth_router as auth_router
    import app.api.users_router as users_router
    import app.api.workstations_router as workstations_router
    import app.api.menu_router as menu_router
    import app.db.dependencies as db_dependencies

    original_storage = app.state.storage
    original_overrides = app.dependency_overrides.copy()

    app.state.storage = analytics_storage

    def override_get_storage():
        return analytics_storage

    def override_get_sqlalchemy_session(request=None):
        return analytics_storage._get_session()

    app.dependency_overrides[get_storage] = override_get_storage
    app.dependency_overrides[get_sqlalchemy_session] = override_get_sqlalchemy_session

    monkeypatch.setattr(db_dependencies, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(auth_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(users_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(workstations_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(menu_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(analytics_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.state.storage = original_storage
        app.dependency_overrides = original_overrides


# ---------- Helpers ----------

async def _signup_and_login(client, username: str, password: str, roles: list[str]) -> str:
    resp = await client.post(
        "/api/auth/signup",
        json={"username": username, "password": password, "roles": roles},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _seed_closed_order(
    storage,
    order_total_cents: int = 1500,
    item_name: str = "Burger",
    item_qty: int = 2,
    item_category: str = "kitchen",
    created_at: datetime | None = None,
):
    """Seed a fully closed table session with one order and items directly into DB."""
    session = storage._get_session()
    try:
        # Minimal User for FK
        user = User(username=f"waiter_{uuid4().hex[:12]}", password_hash="x", roles=["waiter"])
        session.add(user)
        session.flush()

        order_created_at = created_at or (datetime.now() - timedelta(hours=1))
        table_session = TableSession(
            table_label="T1",
            opened_at=order_created_at - timedelta(hours=1),
            closed_at=order_created_at + timedelta(minutes=30),
            waiter_user_id=user.id,
        )
        session.add(table_session)
        session.flush()

        order = Order(
            table_session_id=table_session.id,
            created_by_user_id=user.id,
            status="closed",
            created_at=order_created_at,
            total=order_total_cents,
        )
        session.add(order)
        session.flush()

        unit_price = order_total_cents // max(item_qty, 1)
        item = OrderItem(
            order_id=order.id,
            name=item_name,
            qty=item_qty,
            unit_price=unit_price,
            line_total=unit_price * item_qty,
            category=item_category,
            status="served",
        )
        session.add(item)
        session.commit()
    finally:
        session.close()


def _seed_closed_session_with_multiple_orders(
    storage,
    orders: list[dict],
    created_at: datetime | None = None,
):
    """Seed one closed table session containing multiple Order rows.

    This mirrors the legacy storage behavior where each submitted item may be
    persisted as its own Order row even though the customer pays once when the
    table is closed.
    """
    session = storage._get_session()
    try:
        user = User(username=f"waiter_{uuid4().hex[:12]}", password_hash="x", roles=["waiter"])
        session.add(user)
        session.flush()

        order_created_at = created_at or (datetime.now() - timedelta(hours=1))
        table_session = TableSession(
            table_label="T2",
            opened_at=order_created_at - timedelta(hours=1),
            closed_at=order_created_at + timedelta(minutes=30),
            waiter_user_id=user.id,
        )
        session.add(table_session)
        session.flush()

        for order_data in orders:
            order = Order(
                table_session_id=table_session.id,
                created_by_user_id=user.id,
                status="closed",
                created_at=order_created_at,
                total=order_data["order_total_cents"],
            )
            session.add(order)
            session.flush()

            item = OrderItem(
                order_id=order.id,
                name=order_data.get("item_name", "Item"),
                qty=order_data.get("item_qty", 1),
                unit_price=order_data["order_total_cents"] // max(order_data.get("item_qty", 1), 1),
                line_total=order_data["order_total_cents"],
                category=order_data.get("item_category", "kitchen"),
                status=order_data.get("status", "served"),
            )
            session.add(item)

        session.commit()
    finally:
        session.close()


# ---------- Auth tests ----------

@pytest.mark.asyncio
async def test_summary_returns_401_without_auth(analytics_client):
    """Unauthenticated request is rejected."""
    resp = await analytics_client.get("/api/analytics/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_summary_returns_403_for_non_admin(analytics_client):
    """Non-admin authenticated user is forbidden."""
    token = await _signup_and_login(analytics_client, "waiter1", "secret123", ["waiter"])
    resp = await analytics_client.get(
        "/api/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------- Shape / contract tests ----------

@pytest.mark.asyncio
async def test_summary_returns_200_for_admin(analytics_client):
    """Admin user receives 200 with all required keys."""
    token = await _signup_and_login(analytics_client, "admin1", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_summary_contains_all_required_keys(analytics_client):
    """Response includes every key defined in the spec."""
    token = await _signup_and_login(analytics_client, "admin2", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {
        "today_revenue",
        "revenue_change_vs_previous_day",
        "orders_count",
        "average_ticket_size",
        "top_items_today",
        "busiest_workstation",
        "peak_hour",
    }
    assert expected_keys == set(data.keys())


# ---------- Empty / safe-default tests ----------

@pytest.mark.asyncio
async def test_summary_empty_db_returns_safe_defaults(analytics_client):
    """Empty database returns zeroed numeric fields, not errors."""
    token = await _signup_and_login(analytics_client, "admin3", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["today_revenue"] == 0.0
    assert data["orders_count"] == 0
    assert data["average_ticket_size"] == 0.0
    assert data["revenue_change_vs_previous_day"] == 0.0
    assert data["top_items_today"] == []
    assert data["busiest_workstation"] == ""
    assert data["peak_hour"] == ""


@pytest.mark.asyncio
async def test_summary_empty_date_range_returns_zeros(analytics_client):
    """Explicit date range with no data returns zeroed payload safely."""
    token = await _signup_and_login(analytics_client, "admin4", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/summary?from=2000-01-01&to=2000-01-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["today_revenue"] == 0.0
    assert data["orders_count"] == 0


# ---------- Data accuracy tests ----------

@pytest.mark.asyncio
async def test_summary_reflects_seeded_order(analytics_client, analytics_storage):
    """Revenue and orders_count match seeded data."""
    _seed_closed_order(analytics_storage, order_total_cents=2000, item_name="Steak",
                       item_qty=2, item_category="grill")

    token = await _signup_and_login(analytics_client, "admin5", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["orders_count"] == 1
    assert data["today_revenue"] == pytest.approx(20.0, abs=0.01)
    assert len(data["top_items_today"]) == 1
    assert data["top_items_today"][0]["name"] == "Steak"
    assert data["top_items_today"][0]["qty"] == 2
    assert data["busiest_workstation"] == "grill"
    assert data["peak_hour"] != ""


@pytest.mark.asyncio
async def test_summary_counts_one_checkout_for_multi_item_session(analytics_client, analytics_storage):
    """Multiple legacy Order rows in one closed session count as one checkout."""
    _seed_closed_session_with_multiple_orders(
        analytics_storage,
        orders=[
            {"order_total_cents": 1200, "item_name": "Fries", "item_qty": 1, "item_category": "kitchen"},
            {"order_total_cents": 1800, "item_name": "Beer", "item_qty": 1, "item_category": "drinks"},
            {"order_total_cents": 700, "item_name": "Salad", "item_qty": 1, "item_category": "kitchen"},
        ],
    )

    token = await _signup_and_login(analytics_client, "admin_multi_checkout", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["today_revenue"] == pytest.approx(37.0, abs=0.01)
    assert data["orders_count"] == 1
    assert data["average_ticket_size"] == pytest.approx(37.0, abs=0.01)


@pytest.mark.asyncio
async def test_summary_invalid_date_format_returns_422(analytics_client):
    """Malformed date parameter returns 422."""
    token = await _signup_and_login(analytics_client, "admin6", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/summary?from=not-a-date",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ---------- Revenue per day endpoint tests ----------

@pytest.mark.asyncio
async def test_revenue_per_day_returns_401_without_auth(analytics_client):
    resp = await analytics_client.get("/api/analytics/revenue-per-day")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_revenue_per_day_returns_403_for_non_admin(analytics_client):
    token = await _signup_and_login(analytics_client, "waiter_rpd", "secret123", ["waiter"])
    resp = await analytics_client.get(
        "/api/analytics/revenue-per-day",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_revenue_per_day_returns_array_for_admin(analytics_client, analytics_storage):
    _seed_closed_order(
        analytics_storage,
        order_total_cents=2200,
        item_name="Pasta",
        item_qty=2,
        item_category="kitchen",
    )
    token = await _signup_and_login(analytics_client, "admin_rpd", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/revenue-per-day",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert set(data[0].keys()) == {"date", "revenue"}
    assert data[0]["revenue"] == pytest.approx(22.0, abs=0.01)


@pytest.mark.asyncio
async def test_revenue_per_day_honors_date_window(analytics_client, analytics_storage):
    today = datetime.now()
    old_day = today - timedelta(days=10)

    _seed_closed_order(analytics_storage, order_total_cents=1000, item_name="Old", created_at=old_day)
    _seed_closed_order(analytics_storage, order_total_cents=3000, item_name="Today", created_at=today)

    token = await _signup_and_login(analytics_client, "admin_rpd_window", "secret123", ["admin"])
    day = today.date().isoformat()
    resp = await analytics_client.get(
        f"/api/analytics/revenue-per-day?from={day}&to={day}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["date"] == day
    assert data[0]["revenue"] == pytest.approx(30.0, abs=0.01)


# ---------- Revenue per workstation endpoint tests ----------

@pytest.mark.asyncio
async def test_revenue_per_workstation_returns_401_without_auth(analytics_client):
    resp = await analytics_client.get("/api/analytics/revenue-per-workstation")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_revenue_per_workstation_returns_403_for_non_admin(analytics_client):
    token = await _signup_and_login(analytics_client, "waiter_rpw", "secret123", ["waiter"])
    resp = await analytics_client.get(
        "/api/analytics/revenue-per-workstation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_revenue_per_workstation_returns_array_for_admin(analytics_client, analytics_storage):
    _seed_closed_order(
        analytics_storage,
        order_total_cents=1800,
        item_name="Steak",
        item_qty=1,
        item_category="grill",
    )
    _seed_closed_order(
        analytics_storage,
        order_total_cents=900,
        item_name="Wine",
        item_qty=1,
        item_category="drinks",
    )

    token = await _signup_and_login(analytics_client, "admin_rpw", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/revenue-per-workstation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert set(data[0].keys()) == {"workstation", "revenue"}

    by_station = {row["workstation"]: row["revenue"] for row in data}
    assert by_station["grill"] == pytest.approx(18.0, abs=0.01)
    assert by_station["drinks"] == pytest.approx(9.0, abs=0.01)


@pytest.mark.asyncio
async def test_revenue_per_workstation_empty_returns_empty_array(analytics_client):
    token = await _signup_and_login(analytics_client, "admin_rpw_empty", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/revenue-per-workstation?from=2000-01-01&to=2000-01-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------- Orders by hour endpoint tests ----------

@pytest.mark.asyncio
async def test_orders_by_hour_returns_401_without_auth(analytics_client):
    resp = await analytics_client.get("/api/analytics/orders-by-hour")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_orders_by_hour_returns_403_for_non_admin(analytics_client):
    token = await _signup_and_login(analytics_client, "waiter_obh", "secret123", ["waiter"])
    resp = await analytics_client.get(
        "/api/analytics/orders-by-hour",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_orders_by_hour_returns_24_zero_filled_rows(analytics_client):
    token = await _signup_and_login(analytics_client, "admin_obh_zeros", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/orders-by-hour?from=2000-01-01&to=2000-01-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)
    assert len(data) == 24
    assert data[0]["hour"] == "00:00"
    assert data[-1]["hour"] == "23:00"
    assert all(row["orders_count"] == 0 for row in data)


@pytest.mark.asyncio
async def test_orders_by_hour_reflects_seeded_hours(analytics_client, analytics_storage):
    day = datetime(2026, 3, 24, 11, 15)
    _seed_closed_order(analytics_storage, item_name="A", created_at=day)
    _seed_closed_order(analytics_storage, item_name="B", created_at=day.replace(hour=11, minute=45))
    _seed_closed_order(analytics_storage, item_name="C", created_at=day.replace(hour=13, minute=0))

    token = await _signup_and_login(analytics_client, "admin_obh", "secret123", ["admin"])
    d = day.date().isoformat()
    resp = await analytics_client.get(
        f"/api/analytics/orders-by-hour?from={d}&to={d}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    by_hour = {row["hour"]: row["orders_count"] for row in data}

    assert by_hour["11:00"] == 2
    assert by_hour["13:00"] == 1
    assert by_hour["12:00"] == 0


# ---------- Low rotation items endpoint tests ----------

@pytest.mark.asyncio
async def test_low_rotation_items_returns_401_without_auth(analytics_client):
    resp = await analytics_client.get("/api/analytics/low-rotation-items")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_low_rotation_items_returns_403_for_non_admin(analytics_client):
    token = await _signup_and_login(analytics_client, "waiter_lri", "secret123", ["waiter"])
    resp = await analytics_client.get(
        "/api/analytics/low-rotation-items",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_low_rotation_items_returns_empty_array_for_no_data(analytics_client):
    token = await _signup_and_login(analytics_client, "admin_lri_empty", "secret123", ["admin"])
    resp = await analytics_client.get(
        "/api/analytics/low-rotation-items?from=2000-01-01&to=2000-01-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_low_rotation_items_returns_bottom_10(analytics_client, analytics_storage):
    base = datetime(2026, 3, 24, 12, 0)
    # qty_sold values: 1..12 -> endpoint should return first ten (A..J)
    _seed_closed_order(analytics_storage, item_name="A", item_qty=1, created_at=base)
    _seed_closed_order(analytics_storage, item_name="B", item_qty=2, created_at=base)
    _seed_closed_order(analytics_storage, item_name="C", item_qty=3, created_at=base)
    _seed_closed_order(analytics_storage, item_name="D", item_qty=4, created_at=base)
    _seed_closed_order(analytics_storage, item_name="E", item_qty=5, created_at=base)
    _seed_closed_order(analytics_storage, item_name="F", item_qty=6, created_at=base)
    _seed_closed_order(analytics_storage, item_name="G", item_qty=7, created_at=base)
    _seed_closed_order(analytics_storage, item_name="H", item_qty=8, created_at=base)
    _seed_closed_order(analytics_storage, item_name="I", item_qty=9, created_at=base)
    _seed_closed_order(analytics_storage, item_name="J", item_qty=10, created_at=base)
    _seed_closed_order(analytics_storage, item_name="K", item_qty=11, created_at=base)
    _seed_closed_order(analytics_storage, item_name="L", item_qty=12, created_at=base)

    token = await _signup_and_login(analytics_client, "admin_lri", "secret123", ["admin"])
    d = base.date().isoformat()
    resp = await analytics_client.get(
        f"/api/analytics/low-rotation-items?from={d}&to={d}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 10
    assert set(data[0].keys()) == {"item_name", "qty_sold"}
    qtys = [row["qty_sold"] for row in data]
    assert qtys == sorted(qtys)
    assert [row["item_name"] for row in data] == ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
