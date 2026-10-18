import asyncio

import backend.crud as crud
from backend.crud import insert_ticket_background
from backend.models import User, Admin, Ticket
from testing.test_database import get_test_db, TestSessionLocal


def start_with_empty_database():
    """Opens the SQLite test database and removes rows left over from earlier tests."""
    db = get_test_db()
    db.query(Ticket).delete()
    db.query(Admin).delete()
    db.query(User).delete()
    db.commit()
    return db

def use_test_database_and_fakes(monkeypatch, slack_messages):
    """
    Point crud.py at the SQLite test database instead of Postgres,
    and replace Slack and Gemini with fakes so no real service is called.
    Every message the code sends to Slack is added to slack_messages.
    """
    async def fake_fetch_slack_user(slack_id):
        return {"ok": True, 
                "user": {"profile": 
                {"email": f"{slack_id}@example.com"}
                }}

    async def fake_get_ai_data(issue_text):
        return {"category": "hardware", 
                "priority": 2,
                "flag": "none",
                "suggested_fix": "Reconnect the monitor cable."}

    async def fake_send_slack_response(response_url, payload):
        slack_messages.append(payload["text"])

    monkeypatch.setattr(crud, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(crud, "fetch_slack_user", fake_fetch_slack_user)
    monkeypatch.setattr(crud, "get_ai_data", fake_get_ai_data)
    monkeypatch.setattr(crud, "send_slack_response", fake_send_slack_response)

def test_ticket_insertion(monkeypatch):
    db = start_with_empty_database()
    slack_messages = []
    use_test_database_and_fakes(monkeypatch, slack_messages)

    result = asyncio.run(insert_ticket_background("U0TESTUSER", "Monitor shows no display", "abc", "http://example.com"))

    assert result is True
    ticket = db.query(Ticket).filter(Ticket.slack_id == "U0TESTUSER").first()
    assert ticket is not None
    assert ticket.issue_text == "Monitor shows no display"
    assert ticket.category == "hardware"
    assert slack_messages == [f"Ticket #{ticket.id} sent to IT support"]
    db.close()


def test_ticket_insertion_registers_new_user(monkeypatch):
    db = start_with_empty_database()
    use_test_database_and_fakes(monkeypatch, [])

    asyncio.run(insert_ticket_background("U0TESTUSER", "Monitor shows no display", "abc", "http://example.com"))

    user = db.query(User).filter(User.slack_id == "U0TESTUSER").first()
    assert user is not None
    assert user.email == "U0TESTUSER@example.com"
    db.close()


def test_ticket_insertion_returns_false_when_it_crashes(monkeypatch):
    db = start_with_empty_database()
    slack_messages = []
    use_test_database_and_fakes(monkeypatch, slack_messages)

    async def crashing_create_ticket(db, user_id, issue_text, user_name):
        raise RuntimeError("something went wrong")

    monkeypatch.setattr(crud, "create_ticket", crashing_create_ticket)

    result = asyncio.run(insert_ticket_background("U0TESTUSER", "Monitor shows no display", "abc", "http://example.com"))

    assert result is False
    assert slack_messages == ["Server is not active."]
    db.close()
