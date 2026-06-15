from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import IMAGES_PATH

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{file_path:path}")
def serve_image(file_path: str):
    full_path = (IMAGES_PATH.parent / file_path).resolve()
    data_root = IMAGES_PATH.parent.resolve()

    if not str(full_path).startswith(str(data_root)):
        raise HTTPException(403, "Access denied")
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(404, "Image not found")

    return FileResponse(full_path)
