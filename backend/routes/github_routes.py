from typing import Dict, Optional, Any
import os
import httpx
from fastapi import APIRouter, Depends, Header
from backend.auth import verify_github_signature
from backend.slack_blocks import (
    build_gitpushdetail_block,
    build_gitprdetail_block,
    build_workflow_detail_block
)
from logger import logger

router = APIRouter(tags=["github"])


@router.post("/webhook/github", dependencies=[Depends(verify_github_signature)])
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

        bot_token = (os.getenv('BOT_AUTH_TOKEN') or "").strip()

        if x_github_event == "push":
            commit_details = payload.get('head_commit') or {}
            
            if commit_details:
                committer_name = commit_details.get('author', {}).get('username') or commit_details.get('author', {}).get('name') or "Unknown"
                commit_message = commit_details.get("message") or "No commit message"
                date = commit_details.get('timestamp', "")
                changed_files = (
                    (commit_details.get("added") or [])
                    + (commit_details.get("removed") or [])
                    + (commit_details.get("modified") or [])
                )

                details = {
                    'repo': reponame,
                    'branch': (payload.get('ref') or '').replace('refs/heads/', ''),
                    'name': committer_name,
                    'date': date,
                    'changed_files': changed_files,
                    'message': commit_message,
                    'url': commit_details.get('url')
                }
                block = build_gitpushdetail_block(detail=details)

                message = {
                    'channel': channel_id,
                    'text': f"New push by {committer_name}",
                    'blocks': block,
                    'unfurl_links': False,
                    'unfurl_media': False
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
                "number": pr_data.get("number"),
                "merged": pr_data.get("merged"),
                "user": pr_user,
                "title": pr_title,
                "body": pr_body,
                "state": pr_state,
                "url": pr_url,
                "repo": repo_name,
                "head_branch": (pr_data.get("head") or {}).get("ref"),
                "base_branch": (pr_data.get("base") or {}).get("ref"),
                "date": pr_data.get("updated_at")
            }
            
            block = build_gitprdetail_block(detail=details)

            message = {
                'channel': channel_id,  
                'text': f"PR {action} by {pr_user}",
                'blocks': block,
                'unfurl_links': False,
                'unfurl_media': False
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
                details = {
                    'event': body.get('event') or x_github_event,
                    'name': body.get('name'),
                    'repo': reponame,
                    'branch': body.get('head_branch'),
                    'actor': (body.get('actor') or {}).get('login'),
                    'status': body.get('status'),
                    'conclusion': body.get('conclusion'),
                    'url': body.get('html_url'),
                    'date': body.get('updated_at'),
                    'commit_message': (body.get('head_commit') or {}).get('message')
                }

                workflow_message = {
                    'channel': channel_id,
                    'text': f"Workflow {details['name']}: {details['status']}",
                    'blocks': build_workflow_detail_block(detail=details),
                    'unfurl_links': False,
                    'unfurl_media': False
                }
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={
                            'Authorization': f"Bearer {bot_token}",
                            'Content-Type': 'application/json'
                        },
                        json=workflow_message
                    )
                logger.info(f"Sent workflow notification for {reponame} to Slack channel {channel_id}")
            else:
                logger.info('No workflow_run details in github payload')

        return {'status': 'ok'}
    except Exception as e:
        logger.exception(f"GitHub webhook request processing failed: {e}")
        return {'status': 'failed', 'detail': str(e)}
