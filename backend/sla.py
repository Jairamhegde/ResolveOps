from datetime import datetime, timedelta,timezone
from backend.database import get_db
from backend.models import Ticket
from backend.database import SessionLocal
from logger import logger
SLA_WINDOWS = {
    1: None,                   
    2: timedelta(hours=2),
    3: timedelta(hours=6),
    4: timedelta(hours=12),
    5: timedelta(hours=24),
}

def get_sla_window(priority:int):
    return SLA_WINDOWS.get(priority)


def escalate_active_tickets():
    db = SessionLocal()
    try:
        tickets = db.query(Ticket).filter(Ticket.status == 'active').all()
        escalated_ids = []
        logger.info("Escalation process started")
        for ticket in tickets:
            sla_window = get_sla_window(ticket.priority)
            if sla_window is None:
                continue
            window_age = datetime.now(timezone.utc) - ticket.created_at

            if window_age > sla_window:
                ticket.priority -= 1
                escalated_ids.append(ticket.id)
        db.commit()
        logger.info(f"Escalated IDs: {escalated_ids}")
    except Exception as e:
        logger.error(f"Failed to escalate tickets: {e}")
    finally:
        db.close()



    



if __name__ == "__main__":
    print(escalate_active_tickets())
