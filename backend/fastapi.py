from typing import final
from backend.database import SessionLocal
from backend import database
from fastapi import FastAPI,Request,BackgroundTasks,Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import DeclarativeBase
from backend.database import get_db
from dotenv import load_dotenv
import os
from typing import Optional
from sqlalchemy import Column,String,Integer,Text,ForeignKey
import google.generativeai as genai
import httpx
import json


load_dotenv()
note = FastAPI()


class Base(DeclarativeBase):
    pass
#---------------------Base Model--------------------------------
class InserTicket(BaseModel):
    slack_id : str
    issue_text: str
    category : Optional[str] = "other"
    priority : Optional[str] = "High"
    status : Optional[str] = "active"
    suggested_fix : Optional[str] = "No fix suggested"


class CreateAdmin(BaseModel):
    slack_id : str
    email : str
    role : Optional[str] = "it support"


class CreateUser(BaseModel):
    slack_id : str
    name : str
    email : str
    


#---------------------Table models-------------------------------
class User(Base):
    __tablename__ = "user_details"
    slack_id = Column(String, primary_key = True)
    name = Column(String)
    email = Column(Text)

class Ticket(Base):
    __tablename__ = "ticket"
    id  = Column(Integer, primary_key = True)
    slack_id = Column(String,ForeignKey ('user_details.slack_id'))
    issue_text = Column(Text)
    priority = Column(String)
    category = Column(String)
    status = Column(String, default="active")
    suggested_fix = Column(Text)

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer,primary_key = True)
    slack_id = Column(String,ForeignKey("user_details.slack_id"))
    email = Column(Text)
    role = Column(String)


# ---------------------------------------------------------------

# -------------------------Functions-----------------------------
genai.configure(api_key= os.getenv("GEMINI_API"))
def get_ai_data(issue_text):
    prompt = f"""
    You are an expert IT Helpdesk Assistant. Analyze this user issue: "{issue_text}"
    
    Return a raw JSON object with exactly these three keys:
    - "category": (Choose one: Network, Hardware, Software, Account Access, or Other)
    - "priority": (Choose one: High, Medium, or Low)
    - "suggested_fix": (A short, 1-sentence troubleshooting step for the IT admin)
    
    Return ONLY the JSON. Do not use markdown blocks like ```json.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        model_response = model.generate_content(prompt)
        clean_response = json.loads(model_response.text.strip())
        return  clean_response
    except Exception as e:
        print(f"Failed to generate response.{e}")
        return dict()


async def insert_ticket_atbackground(user_id:str,issue_text:str,user_name:str):
    db = SessionLocal()
    try:
    
        ai_response = get_ai_data(issue_text)
    
        tocken = os.getenv("BOT_AUTH_TOCKEN")
        headers = {"Authorization":f"Bearer {tocken}"}
        url = f"https://slack.com/api/users.info?user={user_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            request_email = response.json()
        

        if request_email.get("ok"):
            user_email = request_email.get('user',{}).get('profile',{}).get('email')
            exists_user = db.query(User).filter(User.slack_id == user_id).first()
            
            if not exists_user:
                create_user = CreateUser(slack_id = user_id,name = user_name,email=user_email)
                insert_user(create_user)
        
            
            issue_category = ai_response.get("category")
            issue_priority = ai_response.get("priority")
            suggested_fix_froai = ai_response.get("suggested_fix")

            new_ticket = InserTicket(
                slack_id=user_id,
                issue_text=issue_text or "",
                priority=issue_priority or "Low",
                category=issue_category or "other",
                suggested_fix=suggested_fix_froai or "No fix suggested"
            )
            ins = insert_to_ticket(new_ticket)
            if ins:
                return True
            else:
                return False
    except Exception as e :
        db.rollback()
        print(f"Error : {e}")


    finally:
        db.close()
            



def insert_to_ticket(details:InserTicket):
    db= SessionLocal()


    new_ticket = Ticket(
        slack_id = details.slack_id,
        issue_text = details.issue_text,
        priority = details.priority,
        category = details.category,
        status = details.status,
        suggested_fix = details.suggested_fix
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


def insert_admin(details:CreateAdmin):
    db = SessionLocal()
    new_admin = Admin(
        slack_id = details.slack_id,
        email = details.email,
        role = details.role
    )
    try:
        db.add(new_admin)
        db.commit()
    except Exception as e:
        db.rollback()
        print(e)

def insert_user(details:CreateUser):
    db = SessionLocal()
    new_user = User(
        slack_id = details.slack_id,
        name = details.name,
        email = details.email
    )
    try:
        db.add(new_user)
        db.commit()
    except Exception as e:
        db.rollback()
        print(e)

    
##---------------------Helpdesk Endpoint-------------------------
@note.post('/webhook/ticket')
async def webhook(request:Request,background_tasks:BackgroundTasks):

    response = await request.form()
    user_id = response.get("user_id")
    user_name = response.get("user_name")
    issue_text = response.get("text")

    background_tasks.add_task(insert_ticket_atbackground,user_id,issue_text,user_name)
    
    return {"text":"Complaint has been sent."}



@note.post('/webhook/listissue')
async def resolve_issue(request:Request):
    response = await request.form()
    user_id = response.get('user_id')
    user_name = response.get('user_name')
    auth_tocken = os.getenv("BOT_AUTH_TOCKEN")
    headers = {"Authorization":f"Bearer {auth_tocken}"}
    url = f"https://slack.com/api/users.info?user={user_id}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url,headers=headers)
        request_email = response.json()

    db = SessionLocal()
    try:
        if request_email.get("ok"):
            user_email = request_email.get('user',{}).get('profile',{}).get('email')
            admin_exist = db.query(Admin).filter(Admin.slack_id == user_id,Admin.email == user_email).first()
            if admin_exist:
                all_rows = db.query(Ticket).all()
                message = []
                for row in all_rows:
                    message_text = f". *Ticket #{row.id}* | Priority: {row.priority} | Category: {row.category}\n _Issue text :{row.issue_text}"
                    message.append(message_text)
                final_message = "\n\n".join(message)
                
                return {"text":final_message}
            else:
                return {"text":"Acces denied"}
    except Exception as e:
        print (e)
        return ""
    finally:
        db.close()

        






     


    







    



