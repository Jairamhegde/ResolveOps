from datetime import datetime, timedelta, timezone

from backend.sla import SLA_WINDOWS, to_utc


ISSUE_PREVIEW_CHARS = 280
CARD_TITLE_CHARS = 150
CARD_BODY_CHARS = 200
SUGGESTED_FIX_CHARS = 2800
RESOLVE_ACTION_ID = "resolve_ticket"
FIX_RESOLVED_ACTION_ID = "ai_fix_resolved"
FIX_NOT_RESOLVED_ACTION_ID = "ai_fix_not_resolved"
USER_CONFIRMS_FIX_ACTION_ID = "user_confirms_fix"
USER_REJECTS_FIX_ACTION_ID = "user_rejects_fix"

PRIORITY_META = {
    1: ("🔴", "Critical"),
    2: ("🟠", "High"),
    3: ("🟡", "Medium"),
    4: ("🟢", "Low"),
    5: ("🔵", "Minimal"),
}


def section_divider() -> dict:
    """Horizontal rule between sections; also closes every message so consecutive ones stay separated."""
    return {"type": "divider"}


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
    """Resolve button on a ticket card; handled by the interactions endpoint via RESOLVE_ACTION_ID."""
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": "Resolve", "emoji": False},
        "style": "primary",
        "action_id": RESOLVE_ACTION_ID,
        "value": str(ticket.id)
    }


def build_ticket_card(ticket, now: datetime) -> dict:
    """One ticket as a Slack card block: id and priority, category and reporter, the issue, and SLA status."""
    priority_label = PRIORITY_META.get(ticket.priority, ("", "Unknown"))[1]
    category = (ticket.category or "other").replace("_", " ").title()
    issue = escape_mrkdwn(truncate((ticket.issue_text or "No description").strip(), CARD_BODY_CHARS))

    subtitle = f"{category} · Submitted by <@{ticket.slack_id}>"
    if ticket.created_at:
        subtitle += f" · {slack_date(ticket.created_at, '{date_short}')}"

    subtext = build_sla_text(ticket, now)
    if ticket.needs_review:
        subtext = f"*Needs review* ({ticket.flag.replace('_', ' ')}) · {subtext}"

    return {
        "type": "card",
        "block_id": f"ticket_{ticket.id}",
        "title": {"type": "mrkdwn", "text": f"T{ticket.id}  P{ticket.priority} {priority_label.upper()}", "verbatim": False},
        "subtitle": {"type": "mrkdwn", "text": subtitle, "verbatim": False},
        "body": {"type": "mrkdwn", "text": issue, "verbatim": False},
        "subtext": {"type": "mrkdwn", "text": subtext, "verbatim": False},
        "actions": [build_resolve_button(ticket)]
    }


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
        section_divider(),
    ]

    if notice:
        blocks.insert(1, build_notice_block(notice))

    for ticket in tickets:
        blocks.append(build_ticket_card(ticket, now))

    footer = "Click *Resolve* on a ticket, or use `/resolve &lt;id&gt;`"
    if total_active > len(tickets):
        footer += f"   ·   {total_active - len(tickets)} lower-priority ticket(s) not shown"

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": footer}]
    })

    blocks = blocks[:49]
    blocks.append(section_divider())
    return blocks


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

    blocks.append(section_divider())
    return blocks


def build_command_reply(command: str, payload: dict) -> dict:
    """Show the user's own command above the reply, so each request and its answer read as one group."""
    request_line = {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"You ran `{escape_mrkdwn(truncate(command.strip(), CARD_TITLE_CHARS))}`"}]
    }

    blocks = payload.get("blocks")
    if not blocks:
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": payload.get("text", "")}},
            section_divider()
        ]

    reply = dict(payload)
    reply["blocks"] = [request_line] + blocks
    return reply


def build_notice_block(notice: str) -> dict:
    """A one-line status message shown under the list header, e.g. after a ticket is resolved."""
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": notice}]
    }


def build_resolution_dm_blocks(ticket_id: int, issue_text: str, admin_id: str) -> list:
    """DM sent to the reporter when an admin fixes their ticket. The ticket only closes when they click Resolved."""
    issue = escape_mrkdwn(truncate((issue_text or "No description").strip(), ISSUE_PREVIEW_CHARS))
    quoted_issue = "> " + issue.replace("\n", "\n> ")
    button_value = f"{ticket_id}:{admin_id}"

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<@{admin_id}> has fixed your ticket `#{ticket_id}`*\n{quoted_issue}"
            }
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "Is your issue resolved?"}]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "action_id": USER_CONFIRMS_FIX_ACTION_ID,
                    "value": button_value,
                    "style": "primary",
                    "text": {"type": "plain_text", "text": "Resolved", "emoji": True}
                },
                {
                    "type": "button",
                    "action_id": USER_REJECTS_FIX_ACTION_ID,
                    "value": button_value,
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Not resolved", "emoji": True}
                }
            ]
        },
        section_divider()
    ]


