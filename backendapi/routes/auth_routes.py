import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Admin, User

load_dotenv()

SECRET = os.environ["JWT_SECRET"]
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Every token says who it is for, so an employee's token can never be used as an admin's.
ADMIN_TOKEN = "admin"
EMPLOYEE_TOKEN = "employee"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def password_matches(password: str, password_hash: str | None) -> bool:
    return password_hash is not None and bcrypt.checkpw(password.encode(), password_hash.encode())


def make_token(subject: str, kind: str) -> str:
    """A token that is valid for 8 hours."""
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": subject, "kind": kind, "exp": expires}, SECRET, algorithm="HS256")


def read_token(authorization: str | None, kind: str) -> str:
    """The subject of a valid 'Bearer <token>' of the given kind, otherwise answer 401."""
    try:
        payload = jwt.decode(authorization.removeprefix("Bearer "), SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Please log in")

    # Admin tokens made before tokens had a kind are admin tokens.
    if payload.get("kind", ADMIN_TOKEN) != kind:
        raise HTTPException(status_code=401, detail="Please log in")
    return payload["sub"]


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(details: LoginRequest, db: Session = Depends(get_db)):
    """Admin login: check the email and password, and return a token."""
    admin = db.query(Admin).filter(Admin.email == details.email).first()

    if admin is None or not password_matches(details.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")

    return {"token": make_token(str(admin.id), ADMIN_TOKEN), "email": admin.email, "role": admin.role}


@router.post("/employee-login")
def employee_login(details: LoginRequest, db: Session = Depends(get_db)):
    """Employee login: check the email and password, and return a token for the employee's own tickets."""
    user = db.query(User).filter(User.email == details.email).first()

    if user is None or not password_matches(details.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")

    return {"token": make_token(user.slack_id, EMPLOYEE_TOKEN), "email": user.email, "name": user.name, "role": "employee"}


def get_current_admin(authorization: str = Header(None), db: Session = Depends(get_db)) -> Admin:
    """The logged-in admin, or answer 401."""
    admin_id = read_token(authorization, ADMIN_TOKEN)

    admin = db.get(Admin, int(admin_id))
    if admin is None or admin.password_hash is None:
        raise HTTPException(status_code=401, detail="Please log in")
    return admin


def get_current_employee(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    """The logged-in employee, or answer 401."""
    slack_id = read_token(authorization, EMPLOYEE_TOKEN)

    user = db.get(User, slack_id)
    if user is None or user.password_hash is None:
        raise HTTPException(status_code=401, detail="Please log in")
    return user
