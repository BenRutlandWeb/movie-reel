from typing import Literal

from pydantic import BaseModel, Field


class MediaStub(BaseModel):
    title: str
    year: int | None = None
    media_type: Literal["movie", "tv"]
    seasons: list[int | str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ImportRequest(BaseModel):
    items: list[MediaStub]
    fetch_metadata: bool = True


class AddMediaRequest(BaseModel):
    tmdb_id: int
    media_type: Literal["movie", "tv"]
    seasons: list[int | str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ResolveErrorRequest(BaseModel):
    notes: str | None = None
    tmdb_id: int | None = None


class ExportData(BaseModel):
    version: int = 1
    app: str = "Movie Reel"
    fetch_metadata: bool = True
    items: list[MediaStub]
