from logger import logger
import os
import time
from sqlalchemy import Date,cast
import httpx
from backend.database import SessionLocal
from backend.models import User, Ticket, Admin
from backend.schemas import InserTicket, CreateAdmin, CreateUser
from backend.ai import get_ai_data
from backend.auth import verify_admin
from datetime import datetime

async def insert_ticket_atbackground(user_id: str, issue_text: str, user_name: str,response_url:str):
    db = SessionLocal()
    try:
        ai_response = get_ai_data(issue_text)
    
        tocken = os.getenv("BOT_AUTH_TOCKEN")
        headers = {"Authorization": f"Bearer {tocken}"}
        url = f"https://slack.com/api/users.info?user={user_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            request_email = response.json()
        
        if request_email.get("ok"):
            user_email = request_email.get('user', {}).get('profile', {}).get('email')
            exists_user = db.query(User).filter(User.slack_id == user_id).first()
            
            if not exists_user:
                create_user = CreateUser(slack_id=user_id, name=user_name, email=user_email)
                insert_user(create_user)
            if exists_user:
                ticket = db.query(Ticket).filter(Ticket.slack_id == user_id,cast(Ticket.created_at,Date)==datetime.now().date()).all()
                if len(ticket) > 5:
                    payload={'text':'No more requests can be submitted today.'}
                    await client.post(response_url,json=payload)
                    return False
                
        
            issue_category = ai_response.get("category")
            issue_priority = ai_response.get("priority")
            suggested_fix_froai = ai_response.get("suggested_fix")

            async with httpx.AsyncClient() as client:
                payload = {"text": f"*Suggested Fix:*\n{suggested_fix_froai}"}
                await client.post(response_url, json=payload)

            new_ticket = InserTicket(
                slack_id=user_id,
                issue_text=issue_text or "",
                priority=issue_priority or 5,
                category=issue_category or "other",
                suggested_fix=suggested_fix_froai or "No fix suggested"
                
            )
            ins = insert_to_ticket(new_ticket)
            if ins:
                return True
            else:
                return False
    except Exception as e:
        db.rollback()
        payload = {"text": f"Server is not active."}
        await client.post(response_url, json=payload)
    finally:
        db.close()

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
        return True
    except Exception as e:
        print(f"Database insertion error: {e}")
        db.rollback()
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
    except Exception as e:
        db.rollback()
        print(e)

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
    except Exception as e:
        db.rollback()
        print(e)

def build_ticket_blocks(tickets):
    priority_emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}
    blocks = [{"type": "header", "text": {"type": "plain_text", "text": "🎫 Active Tickets"}}]

    for row in tickets:
        emoji = priority_emoji.get(row.priority, "⚪")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{row.id}.*Ticket* | *P{row.priority}* | _{row.category}_\n"
                    f"👤 <@{row.slack_id}>\n"
                    f"{row.issue_text}"
                )
            }
        })
        blocks.append({"type": "divider"})

    return blocks

async def backround_procces_resolve(user_id: str, ticket_id: int, response_url: str):
    is_admin = await verify_admin(user_id, 'admin')
    async with httpx.AsyncClient() as client:
        if not is_admin:
            payload = {"text": "Access denied: Only admins can resolve tickets."}
            await client.post(response_url, json=payload)
            return

        db = SessionLocal()
        try:
            ticket_status = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket_status:
                payload = {"text": f"No ticket found with id {ticket_id}"}
                await client.post(response_url, json=payload)
                return
            
            ticket_status.status = 'resolved'
            db.commit()
            
            payload = {"text": f"Resolved ticket :{ticket_id}."}
            await client.post(response_url, json=payload)
        except:
            payload = {"text": f"Server is not active."}
            await client.post(response_url, json=payload)

        finally:
            db.close()

async def background_listissue(user_id: str, response_url: str):
    is_admin = await verify_admin(user_id, check_type="admin")
    async with httpx.AsyncClient() as client:
        if not is_admin:
            await client.post(response_url, json={"text": "Access denied: You are not an admin."})
            return

        db = SessionLocal()
        try:
            all_rows = db.query(Ticket).filter(Ticket.status=='active').order_by(Ticket.id.desc()).limit(15).all()
            if not all_rows:
                payload = {'text': 'No active tickets'}
            else:
                payload = {"blocks": build_ticket_blocks(all_rows)}
            
            await client.post(response_url, json=payload)
        except Exception as e:
            await client.post(response_url, json={"text": "Error fetching tickets."})
        finally:
            db.close()

