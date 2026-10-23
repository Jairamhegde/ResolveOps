import os
import time
import hmac
import hashlib
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from backend.models import User, Admin
from backend.schemas import AdminType
from dotenv import load_dotenv

load_dotenv()

def is_admin_in_database(db: Session, user_id: str, check_type: str = "admin") -> bool:
    
    if check_type == "admin":
        found = db.query(Admin).filter(Admin.slack_id == user_id).first()
    elif check_type == "super_admin":
        found = db.query(Admin).filter(
            Admin.slack_id == user_id,
            Admin.role == AdminType.super_admin.value
        ).first()
    else:
        found = db.query(User).filter(User.slack_id == user_id).first()
    return found is not None


from logger import logger

async def verify_slack_signature(request: Request):
    signing_secret = (os.getenv("SIGNING_SECRET") or "").strip()
    time_stamp = request.headers.get("X-Slack-Request-Timestamp")
    slack_signature = request.headers.get("X-Slack-Signature")

    if not signing_secret:
        logger.error("Server configuration error: SIGNING_SECRET is missing in environment variables.")
        raise HTTPException(status_code=500, detail="Server configuration error: SIGNING_SECRET missing")

    if not slack_signature or not time_stamp:
        logger.warning("Missing Slack signature or timestamp headers")
        raise HTTPException(status_code=403, detail="Missing Slack headers")
    
    try:
        time_diff = abs(time.time() - int(time_stamp))
    except (ValueError, TypeError):
        raise HTTPException(status_code=403, detail="Invalid Slack timestamp")

    if time_diff > 60 * 5:
        logger.warning(f"Slack request expired. Time diff: {time_diff}s")
        raise HTTPException(status_code=403, detail="Request too old")
    
    body = await request.body() 
    basestring = f"v0:{time_stamp}:{body.decode()}"
    my_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(my_signature, slack_signature):
        logger.warning("Slack signature mismatch")
        raise HTTPException(status_code=403, detail="Invalid signature")

async def verify_github_signature(request: Request):
    github_signature = request.headers.get("X-Hub-Signature-256")
    if not github_signature:
        logger.warning("GitHub webhook request missing X-Hub-Signature-256 header")
        raise HTTPException(status_code=403, detail="No github signature..")

    github_secret = (os.getenv('GITHUB_SECRET') or "").strip()
    if not github_secret:
        logger.error("GITHUB_SECRET environment variable is not set on the server!")
        raise HTTPException(status_code=500, detail="No github secret found.")

    body = await request.body()
    hashed = hmac.new(
        github_secret.encode('utf-8'),
        body,
        digestmod=hashlib.sha256
    )
    sign = "sha256=" + hashed.hexdigest()
    if not hmac.compare_digest(sign, github_signature):
        logger.warning("GitHub webhook signature verification failed (secret mismatch)")
        raise HTTPException(status_code=403, detail="Invalid github signature.")

