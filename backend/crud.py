import os
from datetime import datetime, timedelta

import httpx
from sqlalchemy import func

from logger import logger
from backend.database import SessionLocal
from backend.models import User, Ticket, Admin
from backend.schemas import InserTicket, CreateAdmin, CreateUser
from backend.ai import get_ai_data
from backend.auth import verify_admin
from backend.slack_blocks import build_ticket_blocks, build_empty_ticket_blocks


DAILY_TICKET_LIMIT = 5
SLACK_USER_INFO_URL = "https://slack.com/api/users.info"

# Slack allows max 50 blocks per message; each ticket uses 3 blocks + 5 for header/summary/footer
LIST_ISSUE_LIMIT = 12


# Slack helpers

async def send_slack_response(response_url: str, payload: dict):
    """Post a message back to Slack via the slash command's response_url."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(response_url, json=payload)
            logger.info(f"Slack response sent (status {response.status_code})")
    except Exception as e:
        logger.error(f"Failed to send Slack response: {e}")


async def fetch_slack_user(slack_id: str) -> dict:
    """Fetch a user's profile from the Slack users.info API."""
    token = os.getenv("BOT_AUTH_TOCKEN")
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(SLACK_USER_INFO_URL, params={"user": slack_id}, headers=headers)
        user_data = response.json()

    if not user_data.get("ok"):
        logger.error(f"Slack users.info failed for {slack_id}: {user_data.get('error')}")
    else:
        logger.info(f"Fetched Slack profile for {slack_id}")

    return user_data


# Database operations

def insert_to_ticket(details: InserTicket):
    db = SessionLocal()
    new_ticket = Ticket(
        slack_id=details.slack_id,
        issue_text=details.issue_text,
        priority=details.priority,
        category=details.category,
        status=details.status,
        suggested_fix=details.suggested_fix
    )

    try:
        db.add(new_ticket)
        db.commit()
        logger.info(f"Ticket {new_ticket.id} created for user {details.slack_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ticket insertion failed for user {details.slack_id}: {e}")
        return False
    finally:
        db.close()


def insert_admin(details: CreateAdmin):
    db = SessionLocal()
    new_admin = Admin(
        slack_id=details.slack_id,
        email=details.email,
        role=details.role
    )

    try:
        db.add(new_admin)
        db.commit()
        logger.info(f"Admin {details.slack_id} inserted with role '{details.role}'")
    except Exception as e:
        db.rollback()
        logger.error(f"Admin insertion failed for {details.slack_id}: {e}")
    finally:
        db.close()


def insert_user(details: CreateUser):
    db = SessionLocal()
    new_user = User(
        slack_id=details.slack_id,
        name=details.name,
        email=details.email
    )

    try:
        db.add(new_user)
        db.commit()
        logger.info(f"User {details.slack_id} created")
    except Exception as e:
        db.rollback()
        logger.error(f"User insertion failed for {details.slack_id}: {e}")
    finally:
        db.close()


async def add_admin(slack_id: str, name: str, email: str, role: str = 'it support'):
    db = SessionLocal()
    try:
        # Create the user first if they don't exist yet
        user = db.query(User).filter(User.slack_id == slack_id).first()
        if not user:
            db.add(User(slack_id=slack_id, name=name, email=email))
            db.flush()
            logger.info(f"User {slack_id} created while adding admin")

        # Skip if already an admin
        existing_admin = db.query(Admin).filter(Admin.slack_id == slack_id).first()
        if existing_admin:
            logger.info(f"{slack_id} is already an admin")
            return "already_admin"

        db.add(Admin(slack_id=slack_id, email=email, role=role))
        db.commit()
        logger.info(f"Added {slack_id} as admin with role '{role}'")
        return "success"
    except Exception as e:
        db.rollback()
        logger.error(f"Admin database insertion failed for {slack_id}: {e}")
        return "failed"
    finally:
        db.close()


# Background workers (Slack slash commands)

async def insert_ticket_atbackground(user_id: str, issue_text: str, user_name: str, response_url: str):
    logger.info(f"Processing new ticket from {user_id}")
    db = SessionLocal()

    try:
        user_data = await fetch_slack_user(user_id)
        if not user_data.get("ok"):
            await send_slack_response(response_url, {"text": "Could not verify your Slack profile. Please try again later."})
            return False

        # Create the user on first request
        exists_user = db.query(User).filter(User.slack_id == user_id).first()
        if not exists_user:
            user_email = user_data.get('user', {}).get('profile', {}).get('email')
            insert_user(CreateUser(slack_id=user_id, name=user_name, email=user_email))

        # Enforce the daily ticket limit before calling the AI
        start_of_today = datetime.combine(datetime.now().date(), datetime.min.time())
        today_count = db.query(Ticket).filter(
            Ticket.slack_id == user_id,
            Ticket.created_at >= start_of_today,
            Ticket.created_at < start_of_today + timedelta(days=1)
        ).count()

        if today_count >= DAILY_TICKET_LIMIT:
            logger.warning(f"User {user_id} hit the daily ticket limit ({today_count})")
            await send_slack_response(response_url, {"text": "No more requests can be submitted today."})
            return False

        ai_response = await get_ai_data(issue_text)
        logger.info(f"AI classified ticket from {user_id}: category={ai_response.get('category')}, priority={ai_response.get('priority')}")

        issue_category = ai_response.get("category")
        issue_priority = ai_response.get("priority")
        suggested_fix_from_ai = ai_response.get("suggested_fix")

        await send_slack_response(response_url, {"text": f"*Suggested Fix:*\n{suggested_fix_from_ai}"})

        new_ticket = InserTicket(
            slack_id=user_id,
            issue_text=issue_text or "",
            priority=issue_priority or 5,
            category=issue_category or "other",
            suggested_fix=suggested_fix_from_ai or "No fix suggested"
        )
        return insert_to_ticket(new_ticket)

    except Exception as e:
        db.rollback()
        logger.error(f"Ticket processing failed for {user_id}: {e}")
        await send_slack_response(response_url, {"text": "Server is not active."})
        return False
    finally:
        db.close()


