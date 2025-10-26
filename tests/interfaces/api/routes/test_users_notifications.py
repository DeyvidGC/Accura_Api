"""Tests for helper utilities in the users API routes."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.interfaces.api.routes_helpers import compute_credentials_notification


@pytest.mark.parametrize(
    (
        "email_changed",
        "password_changed",
        "is_admin",
        "acting_on_self",
        "expected_send",
        "expected_include",
    ),
    [
        (True, False, True, True, True, True),
        (True, False, True, False, True, True),
        (False, True, True, True, True, False),
        (False, True, True, False, True, True),
        (False, True, False, True, False, False),
        (False, False, True, True, False, False),
    ],
)
def test_compute_credentials_notification(
    email_changed,
    password_changed,
    is_admin,
    acting_on_self,
    expected_send,
    expected_include,
):
    """The helper must describe how to notify the user about updates."""

    decision = compute_credentials_notification(
        email_changed=email_changed,
        password_changed=password_changed,
        is_admin=is_admin,
        acting_on_self=acting_on_self,
    )

    assert decision.should_send is expected_send
    assert decision.include_password is expected_include
