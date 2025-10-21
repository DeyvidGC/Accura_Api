"""Unit tests for the SendGrid email helper utilities."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

# Ensure the project root (which contains the ``app`` package) is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Provide lightweight stand-ins for the optional pydantic dependencies used by ``app.config``
pydantic_module = types.ModuleType("pydantic")


class _StubBaseSettings:
    def __init__(self, **values):
        for name, attribute in self.__class__.__dict__.items():
            if name.startswith("_"):
                continue
            if callable(attribute):
                continue
            setattr(self, name, attribute)
        for key, value in values.items():
            setattr(self, key, value)


def _stub_field(*, default=None, **_kwargs):
    return default


pydantic_module.BaseSettings = _StubBaseSettings
pydantic_module.Field = _stub_field
sys.modules.setdefault("pydantic", pydantic_module)

pydantic_settings_module = types.ModuleType("pydantic_settings")
pydantic_settings_module.BaseSettings = _StubBaseSettings
sys.modules.setdefault("pydantic_settings", pydantic_settings_module)

# Provide a minimal stub for the sendgrid package so the module under test can import it
sendgrid_module = types.ModuleType("sendgrid")


class _StubMail:
    """Simple stand-in for ``sendgrid.helpers.mail.Mail`` used in tests."""

    def __init__(self, **kwargs):  # pragma: no cover - trivial initialiser
        self.payload = kwargs


class _StubSendGridAPIClient:
    """Default stub client that returns a successful response."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def send(self, message):  # pragma: no cover - overridden per test
        return types.SimpleNamespace(status_code=202, body=None)


helpers_module = types.ModuleType("sendgrid.helpers")
helpers_mail_module = types.ModuleType("sendgrid.helpers.mail")
helpers_mail_module.Mail = _StubMail
helpers_module.mail = helpers_mail_module
sendgrid_module.helpers = types.SimpleNamespace(mail=helpers_mail_module)
sendgrid_module.SendGridAPIClient = _StubSendGridAPIClient

sys.modules.setdefault("sendgrid", sendgrid_module)
sys.modules.setdefault("sendgrid.helpers", helpers_module)
sys.modules.setdefault("sendgrid.helpers.mail", helpers_mail_module)

from app.infrastructure import email as email_module


def test_send_email_without_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """When SendGrid settings are missing the helper should exit early."""

    class DummySettings:
        sendgrid_api_key = None
        sendgrid_sender = None

    monkeypatch.setattr(email_module, "get_settings", lambda: DummySettings())

    assert email_module.send_email("Subject", "<p>Body</p>", "user@example.com") is False


def test_send_email_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful SendGrid response should return ``True``."""

    class SuccessfulClient(_StubSendGridAPIClient):
        def send(self, message):
            return types.SimpleNamespace(status_code=202, body=None)

    class DummySettings:
        sendgrid_api_key = "SG.fake"
        sendgrid_sender = "sender@example.com"

    monkeypatch.setattr(email_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(email_module, "SendGridAPIClient", SuccessfulClient)

    assert email_module.send_email("Subject", "<p>Body</p>", "user@example.com") is True


def test_send_email_logs_forbidden_error(monkeypatch: pytest.MonkeyPatch, caplog):
    """Forbidden responses from SendGrid should surface meaningful log details."""

    class FakeForbiddenError(Exception):
        status_code = 403
        body = json.dumps(
            {
                "errors": [
                    {
                        "message": "The provided authorization grant is invalid.",
                        "help": "https://sendgrid.com/docs/API_Reference/Web_API_v3/How_To_Use_The_Web_API_v3/authentication.html",
                    }
                ]
            }
        ).encode()

    class FailingClient(_StubSendGridAPIClient):
        def send(self, message):
            raise FakeForbiddenError()

    class DummySettings:
        sendgrid_api_key = "SG.fake"
        sendgrid_sender = "sender@example.com"

    monkeypatch.setattr(email_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(email_module, "SendGridAPIClient", FailingClient)

    with caplog.at_level("ERROR"):
        result = email_module.send_email("Subject", "<p>Body</p>", "user@example.com")

    assert result is False
    assert "status 403" in caplog.text
    assert "authorization grant is invalid" in caplog.text