async def backround_procces_resolve(user_id: str, ticket_id: int, response_url: str):
    logger.info(f"Resolve request for ticket {ticket_id} by {user_id}")

    is_admin = await verify_admin(user_id, 'admin')
    if not is_admin:
        logger.warning(f"Non-admin {user_id} tried to resolve ticket {ticket_id}")
        await send_slack_response(response_url, {"text": "Access denied: Only admins can resolve tickets."})
        return

    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found")
            await send_slack_response(response_url, {"text": f"No ticket found with id {ticket_id}"})
            return

        ticket.status = 'resolved'
        db.commit()
        logger.info(f"Ticket {ticket_id} resolved by {user_id}")
        await send_slack_response(response_url, {"text": f"Resolved ticket :{ticket_id}."})
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to resolve ticket {ticket_id}: {e}")
        await send_slack_response(response_url, {"text": "Server is not active."})
    finally:
        db.close()


async def background_listissue(user_id: str, response_url: str):
    logger.info(f"List-issues request by {user_id}")

    is_admin = await verify_admin(user_id, check_type="admin")
    if not is_admin:
        logger.warning(f"Non-admin {user_id} tried to list tickets")
        await send_slack_response(response_url, {"text": "Access denied: You are not an admin."})
        return

    db = SessionLocal()
    try:
        # Priority 1 is the most urgent, so sort ascending; newest first within a priority
        all_rows = (
            db.query(Ticket)
            .filter(Ticket.status == 'active')
            .order_by(Ticket.priority.asc(), Ticket.id.desc())
            .limit(LIST_ISSUE_LIMIT)
            .all()
        )

        # Active ticket count per priority, for the summary line
        priority_counts = dict(
            db.query(Ticket.priority, func.count(Ticket.id))
            .filter(Ticket.status == 'active')
            .group_by(Ticket.priority)
            .all()
        )
        total_active = sum(priority_counts.values())
        logger.info(f"Fetched {len(all_rows)} of {total_active} active tickets")

        if not all_rows:
            payload = {
                "text": "No active tickets",
                "blocks": build_empty_ticket_blocks()
            }
        else:
            payload = {
                "text": f"{total_active} active ticket(s)",
                "blocks": build_ticket_blocks(all_rows, priority_counts, total_active)
            }

        await send_slack_response(response_url, payload)
    except Exception as e:
        logger.error(f"Failed to fetch active tickets: {e}")
        await send_slack_response(response_url, {"text": "Error fetching tickets."})
    finally:
        db.close()


async def insert_admin_background(user_id: str, slack_id: str, response_url: str):
    logger.info(f"Add-admin request by {user_id} for '{slack_id}'")

    # Clean Slack mention format (e.g. <@U12345678|username> -> U12345678)
    target_slack_id = slack_id
    if target_slack_id.startswith("<@") and target_slack_id.endswith(">"):
        target_slack_id = target_slack_id[2:-1].split('|')[0]

    # Strip leading '@' if the admin typed '@username' literally
    target_slack_id = target_slack_id.lstrip('@')

    # If it is a username instead of a Slack ID (Slack IDs usually start with 'U' and are 9+ chars)
    if target_slack_id and not (target_slack_id.startswith('U') and len(target_slack_id) >= 9):
        db = SessionLocal()
        try:
            local_user = db.query(User).filter(User.name == target_slack_id).first()
            if local_user:
                logger.info(f"Resolved username '{target_slack_id}' to {local_user.slack_id}")
                target_slack_id = local_user.slack_id
        except Exception as e:
            logger.error(f"Username lookup failed for '{target_slack_id}': {e}")
        finally:
            db.close()

    is_admin = await verify_admin(user_id, 'admin')
    if not is_admin:
        logger.warning(f"Non-admin {user_id} tried to add an admin")
        await send_slack_response(response_url, {'text': 'Access Denied. You are not an admin.'})
        return

    if not target_slack_id:
        await send_slack_response(response_url, {'text': 'Please specify a user. Example: `/add-admin @username`'})
        return

    try:
        user_data = await fetch_slack_user(target_slack_id)
        if not user_data.get("ok"):
            await send_slack_response(response_url, {'text': 'Slack API Error: Could not find user information.'})
            return

        slack_user = user_data.get('user', {})
        user_email = slack_user.get('profile', {}).get('email')
        user_name = slack_user.get('real_name') or slack_user.get('name', 'IT Support')

        if not user_email:
            logger.warning(f"No email found for {target_slack_id}")
            await send_slack_response(response_url, {'text': f'Failed to retrieve email for <@{target_slack_id}>.'})
            return

        status = await add_admin(target_slack_id, user_name, user_email)

        if status == "success":
            payload = {'text': f'Added <@{target_slack_id}> as admin.'}
        elif status == "already_admin":
            payload = {'text': f'<@{target_slack_id}> is already an admin.'}
        else:
            payload = {'text': 'Failed to add admin due to a database error.'}

        await send_slack_response(response_url, payload)
    except Exception as e:
        logger.error(f"Failed to insert admin {target_slack_id}: {e}")
        await send_slack_response(response_url, {'text': 'Internal server error occurred.'})
