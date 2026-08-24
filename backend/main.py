from fastapi import FastAPI, Request, BackgroundTasks, Depends
from backend.auth import verify_slack_signature, verify_admin
from backend.crud import (
    insert_ticket_atbackground,
    background_listissue,
    backround_procces_resolve,
    insert_admin_background
)

from logger import logger
from backend.sla import escalate_active_tickets
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()

scheduler = BackgroundScheduler()

@app.on_event('startup')
def start_scheduler():
    scheduler.add_job(escalate_active_tickets, 'interval', minutes=15, id="sla_escalation_job")
    scheduler.start()
    logger.info("Scheduler started")

@app.on_event('shutdown')
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler shutdown.")

##---------------------Helpdesk Endpoint-------------------------

@app.post('/webhook/ticket', dependencies=[Depends(verify_slack_signature)])
async def webhook(request: Request, background_tasks: BackgroundTasks):
    response = await request.form()
    user_id = response.get("user_id")
    user_name = response.get("user_name")
    issue_text = response.get("text")

    # is_verified = await verify_admin(user_id, check_type="user")
    # if not is_verified :
    #     return {'text':'Acces denied'}
    
    background_tasks.add_task(insert_ticket_atbackground, user_id, issue_text, user_name)
    
    return {"text": "Complaint has been sent."}


@app.post('/webhook/listissue', dependencies=[Depends(verify_slack_signature)])
async def resolve_issue(request: Request, background_tasks: BackgroundTasks):
    response = await request.form()
    user_id = response.get('user_id')
    response_url = response.get('response_url')

    if not response_url:
        return {"text": "Error: No response URL provided."}

    background_tasks.add_task(background_listissue, user_id, response_url)
    return {"text": "Fetching tickets..."}


@app.post('/webhook/resolve', dependencies=[Depends(verify_slack_signature)])
async def resolve_ticket(resolve: Request, background_tasks: BackgroundTasks):
    form = await resolve.form()
    response_url = form.get('response_url')
    user_id = form.get('user_id')
    command_text = form.get('text', '').strip()
    
    if not response_url:
        return {"text": "Error: No response URL provided."}

    if not command_text.isdigit():
        return {"text": "Please provide a valid numeric Ticket ID. Example: `/resolve 12`"}
    
    ticket_id = int(command_text)
    
    background_tasks.add_task(backround_procces_resolve, user_id, ticket_id, response_url)
    return {"text": "Resolving..."}

@app.get('/api/health')
async def health_check():
    return {"status": "ok"}

@app.post('/webhook/add-admin')
async def add_admin(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    response_url = form.get('response_url')
    user_id = form.get('user_id')
    slack_id = form.get("text", "").strip()
    background_tasks.add_task(insert_admin_background, user_id, slack_id, response_url)
    return {'text': f'Processing request...:{slack_id}'}


    # , dependencies=[Depends(verify_slack_signature)]


    