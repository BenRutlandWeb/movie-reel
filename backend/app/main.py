from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routes import images, media, people, settings as settings_routes, tmdb

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(media.router)
app.include_router(people.router)
app.include_router(images.router)
app.include_router(tmdb.router)
app.include_router(settings_routes.router)

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def startup():
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    from app.services.metadata import dedupe_media
    from app.services.scheduler import start_scheduler

    dedupe_media()
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    from app.services.http_client import close_http_client
    from app.services.scheduler import stop_scheduler

    stop_scheduler()
    await close_http_client()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    bbfc_dir = STATIC_DIR / "bbfc"
    if bbfc_dir.exists():
        app.mount("/bbfc", StaticFiles(directory=bbfc_dir), name="bbfc")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not found"}
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"detail": "Frontend not built"}
