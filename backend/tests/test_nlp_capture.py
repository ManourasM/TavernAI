"""Tests for NLP training sample capture and export."""

import csv
import io
import pytest
import pytest_asyncio

from app.db import Base
from app.db.dependencies import require_admin
from app.storage.sqlalchemy_adapter import SQLAlchemyStorage


@pytest.fixture
def nlp_storage(tmp_path):
    """Create SQLAlchemyStorage with file-backed database for NLP tests."""
    db_path = tmp_path / "nlp.db"
    storage = SQLAlchemyStorage(f"sqlite:///{db_path}")
    Base.metadata.create_all(storage.engine)
    yield storage
    storage.close()


@pytest_asyncio.fixture
async def nlp_client(nlp_storage, monkeypatch):
    """Create async HTTP client with isolated NLP router only."""
    import httpx
    from httpx import ASGITransport
    from fastapi import FastAPI
    import app.api.nlp_router as nlp_router

    app = FastAPI()
    app.include_router(nlp_router.router)

    # Override storage dependencies for this isolated app
    def override_get_storage():
        return nlp_storage

    app.dependency_overrides[nlp_router.get_storage_dependency] = override_get_storage
    app.dependency_overrides[require_admin] = lambda: {"id": 1, "roles": ["admin"]}
    app.dependency_overrides[nlp_router.require_admin] = lambda: {"id": 1, "roles": ["admin"]}

    # Force NLP router to use the test storage session directly
    monkeypatch.setattr(nlp_router, "_get_db_session", lambda _storage: nlp_storage._get_session())

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_capture_creates_sample(nlp_client):
    payload = {
        "raw_text": "1 χωριάτικη",
        "predicted_item_id": 10,
        "corrected_item_id": 11,
        "user_id": 5
    }
    response = await nlp_client.post("/api/nlp/capture", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["raw_text"] == payload["raw_text"]
    assert data["predicted_item_id"] == payload["predicted_item_id"]
    assert data["corrected_item_id"] == payload["corrected_item_id"]
    assert data["user_id"] == payload["user_id"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_samples(nlp_client):
    payload = {
        "raw_text": "2 μπριζολα",
        "predicted_item_id": 12,
        "corrected_item_id": 13,
        "user_id": 7
    }
    await nlp_client.post("/api/nlp/capture", json=payload)

    response = await nlp_client.get("/api/nlp/samples")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    sample = data["items"][0]
    assert "raw_text" in sample
    assert "predicted_item_id" in sample
    assert "corrected_item_id" in sample


@pytest.mark.asyncio
async def test_export_samples_csv(nlp_client):
    payload = {
        "raw_text": "1 μυθος",
        "predicted_item_id": 20,
        "corrected_item_id": 21,
        "user_id": 3
    }
    await nlp_client.post("/api/nlp/capture", json=payload)

    response = await nlp_client.post("/api/nlp/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    content = response.text
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    # Header + at least one row
    assert len(rows) >= 2
    assert rows[0] == [
        "id",
        "raw_text",
        "predicted_item_id",
        "corrected_item_id",
        "user_id",
        "created_at"
    ]
    assert rows[1][1] == payload["raw_text"]