def build_fix_feedback_actions(ticket_id: int) -> dict:
    """Resolved / Not resolved buttons for an AI suggested fix; handled by the interactions endpoint."""
    return {
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
        build_fix_feedback_actions(ticket_id),
        section_divider()
    ]


def build_ticket_received_blocks(ticket_id: int, suggested_fix: str = None) -> list:
    """Confirmation for tickets that go straight to IT; shows the AI fix as a tip with feedback buttons when there is one."""
    blocks = []
    if suggested_fix:
        fix = escape_mrkdwn(truncate(suggested_fix.strip(), SUGGESTED_FIX_CHARS))
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*While you wait, try this*  ·  `#{ticket_id}`\n{fix}"}
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"📨 Ticket `#{ticket_id}` has been sent to IT support. An admin will follow up."}]
    })
    if suggested_fix:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "Did this fix your issue?"}]
        })
        blocks.append(build_fix_feedback_actions(ticket_id))
    blocks.append(section_divider())
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
        },
        section_divider()
    ]


def github_date(raw_date: str) -> str:
    """Show a GitHub ISO timestamp in each viewer's own Slack timezone, or the raw text if it can't be parsed."""
    try:
        parsed_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
    except ValueError:
        return str(raw_date)
    return slack_date(parsed_date)


GITHUB_MESSAGE_CHARS = 500


def build_github_message(title: str, fields: list, message_label: str, message: str, url: str) -> list:
    """A short GitHub notification: a header, the key details in two columns, an optional message and a link."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": truncate(title, CARD_TITLE_CHARS)}
        },
        {
            "type": "section",
            "fields": [{"type": "mrkdwn", "text": f"*{label}*\n{value}"} for label, value in fields]
        }
    ]

    if message:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{message_label}*\n{truncate(message, GITHUB_MESSAGE_CHARS)}"}
        })

    if url:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"<{url}|View on GitHub>"}]
        })

    blocks.append(section_divider())
    return blocks


def github_time(detail: dict) -> str:
    """The event time in each viewer's Slack timezone, or 'Unknown'."""
    if not detail.get("date"):
        return "Unknown"
    return github_date(detail["date"])


def build_gitpushdetail_block(detail: dict) -> list:
    repo = escape_mrkdwn(detail.get("repo") or "Unknown")
    commit_message = escape_mrkdwn((detail.get("message") or "No commit message").strip().split("\n")[0])

    return build_github_message(
        title=f"Push to {detail.get('repo') or 'repository'}",
        fields=[
            ("Repository", repo),
            ("Branch", escape_mrkdwn(detail.get("branch") or "Unknown")),
            ("Author", escape_mrkdwn(detail.get("name") or "Unknown")),
            ("Time", github_time(detail)),
        ],
        message_label="Commit message",
        message=commit_message,
        url=detail.get("url")
    )


def build_gitprdetail_block(detail: dict) -> list:
    if detail.get("merged"):
        status = "Merged"
    else:
        status = (detail.get("action") or detail.get("state") or "Unknown").replace("_", " ").capitalize()

    return build_github_message(
        title=f"Pull request #{detail.get('number')}: {detail.get('title') or 'Untitled'}",
        fields=[
            ("Repository", escape_mrkdwn(detail.get("repo") or "Unknown")),
            ("Status", status),
            ("Branch", escape_mrkdwn(f"{detail.get('head_branch') or '?'} into {detail.get('base_branch') or '?'}")),
            ("Author", escape_mrkdwn(detail.get("user") or "Unknown")),
            ("Time", github_time(detail)),
        ],
        message_label="",
        message=None,
        url=detail.get("url")
    )


def build_workflow_detail_block(detail: dict) -> list:
    if detail.get("status") == "completed":
        status = (detail.get("conclusion") or "Unknown").replace("_", " ").capitalize()
    else:
        status = (detail.get("status") or "Unknown").replace("_", " ").capitalize()

    return build_github_message(
        title=f"Workflow {detail.get('name') or 'run'}: {status}",
        fields=[
            ("Repository", escape_mrkdwn(detail.get("repo") or "Unknown")),
            ("Status", status),
            ("Branch", escape_mrkdwn(detail.get("branch") or "Unknown")),
            ("Triggered by", escape_mrkdwn(detail.get("actor") or "Unknown")),
            ("Time", github_time(detail)),
        ],
        message_label="Commit message",
        message=escape_mrkdwn((detail.get("commit_message") or "").strip().split("\n")[0]),
        url=detail.get("url")
    )
