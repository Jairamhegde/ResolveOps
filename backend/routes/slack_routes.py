import json
from fastapi import APIRouter, Request, BackgroundTasks, Depends, Response
from pydantic import ValidationError
from backend.auth import verify_slack_signature
from backend.schemas import AdminType, ValidateAdmin
from backend.crud import (
    insert_ticket_background,
    background_listissue,
    background_process_resolve,
    insert_admin_background,
    background_fix_feedback,
    background_answer_admin_fix
)
from backend.slack_blocks import (
    RESOLVE_ACTION_ID,
    FIX_RESOLVED_ACTION_ID,
    FIX_NOT_RESOLVED_ACTION_ID,
    USER_CONFIRMS_FIX_ACTION_ID,
    USER_REJECTS_FIX_ACTION_ID
)
from logger import logger

router = APIRouter(tags=["slack"])


@router.post('/webhook/ticket', dependencies=[Depends(verify_slack_signature)])
async def webhook(request: Request, background_tasks: BackgroundTasks):
    response = await request.form()
    response_url = response.get("response_url")
    user_id = response.get("user_id")
    user_name = response.get("user_name")
    issue_text = response.get("text")

    background_tasks.add_task(insert_ticket_background, user_id, issue_text, user_name,response_url)
    return Response(status_code=200)


@router.post('/webhook/listissue', dependencies=[Depends(verify_slack_signature)])
async def list_issues(request: Request, background_tasks: BackgroundTasks):
    response = await request.form()
    user_id = response.get('user_id')
    response_url = response.get('response_url')

    if not response_url:
        return {"text": "Error: No response URL provided."}

    background_tasks.add_task(background_listissue, user_id, response_url)
    return Response(status_code=200)


@router.post('/webhook/resolve', dependencies=[Depends(verify_slack_signature)])
async def resolve_ticket(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    response_url = form.get('response_url')
    user_id = form.get('user_id')
    command_text = form.get('text', '').strip()
    
    if not response_url:
        return {"text": "Error: No response URL provided."}

    if not command_text.isdigit():
        return {"text": "Please provide a valid numeric Ticket ID. Example: `/resolve 12`"}
    
    ticket_id = int(command_text)
    
    background_tasks.add_task(background_process_resolve, user_id, ticket_id, response_url)
    return Response(status_code=200)


@router.post('/webhook/add-admin',dependencies=[Depends(verify_slack_signature)])
async def add_admin(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    response_url = form.get('response_url')
    user_id = form.get('user_id')
    valid_types = ", ".join(admin_type.value for admin_type in AdminType)

    parts = form.get("text", "").split()
    if len(parts) != 2:
        return {"text": f"Usage: `/add-admin @username admin_type`. Admin types: {valid_types}"}

    slack_id, admin_type = parts
    try:
        admin = ValidateAdmin(role=admin_type.lower())
    except ValidationError:
        return {"text": f"Unknown admin type `{admin_type}`. Admin types: {valid_types}"}

    background_tasks.add_task(insert_admin_background, user_id, slack_id, response_url, admin.role)
    return Response(status_code=200)


@router.post("/webhook/interactions", dependencies=[Depends(verify_slack_signature)])
async def handle_slack_interaction(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    payload_raw = form.get("payload")
    if not payload_raw:
        return Response(status_code=400, content="Missing payload")

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON payload")

    interaction_type = payload.get("type")
    if interaction_type != "block_actions":
        logger.info(f"Ignoring Slack interaction of type '{interaction_type}'")
        return Response(status_code=200)

    user_id = payload.get("user", {}).get("id")
    response_url = payload.get("response_url")
    actions = payload.get("actions", [])
    action_id = actions[0].get("action_id") if actions else None

    if action_id in (USER_CONFIRMS_FIX_ACTION_ID, USER_REJECTS_FIX_ACTION_ID):
        ticket_val, _, admin_id = actions[0].get("value", "").partition(":")
        if not ticket_val.isdigit() or not admin_id or not response_url:
            logger.warning(f"Invalid '{action_id}' action from {user_id}: value={actions[0].get('value')!r}")
            return Response(status_code=200)

        fixed = action_id == USER_CONFIRMS_FIX_ACTION_ID
        background_tasks.add_task(background_answer_admin_fix, user_id, int(ticket_val), admin_id, fixed, response_url)
        return Response(status_code=200)

    if action_id not in (RESOLVE_ACTION_ID, FIX_RESOLVED_ACTION_ID, FIX_NOT_RESOLVED_ACTION_ID):
        logger.info(f"Ignoring Slack action '{action_id}' from {user_id}")
        return Response(status_code=200)

    ticket_val = actions[0].get("value")
    if not (ticket_val and str(ticket_val).isdigit()) or not response_url:
        logger.warning(f"Invalid '{action_id}' action from {user_id}: value={ticket_val!r}")
        return Response(status_code=200)

    if action_id == RESOLVE_ACTION_ID:
        background_tasks.add_task(background_process_resolve, user_id, int(ticket_val), response_url)
    else:
        resolved = action_id == FIX_RESOLVED_ACTION_ID
        background_tasks.add_task(background_fix_feedback, user_id, int(ticket_val), resolved, response_url)
    return Response(status_code=200)
