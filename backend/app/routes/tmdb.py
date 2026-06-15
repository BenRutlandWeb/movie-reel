from fastapi import APIRouter, HTTPException, Query

from app.services.tmdb import tmdb_client

router = APIRouter(prefix="/api/tmdb", tags=["tmdb"])


@router.get("/search")
async def search_tmdb(
    q: str = Query(..., min_length=1),
    media_type: str | None = Query(None, pattern="^(movie|tv)$"),
    year: int | None = None,
):
    if not tmdb_client.configured:
        raise HTTPException(400, "TMDB API key not configured")

    query = q.strip()
    results: list[dict] = []

    if media_type in (None, "movie"):
        movies = await tmdb_client.search_movie_multi(query, year)
        results.extend(tmdb_client.format_search_result(m, "movie") for m in movies)

    if media_type in (None, "tv"):
        shows = await tmdb_client.search_tv_multi(query, year)
        results.extend(tmdb_client.format_search_result(s, "tv") for s in shows)

    if media_type is None:
        results.sort(key=lambda r: (r.get("title") or "").lower())

    return results[:20]
