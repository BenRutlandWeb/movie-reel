from fastapi import APIRouter, HTTPException

from app.schemas import UpdateAppSettingsRequest
from app.services.tmdb_config import (
    clear_api_key,
    get_config_status,
    queue_pending_metadata,
    set_api_key,
    set_region,
    validate_api_key,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_app_settings():
    return get_config_status()


@router.put("")
async def update_app_settings(body: UpdateAppSettingsRequest):
    result = get_config_status()
    metadata_queued = False
    metadata_total = 0

    if body.tmdb_api_key is not None:
        key = body.tmdb_api_key.strip()
        if not key:
            clear_api_key()
        else:
            if not await validate_api_key(key):
                raise HTTPException(400, "Invalid TMDB API key")
            set_api_key(key)
            if body.queue_pending_metadata:
                metadata_queued, metadata_total = queue_pending_metadata()

    if body.tmdb_region is not None:
        region = body.tmdb_region.strip().upper()
        if len(region) != 2:
            raise HTTPException(400, "Region must be a 2-letter country code (e.g. US, GB)")
        set_region(region)

    return {
        **get_config_status(),
        "metadata_queued": metadata_queued,
        "metadata_total": metadata_total,
    }
