import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.services.import_jobs import start_metadata_rescan_job, start_provider_refresh_job
from app.services.tmdb import tmdb_client

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _scheduled_provider_refresh() -> None:
    if not tmdb_client.configured:
        logger.info("Skipping scheduled provider refresh — TMDB not configured")
        return
    if start_provider_refresh_job(skip_if_pending=True):
        logger.info("Scheduled provider refresh job queued")
    else:
        logger.info("Scheduled provider refresh skipped — queue busy")


def _scheduled_metadata_rescan() -> None:
    if not tmdb_client.configured:
        logger.info("Skipping scheduled metadata rescan — TMDB not configured")
        return
    if start_metadata_rescan_job(skip_if_pending=True):
        logger.info("Scheduled metadata rescan job queued")
    else:
        logger.info("Scheduled metadata rescan skipped — already queued")


def start_scheduler() -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled")
        return
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _scheduled_provider_refresh,
        CronTrigger(hour=settings.provider_refresh_hour, minute=0),
        id="daily_provider_refresh",
        replace_existing=True,
    )
    _scheduler.add_job(
        _scheduled_metadata_rescan,
        CronTrigger(hour=settings.metadata_rescan_hour, minute=0),
        id="daily_metadata_rescan",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started — providers at %02d:00, metadata rescan at %02d:00",
        settings.provider_refresh_hour,
        settings.metadata_rescan_hour,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_schedule_info() -> dict:
    return {
        "enabled": settings.scheduler_enabled,
        "provider_refresh_hour": settings.provider_refresh_hour,
        "metadata_rescan_hour": settings.metadata_rescan_hour,
    }
