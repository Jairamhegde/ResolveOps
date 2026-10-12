import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Admin

load_dotenv()

SECRET = os.environ["JWT_SECRET"]
router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(details: LoginRequest, db: Session = Depends(get_db)):
    """Check the email and password, and return a token that is valid for 8 hours."""
    admin = db.query(Admin).filter(Admin.email == details.email).first()

    if admin is None or admin.password_hash is None or not bcrypt.checkpw(details.password.encode(), admin.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Wrong email or password")

    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode({"sub": str(admin.id), "exp": expires}, SECRET, algorithm="HS256")
    return {"token": token, "email": admin.email, "role": admin.role}


def get_current_admin(authorization: str = Header(None), db: Session = Depends(get_db)) -> Admin:
    """Read 'Authorization: Bearer <token>' and return the logged-in admin, or answer 401."""
    try:
        token = authorization.removeprefix("Bearer ")
        admin_id = int(jwt.decode(token, SECRET, algorithms=["HS256"])["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Please log in")

    admin = db.get(Admin, admin_id)
    if admin is None or admin.password_hash is None:
        raise HTTPException(status_code=401, detail="Please log in")
    return admin
