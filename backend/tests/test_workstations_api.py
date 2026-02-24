"""Tests for workstations API."""

import pytest
import pytest_asyncio

from app.db import Base
from app.storage.sqlalchemy_adapter import SQLAlchemyStorage


@pytest.fixture
def workstations_storage(tmp_path):
    db_path = tmp_path / "workstations.db"
    storage = SQLAlchemyStorage(f"sqlite:///{db_path}")
    Base.metadata.create_all(storage.engine)
    yield storage
    storage.close()


@pytest_asyncio.fixture
async def workstations_client(workstations_storage, monkeypatch):
    import httpx
    from httpx import ASGITransport
    from app.main import app, get_storage
    from app.db.dependencies import get_sqlalchemy_session
    import app.api.nlp_router as nlp_router
    import app.api.users_router as users_router
    import app.api.workstations_router as workstations_router
    import app.api.auth_router as auth_router
    import app.api.menu_router as menu_router
    import app.db.dependencies as db_dependencies

    original_storage = app.state.storage
    original_overrides = app.dependency_overrides.copy()

    app.state.storage = workstations_storage

    def override_get_storage():
        return workstations_storage

    def override_get_sqlalchemy_session(request=None):
        return workstations_storage._get_session()

    app.dependency_overrides[get_storage] = override_get_storage
    app.dependency_overrides[get_sqlalchemy_session] = override_get_sqlalchemy_session
    app.dependency_overrides[nlp_router.get_storage_dependency] = override_get_storage

    # Monkeypatch to ensure all routers use the test session
    monkeypatch.setattr(db_dependencies, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(nlp_router, "_get_db_session", lambda _storage: workstations_storage._get_session())
    monkeypatch.setattr(auth_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(users_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(workstations_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(menu_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)

    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.state.storage = original_storage
        app.dependency_overrides = original_overrides


async def _signup_and_login(client, username, password, roles):
    """Helper to create user and get auth token."""
    signup_payload = {"username": username, "password": password, "roles": roles}
    signup_response = await client.post("/api/auth/signup", json=signup_payload)
    assert signup_response.status_code == 200

    login_response = await client.post(
        "/api/auth/login",
        json={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_workstation(workstations_client):
    """Test creating a new workstation."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    payload = {"name": "Grill Station", "slug": "grill"}
    response = await workstations_client.post(
        "/api/workstations",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Grill Station"
    assert data["slug"] == "grill"
    assert data["active"] is True


@pytest.mark.asyncio
async def test_create_workstation_requires_admin(workstations_client):
    """Test that only admins can create workstations."""
    user_token = await _signup_and_login(workstations_client, "user", "secret123", ["waiter"])

    payload = {"name": "Kitchen", "slug": "kitchen"}
    response = await workstations_client.post(
        "/api/workstations",
        json=payload,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_duplicate_slug(workstations_client):
    """Test that duplicate slugs are rejected."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    payload = {"name": "Kitchen", "slug": "kitchen"}
    first = await workstations_client.post(
        "/api/workstations",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert first.status_code == 201

    second = await workstations_client.post(
        "/api/workstations",
        json={"name": "Kitchen 2", "slug": "kitchen"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_list_workstations(workstations_client):
    """Test listing all workstations."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Create multiple workstations
    for name, slug in [("Grill", "grill"), ("Kitchen", "kitchen"), ("Drinks", "drinks")]:
        await workstations_client.post(
            "/api/workstations",
            json={"name": name, "slug": slug},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    response = await workstations_client.get("/api/workstations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert any(w["slug"] == "grill" for w in data)
    assert any(w["slug"] == "kitchen" for w in data)
    assert any(w["slug"] == "drinks" for w in data)


@pytest.mark.asyncio
async def test_get_active_categories(workstations_client):
    """Test getting active workstation slugs as categories."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Create workstations
    await workstations_client.post(
        "/api/workstations",
        json={"name": "Grill", "slug": "grill"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    await workstations_client.post(
        "/api/workstations",
        json={"name": "Kitchen", "slug": "kitchen"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    response = await workstations_client.get("/api/workstations/active")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(c["slug"] == "grill" for c in data)
    assert any(c["slug"] == "kitchen" for c in data)


@pytest.mark.asyncio
async def test_update_workstation_name(workstations_client):
    """Test updating workstation name."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Create workstation
    create_resp = await workstations_client.post(
        "/api/workstations",
        json={"name": "Grill Station", "slug": "grill"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    ws_id = create_resp.json()["id"]

    # Update name
    update_resp = await workstations_client.put(
        f"/api/workstations/{ws_id}",
        json={"name": "BBQ Grill"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "BBQ Grill"
    assert data["slug"] == "grill"  # slug unchanged


@pytest.mark.asyncio
async def test_update_workstation_slug(workstations_client):
    """Test updating workstation slug."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Create workstation
    create_resp = await workstations_client.post(
        "/api/workstations",
        json={"name": "Grill", "slug": "grill"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    ws_id = create_resp.json()["id"]

    # Update slug
    update_resp = await workstations_client.put(
        f"/api/workstations/{ws_id}",
        json={"slug": "bbq"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["slug"] == "bbq"
    assert data["name"] == "Grill"  # name unchanged


@pytest.mark.asyncio
async def test_update_workstation_active_status(workstations_client):
    """Test deactivating a workstation."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Create workstation
    create_resp = await workstations_client.post(
        "/api/workstations",
        json={"name": "Grill", "slug": "grill"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    ws_id = create_resp.json()["id"]
    assert create_resp.json()["active"] is True

    # Deactivate
    update_resp = await workstations_client.put(
        f"/api/workstations/{ws_id}",
        json={"active": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["active"] is False


@pytest.mark.asyncio
async def test_delete_workstation_soft_delete(workstations_client):
    """Test soft-deleting a workstation (marks as inactive)."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Create workstation
    create_resp = await workstations_client.post(
        "/api/workstations",
        json={"name": "Grill", "slug": "grill"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    ws_id = create_resp.json()["id"]

    # Delete (soft)
    delete_resp = await workstations_client.delete(
        f"/api/workstations/{ws_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert delete_resp.status_code == 200
    data = delete_resp.json()
    assert data["status"] == "deleted"

    # Verify it's no longer in active categories
    active_resp = await workstations_client.get("/api/workstations/active")
    assert len(active_resp.json()) == 0

    # But should still be in full list
    all_resp = await workstations_client.get("/api/workstations")
    assert any(w["id"] == ws_id and w["active"] is False for w in all_resp.json())


@pytest.mark.asyncio
async def test_menu_includes_available_categories(workstations_client):
    """Test that GET /api/menu includes available_categories."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Create workstations
    await workstations_client.post(
        "/api/workstations",
        json={"name": "Grill", "slug": "grill"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    await workstations_client.post(
        "/api/workstations",
        json={"name": "Kitchen", "slug": "kitchen"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Get menu
    response = await workstations_client.get("/api/menu")
    assert response.status_code == 200
    data = response.json()
    assert "available_categories" in data
    categories = data["available_categories"]
    assert "grill" in categories
    assert "kitchen" in categories


@pytest.mark.asyncio
async def test_menu_categories_excludes_inactive_workstations(workstations_client):
    """Test that inactive workstations don't appear in available_categories."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Create and deactivate a workstation
    create_resp = await workstations_client.post(
        "/api/workstations",
        json={"name": "Future", "slug": "future"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    ws_id = create_resp.json()["id"]

    await workstations_client.put(
        f"/api/workstations/{ws_id}",
        json={"active": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Create active workstation
    await workstations_client.post(
        "/api/workstations",
        json={"name": "Kitchen", "slug": "kitchen"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Get menu
    response = await workstations_client.get("/api/menu")
    data = response.json()
    categories = data["available_categories"]
    assert "future" not in categories
    assert "kitchen" in categories


@pytest.mark.asyncio
async def test_invalid_slug_format(workstations_client):
    """Test that invalid slug formats are rejected."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    # Test with invalid characters
    payload = {"name": "Invalid", "slug": "invalid@#$"}
    response = await workstations_client.post(
        "/api/workstations",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_empty_name_rejected(workstations_client):
    """Test that empty names are rejected."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    payload = {"name": "", "slug": "empty"}
    response = await workstations_client.post(
        "/api/workstations",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_workstation_slug_normalization(workstations_client):
    """Test that slug is normalized to lowercase."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    payload = {"name": "Mixed Case", "slug": "MixedCase"}
    response = await workstations_client.post(
        "/api/workstations",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "mixedcase"


@pytest.mark.asyncio
async def test_nonexistent_workstation_update(workstations_client):
    """Test updating non-existent workstation returns 404."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    response = await workstations_client.put(
        "/api/workstations/999",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_nonexistent_workstation_delete(workstations_client):
    """Test deleting non-existent workstation returns 404."""
    admin_token = await _signup_and_login(workstations_client, "admin", "secret123", ["admin"])

    response = await workstations_client.delete(
        "/api/workstations/999",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
