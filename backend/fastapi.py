from fastapi import FastAPI,Request
from pydantic import BaseModel

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import DeclarativeBase
from backend.database import SessionLocal
from dotenv import load_dotenv
import os
from typing import Optional
from sqlalchemy import Column,String,Integer,Text,ForeignKey
import google.generativeai as genai
import requests
import json


load_dotenv()
note = FastAPI()
db = SessionLocal()

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
    priority = Column(Integer)
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



def insert_to_ticket(details:InserTicket):
   

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


def insert_admin(details:CreateAdmin):
    new_admin = Admin(
        slack_id = details.slack_id,
        email = details.email,
        role = details.role
    )
    db.add(new_admin)
    db.commit()

def insert_user(details:CreateUser):
    new_user = User(
        slack_id = details.slack_id,
        name = details.name,
        email = details.email
    )
    db.add(new_user)
    db.commit()

    
##---------------------Helpdesk Endpoint-------------------------
@note.post('/webhook/ticket')
async def webhook(request:Request):

    response = await request.form()
    user_id = response.get("user_id")
    user_name = response.get("user_name")
    issue_text = response.get("text")

    ai_response = get_ai_data(issue_text)
    print(ai_response)

    tocken = os.getenv("BOT_AUTH_TOCKEN")
    headers = {"Authorization":f"Bearer {tocken}"}
    url = f"https://slack.com/api/users.info?user={user_id}"
    request_email = requests.get(url,headers=headers).json()

    if request_email.get("ok"):
        user_email = request_email.get('user',{}).get('profile',{}).get('email')
        exists_user = db.query(User).filter(User.slack_id == user_id).first()
        if exists_user:
            print("User found")
        else:
            print("User not found")
            create_user = CreateUser(slack_id = user_id,name = user_name,email=user_email)
            insert_user(create_user)
            print("User aded succesfully")
        
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
            print("Inserted the  ticket")

    # print(reuqest_email)
    print(user_email)
    print(f"{user_id},{user_name},{issue_text}")

    return "We will resolve it soon."



    



