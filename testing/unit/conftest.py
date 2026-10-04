"""
Shared fixtures for the offline unit test suite.

Every test gets a fresh, file-backed SQLite database, and all external
services (Slack, GitHub, Gemini) are faked, so the suite needs no network,
no Postgres and no secrets.
"""
import os

# Must be set before any backend module is imported: backend.database builds
# its engine from DATABASE_URL at import time, and load_dotenv() never
# overrides variables that are already set.
os.environ["DATABASE_URL"] = "sqlite://"
# Both spellings are set so a value loaded from a local .env can't take precedence
os.environ["SIGNING_SECRET"] = os.environ["SIGNING_SECRETE"] = "test-slack-signing-secret"
os.environ["GITHUB_SECRET"] = os.environ["GITHUB_SECRETE"] = "test-github-secret"
os.environ["BOT_AUTH_TOCKEN"] = "xoxb-test-token"
os.environ["GEMINI_API"] = "test-gemini-key"

from datetime import datetime

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.auth as auth
import backend.crud as crud
import backend.sla as sla
from backend.database import Base
from backend.models import Admin, Ticket, User


# ---------------------------------------------------------------------------
# Async support (uses the anyio pytest plugin, no extra dependency needed)
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

@pytest.fixture
def session_factory(tmp_path, monkeypatch):
    """A fresh SQLite database per test, wired into every module that opens sessions."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    for module in (crud, sla, auth):
        monkeypatch.setattr(module, "SessionLocal", factory)

    yield factory
    engine.dispose()


@pytest.fixture
def db(session_factory):
    """A session for arranging data and asserting on results."""
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def make_user(db):
    def _make(slack_id="U00000USER", name="alice", email="alice@example.com"):
        user = User(slack_id=slack_id, name=name, email=email)
        db.add(user)
        db.commit()
        return user
    return _make


@pytest.fixture
def make_admin(db, make_user):
    def _make(slack_id="U0000ADMIN", email="admin@example.com", role="it support"):
        make_user(slack_id=slack_id, name="admin", email=email)
        admin = Admin(slack_id=slack_id, email=email, role=role)
        db.add(admin)
        db.commit()
        return admin
    return _make


@pytest.fixture
def make_ticket(db):
    def _make(slack_id="U00000USER", priority=3, status="active", category="Network",
              issue_text="VPN is down", created_at=None, escalated_at=None):
        ticket = Ticket(
            slack_id=slack_id,
            issue_text=issue_text,
            priority=priority,
            category=category,
            status=status,
            suggested_fix="Restart the router",
            created_at=created_at or datetime.now(),
            escalated_at=escalated_at,
        )
        db.add(ticket)
        db.commit()
        return ticket
    return _make


# Fakes for external services

@pytest.fixture
def slack_responses(monkeypatch):
    """Capture every message crud.py sends back to Slack via response_url."""
    sent = []

    async def fake_send(response_url, payload):
        sent.append({"url": response_url, "payload": payload})

    monkeypatch.setattr(crud, "send_slack_response", fake_send)
    return sent


@pytest.fixture
def slack_users(monkeypatch):
    """Fake Slack users.info. Register profiles in the returned dict; unknown IDs get ok=False."""
    profiles = {}

    async def fake_fetch(slack_id):
        if slack_id in profiles:
            return {"ok": True, "user": profiles[slack_id]}
        return {"ok": False, "error": "user_not_found"}

    monkeypatch.setattr(crud, "fetch_slack_user", fake_fetch)
    return profiles


@pytest.fixture
def admin_check(monkeypatch):
    """Control crud.verify_admin. Add Slack IDs to the returned set to make them admins."""
    admins = set()

    async def fake_verify_admin(user_id, check_type="admin"):
        return user_id in admins

    monkeypatch.setattr(crud, "verify_admin", fake_verify_admin)
    return admins


@pytest.fixture
def ai_response(monkeypatch):
    """Control the Gemini triage result. Mutate the returned dict to change the response."""
    result = {"category": "Network", "priority": 2, "suggested_fix": "Restart the VPN client."}
    calls = []

    async def fake_get_ai_data(issue_text):
        calls.append(issue_text)
        return dict(result)

    monkeypatch.setattr(crud, "get_ai_data", fake_get_ai_data)
    result["_calls"] = calls
    return result


@pytest.fixture
def mock_http(monkeypatch):
    """
    Route every httpx.AsyncClient request through a fake transport.

    Set `mock_http.handler` to a function(request) -> httpx.Response;
    every request made is recorded in `mock_http.requests`.
    """
    class MockHttp:
        def __init__(self):
            self.requests = []
            self.handler = lambda request: httpx.Response(200, json={"ok": True})

        def _dispatch(self, request):
            self.requests.append(request)
            return self.handler(request)

    mock = MockHttp()
    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(mock._dispatch)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    return mock
