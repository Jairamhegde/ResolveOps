import os
import time
import hmac
import hashlib
import httpx
from fastapi import Request, HTTPException
from backend.database import SessionLocal
from backend.models import User, Admin
from dotenv import load_dotenv

load_dotenv()

async def verify_admin(user_id: str, check_type: str = "admin"):

    tocken = os.getenv("BOT_AUTH_TOCKEN")
    headers = {"Authorization": f"Bearer {tocken}"}
    url = f"https://slack.com/api/users.info?user={user_id}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        request_email = response.json()

    if not request_email.get("ok"):
        return False

    user_email = request_email.get('user', {}).get('profile', {}).get('email')

    db = SessionLocal()
    try:
        if check_type == "admin":
            found = db.query(Admin).filter(
                Admin.slack_id == user_id,
                Admin.email == user_email
            ).first()
        else:
            found = db.query(User).filter(
                User.slack_id == user_id,
                User.email == user_email
            ).first()
        return found is not None
    finally:
        db.close()

from logger import logger

async def verify_slack_signature(request: Request):
    signing_signature = (os.getenv("SIGNING_SECRETE") or os.getenv("SIGNING_SECRET") or "").strip()
    time_stamp = request.headers.get("X-Slack-Request-Timestamp")
    slack_signature = request.headers.get("X-Slack-Signature")

    if not signing_signature:
        logger.error("Server configuration error: SIGNING_SECRET / SIGNING_SECRETE is missing in environment variables.")
        raise HTTPException(status_code=500, detail="Server configuration error: SIGNING_SECRETE missing")

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
        signing_signature.encode(),
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

    github_secret = (os.getenv('GITHUB_SECRETE') or os.getenv('GITHUB_SECRET') or "").strip()
    if not github_secret:
        logger.error("Neither GITHUB_SECRETE nor GITHUB_SECRET environment variable is set on the server!")
        raise HTTPException(status_code=500, detail="No github secrete found.")

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

