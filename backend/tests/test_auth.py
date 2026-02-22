"""Tests for auth signup/login and admin enforcement."""

import pytest
import pytest_asyncio

from app.db import Base
from app.storage.sqlalchemy_adapter import SQLAlchemyStorage


@pytest.fixture
def auth_storage(tmp_path):
    """Create SQLAlchemyStorage with file-backed database for auth tests."""
    db_path = tmp_path / "auth.db"
    storage = SQLAlchemyStorage(f"sqlite:///{db_path}")
    Base.metadata.create_all(storage.engine)
    yield storage
    storage.close()


@pytest_asyncio.fixture
async def auth_client(auth_storage, monkeypatch):
    """Create async HTTP client with isolated auth storage."""
    import httpx
    from httpx import ASGITransport
    from app.main import app, get_storage
    import app.api.nlp_router as nlp_router

    original_storage = app.state.storage
    original_overrides = app.dependency_overrides.copy()

    app.state.storage = auth_storage

    def override_get_storage():
        return auth_storage

    app.dependency_overrides[get_storage] = override_get_storage
    app.dependency_overrides[nlp_router.get_storage_dependency] = override_get_storage

    monkeypatch.setattr(nlp_router, "_get_db_session", lambda _storage: auth_storage._get_session())

    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.state.storage = original_storage
        app.dependency_overrides = original_overrides


@pytest.mark.asyncio
async def test_signup_login_flow(auth_client):
    signup_payload = {
        "username": "admin_user",
        "password": "secret123",
        "roles": ["admin"]
    }

    signup_response = await auth_client.post("/api/auth/signup", json=signup_payload)
    assert signup_response.status_code == 200
    signup_data = signup_response.json()
    assert signup_data["username"] == "admin_user"
    assert "admin" in signup_data["roles"]

    login_payload = {
        "username": "admin_user",
        "password": "secret123"
    }
    login_response = await auth_client.post("/api/auth/login", json=login_payload)
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_require_admin_blocks_non_admin(auth_client):
    # Create non-admin user
    signup_payload = {
        "username": "basic_user",
        "password": "secret123",
        "roles": []
    }
    await auth_client.post("/api/auth/signup", json=signup_payload)

    login_response = await auth_client.post(
        "/api/auth/login",
        json={"username": "basic_user", "password": "secret123"}
    )
    token = login_response.json()["access_token"]

    response = await auth_client.get(
        "/api/nlp/samples",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_allows_admin(auth_client):
    # Create admin user
    signup_payload = {
        "username": "admin_user2",
        "password": "secret123",
        "roles": ["admin"]
    }
    await auth_client.post("/api/auth/signup", json=signup_payload)

    login_response = await auth_client.post(
        "/api/auth/login",
        json={"username": "admin_user2", "password": "secret123"}
    )
    token = login_response.json()["access_token"]

    response = await auth_client.get(
        "/api/nlp/samples",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
