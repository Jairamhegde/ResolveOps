from pydantic import BaseModel
from typing import Optional
from enum import Enum

class Category(str, Enum):
    network = "network"
    hardware = "hardware"
    software = "software"
    account_access = "account_access"
    other = "other"


class Flag(str, Enum):
    """Values stored in ticket.flag. Anything other than `none` needs an admin to review it."""
    none = "none"
    unclear = "unclear"
    spam = "spam"
    injection = "injection"
    ai_failed = "ai_failed"  # set by our code when the AI call fails, never returned by the model


class InserTicket(BaseModel):
    slack_id: str
    issue_text: str
    category: Optional[str] = "other"
    priority: Optional[int] = 5
    status: Optional[str] = "active"
    suggested_fix: Optional[str] = "No fix suggested"
    flag: Flag = Flag.none
    needs_review: bool = False

class CreateAdmin(BaseModel):
    slack_id: str
    email: str
    role: Optional[str] = "it support"

class CreateUser(BaseModel):
    slack_id: str
    name: str
    email: str


class AiResponseModel(BaseModel):
    category: Category
    priority: int
    flag: Flag
    suggested_fix: str
