from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tmdb_api_key: str = ""
    tmdb_region: str = "US"
    database_path: str = "/data/movie-reel.db"
    images_path: str = "/data/images"
    app_name: str = "Movie Reel"
    scheduler_enabled: bool = True
    provider_refresh_hour: int = 2
    metadata_rescan_hour: int = 3

    class Config:
        env_file = ".env"


settings = Settings()

DATABASE_PATH = Path(settings.database_path)
IMAGES_PATH = Path(settings.images_path)
