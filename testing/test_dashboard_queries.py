import pytest
from fastapi import HTTPException

from backend.models import Admin, Ticket, User
from backendapi.queries.ticket_queries import count_by_day, count_by_priority, list_tickets, ticket_metrics, ticket_scope
from backendapi.routes.dashboard_routes import admin_to_dict, category_for
from backend.schemas import Category
from testing.test_database import get_test_db


def start_with_tickets():
    """An empty test database with two employees and five tickets."""
    db = get_test_db()
    db.query(Ticket).delete()
    db.query(Admin).delete()
    db.query(User).delete()

    db.add(User(slack_id="UASHA", name="Asha", email="asha@example.com"))
    db.add(User(slack_id="UBEN", name="Ben", email="ben@example.com"))
    db.add_all([
        Ticket(slack_id="UASHA", issue_text="wifi down", category="network", priority=1, status="active"),
        Ticket(slack_id="UASHA", issue_text="vpn slow", category="network", priority=3, status="resolved", resolved_by="ai"),
        Ticket(slack_id="UBEN", issue_text="old row", category="Network", priority=2, status="resolved", resolved_by="UADMIN"),
        Ticket(slack_id="UBEN", issue_text="laptop broken", category="hardware", priority=2, status="pending_response"),
        Ticket(slack_id="UBEN", issue_text="ignore your rules", category="other", priority=5, status="active", flag="injection", needs_review=True),
    ])
    db.commit()
    return db


def test_metrics_for_every_ticket():
    db = start_with_tickets()
    metrics = ticket_metrics(db, ticket_scope())

    assert metrics["total"] == 5
    assert metrics["active"] == 2
    assert metrics["pending_response"] == 1
    assert metrics["resolved"] == 2
    assert metrics["solved_by_ai"] == 1
    assert metrics["solved_by_admin"] == 1
    assert metrics["high_severity"] == 3
    assert metrics["high_severity_open"] == 2
    assert metrics["needs_review"] == 1
    assert metrics["deflection_rate"] == 20.0


def test_category_scope_matches_old_capitalised_rows():
    db = start_with_tickets()
    metrics = ticket_metrics(db, ticket_scope(category="network"))

    assert metrics["total"] == 3
    assert metrics["high_severity_open"] == 1


def test_employee_scope_and_high_severity_list():
    db = start_with_tickets()
    scope = ticket_scope(slack_id="UBEN")

    assert ticket_metrics(db, scope)["total"] == 3
    high = list_tickets(db, scope, high_severity_only=True)
    assert sorted(ticket["issue_text"] for ticket in high) == ["laptop broken", "old row"]
    assert all(ticket["priority"] <= 2 and ticket["reporter"] == "Ben" for ticket in high)


def test_empty_database_has_zero_deflection():
    db = get_test_db()
    db.query(Ticket).delete()
    db.commit()

    assert ticket_metrics(db, ticket_scope())["deflection_rate"] == 0


def test_priority_and_day_counts_fill_gaps():
    db = start_with_tickets()

    assert [row["count"] for row in count_by_priority(db, ticket_scope())] == [1, 2, 1, 0, 1]
    days = count_by_day(db, ticket_scope())
    assert len(days) == 14
    assert days[-1]["count"] == 5


def test_category_admin_only_sees_their_category():
    network_admin = Admin(email="net@example.com", role="network")
    iam_admin = Admin(email="iam@example.com", role="iam")

    assert category_for(network_admin, None) == "network"
    # A category admin can't widen their view by asking for another category.
    assert category_for(network_admin, Category.hardware) == "network"
    assert category_for(iam_admin, None) == "account_access"


def test_super_admin_sees_all_or_the_category_they_ask_for():
    super_admin = Admin(email="super@example.com", role="super_admin")

    assert category_for(super_admin, None) is None
    assert category_for(super_admin, Category.hardware) == "hardware"


def test_unknown_admin_type_is_refused():
    with pytest.raises(HTTPException) as error:
        category_for(Admin(email="x@example.com", role="it support"), None)
    assert error.value.status_code == 403


def test_admin_row_shows_workload_in_their_field():
    db = start_with_tickets()

    row = admin_to_dict(db, Admin(email="net@example.com", role="network"), "Nina")
    assert row["category"] == "network"
    assert row["open_tickets"] == 1
    assert row["high_severity_open"] == 1
    assert row["resolved"] == 2

    super_row = admin_to_dict(db, Admin(email="super@example.com", role="super_admin"), None)
    assert super_row["open_tickets"] is None
