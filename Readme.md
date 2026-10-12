# ResolveOps

**An AI-triaged IT helpdesk and DevOps notifier that lives inside Slack, with a live analytics dashboard.**

Employees file issues with a slash command. Gemini classifies, prioritizes, and suggests a fix in seconds. Simple issues are offered a self-service fix with **Resolved / Not resolved** buttons, and anything the fix doesn't solve goes to the right IT admin. A background SLA engine escalates anything left unresolved, and a React dashboard shows how many tickets the AI solved on its own. GitHub activity (pushes, PRs, and CI runs) is posted to per-repo Slack channels.

## Live Demo

| | |
|---|---|
| **Dashboard** | [ResolveOps](https://resolveops-1.onrender.com) (the demo login is filled in, just click **Sign in**) |
| **Backend** | [Health check](https://resolveops.onrender.com/api/health) |
| **Slack** | [Join the Slack workspace](https://join.slack.com/t/solver-g678160/shared_invite/zt-47kxbtf9z-je55g8UYaiSfeaDa2xQCLQ) and try `/ticket my laptop won't connect to wifi` |

> Free-tier Render host: open the health check first to wake the backend up (~30s cold start).

---

## Features

| | |
|---|---|
| **AI triage** | `/ticket <issue>` uses Gemini 2.5 Flash with a strict JSON response schema to assign a category, a priority (1–5), a flag, and a suggested fix. |
| **Self-service fixes** | Low-risk tickets (P3–P5, not hardware or account access) get the AI's suggested fix with **Resolved** / **Not resolved** buttons. Resolved closes the ticket as solved by the AI; Not resolved sends it to IT support. Urgent, hardware and account-access tickets go straight to IT. |
| **Interactive buttons** | Slack button clicks hit `/webhook/interactions`. Only the person who raised a ticket can answer its fix buttons, and a ticket that was already answered is ignored, so double clicks are safe. `/listissue` shows each ticket as a card with its own **Resolve** button. |
| **Pending-response timeout** | If the user never answers the fix buttons, the ticket is moved to IT support after 5 hours. |
| **Prompt-injection guard** | User text is wrapped in `<user_text>` tags and treated as untrusted data. The AI flags each ticket as `none`, `unclear`, `spam` or `injection`; flagged tickets skip the self-service fix and are marked `needs_review` for an admin. If the AI call fails, the ticket is flagged `ai_failed` and still reaches IT. |
| **SLA auto-escalation** | APScheduler runs every 15 minutes and bumps the priority of any ticket that breaches its window (P2: 2h, P3: 6h, P4: 12h, P5: 24h). |
| **Admin types** | Admins are `hardware`, `network`, `software`, `iam`, `other` or `super_admin`. Each admin only sees and resolves tickets in their own category; a `super_admin` sees every ticket and is the only one who can add admins. |
| **Analytics dashboard** | A React + Recharts dashboard behind a JWT login, with separate views for an employee, a category admin and the super admin. See [Dashboard](#dashboard). |
| **Abuse protection** | Users are auto-registered on first use, and each user has a daily cap on tickets. |
| **GitHub → Slack** | Push, pull request, and `workflow_run` events are routed to each repo's Slack channel as Block Kit cards with a link back to GitHub. |
| **Request security** | HMAC verification of Slack signatures (with replay protection) and GitHub `X-Hub-Signature-256`. Invalid requests get a 403. Dashboard passwords are hashed with bcrypt. |
| **Built for Slack's 3s limit** | Every webhook acknowledges immediately. The slow work (AI calls, database, Slack API) runs in background tasks and replies through `response_url`. |
| **Schema migrations** | Alembic manages the database schema. Check constraints keep `flag` to its valid values and only allow `resolved_by` on resolved tickets. |

## Ticket Lifecycle

```mermaid
flowchart LR
    T["/ticket"] --> AI[Gemini triage]
    AI -->|flagged or AI failed| A[active + needs_review]
    AI -->|P1–P2, hardware, account access| B[active]
    AI -->|everything else| P[pending_response<br/>fix + buttons]
    P -->|Resolved| R[resolved by AI]
    P -->|Not resolved / no answer in 5h| B
    A --> AD[Admin: /listissue → Resolve]
    B --> AD
    AD --> R2[resolved by admin]
```

## Slack Commands

| Command | Who | What it does |
|---|---|---|
| `/ticket <issue>` | Anyone | Raise a ticket. The AI triages it and replies with a fix or a confirmation. |
| `/listissue` | Admins | Active tickets for your admin type, sorted by priority, each with a **Resolve** button. |
| `/resolve <id>` | Admins | Resolve a ticket by ID. |
| `/add-admin @user <admin_type>` | `super_admin` | Make a user an admin of the given type. |

Slack sends slash commands as form-encoded fields (`user_id`, `user_name`, `text`, `response_url`). Button clicks arrive at `/webhook/interactions` as a form field `payload` that holds the JSON. Example payloads for Slack interactions and GitHub events are in [`payloadformats.md`](payloadformats.md).

## Dashboard

**Live:** [resolveops-1.onrender.com](https://resolveops-1.onrender.com)

Admins sign in with an email and password. The backend checks the bcrypt hash and returns a JWT that is valid for 8 hours; every dashboard request sends it as `Authorization: Bearer <token>`, and an expired token sends the user back to the login page. The tabs in the navbar show the same data from three points of view:

| Tab | What it shows |
|---|---|
| **As super admin** | The **AI deflection rate** (share of tickets the AI fix solved with no admin), total, open, AI-solved and needs-review counts, bar charts of tickets by category and by priority, the 10 most recent tickets, and the tickets caught by the AI guard (spam, prompt injection, unclear). Refreshes every 10 seconds. |
| **As admin** | A category admin's queue (network in the demo): total, open and needs-review counts, and every ticket in that category, most urgent first. |
| **As user** | Pick an employee to see the tickets they raised in Slack, their status, and the AI's suggested fix. |

It supports light and dark mode and works at phone width. Each UI piece (`Navbar`, `StatCard`, `BarChartCard`, `TicketCard`, …) is a reusable component with its own CSS file.

### Dashboard API

The dashboard API is served by the same FastAPI app as the Slack webhooks (`backendapi/` is included with `app.include_router`).

| Endpoint | Auth | Returns |
|---|---|---|
| `POST /api/auth/login` | – | `{ token, email, role }` for a correct email and password, otherwise 401. |
| `GET /api/dashboard/overview` | JWT | Everything the super admin view shows: `kpis` (total, open, solved_by_ai, deflection_rate, needs_review), `by_category`, `by_priority`, the 10 most `recent` tickets, and the `flagged` tickets. |
| `GET /api/dashboard/category-tickets?category=` | JWT | Every ticket in one category, with total, open and needs-review counts. |
| `GET /api/dashboard/users` | JWT | The users who have raised tickets. |
| `GET /api/dashboard/user-tickets?slack_id=` | JWT | Every ticket one user raised. |
| `GET /api/dashboard/summary` | – | Total, solved, unsolved and AI-solved counts. |
| `GET /api/dashboard/ai-solved-tickets` | – | The latest tickets the AI fix solved. |
| `GET /api/dashboard/todays-tickets` | – | Tickets raised since midnight UTC, newest first. |

## Testing

Tests run against a **SQLite test database** (`testing/test.db`), never the real PostgreSQL database. Slack and Gemini are replaced with fakes using `monkeypatch`, so the tests need no API keys and no network.

- **Same schema as production, automatically.** `testing/test_database.py` drops and recreates every table from `backend/models.py` each time pytest starts, so a new migration needs no extra step for the tests.
- **Dependency injection.** The CRUD functions take the database session as a parameter (`resolve_ticket(db, ...)`), so a test passes in a SQLite session instead of PostgreSQL.
- **A clean database per test.** Each test starts by emptying the tables, so tests don't depend on each other.
- **AI tests save quota.** The test that calls the real Gemini API is marked `ai` and skipped by default (`pytest.ini` has `addopts = -m "not ai"`).

| File | What it covers |
|---|---|
| `test_admin_tickets.py` | Admin types: who can `/resolve` and `/listissue` which categories, super admin access, `add_admin`, the super-admin check, ticket creation when the AI answers and when it fails |
| `test_crud.py` | The `/ticket` background job: saves the ticket, registers a first-time user, and still replies "Server is not active." in Slack when something crashes |
| `test_ai_response.py` | The real Gemini triage: response shape, category, and that non-IT messages are flagged (marked `ai`) |

```bash
pytest              # 17 tests, no API keys needed
pytest -m ai        # only the Gemini test (uses real quota, needs GEMINI_API)
```

**CI:** [`.github/workflows/test.yml`](.github/workflows/test.yml) runs `pytest` on every push to `main` and every pull request. Its only setting is `DATABASE_URL=sqlite:///testing/test.db`; it needs no secrets.

## Tech Stack

**Backend:** Python, FastAPI, Uvicorn, httpx (async)  
**Frontend:** React, Vite, Recharts  
**Data:** PostgreSQL, SQLAlchemy, Alembic, Pydantic  
**AI:** Google Gemini 2.5 Flash (structured output)  
**Auth:** Slack/GitHub HMAC signatures, bcrypt, JWT (PyJWT)  
**Automation:** APScheduler  
**Integrations:** Slack Slash Commands, Interactivity and Web API, GitHub Webhooks  
**Testing / CI / Deploy:** Pytest, SQLite, GitHub Actions, Render

## Architecture

```mermaid
flowchart LR
    S[Slack command / button] --> V{HMAC valid?} -->|ack < 3s| BG[Background task]
    BG --> AI[Gemini triage] --> DB[(PostgreSQL)]
    BG -->|response_url| S
    GH[GitHub webhook] --> V2{HMAC valid?} --> R[Event router] --> CH[Repo Slack channel]
    SCH[APScheduler / 15 min] --> DB
    UI[React dashboard] -->|JWT| API[Dashboard API] --> DB
```

## Project Structure

```
backend/
├── main.py          # Routes, Slack interactions, GitHub event router, scheduler lifecycle
├── ai.py            # Gemini prompt, schema-enforced triage, injection guard
├── sla.py           # SLA escalation + pending-response timeout jobs
├── crud.py          # DB ops, background workers, fix feedback
├── slack_blocks.py  # Slack Block Kit message builders and button action IDs
├── auth.py          # Slack/GitHub signature checks, admin role checks
└── models.py / schemas.py / database.py
backendapi/
├── queries/ticket_queries.py     # Dashboard ticket queries
└── routes/
    ├── auth_routes.py            # /api/auth/login and the JWT check
    └── dashboard_routes.py       # /api/dashboard/* endpoints
frontend/src/
├── App.jsx          # Login check and the page tabs
├── api.js           # Backend calls (with the JWT)
├── pages/           # SuperAdminPage, AdminPage, UserPage
└── components/      # Navbar, LoginPage, StatCard, BarChartCard, TicketCard, … (each with its own CSS)
alembic/             # Database migrations
scripts/
└── create_demo_admins.py  # Creates the demo super admin for the dashboard
testing/
├── test_database.py       # SQLite test database, rebuilt from the models on every run
├── test_admin_tickets.py
├── test_crud.py
└── test_ai_response.py
.github/workflows/test.yml # Runs pytest on every push and PR
payloadformats.md          # Example Slack and GitHub payloads
```

## Quick Start

```bash
git clone https://github.com/<your-username>/ResolveOps.git && cd ResolveOps
pip install -r requirements.txt
# .env → DATABASE_URL, GEMINI_API, BOT_AUTH_TOKEN, SIGNING_SECRET, GITHUB_SECRET, JWT_SECRET, FRONTEND_URL
alembic upgrade head
python -m scripts.create_demo_admins       # dashboard login: super@demo.com
uvicorn backend.main:app --reload

pytest

cd frontend && npm install && npm run dev  # dashboard on http://localhost:5173
```

In your Slack app, point the slash commands at `/webhook/{ticket,listissue,resolve,add-admin}` and **Interactivity & Shortcuts** at `/webhook/interactions`. Point the GitHub webhook at `/webhook/github` (push, PR, and workflow run events).

Set `VITE_API_URL` in the frontend if the backend is not on `http://localhost:8000`. The backend always accepts requests from `http://localhost:5173`, plus the deployed dashboard set in `FRONTEND_URL`.

## Roadmap

- Async SQLAlchemy / `asyncpg` so database calls don't block the event loop
- Move background work and the scheduler to a dedicated worker / queue for horizontal scaling
- Dashboard logins for employees and category admins, showing only their own tickets
- Track `resolved_at` to report mean time to resolve on the dashboard

---

Built by **Jairam Hegde**
