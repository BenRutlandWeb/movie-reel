from pathlib import Path

import httpx

from app.config import IMAGES_PATH
from app.services.tmdb import TMDB_IMAGE_BASE


async def download_image(
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
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            dest.write_bytes(response.content)
            return str(dest.relative_to(IMAGES_PATH.parent))
    except httpx.HTTPError:
        return None


def local_image_url(local_path: str | None) -> str | None:
    if not local_path:
        return None
    return f"/api/images/{local_path.replace(chr(92), '/')}"
