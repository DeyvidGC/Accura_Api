"""Tests for the authentication token endpoint."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

TEST_DB_PATH = Path(tempfile.gettempdir()) / "accura_api_test_auth_token.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from app.config import get_settings

get_settings.cache_clear()

from app.infrastructure.database import (  # noqa: E402
    Base,
    SessionLocal,
    engine,
    initialize_database,
)
from app.infrastructure.models import RoleModel, UserModel  # noqa: E402
from app.infrastructure.security import get_password_hash  # noqa: E402
from main import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database() -> None:
    """Ensure the test database starts from a clean state for each test."""

    Base.metadata.drop_all(bind=engine)
    initialize_database()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_user(*, must_change_password: bool, email: str, password: str) -> None:
    """Insert a user record with the provided password settings."""

    hashed_password = get_password_hash(password)
    with SessionLocal() as session:
        role = RoleModel(name="Administrator", alias="admin")
        session.add(role)
        session.commit()
        session.refresh(role)

        user = UserModel(
            role_id=role.id,
            name="Test User",
            email=email,
            password=hashed_password,
            must_change_password=must_change_password,
            is_active=True,
        )
        session.add(user)
        session.commit()


@pytest.mark.parametrize("must_change", [True, False])
def test_login_includes_must_change_password_flag(must_change: bool) -> None:
    """Obtaining a token should succeed regardless of the password reset flag."""

    email = "user@example.com"
    password = "StrongPass123"

    _create_user(must_change_password=must_change, email=email, password=password)

    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/auth/token",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["role"] == "admin"
    assert bool(payload["access_token"])
    assert payload["must_change_password"] is must_change
