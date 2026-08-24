# ResolveOps

An AI-triaged IT helpdesk bot for Slack. Employees report issues with a slash command; the system automatically classifies, prioritizes, and routes them to IT admins — with automated SLA-based escalation for tickets that sit unresolved too long.

Built with FastAPI, PostgreSQL, and Google Gemini.

---

## Overview

Traditional helpdesk workflows rely on someone manually reading, categorizing, and prioritizing every incoming request. ResolveOps automates that first triage step: when a user submits an issue through Slack, Gemini analyzes the text and assigns a category, priority level, and a suggested first fix — before an admin ever looks at it. A background scheduler then enforces SLA windows per priority level, automatically escalating tickets that go unresolved for too long, so nothing quietly ages out of view.

## Features

- **`/ticket <description>`** — Any workspace member can file an issue. Gemini classifies it (category, priority, suggested fix) and it's inserted into the queue. New users are registered automatically on first use.
- **`/listissue`** — Admins get a formatted, priority-sorted list of active tickets, tagged with the reporter's Slack mention.
- **`/resolve <ticket_id>`** — Admins mark a ticket resolved.
- **`/add-admin @user`** — Existing admins can promote another workspace member to admin, without any direct database access.
- **Automated SLA escalation** — A background job runs every 15 minutes, checking how long each active ticket has been open against an SLA window tied to its current priority. Tickets that breach their window get automatically bumped to a higher priority, so unresolved issues can't silently sit forgotten.
- **Slack request verification** — Every webhook validates Slack's HMAC signature (`X-Slack-Signature` + `X-Slack-Request-Timestamp`) before processing anything, rejecting forged or replayed requests.
- **Role-based access control** — Admin-only actions are gated by a live lookup against the database, independent of the request-authenticity check above.

## Architecture

```mermaid
flowchart LR
    A[Slack Slash Command] -->|HTTP POST| B[FastAPI Webhook]
    B --> C{Signature Valid?}
    C -- No --> X[403 Rejected]
    C -- Yes --> D[Immediate Ack to Slack]
    D --> E[Background Task]
    E --> F{Admin Check}
    F --> G[Gemini AI Triage]
    F --> H[PostgreSQL]
    G --> H
    H -->|response_url| I[Slack Message Update]

    J[APScheduler - every 15 min] --> K[SLA Escalation Job]
    K --> H
```

**Why background tasks + `response_url`, not synchronous responses:** Slack requires a response within 3 seconds of a slash command. Triage (a Gemini API call) and admin verification (a Slack API round-trip) can both take longer than that. Every webhook acknowledges immediately, then does the real work in a background task and posts the final result back to Slack's `response_url` asynchronously.

**Why an in-process scheduler instead of system cron:** the whole service runs as a single deployed process on a free-tier host with no separate shell/cron access. APScheduler runs the SLA check inside the same FastAPI process, with no extra infrastructure to manage. (Known tradeoff: if this were ever scaled to multiple instances, the scheduler would need to move to a single dedicated worker to avoid duplicate escalation runs.)

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy ORM |
| AI Triage | Google Gemini (`gemini-2.5-flash`) |
| Scheduling | APScheduler |
| Auth | HMAC-SHA256 request signing, role-based DB lookups |
| Hosting | Render |

## Project Structure

```
backend/
├── main.py       # FastAPI app, routes, scheduler startup
├── auth.py        # Slack signature verification, admin/user role checks
├── crud.py         # Database operations and background task handlers
├── ai.py             # Gemini prompt and triage logic
├── sla.py             # SLA windows and escalation job
├── models.py           # SQLAlchemy table definitions
├── schemas.py            # Pydantic request models
└── database.py             # Engine, session, and Base setup
logger.py                    # Centralized logging config
```

## API Endpoints

| Endpoint | Method | Access | Description |
|---|---|---|---|
| `/webhook/ticket` | POST | Any workspace member | Submit a new ticket |
| `/webhook/listissue` | POST | Admin only | List active tickets |
| `/webhook/resolve` | POST | Admin only | Mark a ticket resolved |
| `/webhook/add-admin` | POST | Admin only | Promote a user to admin |
| `/api/health` | GET | Public | Health check |

All `/webhook/*` endpoints require a valid Slack request signature.

## SLA Escalation Windows

| Current Priority | Escalates after |
|---|---|
| 2 | 2 hours |
| 3 | 6 hours |
| 4 | 12 hours |
| 5 (lowest) | 24 hours |

Priority 1 is already the highest urgency level and does not escalate further. Checked every 15 minutes; a ticket left unresolved long enough can escalate multiple times.

## Setup

**1. Clone and install dependencies**
```bash
git clone https://github.com/<your-username>/ResolveOps.git
cd ResolveOps
pip install -r requirements.txt
```

**2. Environment variables** — create a `.env` file in the project root:
```
DATABASE_URL=postgresql://user:password@host:port/dbname
GEMINI_API=your_gemini_api_key
BOT_AUTH_TOCKEN=xoxb-your-slack-bot-token
SIGNING_SECRETE=your_slack_signing_secret
```

**3. Create a Slack app** at [api.slack.com/apps](https://api.slack.com/apps) with slash commands pointed at your deployed URLs:
- `/ticket` → `POST /webhook/ticket`
- `/listissue` → `POST /webhook/listissue`
- `/resolve` → `POST /webhook/resolve`
- `/add-admin` → `POST /webhook/add-admin`

**4. Seed your first admin** (subsequent admins can be added via `/add-admin` once one exists):
```python
from backend.database import SessionLocal
from backend.models import Admin

db = SessionLocal()
db.add(Admin(slack_id="U0XXXXXXX", email="you@example.com", role="it support"))
db.commit()
db.close()
```

**5. Run locally**
```bash
uvicorn backend.main:app --reload
```

## Live Demo

Backend is deployed on Render (free tier). Since the service spins down after periods of inactivity, warm it up before testing:

**Health check:** [https://resolveops.onrender.com/api/health](https://resolveops.onrender.com/api/health)

**Slack workspace:** [Join here](https://join.slack.com/t/solver-g678160/shared_invite/zt-47kxbtf9z-je55g8UYaiSfeaDa2xQCLQ) to try the bot directly — file a ticket with `/ticket`, and if you'd like admin access to try `/listissue` and `/resolve`, reach out.

> This is a portfolio/demo deployment on a free-tier host — expect a short delay on the first request after idle periods, and please be considerate with usage as it shares a limited AI API quota.

## Known Limitations

- Database calls use synchronous SQLAlchemy inside async route handlers — acceptable at this scale, but a production version would move to async SQLAlchemy or `asyncpg` to avoid blocking the event loop on DB I/O.
- No automated test suite yet.
- Scheduler runs in-process; would need to move to a dedicated worker before horizontal scaling.

## Author

Jairam Hegde 