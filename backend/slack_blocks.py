import time
from datetime import datetime, timedelta, timezone

from logger import logger
from backend.sla import SLA_WINDOWS, to_utc


ISSUE_PREVIEW_CHARS = 280
# Slack section text is capped at 3000 chars
SUGGESTED_FIX_CHARS = 2800
RESOLVE_ACTION_ID = "resolve_ticket"
FIX_RESOLVED_ACTION_ID = "ai_fix_resolved"
FIX_NOT_RESOLVED_ACTION_ID = "ai_fix_not_resolved"

PRIORITY_META = {
    1: ("🔴", "Critical"),
    2: ("🟠", "High"),
    3: ("🟡", "Medium"),
    4: ("🟢", "Low"),
    5: ("🔵", "Minimal"),
}

CATEGORY_EMOJI = {
    "network": "🌐",
    "hardware": "🖥️",
    "software": "💾",
    "account_access": "🔐",
    "spam": "🚫",
}


# Formatting helpers

def escape_mrkdwn(text: str) -> str:
    """Escape user text so it can't inject mentions like <!channel> or links into Slack."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def format_duration(delta: timedelta) -> str:
    """Format a timedelta compactly, e.g. '2d 4h', '3h 15m', '12m'."""
    minutes = int(abs(delta).total_seconds() // 60)
    days, minutes = divmod(minutes, 60 * 24)
    hours, minutes = divmod(minutes, 60)

    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def slack_date(value: datetime, token_format: str = "{date_short_pretty} at {time}") -> str:
    """Render a timestamp in each viewer's own Slack timezone."""
    value = to_utc(value)
    fallback = value.strftime('%b %d, %Y %H:%M UTC')
    return f"<!date^{int(value.timestamp())}^{token_format}|{fallback}>"


# Ticket list (/listissue)

def build_sla_text(ticket, now: datetime) -> str:
    sla_window = SLA_WINDOWS.get(ticket.priority)
    if sla_window is None:
        return " *Top priority*"

    last_escalated = ticket.escalated_at or ticket.created_at
    if last_escalated is None:
        return "SLA unknown"

    remaining = to_utc(last_escalated) + sla_window - now
    if remaining.total_seconds() <= 0:
        return f"*SLA breached {format_duration(remaining)} ago*"
    return f"Escalates in {format_duration(remaining)}"


def build_resolve_button(ticket) -> dict:
    """Resolve button with a confirmation dialog; handled by the interactions endpoint via RESOLVE_ACTION_ID."""
    issue_preview = escape_mrkdwn(truncate((ticket.issue_text or "No description").strip(), 120))

    return {
        "type": "button",
        "action_id": RESOLVE_ACTION_ID,
        "value": str(ticket.id),
        "style": "primary",
        "text": {"type": "plain_text", "text": "Resolve", "emoji": True},
        "confirm": {
            "title": {"type": "plain_text", "text": f"Resolve ticket #{ticket.id}?"},
            "text": {
                "type": "mrkdwn",
                "text": f"This will close the ticket.\n> {issue_preview}"
            },
            "confirm": {"type": "plain_text", "text": "Resolve"},
            "deny": {"type": "plain_text", "text": "Cancel"},
            "style": "primary"
        }
    }


def build_ticket_card(ticket, now: datetime) -> list:
    emoji, label = PRIORITY_META.get(ticket.priority, ("⚪", "Unknown"))
    category = (ticket.category or "other").lower().replace(" ", "_")
    category_emoji = CATEGORY_EMOJI.get(category, "📁")

    issue = escape_mrkdwn(truncate((ticket.issue_text or "No description").strip(), ISSUE_PREVIEW_CHARS))
    quoted_issue = "> " + issue.replace("\n", "\n> ")

    meta = [
        f"<@{ticket.slack_id}>",
        f"{category_emoji} {escape_mrkdwn(category.replace('_', ' ').title())}",
    ]
    if ticket.needs_review:
        meta.insert(0, f"⚠️ *Needs review* ({ticket.flag.replace('_', ' ')})")
    if ticket.created_at:
        meta.append(f"Opened {slack_date(ticket.created_at)}")
    meta.append(build_sla_text(ticket, now))

    return [
        {
            "type": "section",
            "block_id": f"ticket_{ticket.id}",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *P{ticket.priority} · {label}*  ·  `#{ticket.id}`\n{quoted_issue}"
            },
            "accessory": build_resolve_button(ticket)
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "   ·   ".join(meta)}]
        },
        {"type": "divider"}
    ]


def build_ticket_blocks(tickets, priority_counts: dict, total_active: int, notice: str = None) -> list:
    now = datetime.now(timezone.utc)

    breakdown = "   ".join(
        f"{PRIORITY_META[p][0]} *{priority_counts[p]}* {PRIORITY_META[p][1]}"
        for p in sorted(priority_counts)
        if p in PRIORITY_META
    )

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🎫 Active Tickets", "emoji": True}
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"Showing *{len(tickets)}* of *{total_active}* active, sorted by priority"
                        f"   ·   Updated {slack_date(now, '{time}')}"
                    )
                }
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": breakdown or "_No priority data_"}
        },
        {"type": "divider"},
    ]

    if notice:
        blocks.insert(1, build_notice_block(notice))

    for ticket in tickets:
        blocks.extend(build_ticket_card(ticket, now))

    footer = "Click *Resolve* on a ticket, or use `/resolve &lt;id&gt;`"
    if total_active > len(tickets):
        footer += f"   ·   {total_active - len(tickets)} lower-priority ticket(s) not shown"

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": footer}]
    })

    return blocks[:50]


