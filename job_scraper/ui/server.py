"""
FastAPI server with APScheduler.

Endpoints:
  GET  /                        Dashboard (single HTML page)
  GET  /api/status              Scheduler state + last run
  GET  /api/runs                Last 10 runs from run_log
  GET  /api/errors              Last 20 errors from error_log
  POST /api/scheduler/start     Start the daily scheduler
  POST /api/scheduler/stop      Stop the daily scheduler
  POST /api/run/now             Trigger a full run (all sources)
  POST /api/run/nvb             Trigger NVB only
  POST /api/run/indeed          Trigger Indeed only
  POST /api/run/linkedin        Trigger LinkedIn only

Usage:
  cd job_scraper
  python -m ui.server
  # or: uvicorn ui.server:app --host 0.0.0.0 --port 8000
"""
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone

# Allow imports from job_scraper root
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from src.state import init_db, get_recent_runs, get_recent_errors, get_seen_count, get_jobs
from src.pipeline import run_pipeline, ALL_SOURCES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App + scheduler
# ---------------------------------------------------------------------------

scheduler = AsyncIOScheduler(timezone="Europe/Amsterdam")
_run_lock = asyncio.Lock()
_active_source: str | None = None   # "all" | "nvb" | "indeed" | "linkedin" | None


def _schedule_job():
    """Register the daily weekday job at 07:00 Amsterdam time."""
    if scheduler.get_job("daily_run"):
        scheduler.remove_job("daily_run")
    scheduler.add_job(
        _run_safe,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=7,
            minute=0,
            timezone="Europe/Amsterdam",
        ),
        id="daily_run",
        name="Daily NL job fetch",
        replace_existing=True,
    )
    logger.info("Scheduled daily run: Mon-Fri 07:00 Amsterdam")


async def _run_safe(sources: list[str] | None = None):
    """Run the pipeline for the given sources, guarding against concurrent executions."""
    global _active_source
    if _run_lock.locked():
        logger.warning("Run requested but a run is already in progress — skipping")
        return
    async with _run_lock:
        _active_source = "all" if not sources else "+".join(sources)
        try:
            await run_pipeline(sources=sources)
        except Exception as e:
            logger.error("Pipeline run failed: %s", e)
        finally:
            _active_source = None


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _schedule_job()
    scheduler.start()
    logger.info("Scheduler started. Next run: %s", _next_run_str())
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="NL Job Scraper", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scheduler_state() -> dict:
    job = scheduler.get_job("daily_run")
    return {
        "running":    scheduler.running,
        "job_active": job is not None,
        "next_run":   _next_run_str(),
    }


def _next_run_str() -> str | None:
    job = scheduler.get_job("daily_run")
    if not job or not job.next_run_time:
        return None
    return job.next_run_time.isoformat()


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def api_status():
    last_runs = get_recent_runs(limit=1)
    return {
        **_scheduler_state(),
        "run_in_progress": _run_lock.locked(),
        "active_source":   _active_source,
        "seen_jobs_total": get_seen_count(),
        "last_run":        last_runs[0] if last_runs else None,
    }


@app.get("/api/runs")
async def api_runs():
    return get_recent_runs(limit=10)


@app.get("/api/jobs")
async def api_jobs(
    since:  str | None = None,
    source: str | None = None,
    limit:  int        = 200,
    offset: int        = 0,
):
    """
    Query all unique jobs from the dedup store.

    ?since=YYYY-MM-DD   filter by first_seen date
    ?source=nvb         filter by source (indeed | linkedin | nvb)
    ?limit=200          max results (capped at 500)
    ?offset=0           pagination offset
    """
    if since is not None:
        try:
            datetime.strptime(since, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=422, detail="since must be a date in YYYY-MM-DD format")
    limit = min(limit, 500)
    return get_jobs(since=since, source=source, limit=limit, offset=offset)


@app.get("/api/errors")
async def api_errors():
    return get_recent_errors(limit=20)



@app.post("/api/scheduler/start")
async def api_start():
    if not scheduler.running:
        scheduler.start()
    _schedule_job()
    return {"status": "started", "next_run": _next_run_str()}


@app.post("/api/scheduler/stop")
async def api_stop():
    if scheduler.get_job("daily_run"):
        scheduler.remove_job("daily_run")
    return {"status": "stopped"}


def _run_endpoint(sources: list[str] | None, background_tasks: BackgroundTasks):
    """Shared logic for all /api/run/* endpoints."""
    if _run_lock.locked():
        return JSONResponse(
            status_code=409,
            content={"error": "A run is already in progress"},
        )
    background_tasks.add_task(_run_safe, sources)
    label = "all" if sources is None else "+".join(sources)
    return {"status": "started", "sources": label}


@app.post("/api/run/now")
async def api_run_now(background_tasks: BackgroundTasks):
    return _run_endpoint(None, background_tasks)


@app.post("/api/run/nvb")
async def api_run_nvb(background_tasks: BackgroundTasks):
    return _run_endpoint(["nvb"], background_tasks)


@app.post("/api/run/indeed")
async def api_run_indeed(background_tasks: BackgroundTasks):
    return _run_endpoint(["indeed"], background_tasks)


@app.post("/api/run/linkedin")
async def api_run_linkedin(background_tasks: BackgroundTasks):
    return _run_endpoint(["linkedin"], background_tasks)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_path = Path(__file__).parent / "index.html"
    return html_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ui.server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )
