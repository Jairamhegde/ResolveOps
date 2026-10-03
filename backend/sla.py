from datetime import datetime, timedelta, timezone

from logger import logger
from backend.database import SessionLocal
from backend.models import Ticket, utc_now_naive


SLA_WINDOWS = {
    1: None,
    2: timedelta(hours=2),
    3: timedelta(hours=6),
    4: timedelta(hours=12),
    5: timedelta(hours=24),
}


def get_sla_window(priority: int):
    return SLA_WINDOWS.get(priority)


def to_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so they can be compared with aware ones."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def escalate_active_tickets():
    logger.info("SLA escalation job started")
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)
        tickets = db.query(Ticket).filter(Ticket.status == 'active').all()
        escalated_ids = []

        for ticket in tickets:
            sla_window = get_sla_window(ticket.priority)
            if sla_window is None:
                continue

            # Fall back to created_at for tickets created before escalated_at existed
            last_escalated = ticket.escalated_at or ticket.created_at
            if last_escalated is None:
                logger.warning(f"Ticket {ticket.id} has no escalated_at or created_at, skipping")
                continue

            if now - to_utc(last_escalated) > sla_window:
                old_priority = ticket.priority
                ticket.priority -= 1
                ticket.escalated_at = utc_now_naive()
                escalated_ids.append(ticket.id)
                logger.info(f"Ticket {ticket.id} escalated P{old_priority} -> P{ticket.priority}")

        db.commit()
        logger.info(f"SLA escalation finished: {len(escalated_ids)} ticket(s) escalated {escalated_ids}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to escalate tickets: {e}")
    finally:
        db.close()
