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
    ai_failed = "ai_failed"

class InsertTicket(BaseModel):
    slack_id: str
    issue_text: str
    category: Optional[str] = "other"
    priority: Optional[int] = 5
    status: Optional[str] = "active"
    suggested_fix: Optional[str] = "No fix suggested"
    flag: Flag = Flag.none
    needs_review: bool = False

class CreateUser(BaseModel):
    slack_id: str
    name: str
    email: str

class AiResponseModel(BaseModel):
    category: Category
    priority: int
    flag: Flag
    suggested_fix: str

class AdminType(str, Enum):
    """Values stored in admin.role, always lowercase. Only a super_admin can add new admins."""
    hardware = "hardware"
    network = "network"
    software = "software"
    iam = "iam"
    super_admin = "super_admin"
    other = "other"

# The ticket category each admin type looks after. A super_admin has none: they see every category.
# The `other` admin also owns spam and prompt-injection tickets, which are always saved as `other`.
# Slack commands and the dashboard both read this, so they always agree.
ADMIN_TYPE_CATEGORY = {
    AdminType.hardware.value: Category.hardware.value,
    AdminType.network.value: Category.network.value,
    AdminType.software.value: Category.software.value,
    AdminType.iam.value: Category.account_access.value,
    AdminType.other.value: Category.other.value,
}

class ValidateAdmin(BaseModel):
    role: AdminType
