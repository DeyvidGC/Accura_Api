"""Integration tests for the user API endpoints."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


TEST_DB_PATH = Path(__file__).parent / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"


def _reset_database() -> None:
    """Reload database related modules to ensure a clean state."""

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    from app import config as app_config

    app_config.get_settings.cache_clear()
    importlib.reload(app_config)

    from app.infrastructure import database

    importlib.reload(database)
    database.initialize_database()


@pytest.fixture(autouse=True)
def setup_database():
    """Prepare a fresh database for every test."""

    _reset_database()
    yield
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture()
def client():
    """Return a test client bound to a clean application instance."""

    from app.infrastructure import database

    database.Base.metadata.drop_all(bind=database.engine, checkfirst=True)
    database.Base.metadata.create_all(bind=database.engine)

    from main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_user_crud_and_auth_flow(client: TestClient) -> None:
    """Exercise the full CRUD lifecycle and authentication for users."""

    registration_payload = {
        "name": "Test User",
        "alias": "tester",
        "email": "user@example.com",
        "password": "Secret123",
        "must_change_password": False,
    }

    response = client.post("/users/", json=registration_payload)
    assert response.status_code == 201
    created_user = response.json()
    user_id = created_user["id"]

    token_response = client.post(
        "/auth/token",
        data={"username": registration_payload["email"], "password": registration_payload["password"]},
    )
    assert token_response.status_code == 200
    access_token = token_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    list_response = client.get("/users/", headers=auth_headers)
    assert list_response.status_code == 200
    assert any(user["email"] == registration_payload["email"] for user in list_response.json())

    detail_response = client.get(f"/users/{user_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["email"] == registration_payload["email"]

    updated_payload = {
        "name": "Updated User",
        "alias": "updated",
        "email": "updated@example.com",
        "must_change_password": True,
        "is_active": True,
        "password": "NewSecret123",
    }
    update_response = client.put(
        f"/users/{user_id}",
        json=updated_payload,
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["email"] == updated_payload["email"]
    assert update_response.json()["must_change_password"] is True

    new_token_response = client.post(
        "/auth/token",
        data={"username": updated_payload["email"], "password": updated_payload["password"]},
    )
    assert new_token_response.status_code == 200

    delete_response = client.delete(f"/users/{user_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    not_found_response = client.get(f"/users/{user_id}", headers=auth_headers)
    assert not_found_response.status_code == 404