def build_empty_ticket_blocks(notice: str = None) -> list:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🎫 Active Tickets", "emoji": True}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*All clear!* There are no active tickets right now."}
        }
    ]

    if notice:
        blocks.insert(1, build_notice_block(notice))

    return blocks


def build_notice_block(notice: str) -> dict:
    """A one-line status message shown under the list header, e.g. after a ticket is resolved."""
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": notice}]
    }


def build_resolution_dm_blocks(ticket_id: int, issue_text: str, admin_id: str) -> list:
    """DM sent to the reporter when their ticket is resolved."""
    issue = escape_mrkdwn(truncate((issue_text or "No description").strip(), ISSUE_PREVIEW_CHARS))
    quoted_issue = "> " + issue.replace("\n", "\n> ")

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Your ticket `#{ticket_id}` has been resolved*\n{quoted_issue}"
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Resolved by <@{admin_id}>   ·   Still having trouble? File a new ticket with `/ticket`"}
            ]
        }
    ]


# AI suggested fix (/ticket)

def build_suggested_fix_blocks(ticket_id: int, suggested_fix: str) -> list:
    """Suggested fix with Resolved / Not resolved buttons; handled by the interactions endpoint."""
    fix = escape_mrkdwn(truncate((suggested_fix or "No fix suggested").strip(), SUGGESTED_FIX_CHARS))

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Suggested Fix*  ·  `#{ticket_id}`\n{fix}"}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "Did this fix your issue?"}]
        },
        {
            "type": "actions",
            "block_id": f"fix_feedback_{ticket_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": FIX_RESOLVED_ACTION_ID,
                    "value": str(ticket_id),
                    "style": "primary",
                    "text": {"type": "plain_text", "text": "Resolved", "emoji": True}
                },
                {
                    "type": "button",
                    "action_id": FIX_NOT_RESOLVED_ACTION_ID,
                    "value": str(ticket_id),
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Not resolved", "emoji": True}
                }
            ]
        }
    ]


def build_ticket_received_blocks(ticket_id: int, suggested_fix: str = None) -> list:
    """Confirmation for tickets that go straight to IT; shows the AI fix as a tip when there is one."""
    blocks = []
    if suggested_fix:
        fix = escape_mrkdwn(truncate(suggested_fix.strip(), SUGGESTED_FIX_CHARS))
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*💡 While you wait, try this*  ·  `#{ticket_id}`\n{fix}"}
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"📨 Ticket `#{ticket_id}` has been sent to IT support. An admin will follow up."}]
    })
    return blocks


def build_fix_feedback_result_blocks(ticket_id: int, suggested_fix: str, resolved: bool) -> list:
    """Replaces the suggested-fix message once the user answers, so the buttons can't be clicked again."""
    fix = escape_mrkdwn(truncate((suggested_fix or "No fix suggested").strip(), SUGGESTED_FIX_CHARS))

    if resolved:
        outcome = f"Glad that worked! Ticket `#{ticket_id}` has been closed."
    else:
        outcome = f"📨 Ticket `#{ticket_id}` has been sent to IT support. An admin will follow up."

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Suggested Fix*  ·  `#{ticket_id}`\n{fix}"}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": outcome}]
        }
    ]


# GitHub notifications

def build_gitpushdetail_block(detail: dict):
    modified_files = detail.get('modified', [])

    # Format the list of files nicely, or show 'None'
    if modified_files:
        modified_text = ", ".join(f"`{f}`" for f in modified_files)
    else:
        modified_text = "`None`"

    # Format the commit message as a blockquote
    message = detail.get('message') or 'No message provided'
    quoted_message = "> " + message.replace("\n", "\n> ")

    raw_date = detail.get('date')
    unix_ts = int(time.time())
    fallback_date = None
    if raw_date:
        try:
            dt = datetime.fromisoformat(str(raw_date).replace('Z', '+00:00'))
            unix_ts = int(dt.timestamp())
            fallback_date = dt.strftime('%b %d, %Y at %I:%M %p')
        except Exception as e:
            logger.warning(f"Could not parse push date '{raw_date}': {e}")
            fallback_date = str(raw_date)
    if not fallback_date:
        fallback_date = datetime.now().strftime('%b %d, %Y at %I:%M %p')

    date_display = f"<!date^{unix_ts}^{{date_short}} at {{time}}|{fallback_date}>"

    block = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🔹New GitHub Push", "emoji": True}
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Pushed by:* @{detail.get('name') or 'Unknown'}"},
                {"type": "mrkdwn", "text": f"*Date:* {date_display}"}
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
    quoted_body = "> " + body.replace("\n", "\n> ")

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
