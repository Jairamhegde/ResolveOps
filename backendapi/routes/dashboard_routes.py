from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Admin, User
from backend.schemas import ADMIN_TYPE_CATEGORY, AdminType, Category
from backendapi.routes.auth_routes import get_current_admin, get_current_employee
from backendapi.queries.ticket_queries import (
    count_by_category,
    count_by_day,
    count_by_priority,
    list_admins,
    list_tickets,
    list_users_with_tickets,
    ticket_metrics,
    ticket_scope,
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def is_super_admin(admin: Admin) -> bool:
    return admin.role == AdminType.super_admin.value


def category_for(admin: Admin, requested: Category | None) -> str | None:
    """The category this admin may see: their own, or for a super admin the one they asked for (None = all)."""
    if is_super_admin(admin):
        return requested.value if requested else None

    category = ADMIN_TYPE_CATEGORY.get(admin.role)
    if category is None:
        raise HTTPException(status_code=403, detail=f"Admin type '{admin.role}' is not linked to a ticket category")
    return category


@router.get("/summary")
def get_summary(category: Category | None = None, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    """Metrics and chart data for the admin's tickets."""
    allowed_category = category_for(admin, category)
    scope = ticket_scope(category=allowed_category)

    return {
        "category": allowed_category,
        "metrics": ticket_metrics(db, scope),
        "by_category": count_by_category(db, scope),
        "by_priority": count_by_priority(db, scope),
        "by_day": count_by_day(db, scope),
    }


@router.get("/tickets")
def get_tickets(category: Category | None = None, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    """The admin's tickets with full details, newest first."""
    scope = ticket_scope(category=category_for(admin, category))
    return list_tickets(db, scope)


@router.get("/users")
def get_users(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    """Employees who raised a ticket the admin can see, for the employee picker."""
    scope = ticket_scope(category=category_for(admin, None))
    return list_users_with_tickets(db, scope)


@router.get("/users/{slack_id}")
def get_user_dashboard(slack_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    """One employee's numbers, their high-severity tickets and all their tickets (limited to the admin's category)."""
    scope = ticket_scope(category=category_for(admin, None), slack_id=slack_id)

    return {
        "metrics": ticket_metrics(db, scope),
        "high_severity": list_tickets(db, scope, high_severity_only=True),
        "tickets": list_tickets(db, scope),
    }


@router.get("/my-tickets")
def get_my_tickets(db: Session = Depends(get_db), employee: User = Depends(get_current_employee)):
    """The signed-in employee's own numbers and every ticket they submitted. Employees only."""
    scope = ticket_scope(slack_id=employee.slack_id)

    return {
        "name": employee.name,
        "metrics": ticket_metrics(db, scope),
        "by_priority": count_by_priority(db, scope),
        "tickets": list_tickets(db, scope),
    }


@router.get("/admins")
def get_admins(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    """Every admin, the field they look after and the open work in it. Super admins only."""
    if not is_super_admin(admin):
        raise HTTPException(status_code=403, detail="Only a super admin can see the admin list")

    return [admin_to_dict(db, other_admin, name) for other_admin, name in list_admins(db)]


def admin_to_dict(db: Session, admin: Admin, name: str | None) -> dict:
    """One row of the admin list. Workload numbers are None for a super admin, who has no single category."""
    category = ADMIN_TYPE_CATEGORY.get(admin.role)
    row = {
        "id": admin.id,
        "name": name,
        "email": admin.email,
        "role": admin.role,
        "category": category,
        "can_sign_in": admin.password_hash is not None,
        "open_tickets": None,
        "high_severity_open": None,
        "resolved": None,
    }

    if category is not None:
        workload = ticket_metrics(db, ticket_scope(category=category))
        row["open_tickets"] = workload["active"] + workload["pending_response"]
        row["high_severity_open"] = workload["high_severity_open"]
        row["resolved"] = workload["resolved"]

    return row
