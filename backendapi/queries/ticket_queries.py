"""
Read-only queries for the dashboard.

Every function takes a `scope`: a list of SQLAlchemy filters that picks which tickets count.
Build one with `ticket_scope()`, so the same metrics work for the whole company, one category or one employee.
"""
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import Admin, Ticket, User


ACTIVE = "active"
PENDING_RESPONSE = "pending_response"
RESOLVED = "resolved"
AI_RESOLVER = "ai"

# P1 and P2 are high severity.
HIGH_SEVERITY = Ticket.priority <= 2

# Older tickets were saved as "Network" or "Account Access"; this matches them with "network" and "account_access".
NORMALIZED_CATEGORY = func.lower(func.replace(Ticket.category, " ", "_"))


def ticket_scope(category: str | None = None, slack_id: str | None = None) -> list:
    """The filters for one category and/or one employee. No arguments means every ticket."""
    scope = []
    if category is not None:
        scope.append(NORMALIZED_CATEGORY == category)
    if slack_id is not None:
        scope.append(Ticket.slack_id == slack_id)
    return scope


def ticket_metrics(db: Session, scope: list) -> dict:
    """The headline numbers, counted in one query."""
    row = (
        db.query(
            func.count(Ticket.id).label("total"),
            func.count(Ticket.id).filter(Ticket.status == ACTIVE).label("active"),
            func.count(Ticket.id).filter(Ticket.status == PENDING_RESPONSE).label("pending_response"),
            func.count(Ticket.id).filter(Ticket.status == RESOLVED).label("resolved"),
            func.count(Ticket.id).filter(Ticket.resolved_by == AI_RESOLVER).label("solved_by_ai"),
            func.count(Ticket.id).filter(HIGH_SEVERITY).label("high_severity"),
            func.count(Ticket.id).filter(HIGH_SEVERITY, Ticket.status != RESOLVED).label("high_severity_open"),
            func.count(Ticket.id).filter(Ticket.needs_review == True).label("needs_review"),
        )
        .filter(*scope)
        .one()
    )

    metrics = dict(row._mapping)
    metrics["solved_by_admin"] = metrics["resolved"] - metrics["solved_by_ai"]
    # Share of all tickets that the AI's suggested fix solved without an admin.
    metrics["deflection_rate"] = round(metrics["solved_by_ai"] / metrics["total"] * 100, 1) if metrics["total"] else 0
    return metrics


def count_by_category(db: Session, scope: list) -> list[dict]:
    """Ticket count per category, largest first."""
    rows = (
        db.query(NORMALIZED_CATEGORY.label("category"), func.count(Ticket.id).label("count"))
        .filter(*scope)
        .group_by(NORMALIZED_CATEGORY)
        .order_by(func.count(Ticket.id).desc())
        .all()
    )
    return [{"category": row.category or "uncategorized", "count": row.count} for row in rows]


def count_by_priority(db: Session, scope: list) -> list[dict]:
    """Ticket count for each priority, always P1 to P5 (zero when a priority has no tickets)."""
    rows = db.query(Ticket.priority, func.count(Ticket.id)).filter(*scope).group_by(Ticket.priority).all()
    counts = dict(rows)
    return [{"priority": priority, "count": counts.get(priority, 0)} for priority in range(1, 6)]


def count_by_day(db: Session, scope: list, days: int = 14) -> list[dict]:
    """Tickets raised on each of the last `days` days (UTC), oldest first, including days with none."""
    first_day = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    day = func.date(Ticket.created_at)

    rows = (
        db.query(day, func.count(Ticket.id))
        .filter(*scope, Ticket.created_at >= datetime.combine(first_day, time.min, tzinfo=timezone.utc))
        .group_by(day)
        .all()
    )
    # Postgres returns dates, SQLite returns "YYYY-MM-DD" text: compare both as text.
    counts = {str(row_day): count for row_day, count in rows}

    all_days = [first_day + timedelta(days=offset) for offset in range(days)]
    return [{"day": day.isoformat(), "count": counts.get(day.isoformat(), 0)} for day in all_days]


def list_tickets(db: Session, scope: list, high_severity_only: bool = False, limit: int = 500) -> list[dict]:
    """Tickets with the name of the employee who raised them, newest first."""
    query = db.query(Ticket, User.name).outerjoin(User, User.slack_id == Ticket.slack_id).filter(*scope)
    if high_severity_only:
        query = query.filter(HIGH_SEVERITY)

    rows = query.order_by(Ticket.created_at.desc().nulls_last()).limit(limit).all()
    return [ticket_to_dict(ticket, reporter) for ticket, reporter in rows]


def ticket_to_dict(ticket: Ticket, reporter: str | None) -> dict:
    return {
        "id": ticket.id,
        "issue_text": ticket.issue_text,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "flag": ticket.flag,
        "needs_review": ticket.needs_review,
        "suggested_fix": ticket.suggested_fix,
        "resolved_by": ticket.resolved_by,
        "reporter": reporter,
        "created_at": ticket.created_at,
        "escalated_at": ticket.escalated_at,
    }


def list_users_with_tickets(db: Session, scope: list) -> list[dict]:
    """Employees who raised at least one ticket in the scope, by name."""
    users = (
        db.query(User)
        .join(Ticket, Ticket.slack_id == User.slack_id)
        .filter(*scope)
        .distinct()
        .order_by(User.name)
        .all()
    )
    return [{"slack_id": user.slack_id, "name": user.name} for user in users]


def list_admins(db: Session) -> list[tuple[Admin, str | None]]:
    """Every admin with their Slack name (None for dashboard-only admins), super admins first."""
    return (
        db.query(Admin, User.name)
        .outerjoin(User, User.slack_id == Admin.slack_id)
        .order_by(Admin.role != "super_admin", Admin.role, Admin.email)
        .all()
    )
