from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import database
from config import FOLLOWUP_INTERVALS, MAX_FOLLOWUPS

_scheduler: BackgroundScheduler = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
    return _scheduler


def start_scheduler(followup_callback):
    sched = get_scheduler()
    sched.add_job(
        func=lambda: _run_followups(followup_callback),
        trigger=IntervalTrigger(minutes=30),
        id="followup_runner",
        replace_existing=True,
    )
    if not sched.running:
        sched.start()


def _run_followups(callback):
    due = database.get_due_followups()
    for item in due:
        try:
            callback(item)
            database.mark_followup_done(item["id"])
        except Exception as e:
            print(f"[scheduler] followup {item['id']} failed: {e}")


def compute_next_followup_date(stage: str, attempt: int) -> str:
    days = FOLLOWUP_INTERVALS.get(stage, 3)
    dt = datetime.utcnow() + timedelta(days=days)
    return dt.isoformat()


def should_followup(stage: str, attempt: int) -> bool:
    return attempt <= MAX_FOLLOWUPS and stage in FOLLOWUP_INTERVALS
