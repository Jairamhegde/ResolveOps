from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import Ticket


ACTIVE_STATUS = "active"
RESOLVED_STATUS = "resolved"
AI_RESOLVER = "ai"


def count_total_tickets(db: Session) -> int:
    """Number of tickets ever raised."""
    return db.query(Ticket).count()


def count_active_tickets(db: Session) -> int:
    """Number of tickets that are still open and waiting for an admin."""
    return db.query(Ticket).filter(Ticket.status == ACTIVE_STATUS).count()


def count_inactive_tickets(db: Session) -> int:
    """Number of tickets that are not active, such as resolved tickets."""
    return db.query(Ticket).filter(Ticket.status != ACTIVE_STATUS).count()


def count_solved_tickets(db: Session) -> int:
    """Number of tickets that have been resolved, by an admin or by the AI."""
    return db.query(Ticket).filter(Ticket.status == RESOLVED_STATUS).count()


def count_unsolved_tickets(db: Session) -> int:
    """Number of tickets that are not resolved yet, such as active tickets or tickets waiting for the user's answer."""
    return db.query(Ticket).filter(Ticket.status != RESOLVED_STATUS).count()


def count_tickets_solved_by_ai(db: Session) -> int:
    """Number of tickets the user marked as fixed by the AI suggested fix."""
    return (
        db.query(Ticket)
        .filter(Ticket.status == RESOLVED_STATUS, Ticket.resolved_by == AI_RESOLVER)
        .count()
    )


def get_tickets_solved_by_ai(db: Session, limit: int = 20) -> list[Ticket]:
    """The most recent tickets the user marked as fixed by the AI suggested fix, newest first."""
    return (
        db.query(Ticket)
        .filter(Ticket.status == RESOLVED_STATUS, Ticket.resolved_by == AI_RESOLVER)
        .order_by(Ticket.created_at.desc())
        .limit(limit)
        .all()
    )


def get_todays_tickets(db: Session, limit: int = 20) -> list[Ticket]:
    """Tickets raised since midnight UTC today, newest first."""
    start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(Ticket)
        .filter(Ticket.created_at >= start_of_today)
        .order_by(Ticket.created_at.desc())
        .limit(limit)
        .all()
    )



def count_needs_review(db: Session) -> int:
    """Number of tickets the AI flagged for an admin to review."""
    return db.query(Ticket).filter(Ticket.needs_review == True).count()


def count_tickets_by_category(db: Session) -> list[tuple[str, int]]:
    """(category, ticket count) pairs, largest first."""
    # Older tickets were saved as "Hardware" or "Account Access"; count them with "hardware" and "account_access".
    category = func.lower(func.replace(Ticket.category, " ", "_"))
    return (
        db.query(category, func.count(Ticket.id))
        .group_by(category)
        .order_by(func.count(Ticket.id).desc())
        .all()
    )


def count_tickets_by_priority(db: Session) -> list[tuple[int, int]]:
    """(priority, ticket count) pairs, from P1 to P5."""
    return (
        db.query(Ticket.priority, func.count(Ticket.id))
        .group_by(Ticket.priority)
        .order_by(Ticket.priority)
        .all()
    )


def get_recent_tickets(db: Session, limit: int = 10) -> list[Ticket]:
    """The most recently raised tickets, newest first."""
    # nulls_last: Postgres puts tickets without a created_at first in a descending sort.
    return db.query(Ticket).order_by(Ticket.created_at.desc().nulls_last()).limit(limit).all()


def get_flagged_tickets(db: Session, limit: int = 20) -> list[Ticket]:
    """Tickets the AI flagged for review (injection, spam, unclear, ai_failed), newest first."""
    return (
        db.query(Ticket)
        .filter(Ticket.needs_review == True)
        .order_by(Ticket.created_at.desc().nulls_last())
        .limit(limit)
        .all()
    )
