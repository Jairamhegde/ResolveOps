from typing import Dict, Optional, Any
from fastapi import FastAPI, Request, BackgroundTasks, Depends, Header
from backend.auth import verify_slack_signature, verify_admin, verify_github_signature
from backend.crud import (
    insert_ticket_atbackground,
    background_listissue,
    backround_procces_resolve,
    insert_admin_background
)
from backend.slack_blocks import (
    build_gitpushdetail_block,
    build_gitprdetail_block,
    build_workflow_detail_block
)
import httpx
from logger import logger
from backend.sla import escalate_active_tickets
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import os
app = FastAPI()
load_dotenv()

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
    response_url = response.get("response_url")
    user_id = response.get("user_id")
    user_name = response.get("user_name")
    issue_text = response.get("text")

    background_tasks.add_task(insert_ticket_atbackground, user_id, issue_text, user_name,response_url)
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

@app.post('/webhook/add-admin',dependencies=[Depends(verify_slack_signature)])
async def add_admin(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    response_url = form.get('response_url')
    user_id = form.get('user_id')
    slack_id = form.get("text", "").strip()
    background_tasks.add_task(insert_admin_background, user_id, slack_id, response_url)
    return {'text': f'Processing request...:{slack_id}'}

# 
@app.post("/webhook/github", dependencies=[Depends(verify_github_signature)])
async def get_github_updates(payload: Dict[str, Any], x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event")):
    if not x_github_event:
        return {"status": "ignored", "reason": "No event header"}

    if x_github_event == "ping":
        logger.info("GitHub ping event received successfully")
        return {"status": "ok", "message": "Pong! Webhook configured successfully."}

    try:
        channel = {'InternIQ': 'C0C1CDUGQ2C', 'HybridGuard': 'C0C0CV1EWG1'}

        repo_info = payload.get('repository') or {}
        reponame = repo_info.get('name')
        
        channel_id = channel.get(reponame)
        if not channel_id:
            logger.info(f"Ignoring GitHub event: no channel mapping for repository '{reponame}'")
            return {"status": "ignored", "reason": f"No channel mapping for repository: {reponame}"}

        bot_token = (os.getenv('BOT_AUTH_TOCKEN') or os.getenv('BOT_AUTH_TOKEN') or os.getenv('SLACK_BOT_TOKEN') or "").strip()

        if x_github_event == "push":
            commit_details = payload.get('head_commit') or {}
            
            if commit_details:
                commiter_name = commit_details.get('author', {}).get('username') or commit_details.get('author', {}).get('name') or "Unknown"
                comm_mess = commit_details.get("message") or "No commit message"
                date = commit_details.get('author', {}).get('date', "")
                modified_file = commit_details.get("modified") or []
                
                details = {
                    'event': 'push',
                    'name': commiter_name,
                    'date': date,
                    'modified': modified_file,
                    'message': comm_mess
                }
                block = build_gitpushdetail_block(detail=details)

                message = {
                    'channel': channel_id,
                    'text': f"New push by {commiter_name}",
                    'blocks': block
                }
                
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={
                            "Authorization": f"Bearer {bot_token}",
                            "Content-Type": "application/json"
                        },
                        json=message
                    )
                logger.info(f"Sent push notification for {reponame} to Slack channel {channel_id}")
                    
        # Handle Pull Request Events
        elif x_github_event == "pull_request":
            action = payload.get("action")
            pr_data = payload.get("pull_request") or {}
            repo_name = reponame or ""
            
            pr_user = (pr_data.get("user") or {}).get("login", "Unknown")
            pr_title = pr_data.get("title", "")
            pr_body = pr_data.get("body") or ""
            pr_state = pr_data.get("state", "")
            pr_url = pr_data.get("html_url", "")
            
            details = {
                "action": action,
                "user": pr_user,
                "title": pr_title,
                "body": pr_body,
                "state": pr_state,
                "url": pr_url,
                "repo": repo_name
            }
            
            block = build_gitprdetail_block(detail=details)

            message = {
                'channel': channel_id,  
                'text': f"PR {action} by {pr_user}",
                'blocks': block
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {bot_token}",
                        "Content-Type": "application/json"
                    },
                    json=message
                )
            logger.info(f"Sent PR notification for {reponame} to Slack channel {channel_id}")
        
        elif x_github_event == "workflow_run":
            body = payload.get("workflow_run") or {}
            if body:
                event = body.get("event") or x_github_event
                name = body.get("name", "")
                status = body.get('status', '')
                conclusion = body.get('conclusion', '')
                html_url = body.get('html_url', '')

                blk = build_workflow_detail_block(event, name, status, conclusion, html_url)
                messg = {
                    'channel': channel_id,
                    'text': 'Workflow Run',
                    'blocks': blk
                }
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={
                            'Authorization': f"Bearer {bot_token}",
                            'Content-Type': 'application/json'
                        },
                        json=messg
                    )
                logger.info(f"Sent workflow notification for {reponame} to Slack channel {channel_id}")
            else:
                logger.info('No workflow_run details in github payload')

        return {'status': 'ok'}
    except Exception as e:
        logger.exception(f"GitHub webhook request processing failed: {e}")
        return {'status': 'failed', 'detail': str(e)}



    
