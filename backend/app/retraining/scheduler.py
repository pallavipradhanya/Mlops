"""Local scheduler (APScheduler). Windows Task Scheduler alternative: scripts/run_retraining.py."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.database.db import SessionLocal
from app.retraining.workflow import run_retraining
from app.services import settings_service

JOB_ID = "scheduled-retraining"
_scheduler = BackgroundScheduler(timezone="UTC")


def _job() -> None:
    db = SessionLocal()
    try:
        run_retraining(db, trigger="scheduled")
    except RuntimeError:
        pass  # a run is already in progress
    finally:
        db.close()


def start() -> None:
    if not _scheduler.running:
        _scheduler.start()
    db = SessionLocal()
    try:
        configure(settings_service.get_all(db)["schedule_hours"])
    finally:
        db.close()


def configure(hours: float) -> None:
    if _scheduler.get_job(JOB_ID):
        _scheduler.remove_job(JOB_ID)
    if hours and hours > 0:
        _scheduler.add_job(_job, "interval", hours=float(hours), id=JOB_ID, max_instances=1, coalesce=True)


def status() -> dict:
    job = _scheduler.get_job(JOB_ID) if _scheduler.running else None
    return {"running": _scheduler.running, "enabled": job is not None,
            "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None}


def stop() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