async def insert_admin_background(user_id: str, slack_id: str, response_url: str):
    # Clean Slack mention format (e.g. <@U12345678|username> -> U12345678)
    target_slack_id = slack_id
    if target_slack_id.startswith("<@") and target_slack_id.endswith(">"):
        target_slack_id = target_slack_id[2:-1].split('|')[0]

    # Strip leading '@' if the admin typed '@username' literally
    target_slack_id = target_slack_id.lstrip('@')

    # If it is a username instead of a Slack ID (Slack IDs usually start with 'U' and are 9+ chars)
    if not (target_slack_id.startswith('U') and len(target_slack_id) >= 9):
        db = SessionLocal()
        try:
            local_user = db.query(User).filter(User.name == target_slack_id).first()
            if local_user:
                target_slack_id = local_user.slack_id
        finally:
            db.close()

    is_admin = await verify_admin(user_id, 'admin')
    async with httpx.AsyncClient() as client:
        if not is_admin:
            payload = {'text': 'Access Denied. You are not an admin.'}
            await client.post(response_url, json=payload)
            return

        if not target_slack_id:
            payload = {'text': 'Please specify a user. Example: `/add-admin @username`'}
            await client.post(response_url, json=payload)
            return

        try:
            token = os.getenv("BOT_AUTH_TOCKEN")
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://slack.com/api/users.info?user={target_slack_id}"
            response = await client.get(url, headers=headers)
            user_data = response.json()
            
            if user_data.get("ok"):
                profile = user_data.get('user', {}).get('profile', {})
                user_email = profile.get('email')
                user_name = user_data.get('user', {}).get('real_name') or user_data.get('user', {}).get('name', 'IT Support')
                
                if not user_email:
                    payload = {'text': f'Failed to retrieve email for <@{target_slack_id}>.'}
                    await client.post(response_url, json=payload)
                    return
                
                status = await add_admin(target_slack_id, user_name, user_email)
                
                if status == "success":
                    payload = {'text': f'Added <@{target_slack_id}> as admin.'}
                elif status == "already_admin":
                    payload = {'text': f'<@{target_slack_id}> is already an admin.'}
                else:
                    payload = {'text': 'Failed to add admin due to a database error.'}
                
                await client.post(response_url, json=payload)
            else:
                payload = {'text': f'Slack API Error: Could not find user information.'}
                await client.post(response_url, json=payload)
                logger.error(f"Slack API error fetching user details: {user_data.get('error')}")

        except Exception as e:
            logger.error(f"Failed to insert admin: {e}")
            await client.post(response_url, json={'text': 'Internal server error occurred.'})
     
async def add_admin(slack_id: str, name: str, email: str, role: str = 'it support'):
    db = SessionLocal()
    try:
        #check user already exists
        user = db.query(User).filter(User.slack_id == slack_id).first()
        if not user:
            new_user = User(slack_id=slack_id, name=name, email=email)
            db.add(new_user)
            db.flush() 

        #check if already admin
        existing_admin = db.query(Admin).filter(Admin.slack_id == slack_id).first()
        if existing_admin:
            return "already_admin"
        #else add admin
        new_admin = Admin(
            slack_id=slack_id,
            email=email,
            role=role
        )
        db.add(new_admin)
        db.commit()
        return "success"
    except Exception as e:
        db.rollback()
        logger.error(f"Admin database insertion failed: {e}")
        return "failed"
    finally:
        db.close()

def build_gitpushdetail_block(detail: dict):
    modified_files = detail.get('modified', [])
    # Format the list of files nicely, or show 'None'
    if modified_files:
        modified_text = ", ".join(f"`{f}`" for f in modified_files)
    else:
        modified_text = "`None`"
        
    # Format the commit message as a blockquote for a modern look
    message = detail.get('message') or 'No message provided'
    quoted_message = f"> {message.replace(chr(10), chr(10) + '> ')}"

    block = [
        {
            "type": "header", 
            "text": {"type": "plain_text", "text": "🔹New GitHub Push", "emoji": True}
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Pushed by:* @{detail.get('name')}"},
                {"type": "mrkdwn", "text": f"*Date:* <!date^{int(time.time())}^{{date_short_pretty}} at {{time}}|{detail.get('date')}>"} 
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Event Type:*\n`{detail.get('event')}`"},
                {"type": "mrkdwn", "text": f"*Files Changed:*\n`{len(modified_files)}`"}
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Modified Files:*\n{modified_text}"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Commit Message:*\n{quoted_message}"}
        }
    ]
    return block

def build_gitprdetail_block(detail: dict):
    # Format the PR description as a blockquote
    body = detail.get('body') or 'No description provided'
    quoted_body = f"> {body.replace('\n', '\n> ')}"

    block = [
        {
            "type": "header", 
            "text": {"type": "plain_text", "text": "Pull Request Update", "emoji": True}
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Triggered by:* @{detail.get('user')}"},
                {"type": "mrkdwn", "text": f"*Repository:* {detail.get('repo')}"} 
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Action:*\n`{detail.get('action')}`"},
                {"type": "mrkdwn", "text": f"*Status:*\n`{detail.get('state')}`"}
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Title:*\n<{detail.get('url')}|{detail.get('title')}>"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Description:*\n{quoted_body}"}
        }
    ]
    return block


def build_workflow_detail_block(event, name, status, conclusion, html_url):
    block = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Workflow Run: {name}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Event:* `{event}`"},
                {"type": "mrkdwn", "text": f"*Status:* {status}"},
                {"type": "mrkdwn", "text": f"*Conclusion:* {conclusion}"}
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<{html_url}|View Workflow Run on GitHub>"
            }
        }
    ]
    return block


