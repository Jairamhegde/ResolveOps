import os
from datetime import datetime, timedelta

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from logger import logger
from backend.database import SessionLocal
from backend.models import User, Ticket, Admin, utc_now_naive
from backend.schemas import InsertTicket, CreateAdmin, CreateUser, AdminType, Category
from backend.ai import get_ai_data
from backend.auth import is_admin_in_database
from backend.slack_blocks import (
    build_ticket_blocks,
    build_empty_ticket_blocks,
    build_suggested_fix_blocks,
    build_fix_feedback_result_blocks,
    build_ticket_received_blocks,
    build_resolution_dm_blocks,
    build_command_reply
)


DAILY_TICKET_LIMIT = 5
SLACK_USER_INFO_URL = "https://slack.com/api/users.info"
SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"

LIST_ISSUE_LIMIT = 12

ADMIN_TYPE_TO_TICKET_CATEGORY = {
    AdminType.hardware.value: Category.hardware.value,
    AdminType.network.value: Category.network.value,
    AdminType.software.value: Category.software.value,
    AdminType.iam.value: Category.account_access.value,
}

async def send_slack_response(response_url: str, payload: dict):
    """Post a message back to Slack via the slash command's response_url."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(response_url, json=payload)
            logger.info(f"Slack response sent (status {response.status_code})")
    except Exception as e:
        logger.error(f"Failed to send Slack response: {e}")


async def send_slack_dm(slack_id: str, text: str, blocks: list):
    """Send a direct message from the bot to one Slack user."""
    token = os.getenv("BOT_AUTH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    message = {"channel": slack_id, "text": text, "blocks": blocks}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(SLACK_POST_MESSAGE_URL, json=message, headers=headers)
            result = response.json()
        if not result.get("ok"):
            logger.error(f"Slack DM to {slack_id} failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"Failed to send Slack DM to {slack_id}: {e}")


async def fetch_slack_user(slack_id: str) -> dict:
    """Fetch a user's profile from the Slack users.info API."""
    token = os.getenv("BOT_AUTH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(SLACK_USER_INFO_URL, params={"user": slack_id}, headers=headers)
        user_data = response.json()

    if not user_data.get("ok"):
        logger.error(f"Slack users.info failed for {slack_id}: {user_data.get('error')}")
    else:
        logger.info(f"Fetched Slack profile for {slack_id}")

    return user_data


def insert_to_ticket(db: Session, details: InsertTicket):
    """Insert a ticket and return its id, or None if the insert failed."""
    new_ticket = Ticket(
        slack_id=details.slack_id,
        issue_text=details.issue_text,
        priority=details.priority,
        category=details.category,
        status=details.status,
        suggested_fix=details.suggested_fix,
        flag=details.flag.value if hasattr(details.flag, 'value') else str(details.flag),
        needs_review=details.needs_review
    )

    try:
        db.add(new_ticket)
        db.commit()
        logger.info(f"Ticket {new_ticket.id} created for user {details.slack_id} with status '{details.status}'")
        return new_ticket.id
    except Exception as e:
        db.rollback()
        logger.error(f"Ticket insertion failed for user {details.slack_id}: {e}")
        return None


def insert_admin(db: Session, details: CreateAdmin):
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


def insert_user(db: Session, details: CreateUser):
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


def add_admin(db: Session, slack_id: str, name: str, email: str, role: str) -> str:
    """Make a user an admin. Returns "success", "already_admin" or "failed"."""
    try:
        user = db.query(User).filter(User.slack_id == slack_id).first()
        if not user:
            db.add(User(slack_id=slack_id, name=name, email=email))
            db.flush()
            logger.info(f"User {slack_id} created while adding admin")

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


async def create_ticket(db: Session, user_id: str, issue_text: str, user_name: str) -> dict:
    """Register the user if needed, check the daily limit, classify the issue with AI and save the ticket. Returns the Slack reply."""
    user_data = await fetch_slack_user(user_id)
    if not user_data.get("ok"):
        return {"text": "Could not verify your Slack profile. Please try again later."}

    exists_user = db.query(User).filter(User.slack_id == user_id).first()
    if not exists_user:
        user_email = user_data.get('user', {}).get('profile', {}).get('email')
        insert_user(db, CreateUser(slack_id=user_id, name=user_name, email=user_email))

    start_of_today = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(Ticket).filter(
        Ticket.slack_id == user_id,
        Ticket.created_at >= start_of_today,
        Ticket.created_at < start_of_today + timedelta(days=1)
    ).count()

    if today_count >= DAILY_TICKET_LIMIT:
        logger.warning(f"User {user_id} hit the daily ticket limit ({today_count})")
        return {"text": "No more requests can be submitted today."}

    ai_response = await get_ai_data(issue_text)
    priority = ai_response.get('priority','')
    category = ai_response.get('category','')
    flag = ai_response.get('flag','')
    suggested_fix = ai_response.get('suggested_fix')
    logger.info(f"AI classified ticket from {user_id}: category={category}, priority={priority}")

    if not ai_response:
        status, priority, category, suggested_fix, flag, needs_review = 'active', 3, 'other', None, 'ai_failed', True
    elif flag != 'none':
        status, needs_review = 'active', True
    elif priority <= 2 or category in {'hardware', 'account_access'}:
        status, needs_review = 'active', False
    else:
        status, needs_review = 'pending_response', False

    new_ticket = InsertTicket(
        slack_id=user_id,
        issue_text=issue_text or "",
        priority=priority,
        category=category,
        status=status,
        suggested_fix=suggested_fix,
        flag=flag,
        needs_review=needs_review
    )

    ticket_id = insert_to_ticket(db, new_ticket)
    if ticket_id is None:
        return {"text": "Could not save your ticket. Please try again later."}

    if status == 'pending_response':
        return {
            "text": f"Suggested fix for ticket #{ticket_id}",
            "blocks": build_suggested_fix_blocks(ticket_id, suggested_fix)
        }

    return {
        "text": f"Ticket #{ticket_id} sent to IT support",
        "blocks": build_ticket_received_blocks(ticket_id, None if needs_review else suggested_fix)
    }


async def insert_ticket_background(user_id: str, issue_text: str, user_name: str, response_url: str):
    logger.info(f"Processing new ticket from {user_id}")
    succeded = True
    db = SessionLocal()
    try:
        payload = await create_ticket(db, user_id, issue_text, user_name)
    except Exception as e:
        db.rollback()
        logger.error(f"Ticket processing failed for {user_id}: {e}")
        payload = {"text": "Server is not active."}
        succeded = False
        
    finally:
        db.close()
    await send_slack_response(response_url, build_command_reply(f"/ticket {issue_text or ''}", payload))
    
    return succeded

async def background_fix_feedback(user_id: str, ticket_id: int, resolved: bool, response_url: str):

    """Handle the Resolved / Not resolved buttons on the AI suggested fix."""
    logger.info(f"Fix feedback for ticket {ticket_id} from {user_id}: resolved={resolved}")

    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found")
            await send_slack_response(response_url, {"text": f"No ticket found with id {ticket_id}", "replace_original": False})
            return

        if ticket.slack_id != user_id:
            logger.warning(f"{user_id} tried to answer fix feedback for ticket {ticket_id} owned by {ticket.slack_id}")
            await send_slack_response(response_url, {"text": "Only the person who raised this ticket can respond.", "replace_original": False})
            return

        if ticket.status not in ('pending_response', 'active'):
            logger.info(f"Ticket {ticket_id} already answered (status '{ticket.status}')")
            return

        if resolved:
            ticket.status = 'resolved'
            ticket.resolved_by = 'ai'
        elif ticket.status == 'pending_response':
            ticket.status = 'active'
            ticket.resolved_by = None
            ticket.escalated_at = utc_now_naive()
        db.commit()
        logger.info(f"Ticket {ticket_id} set to '{ticket.status}' from fix feedback")

        await send_slack_response(response_url, {
            "replace_original": True,
            "text": f"Ticket #{ticket_id} {'resolved' if resolved else 'sent to IT support'}",
            "blocks": build_fix_feedback_result_blocks(ticket_id, ticket.suggested_fix, resolved)
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record fix feedback for ticket {ticket_id}: {e}")
        await send_slack_response(response_url, {"text": "Server is not active.", "replace_original": False})
    finally:
        db.close()


def can_admin_handle_ticket(admin: Admin, ticket: Ticket) -> bool:
    """A super_admin can handle every ticket, other admins only tickets in their own category."""
    if admin.role == AdminType.super_admin.value:
        return True

    admin_category = ADMIN_TYPE_TO_TICKET_CATEGORY.get(admin.role)
    return admin_category is not None and admin_category == ticket.category


def resolve_ticket(db: Session, admin_slack_id: str, ticket_id: int):
    """
    An admin marks a ticket as fixed. It waits for the user to confirm, it is not closed yet.
    Returns the message to show the admin, and the ticket when the user must be asked (otherwise None).
    """
    admin = db.query(Admin).filter(Admin.slack_id == admin_slack_id).first()
    if admin is None:
        logger.warning(f"Non-admin {admin_slack_id} tried to resolve ticket {ticket_id}")
        return "Access denied: Only admins can resolve tickets.", None

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        logger.warning(f"Ticket {ticket_id} not found")
        return f"No ticket found with id {ticket_id}", None

    if not can_admin_handle_ticket(admin, ticket):
        logger.warning(f"{admin.role} admin {admin_slack_id} tried to resolve {ticket.category} ticket {ticket_id}")
        return f"Access denied: Ticket {ticket_id} is a `{ticket.category}` ticket and you are a `{admin.role}` admin.", None

    if ticket.status == 'resolved':
        return f"Ticket {ticket_id} is already resolved.", None

    ticket.status = 'awaiting_user'
    db.commit()
    logger.info(f"Ticket {ticket_id} fixed by {admin_slack_id}, waiting for {ticket.slack_id} to confirm")
    return f"Ticket {ticket_id} marked as fixed. Waiting for <@{ticket.slack_id}> to confirm.", ticket


async def background_process_resolve(user_id: str, ticket_id: int, response_url: str):
    logger.info(f"Resolve request for ticket {ticket_id} by {user_id}")

    db = SessionLocal()
    try:
        message, ticket = resolve_ticket(db, user_id, ticket_id)
        if ticket is not None:
            await send_slack_dm(
                ticket.slack_id,
                f"Your ticket #{ticket_id} has been fixed. Is your issue resolved?",
                build_resolution_dm_blocks(ticket_id, ticket.issue_text, user_id)
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to resolve ticket {ticket_id}: {e}")
        message = "Server is not active."
    finally:
        db.close()

    await send_slack_response(response_url, build_command_reply(f"/resolve {ticket_id}", {"text": message}))


def answer_admin_fix(db: Session, user_id: str, ticket_id: int, admin_id: str, fixed: bool) -> str:
    """The user answers the admin's fix: Resolved closes the ticket, Not resolved puts it back in the admin queue."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        return f"No ticket found with id {ticket_id}"

    if ticket.slack_id != user_id:
        logger.warning(f"{user_id} tried to answer the fix for ticket {ticket_id} owned by {ticket.slack_id}")
        return "Only the person who raised this ticket can respond."

    if ticket.status != 'awaiting_user':
        return f"Ticket {ticket_id} was already answered."

    if fixed:
        ticket.status = 'resolved'
        ticket.resolved_by = admin_id
        message = f"Glad it works! Ticket #{ticket_id} has been closed."
    else:
        ticket.status = 'active'
        ticket.escalated_at = utc_now_naive()
        message = f"Ticket #{ticket_id} is still open. An admin will look at it again."

    db.commit()
    logger.info(f"User {user_id} answered the fix for ticket {ticket_id}: fixed={fixed}")
    return message


async def background_answer_admin_fix(user_id: str, ticket_id: int, admin_id: str, fixed: bool, response_url: str):
    db = SessionLocal()
    try:
        message = answer_admin_fix(db, user_id, ticket_id, admin_id, fixed)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record the answer for ticket {ticket_id}: {e}")
        message = "Server is not active."
    finally:
        db.close()

    await send_slack_response(response_url, {"replace_original": True, "text": message})


def list_tickets_for_admin(db: Session, admin_slack_id: str) -> dict:
    """Build the /listissue reply: active tickets in this admin's category, or every active ticket for a super_admin."""
    admin = db.query(Admin).filter(Admin.slack_id == admin_slack_id).first()
    if admin is None:
        logger.warning(f"Non-admin {admin_slack_id} tried to list tickets")
        return {"text": "Access denied: You are not an admin."}

    ticket_filters = [Ticket.status == 'active']

    if admin.role != AdminType.super_admin.value:
        ticket_category = ADMIN_TYPE_TO_TICKET_CATEGORY.get(admin.role)
        if ticket_category is None:
            logger.warning(f"Admin {admin_slack_id} has unknown admin type '{admin.role}'")
            return {"text": f"Your admin type `{admin.role}` is not linked to any ticket category. Ask a super_admin to update it."}
        ticket_filters.append(Ticket.category == ticket_category)

    all_rows = (
        db.query(Ticket)
        .filter(*ticket_filters)
        .order_by(Ticket.priority.asc(), Ticket.id.desc())
        .limit(LIST_ISSUE_LIMIT)
        .all()
    )

    priority_counts = dict(
        db.query(Ticket.priority, func.count(Ticket.id))
        .filter(*ticket_filters)
        .group_by(Ticket.priority)
        .all()
    )
    total_active = sum(priority_counts.values())
    logger.info(f"Fetched {len(all_rows)} of {total_active} active tickets for {admin.role} admin {admin_slack_id}")

    if not all_rows:
        return {
            "text": "No active tickets",
            "blocks": build_empty_ticket_blocks()
        }

    return {
        "text": f"{total_active} active ticket(s)",
        "blocks": build_ticket_blocks(all_rows, priority_counts, total_active)
    }


async def background_listissue(user_id: str, response_url: str):
    logger.info(f"List-issues request by {user_id}")

    db = SessionLocal()
    try:
        payload = list_tickets_for_admin(db, user_id)
    except Exception as e:
        logger.error(f"Failed to fetch active tickets: {e}")
        payload = {"text": "Error fetching tickets."}
    finally:
        db.close()

    await send_slack_response(response_url, build_command_reply("/listissue", payload))


def find_slack_id_by_name(db: Session, name: str) -> str:
    """Turn a username like 'jairam' into a Slack ID using the users we already know. Returns the name unchanged if not found."""
    local_user = db.query(User).filter(User.name == name).first()
    if local_user:
        logger.info(f"Resolved username '{name}' to {local_user.slack_id}")
        return local_user.slack_id
    return name


async def process_add_admin(db: Session, user_id: str, slack_id: str, admin_type: AdminType) -> str:
    """Handle /add-admin: only a super_admin may add admins. Returns the message to show the requester."""
    is_super_admin = is_admin_in_database(db, user_id, 'super_admin')
    if not is_super_admin:
        logger.warning(f"Non-super-admin {user_id} tried to add an admin")
        return 'Access Denied. Only a super_admin can add admins.'

    target_slack_id = slack_id
    if target_slack_id.startswith("<@") and target_slack_id.endswith(">"):
        target_slack_id = target_slack_id[2:-1].split('|')[0]

    target_slack_id = target_slack_id.lstrip('@')

    if target_slack_id and not (target_slack_id.startswith('U') and len(target_slack_id) >= 9):
        target_slack_id = find_slack_id_by_name(db, target_slack_id)

    if not target_slack_id:
        return 'Please specify a user. Example: `/add-admin @username network`'

    user_data = await fetch_slack_user(target_slack_id)
    if not user_data.get("ok"):
        return 'Slack API Error: Could not find user information.'

    slack_user = user_data.get('user', {})
    user_email = slack_user.get('profile', {}).get('email')
    user_name = slack_user.get('real_name') or slack_user.get('name', 'IT Support')

    if not user_email:
        logger.warning(f"No email found for {target_slack_id}")
        return f'Failed to retrieve email for <@{target_slack_id}>.'

    status = add_admin(db, target_slack_id, user_name, user_email, admin_type.value)

    if status == "success":
        return f'Added <@{target_slack_id}> as {admin_type.value} admin.'
    if status == "already_admin":
        return f'<@{target_slack_id}> is already an admin.'
    return 'Failed to add admin due to a database error.'


async def insert_admin_background(user_id: str, slack_id: str, response_url: str, admin_type: AdminType):
    logger.info(f"Add-admin request by {user_id} for '{slack_id}' as '{admin_type.value}'")

    db = SessionLocal()
    try:
        message = await process_add_admin(db, user_id, slack_id, admin_type)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add admin '{slack_id}': {e}")
        message = 'Internal server error occurred.'
    finally:
        db.close()

    await send_slack_response(response_url, build_command_reply(f"/add-admin {slack_id} {admin_type.value}", {'text': message}))
