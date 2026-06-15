import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from app.database import get_db
from app.schemas import MediaStub
from app.services.metadata import (
    MetadataFetchError,
    dedupe_media,
    fetch_and_store_metadata,
    refresh_streaming_providers,
)
from app.services.metadata_errors import clear_metadata_error, log_metadata_error, set_setting

logger = logging.getLogger(__name__)

METADATA_FETCH_DELAY_SECONDS = 0.26


class JobType(str, Enum):
    METADATA_IMPORT = "metadata_import"
    PROVIDER_REFRESH = "provider_refresh"
    METADATA_RESCAN = "metadata_rescan"
    SINGLE_METADATA = "single_metadata"


@dataclass
class QueueJob:
    job_type: JobType
    label: str
    total: int
    completed: int = 0
    failed: int = 0
    running: bool = False
    current_item: str | None = None
    items: list = field(default_factory=list)


_queue: deque[QueueJob] = deque()
_current_job: QueueJob | None = None
_worker_task: asyncio.Task | None = None


def get_job_status() -> dict | None:
    if _current_job:
        return _job_to_status(_current_job)
    if _queue:
        next_job = _queue[0]
        status = _job_to_status(next_job)
        status["queued"] = True
        status["queue_length"] = len(_queue)
        return status
    return None


def get_queue_info() -> dict:
    return {
        "running": _current_job is not None and _current_job.running,
        "current": _job_to_status(_current_job) if _current_job else None,
        "queued": [
            {"job_type": j.job_type.value, "label": j.label, "total": j.total}
            for j in _queue
        ],
    }


def _job_to_status(job: QueueJob) -> dict:
    return {
        "job_type": job.job_type.value,
        "label": job.label,
        "total": job.total,
        "completed": job.completed,
        "failed": job.failed,
        "running": job.running,
        "current_item": job.current_item,
    }


def _enqueue(job: QueueJob) -> None:
    _queue.append(job)
    _ensure_worker()


def _ensure_worker() -> None:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_run_worker())


async def _run_worker() -> None:
    global _current_job
    while _queue:
        job = _queue.popleft()
        _current_job = job
        job.running = True
        try:
            if job.job_type == JobType.PROVIDER_REFRESH:
                await _process_provider_refresh(job)
            elif job.job_type in (
                JobType.METADATA_IMPORT,
                JobType.METADATA_RESCAN,
                JobType.SINGLE_METADATA,
            ):
                await _process_metadata_job(job)
        except Exception:
            logger.exception("Job %s failed unexpectedly", job.job_type.value)
        finally:
            job.running = False
            job.current_item = None
            if job.job_type == JobType.PROVIDER_REFRESH:
                set_setting("last_provider_refresh", _now_iso())
            elif job.job_type == JobType.METADATA_RESCAN:
                set_setting("last_metadata_rescan", _now_iso())
        _current_job = None


def _has_pending_job(job_type: JobType) -> bool:
    if _current_job and _current_job.job_type == job_type:
        return True
    return any(j.job_type == job_type for j in _queue)


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _process_metadata_job(job: QueueJob) -> None:
    for stub, media_id in job.items:
        job.current_item = stub.title
        try:
            await fetch_and_store_metadata(stub, media_id)
            if media_id:
                clear_metadata_error(media_id)
            job.completed += 1
        except MetadataFetchError as exc:
            if media_id:
                log_metadata_error(media_id, exc.error_type, exc.message)
            job.failed += 1
            logger.warning("Metadata failed for %s: %s", stub.title, exc.message)
        except Exception as exc:
            if media_id:
                log_metadata_error(media_id, "unknown", str(exc))
            job.failed += 1
            logger.exception("Metadata failed for %s", stub.title)
        await asyncio.sleep(METADATA_FETCH_DELAY_SECONDS)
    if job.job_type in (JobType.METADATA_IMPORT, JobType.METADATA_RESCAN):
        dedupe_media()


async def _process_provider_refresh(job: QueueJob) -> None:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, tmdb_id, media_type, title FROM media WHERE tmdb_id IS NOT NULL ORDER BY id"
        ).fetchall()

    job.total = len(rows)
    for row in rows:
        job.current_item = row["title"]
        try:
            await refresh_streaming_providers(row["id"], row["tmdb_id"], row["media_type"])
            job.completed += 1
        except Exception as exc:
            job.failed += 1
            logger.warning("Provider refresh failed for %s: %s", row["title"], exc)
        await asyncio.sleep(METADATA_FETCH_DELAY_SECONDS)


def _is_busy() -> bool:
    if _current_job and _current_job.running:
        return True
    return bool(_queue)

def start_metadata_job(items: list[tuple[MediaStub, int | None]]) -> bool:
    if not items:
        return False
    _enqueue(
        QueueJob(
            job_type=JobType.METADATA_IMPORT,
            label="Import metadata",
            total=len(items),
            items=items,
        )
    )
    return True


def start_provider_refresh_job(*, skip_if_pending: bool = False) -> bool:
    if skip_if_pending and _has_pending_job(JobType.PROVIDER_REFRESH):
        return False
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM media WHERE tmdb_id IS NOT NULL"
        ).fetchone()[0]
    if total == 0:
        return False
    _enqueue(
        QueueJob(
            job_type=JobType.PROVIDER_REFRESH,
            label="Refresh streaming providers",
            total=total,
        )
    )
    return True


def start_metadata_rescan_job(*, skip_if_pending: bool = False) -> bool:
    if skip_if_pending and _has_pending_job(JobType.METADATA_RESCAN):
        return False
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, year, media_type, seasons FROM media ORDER BY id"
        ).fetchall()

    if not rows:
        return False

    items: list[tuple[MediaStub, int]] = []
    for row in rows:
        from app.services.metadata import _deserialize_seasons

        stub = MediaStub(
            title=row["title"],
            year=row["year"],
            media_type=row["media_type"],
            seasons=_deserialize_seasons(row["seasons"]),
        )
        items.append((stub, row["id"]))

    _enqueue(
        QueueJob(
            job_type=JobType.METADATA_RESCAN,
            label="Rescan metadata",
            total=len(items),
            items=items,
        )
    )
    return True


def enqueue_single_metadata(stub: MediaStub, media_id: int) -> bool:
    _enqueue(
        QueueJob(
            job_type=JobType.SINGLE_METADATA,
            label=f"Refresh: {stub.title}",
            total=1,
            items=[(stub, media_id)],
        )
    )
    return True
