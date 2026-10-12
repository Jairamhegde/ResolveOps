from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backendapi.queries.ticket_queries import (
    count_total_tickets,
    count_active_tickets,
    count_inactive_tickets,
    count_solved_tickets,
    count_unsolved_tickets,
    count_tickets_solved_by_ai,
    get_tickets_solved_by_ai,
    get_todays_tickets,
    count_needs_review,
    count_tickets_by_category,
    count_tickets_by_priority,
    get_recent_tickets,
    get_flagged_tickets,
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/ticket-counts")
def get_ticket_counts(db: Session = Depends(get_db)):
    """Total, active and inactive ticket counts."""
    return {
        "total": count_total_tickets(db),
        "active": count_active_tickets(db),
        "inactive": count_inactive_tickets(db),
    }

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Ticket totals for the dashboard cards."""
    return {
        "total": count_total_tickets(db),
        "solved": count_solved_tickets(db),
        "unsolved": count_unsolved_tickets(db),
        "solved_by_ai": count_tickets_solved_by_ai(db),
    }

@router.get("/ai-solved-tickets")
def get_ai_solved_tickets(db: Session = Depends(get_db)):
    """The most recent tickets that the AI suggested fix solved."""
    tickets = get_tickets_solved_by_ai(db)

    return [
        {
            "id": ticket.id,
            "issue_text": ticket.issue_text,
            "category": ticket.category,
            "priority": ticket.priority,
            "suggested_fix": ticket.suggested_fix,
            "created_at": ticket.created_at,
        }
        for ticket in tickets
    ]

@router.get("/todays-tickets")
def get_todays_tickets_route(db: Session = Depends(get_db)):
    """Tickets raised today, newest first."""
    tickets = get_todays_tickets(db)

    return [
        {
            "id": ticket.id,
            "issue_text": ticket.issue_text,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "flag": ticket.flag,
            "created_at": ticket.created_at,
        }
        for ticket in tickets
    ]

def ticket_to_dict(ticket):
    """The ticket fields the dashboard lists show."""
    return {
        "id": ticket.id,
        "issue_text": ticket.issue_text,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "flag": ticket.flag,
        "created_at": ticket.created_at,
    }

@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """Everything the dashboard shows, in one request."""
    total = count_total_tickets(db)
    solved_by_ai = count_tickets_solved_by_ai(db)

    # Share of all tickets that the AI fix resolved without an admin.
    deflection_rate = round(solved_by_ai / total * 100, 1) if total else 0

    return {
        "kpis": {
            "total": total,
            "open": count_unsolved_tickets(db),
            "solved_by_ai": solved_by_ai,
            "deflection_rate": deflection_rate,
            "needs_review": count_needs_review(db),
        },
        "by_category": [
            {"category": category, "count": count}
            for category, count in count_tickets_by_category(db)
        ],
        "by_priority": [
            {"priority": priority, "count": count}
            for priority, count in count_tickets_by_priority(db)
        ],
        "recent": [ticket_to_dict(ticket) for ticket in get_recent_tickets(db)],
        "flagged": [ticket_to_dict(ticket) for ticket in get_flagged_tickets(db)],
    }
