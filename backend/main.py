import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backendapi.routes.dashboard_routes import router as dashboard_router
from backendapi.routes.auth_routes import router as auth_router
from backend.routes.slack_routes import router as slack_router
from backend.routes.github_routes import router as github_router
from logger import logger
from backend.sla import escalate_active_tickets, activate_stale_pending_tickets
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173"), "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(slack_router)
app.include_router(github_router)

scheduler = BackgroundScheduler()

@app.on_event('startup')
def start_scheduler():
    scheduler.add_job(escalate_active_tickets, 'interval', minutes=15, id="sla_escalation_job")
    scheduler.add_job(activate_stale_pending_tickets, 'interval', minutes=15, id="pending_response_timeout_job")
    scheduler.start()
    logger.info("Scheduler started")

@app.on_event('shutdown')
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler shutdown.")

@app.get('/api/health')
async def health_check():
    return {"status": "ok"}
