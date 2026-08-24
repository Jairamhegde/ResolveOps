from pydantic import BaseModel
from typing import Optional

class InserTicket(BaseModel):
    slack_id: str
    issue_text: str
    category: Optional[str] = "other"
    priority: Optional[int] = 5
    status: Optional[str] = "active"
    suggested_fix: Optional[str] = "No fix suggested"

class CreateAdmin(BaseModel):
    slack_id: str
    email: str
    role: Optional[str] = "it support"

class CreateUser(BaseModel):
    slack_id: str
    name: str
    email: str
