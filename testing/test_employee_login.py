import pytest
from fastapi import HTTPException

from backend.models import Admin, Ticket, User
from backendapi.routes.auth_routes import (
    ADMIN_TOKEN,
    EMPLOYEE_TOKEN,
    LoginRequest,
    employee_login,
    get_current_admin,
    get_current_employee,
    hash_password,
    make_token,
)
from backendapi.routes.dashboard_routes import get_my_tickets
from testing.test_database import get_test_db


def start_with_employee():
    """An empty test database with one employee who has a password, and their two tickets."""
    db = get_test_db()
    db.query(Ticket).delete()
    db.query(Admin).delete()
    db.query(User).delete()

    db.add(User(slack_id="UASHA", name="Asha", email="asha@example.com", password_hash=hash_password("secret-123")))
    db.add(User(slack_id="UBEN", name="Ben", email="ben@example.com"))
    db.add_all([
        Ticket(slack_id="UASHA", issue_text="wifi down", category="network", priority=1, status="active"),
        Ticket(slack_id="UASHA", issue_text="vpn slow", category="network", priority=3, status="resolved", resolved_by="ai"),
        Ticket(slack_id="UBEN", issue_text="not Asha's", category="hardware", priority=2, status="active"),
    ])
    db.commit()
    return db


def test_employee_signs_in_and_sees_only_their_tickets():
    db = start_with_employee()

    session = employee_login(LoginRequest(email="asha@example.com", password="secret-123"), db)
    employee = get_current_employee(f"Bearer {session['token']}", db)
    result = get_my_tickets(db, employee)

    assert session["role"] == "employee"
    assert result["metrics"]["total"] == 2
    assert result["metrics"]["resolved"] == 1
    assert sorted(ticket["issue_text"] for ticket in result["tickets"]) == ["vpn slow", "wifi down"]


def test_wrong_password_and_employee_without_password_are_refused():
    db = start_with_employee()

    for email, password in [("asha@example.com", "wrong"), ("ben@example.com", "anything")]:
        with pytest.raises(HTTPException) as error:
            employee_login(LoginRequest(email=email, password=password), db)
        assert error.value.status_code == 401


def test_employee_token_is_not_an_admin_token():
    db = start_with_employee()
    db.add(Admin(id=1, email="admin@example.com", role="super_admin", password_hash=hash_password("x")))
    db.commit()

    # The subject "1" would match the admin's id, but the token is for an employee.
    employee_token = make_token("1", EMPLOYEE_TOKEN)
    with pytest.raises(HTTPException) as error:
        get_current_admin(f"Bearer {employee_token}", db)
    assert error.value.status_code == 401


def test_admin_token_is_not_an_employee_token():
    db = start_with_employee()

    admin_token = make_token("UASHA", ADMIN_TOKEN)
    with pytest.raises(HTTPException) as error:
        get_current_employee(f"Bearer {admin_token}", db)
    assert error.value.status_code == 401
