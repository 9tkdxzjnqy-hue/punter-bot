"""
Scheduled jobs for The Betting Butler.

Uses APScheduler to run timed reminders and deadline enforcement.
All times are in Europe/Dublin timezone.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import Config
from src.services.pick_service import get_missing_players
from src.services.week_service import (
    get_or_create_current_week, get_current_week, close_week, is_past_deadline,
)
import src.butler as butler

logger = logging.getLogger(__name__)

_scheduler = None
_send_fn = None


def init_scheduler(send_message_fn):
    """
    Initialize and start the scheduler.

    send_message_fn should accept (chat_id, text) and send the message
    to the WhatsApp group.
    """
    global _scheduler, _send_fn
    _send_fn = send_message_fn

    _scheduler = BackgroundScheduler(timezone=Config.TIMEZONE)

    # Wednesday 7PM — silently create the week if none exists
    _scheduler.add_job(
        _job_create_week,
        "cron",
        day_of_week="wed",
        hour=19,
        minute=0,
        id="create_week",
    )

    # Thursday 7PM — reminder to all players
    _scheduler.add_job(
        _job_reminder_thursday,
        "cron",
        day_of_week="thu",
        hour=19,
        minute=0,
        id="reminder_thursday",
    )

    # Friday 5PM — reminder to missing players
    _scheduler.add_job(
        _job_reminder_friday,
        "cron",
        day_of_week="fri",
        hour=17,
        minute=0,
        id="reminder_friday",
    )

    # Friday 9:30PM — final warning
    _scheduler.add_job(
        _job_reminder_final,
        "cron",
        day_of_week="fri",
        hour=21,
        minute=30,
        id="reminder_final",
    )

    # Friday 10PM — close the week
    _scheduler.add_job(
        _job_close_week,
        "cron",
        day_of_week="fri",
        hour=22,
        minute=0,
        id="close_week",
    )

    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))


def _send(text):
    """Send a message to the group chat."""
    if _send_fn and Config.GROUP_CHAT_ID:
        _send_fn(Config.GROUP_CHAT_ID, text)


def _job_create_week():
    """Wednesday 7PM: Create the week silently."""
    try:
        week = get_or_create_current_week()
        logger.info("Week %s ready (id=%s)", week["week_number"], week["id"])
    except Exception:
        logger.exception("Error in create_week job")


def _job_reminder_thursday():
    """Thursday 7PM: Remind all players that picks are due."""
    try:
        _send(butler.reminder_thursday())
        logger.info("Thursday reminder sent")
    except Exception:
        logger.exception("Error in reminder_thursday job")


def _job_reminder_friday():
    """Friday 5PM: Remind players who haven't submitted."""
    try:
        week = get_current_week()
        if not week:
            return

        missing = get_missing_players(week["id"])
        if missing:
            _send(butler.reminder_friday(missing))
            logger.info("Friday reminder sent for %d missing players", len(missing))
        else:
            logger.info("Friday reminder skipped — all picks in")
    except Exception:
        logger.exception("Error in reminder_friday job")


def _job_reminder_final():
    """Friday 9:30PM: Final warning to missing players."""
    try:
        week = get_current_week()
        if not week:
            return

        missing = get_missing_players(week["id"])
        if missing:
            _send(butler.reminder_final(missing))
            logger.info("Final reminder sent for %d missing players", len(missing))
        else:
            logger.info("Final reminder skipped — all picks in")
    except Exception:
        logger.exception("Error in reminder_final job")


def _job_close_week():
    """Friday 10PM: Close the week (no more regular picks)."""
    try:
        week = get_current_week()
        if not week:
            return

        if week["status"] == "open":
            close_week(week["id"])
            logger.info("Week %s closed (deadline passed)", week["week_number"])
    except Exception:
        logger.exception("Error in close_week job")
