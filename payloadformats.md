## slack interactions payload template
``` json
{
    "type": "block_actions",
    "user": {
        "id": "U0123456789",
        "username": "jairam",
        "name": "jairam",
        "team_id": "T0123456789"
    },
    "api_app_id": "A0123456789",
    "token": "verification_token_deprecated",
    "container": {
        "type": "message",
        "message_ts": "1712345678.000100",
        "channel_id": "C0123456789",
        "is_ephemeral": false
    },
    "trigger_id": "1234567890.1234567890.abcdef...",
    "team": {
        "id": "T0123456789",
        "domain": "workspace-domain"
    },
    "channel": {
        "id": "C0123456789",
        "name": "alerts"
    },
    "message": {
        "bot_id": "B0123456789",
        "type": "message",
        "text": "Fallback text",
        "ts": "1712345678.000100",
        "blocks": [ ...]
    },
    "response_url": "https://hooks.slack.com/actions/T0123456789/123456789/abcdef...",
    "actions": [
        {
            "action_id": "resolve_ticket",
            "block_id": "action_block_1",
            "text": {
                "type": "plain_text",
                "text": "Resolve",
                "emoji": true
            },
            "value": "12",
            "style": "primary",
            "type": "button",
            "action_ts": "1712345680.123456"
        }
    ]
}
```

## Slack Messages Payload

``` json
{
    "channel": "C0123456789",
    "text": "Fallback text for notifications (e.g. mobile push / preview)",
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Ticket Notification",
                "emoji": true
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Ticket #101* created by <@U0123456789>\n*Issue:* Unable to connect to database."
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Priority: *High* | Status: *Open*"
                }
            ]
        }
    ]
}
```

## Slack Incoming Message Event (Slack Events API `message` event)
``` json
{
    "token": "verification_token",
    "team_id": "T0123456789",
    "api_app_id": "A0123456789",
    "type": "event_callback",
    "event_id": "Ev0123456789",
    "event_time": 1712345678,
    "event": {
        "type": "message",
        "channel": "C0123456789",
        "user": "U0123456789",
        "text": "Hello, can someone help me reset my password?",
        "ts": "1712345678.000200",
        "event_ts": "1712345678.000200",
        "channel_type": "channel"
    }
}
```

## GitHub Webhook Payloads (`/webhook/github`)

GitHub sends HTTP `POST` requests with `Content-Type: application/json`.
Key headers sent by GitHub:
- `X-GitHub-Event`: `"push"`, `"pull_request"`, `"workflow_run"`, or `"ping"`
- `X-Hub-Signature-256`: `sha256=...` HMAC hex digest of the raw body

### 1. `push` Event (`X-GitHub-Event: push`)
``` json
{
    "ref": "refs/heads/main",
    "repository": {
        "id": 123456789,
        "name": "InternIQ",
        "full_name": "org/InternIQ"
    },
    "head_commit": {
        "id": "b6a9c8f0d1e2f3a4b5c6d7e8f90123456789abcd",
        "message": "fix: resolve memory leak in background worker",
        "timestamp": "2026-10-09T14:20:00Z",
        "author": {
            "name": "Jairam Hegde",
            "email": "jairam@example.com",
            "username": "jairam"
        },
        "modified": [
            "backend/worker.py",
            "backend/main.py"
        ],
        "added": [],
        "removed": []
    }
}
```

### 2. `pull_request` Event (`X-GitHub-Event: pull_request`)
``` json
{
    "action": "opened",
    "repository": {
        "id": 123456789,
        "name": "HybridGuard",
        "full_name": "org/HybridGuard"
    },
    "pull_request": {
        "id": 987654321,
        "number": 42,
        "title": "Add authentication rate limiting",
        "body": "Implements token bucket algorithm for auth endpoints.",
        "state": "open",
        "html_url": "https://github.com/org/HybridGuard/pull/42",
        "user": {
            "login": "octocat",
            "id": 1
        }
    }
}
```

### 3. `workflow_run` Event (`X-GitHub-Event: workflow_run`)
``` json
{
    "action": "completed",
    "repository": {
        "id": 123456789,
        "name": "InternIQ",
        "full_name": "org/InternIQ"
    },
    "workflow_run": {
        "id": 1029384756,
        "name": "CI / Test Suite",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "html_url": "https://github.com/org/InternIQ/actions/runs/1029384756"
    }
}
```