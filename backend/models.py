from datetime import datetime, timezone
from typing import Dict, Any

from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, CheckConstraint, text, Boolean

from backend.database import Base
from backend.schemas import Flag


def utc_now_naive():
    """Current UTC time without tzinfo, for Postgres `timestamp` (without time zone) columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_now():
    """Current UTC time with tzinfo, for Postgres `timestamptz` columns."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "user_details"
    slack_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(Text, nullable=False, unique=True)


class Ticket(Base):
    __tablename__ = "ticket"
    __table_args__ = (
        # resolved_by may only be set once the ticket is resolved
        CheckConstraint(
            "resolved_by IS NULL OR status = 'resolved'",
            name="ck_ticket_resolved_by_requires_resolved",
        ),
        CheckConstraint(
            "flag IN (" + ", ".join(f"'{f.value}'" for f in Flag) + ")",
            name="ck_ticket_flag_valid",
        ),
    )
    id = Column(Integer, primary_key=True)
    slack_id = Column(String(50), ForeignKey('user_details.slack_id'))
    issue_text = Column(Text, nullable=False)
    priority = Column(Integer)
    category = Column(String(100))
    status = Column(String(100), default="active", server_default=text("'active'"))
    suggested_fix = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP"))
    escalated_at = Column(DateTime)
    resolved_by = Column(String(50))
    flag = Column(String(50), nullable=False, default=Flag.none.value, server_default=text("'none'"))
    needs_review = Column(Boolean, nullable=False, default=False, server_default=text("false"))


class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)
    slack_id = Column(String(50), ForeignKey("user_details.slack_id"))
    email = Column(String(100), nullable=False, unique=True)
    role = Column(String(100), server_default=text("'it support'"))


class GitRequest(BaseModel):
    repository: Dict[str, Any]
