from backend.models import User
from backend.models import Ticket
from backend.database import SessionLocal
from backend.crud import insert_ticket_atbackground
import asyncio
from backend.database import create_engine
from backend.models import *
import logger

def delete_ticket(data:dict): 
    try:
        db = SessionLocal()
        filtered = db.query(User).filter(User.slack_id == data['user_id'])
        filtered.delete()
        logger.info("Test data deletion succesfull.")
        filtered_ticket = db.query(Ticket).filter(Ticket.slack_id == data['user_id'])
        filtered_ticket.delete()
        db.commit()
        return True

    except Exception as e:
        logger.error("failed to remove the test data from database.")



def test_ticket_insertion():
    fake_ticket =  {
        'user_id':123,
        'issue_text': "Sample issue text",
        'user_name':'abc',
        'response_url':'http://example.com'
    }
    res = asyncio.run(insert_ticket_atbackground(
        fake_ticket['user_id'],
        fake_ticket['issue_text'],
        fake_ticket['user_name'],
        fake_ticket['response_url']
    ))
    assert res == True
    result = delete_ticket(fake_ticket)
    logger.info(result)


    







