import httpx

from app.config import settings
from app.database import get_db
from app.services.http_client import request_with_retry

TMDB_BASE = "https://api.themoviedb.org/3"
API_KEY_SETTING = "tmdb_api_key"
REGION_SETTING = "tmdb_region"


def _get_setting(key: str) -> str | None:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _set_setting(key: str, value: str) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def _delete_setting(key: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))


def get_api_key() -> str:
    db_key = _get_setting(API_KEY_SETTING)
    if db_key is not None:
        return db_key
    return settings.tmdb_api_key


def get_region() -> str:
    db_region = _get_setting(REGION_SETTING)
    if db_region is not None:
        return db_region
    return settings.tmdb_region


def mask_api_key(key: str) -> str | None:
    if not key:
        return None
    if len(key) <= 4:
        return "•" * len(key)
    return "•" * (len(key) - 4) + key[-4:]


def get_key_source() -> str:
    if _get_setting(API_KEY_SETTING) is not None:
        return "database"
    if settings.tmdb_api_key:
        return "environment"
    return "none"


def get_config_status() -> dict:
    api_key = get_api_key()
    return {
        "tmdb_configured": bool(api_key),
        "tmdb_api_key_preview": mask_api_key(api_key),
        "tmdb_region": get_region(),
        "tmdb_key_source": get_key_source(),
    }


async def validate_api_key(api_key: str) -> bool:
    if not api_key:
        return False
    try:
        response = await request_with_retry(
            "GET",
            f"{TMDB_BASE}/configuration",
            params={"api_key": api_key},
        )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def set_api_key(api_key: str) -> None:
    _set_setting(API_KEY_SETTING, api_key)


def clear_api_key() -> None:
    _delete_setting(API_KEY_SETTING)


def set_region(region: str) -> None:
    _set_setting(REGION_SETTING, region.strip().upper())


def queue_pending_metadata() -> tuple[bool, int]:
    from app.schemas import MediaStub
    from app.services.import_jobs import start_metadata_job
    from app.services.metadata import _deserialize_seasons

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, title, year, media_type, seasons
            FROM media
            WHERE tmdb_id IS NULL
            ORDER BY id
            """
        ).fetchall()

    if not rows:
        return False, 0

    items = [
        (
            MediaStub(
                title=row["title"],
                year=row["year"],
                media_type=row["media_type"],
                seasons=_deserialize_seasons(row["seasons"]),
            ),
            row["id"],
        )
        for row in rows
    ]
    queued = start_metadata_job(items)
    return queued, len(items)
