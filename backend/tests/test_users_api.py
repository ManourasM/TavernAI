"""Tests for admin user management API."""

import pytest
import pytest_asyncio

from app.db import Base
from app.db.dependencies import verify_password
from app.storage.sqlalchemy_adapter import SQLAlchemyStorage


@pytest.fixture
def users_storage(tmp_path):
    db_path = tmp_path / "users.db"
    storage = SQLAlchemyStorage(f"sqlite:///{db_path}")
    Base.metadata.create_all(storage.engine)
    yield storage
    storage.close()


@pytest_asyncio.fixture
async def users_client(users_storage, monkeypatch):
    import httpx
    from httpx import ASGITransport
    from app.main import app, get_storage
    from app.db.dependencies import get_sqlalchemy_session
    import app.api.nlp_router as nlp_router
    import app.api.users_router as users_router
    import app.api.auth_router as auth_router
    import app.db.dependencies as db_dependencies

    original_storage = app.state.storage
    original_overrides = app.dependency_overrides.copy()

    app.state.storage = users_storage

    def override_get_storage():
        return users_storage

    def override_get_sqlalchemy_session(request=None):
        return users_storage._get_session()

    app.dependency_overrides[get_storage] = override_get_storage
    app.dependency_overrides[get_sqlalchemy_session] = override_get_sqlalchemy_session
    app.dependency_overrides[nlp_router.get_storage_dependency] = override_get_storage

    # Monkeypatch to ensure all routers use the test session
    monkeypatch.setattr(db_dependencies, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(nlp_router, "_get_db_session", lambda _storage: users_storage._get_session())
    monkeypatch.setattr(auth_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)
    monkeypatch.setattr(users_router, "get_sqlalchemy_session", override_get_sqlalchemy_session)

    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.state.storage = original_storage
        app.dependency_overrides = original_overrides


async def _signup_and_login(client, username, password, roles):
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
async def test_create_user_and_hash_password(users_client, users_storage):
    admin_token = await _signup_and_login(users_client, "admin", "secret123", ["admin"])

    payload = {"username": "waiter1", "password": "pass123", "roles": ["waiter"]}
    response = await users_client.post(
        "/api/users",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "waiter1"
    assert "waiter" in data["roles"]

    from app.db.models import User
    session = users_storage._get_session()
    try:
        user = session.query(User).filter_by(username="waiter1").first()
    finally:
        session.close()

    assert user is not None
    assert user.password_hash != "pass123"
    assert verify_password("pass123", user.password_hash)


@pytest.mark.asyncio
async def test_create_duplicate_username(users_client):
    admin_token = await _signup_and_login(users_client, "admin2", "secret123", ["admin"])

    payload = {"username": "dup", "password": "pass123", "roles": ["waiter"]}
    first = await users_client.post(
        "/api/users",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert first.status_code == 200

    second = await users_client.post(
        "/api/users",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert second.status_code in (400, 409)


@pytest.mark.asyncio
async def test_list_users(users_client):
    admin_token = await _signup_and_login(users_client, "admin3", "secret123", ["admin"])

    await users_client.post(
        "/api/users",
        json={"username": "user1", "password": "pass123", "roles": ["waiter"]},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    response = await users_client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert any(u["username"] == "user1" for u in data)


@pytest.mark.asyncio
async def test_update_user_roles(users_client):
    admin_token = await _signup_and_login(users_client, "admin4", "secret123", ["admin"])

    create_resp = await users_client.post(
        "/api/users",
        json={"username": "user2", "password": "pass123", "roles": ["waiter"]},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    user_id = create_resp.json()["id"]

    update_resp = await users_client.put(
        f"/api/users/{user_id}",
        json={"roles": ["station_kitchen"]},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["roles"] == ["station_kitchen"]


@pytest.mark.asyncio
async def test_delete_user(users_client):
    admin_token = await _signup_and_login(users_client, "admin5", "secret123", ["admin"])

    create_resp = await users_client.post(
        "/api/users",
        json={"username": "user3", "password": "pass123", "roles": ["waiter"]},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    user_id = create_resp.json()["id"]

    delete_resp = await users_client.delete(
        f"/api/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert delete_resp.status_code == 200


@pytest.mark.asyncio
async def test_non_admin_forbidden(users_client):
    admin_token = await _signup_and_login(users_client, "admin6", "secret123", ["admin"])

    await users_client.post(
        "/api/users",
        json={"username": "user4", "password": "pass123", "roles": ["waiter"]},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    user_token = await _signup_and_login(users_client, "basic", "secret123", [])

    resp = await users_client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert resp.status_code == 403
