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
    """
    Looks up the slack user's email via Slack API, then checks if
    that user exists in the admin table (check_type="admin")
    or the regular user table (check_type="user").
    Returns True if verified, False otherwise.
    """
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

signing_signature = os.getenv("SIGNING_SECRETE")

async def verify_slack_signature(request: Request):
    time_stamp = request.headers.get("X-Slack-Request-Timestamp")
    slack_signature = request.headers.get("X-Slack-Signature")

    if not signing_signature:
        print("❌ SIGNING_SECRETE is missing in .env")
        raise HTTPException(status_code=500, detail="Server configuration error: SIGNING_SECRETE missing")

    if not slack_signature or not time_stamp:
        print("❌ Missing Slack Headers")
        raise HTTPException(status_code=403, detail="Missing Slack headers")
    
    time_diff = abs(time.time() - int(time_stamp))
    print(f"🕒 Clock Difference: {time_diff} seconds")
    if time_diff > 60 * 5:
        print("❌ Request too old (Clock drift > 5 mins)")
        raise HTTPException(status_code=403, detail="Request too old")
    
    body = await request.body() 
    basestring = f"v0:{time_stamp}:{body.decode()}"
    my_signature = "v0=" + hmac.new(
        signing_signature.encode(),
        basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(my_signature, slack_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
