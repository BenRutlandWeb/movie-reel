from pathlib import Path

from app.config import IMAGES_PATH
from app.services.http_client import TRANSIENT_ERRORS, request_with_retry
from app.services.tmdb import TMDB_IMAGE_BASE


async def download_image_immediate(
    remote_path: str | None,
    category: str,
    filename: str,
    size: str = "original",
) -> str | None:
    if not remote_path:
        return None

    dest_dir = IMAGES_PATH / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    if dest.exists():
        return str(dest.relative_to(IMAGES_PATH.parent))

    url = f"{TMDB_IMAGE_BASE}/{size}{remote_path}"
    try:
        response = await request_with_retry("GET", url)
        if response.status_code != 200:
            return None
        dest.write_bytes(response.content)
        return str(dest.relative_to(IMAGES_PATH.parent))
    except TRANSIENT_ERRORS:
        return None


def local_image_url(local_path: str | None) -> str | None:
    if not local_path:
        return None
    return f"/api/images/{local_path.replace(chr(92), '/')}"
