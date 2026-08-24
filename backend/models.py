from sqlalchemy import Column, String, Integer, Text, ForeignKey,DateTime
from backend.database import Base

class User(Base):
    __tablename__ = "user_details"
    slack_id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(Text)

class Ticket(Base):
    __tablename__ = "ticket"
    id = Column(Integer, primary_key=True)
    slack_id = Column(String, ForeignKey('user_details.slack_id'))
    issue_text = Column(Text)
    priority = Column(Integer)
    category = Column(String)
    status = Column(String, default="active")
    suggested_fix = Column(Text)
    created_at = Column(DateTime(timezone=True))

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)
    slack_id = Column(String, ForeignKey("user_details.slack_id"))
    email = Column(Text)
    role = Column(String)
