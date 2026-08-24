import os
import httpx
from backend.database import SessionLocal
from backend.models import User, Ticket, Admin
from backend.schemas import InserTicket, CreateAdmin, CreateUser
from backend.ai import get_ai_data
from backend.auth import verify_admin

async def insert_ticket_atbackground(user_id: str, issue_text: str, user_name: str):
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
        
            issue_category = ai_response.get("category")
            issue_priority = ai_response.get("priority")
            suggested_fix_froai = ai_response.get("suggested_fix")

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
        print(f"Error : {e}")
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
                "text": f"*Ticket #{row.id}* {emoji} *{row.priority}* | _{row.category}_\n{row.issue_text}"
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
            
            payload = {"text": f"✅ Resolved ticket #{ticket_id}."}
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
            all_rows = db.query(Ticket).order_by(Ticket.id.desc()).limit(15).all()
            if not all_rows:
                payload = {'text': 'No active tickets'}
            else:
                payload = {"blocks": build_ticket_blocks(all_rows)}
            
            await client.post(response_url, json=payload)
        except Exception as e:
            print(e)
            await client.post(response_url, json={"text": "Error fetching tickets."})
        finally:
            db.close()
