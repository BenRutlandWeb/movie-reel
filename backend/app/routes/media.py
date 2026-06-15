from fastapi import APIRouter, HTTPException, Query

from app.database import get_db, row_to_dict
from app.schemas import AddMediaRequest, ImportRequest, MediaStub, ResolveErrorRequest
from app.services.images import local_image_url
from app.services.metadata import (
    _deserialize_seasons,
    _get_media_genres,
    _get_media_tags,
    _link_tags,
    _serialize_seasons,
    build_export,
    fetch_and_store_metadata,
)
from app.services.tmdb import tmdb_client

router = APIRouter(prefix="/api/media", tags=["media"])


def _enrich_media(media: dict, genres: list[str] | None = None, tags: list[str] | None = None) -> dict:
    seasons = media.get("seasons")
    if isinstance(seasons, str):
        media["seasons"] = _deserialize_seasons(seasons)
    elif seasons is None:
        media["seasons"] = []
    media["poster_url"] = local_image_url(media.get("poster_local"))
    media["backdrop_url"] = local_image_url(media.get("backdrop_local"))
    if genres is not None:
        media["genres"] = genres
    if tags is not None:
        media["tags"] = tags
    return media


def _find_related_media(conn, media_id: int, limit: int = 12) -> list[dict]:
    rows = conn.execute(
        """
        WITH current_genres AS (
            SELECT genre_id FROM media_genres WHERE media_id = ?
        ),
        current_tags AS (
            SELECT tag_id FROM media_tags WHERE media_id = ?
        ),
        scored AS (
            SELECT
                m.*,
                (
                    SELECT COUNT(*) FROM media_genres mg
                    WHERE mg.media_id = m.id AND mg.genre_id IN (SELECT genre_id FROM current_genres)
                ) + (
                    SELECT COUNT(*) FROM media_tags mt
                    WHERE mt.media_id = m.id AND mt.tag_id IN (SELECT tag_id FROM current_tags)
                ) AS overlap
            FROM media m
            WHERE m.id != ?
        )
        SELECT * FROM scored
        WHERE overlap > 0
        ORDER BY overlap DESC, title ASC
        LIMIT ?
        """,
        (media_id, media_id, media_id, limit),
    ).fetchall()

    results = []
    for row in rows:
        item = _enrich_media(
            row_to_dict(row),
            genres=_get_media_genres(conn, row["id"]),
            tags=_get_media_tags(conn, row["id"]),
        )
        results.append(item)
    return results


async def _fetch_owned_seasons(tmdb_id: int, owned_seasons: list) -> list[dict]:
    if not tmdb_client.configured or not owned_seasons:
        return []

    season_details = []
    for season in owned_seasons:
        season_num = 0 if season == "specials" else int(season)
        data = await tmdb_client.get_tv_season(tmdb_id, season_num)
        if not data:
            continue
        episodes = [
            {
                "episode_number": ep.get("episode_number"),
                "name": ep.get("name"),
                "overview": ep.get("overview"),
                "air_date": ep.get("air_date"),
                "runtime": ep.get("runtime"),
                "vote_average": ep.get("vote_average"),
                "vote_count": ep.get("vote_count"),
                "still_url": tmdb_client.image_url(ep.get("still_path"), "w300"),
            }
            for ep in data.get("episodes", [])
        ]
        season_details.append(
            {
                "season_number": season,
                "name": data.get("name"),
                "overview": data.get("overview"),
                "episode_count": data.get("episode_count"),
                "air_date": data.get("air_date"),
                "episodes": episodes,
            }
        )
    return season_details


def _parse_episode_credits(credits: dict | None) -> tuple[list[dict], list[dict]]:
    if not credits:
        return [], []
    guest_stars = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "character_name": p.get("character"),
            "profile_url": tmdb_client.image_url(p.get("profile_path"), "w185"),
        }
        for p in credits.get("guest_stars", [])[:20]
    ]
    crew = [
        {
            "name": p.get("name"),
            "job": p.get("job"),
            "department": p.get("department"),
        }
        for p in credits.get("crew", [])
        if p.get("job") in ("Director", "Writer", "Screenplay", "Story")
    ]
    return guest_stars, crew


@router.get("/{media_id}/seasons/{season}/episodes/{episode}")
async def get_episode(media_id: int, season: str, episode: int):
    with get_db() as conn:
        media = row_to_dict(conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone())
        if not media:
            raise HTTPException(404, "Media not found")
        if media["media_type"] != "tv":
            raise HTTPException(400, "Episodes are only available for TV shows")

        owned = _deserialize_seasons(media.get("seasons"))
        owned_normalized = {str(s) for s in owned}
        if season not in owned_normalized:
            raise HTTPException(404, "Season not in your collection")

    tmdb_id = media.get("tmdb_id")
    if not tmdb_id or not tmdb_client.configured:
        raise HTTPException(404, "Episode metadata not available")

    season_num = 0 if season == "specials" else int(season)
    data = await tmdb_client.get_tv_episode(tmdb_id, season_num, episode)
    if not data:
        raise HTTPException(404, "Episode not found")

    guest_stars, crew = _parse_episode_credits(data.get("credits"))
    show_genres = []
    show_tags = []
    with get_db() as conn:
        show_genres = _get_media_genres(conn, media_id)
        show_tags = _get_media_tags(conn, media_id)

    return {
        "media_id": media_id,
        "show_title": media["title"],
        "show_poster_url": local_image_url(media.get("poster_local")),
        "season_number": season,
        "episode_number": data.get("episode_number"),
        "name": data.get("name"),
        "overview": data.get("overview"),
        "air_date": data.get("air_date"),
        "runtime": data.get("runtime"),
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "still_url": tmdb_client.image_url(data.get("still_path"), "w780"),
        "guest_stars": guest_stars,
        "crew": crew,
        "genres": show_genres,
        "tags": show_tags,
    }


@router.get("")
def list_media(
    media_type: str | None = Query(None, pattern="^(movie|tv)$"),
    genre: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    providers: str | None = None,
    limit: int | None = Query(None, ge=1, le=50),
    sort: str = Query("title", pattern="^(title|year|updated|relevance)$"),
):
    query = "SELECT DISTINCT m.* FROM media m"
    params: list = []
    conditions: list[str] = []

    if genre:
        conditions.append(
            "EXISTS (SELECT 1 FROM media_genres mg JOIN genres g ON g.id = mg.genre_id "
            "WHERE mg.media_id = m.id AND g.name = ?)"
        )
        params.append(genre)

    if tag:
        conditions.append(
            "(EXISTS (SELECT 1 FROM media_genres mg JOIN genres g ON g.id = mg.genre_id "
            "WHERE mg.media_id = m.id AND g.name = ?) OR "
            "EXISTS (SELECT 1 FROM media_tags mt JOIN tags t ON t.id = mt.tag_id "
            "WHERE mt.media_id = m.id AND t.name = ?))"
        )
        params.extend([tag, tag])

    if q:
        q_pattern = f"%{q}%"
        conditions.append(
            "(m.title LIKE ? OR "
            "EXISTS (SELECT 1 FROM media_people mp JOIN people p ON p.id = mp.person_id "
            "WHERE mp.media_id = m.id AND p.name LIKE ?) OR "
            "EXISTS (SELECT 1 FROM media_genres mg JOIN genres g ON g.id = mg.genre_id "
            "WHERE mg.media_id = m.id AND g.name LIKE ?) OR "
            "EXISTS (SELECT 1 FROM media_tags mt JOIN tags t ON t.id = mt.tag_id "
            "WHERE mt.media_id = m.id AND t.name LIKE ?))"
        )
        params.extend([q_pattern, q_pattern, q_pattern, q_pattern])

    if media_type:
        conditions.append("m.media_type = ?")
        params.append(media_type)

    if providers:
        provider_ids = [int(p.strip()) for p in providers.split(",") if p.strip().isdigit()]
        if provider_ids:
            placeholders = ",".join("?" * len(provider_ids))
            conditions.append(
                f"EXISTS (SELECT 1 FROM streaming_providers sp "
                f"WHERE sp.media_id = m.id AND sp.provider_id IN ({placeholders}))"
            )
            params.extend(provider_ids)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if sort == "relevance" and q:
        q_start = f"{q}%"
        q_pattern = f"%{q}%"
        query += (
            " ORDER BY CASE"
            " WHEN m.title LIKE ? THEN 0"
            " WHEN m.title LIKE ? THEN 1"
            " WHEN EXISTS (SELECT 1 FROM media_people mp JOIN people p ON p.id = mp.person_id"
            " WHERE mp.media_id = m.id AND p.name LIKE ?) THEN 2"
            " WHEN EXISTS (SELECT 1 FROM media_genres mg JOIN genres g ON g.id = mg.genre_id"
            " WHERE mg.media_id = m.id AND g.name LIKE ?) THEN 3"
            " WHEN EXISTS (SELECT 1 FROM media_tags mt JOIN tags t ON t.id = mt.tag_id"
            " WHERE mt.media_id = m.id AND t.name LIKE ?) THEN 4"
            " ELSE 5 END, m.title ASC"
        )
        params.extend([q_start, q_pattern, q_pattern, q_pattern, q_pattern])
    else:
        order = {"title": "m.title ASC", "year": "m.year DESC", "updated": "m.updated_at DESC"}[
            sort if sort != "relevance" else "title"
        ]
        query += f" ORDER BY {order}"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            genres = _get_media_genres(conn, row["id"])
            tags = _get_media_tags(conn, row["id"])
            results.append(_enrich_media(row_to_dict(row), genres=genres, tags=tags))

    return results


@router.get("/suggest")
def search_suggest(
    q: str = Query(..., min_length=2),
    limit: int = Query(3, ge=1, le=10),
):
    trimmed = q.strip()
    if not trimmed:
        return []

    q_pattern = f"%{trimmed}%"
    q_start = f"{trimmed}%"
    results: list[dict] = []

    with get_db() as conn:
        media_rows = conn.execute(
            """
            SELECT m.* FROM media m
            WHERE m.title LIKE ?
            ORDER BY CASE WHEN m.title LIKE ? THEN 0 ELSE 1 END, m.title ASC
            LIMIT ?
            """,
            (q_pattern, q_start, limit),
        ).fetchall()

        for row in media_rows:
            genres = _get_media_genres(conn, row["id"])
            tags = _get_media_tags(conn, row["id"])
            item = _enrich_media(row_to_dict(row), genres=genres, tags=tags)
            item["type"] = "media"
            results.append(item)

        remaining = limit - len(results)
        if remaining > 0:
            person_rows = conn.execute(
                """
                SELECT DISTINCT p.*
                FROM people p
                JOIN media_people mp ON mp.person_id = p.id
                WHERE p.name LIKE ?
                ORDER BY CASE WHEN p.name LIKE ? THEN 0 ELSE 1 END, p.name ASC
                LIMIT ?
                """,
                (q_pattern, q_start, remaining),
            ).fetchall()

            for row in person_rows:
                results.append(
                    {
                        "type": "person",
                        "id": row["id"],
                        "name": row["name"],
                        "profile_url": local_image_url(row["profile_local"]),
                        "known_for_department": row["known_for_department"],
                    }
                )

        remaining = limit - len(results)
        if remaining > 0:
            label_rows = conn.execute(
                """
                SELECT name, kind, count FROM (
                    SELECT g.name, 'genre' as kind, COUNT(mg.media_id) as count,
                        CASE WHEN g.name LIKE ? THEN 0 ELSE 1 END as rank
                    FROM genres g
                    LEFT JOIN media_genres mg ON mg.genre_id = g.id
                    WHERE g.name LIKE ?
                    GROUP BY g.id
                    UNION ALL
                    SELECT t.name, 'category' as kind, COUNT(mt.media_id) as count,
                        CASE WHEN t.name LIKE ? THEN 0 ELSE 1 END as rank
                    FROM tags t
                    LEFT JOIN media_tags mt ON mt.tag_id = t.id
                    WHERE t.name LIKE ?
                    GROUP BY t.id
                ) labels
                ORDER BY labels.rank ASC, labels.kind ASC, labels.name ASC
                LIMIT ?
                """,
                (q_start, q_pattern, q_start, q_pattern, remaining),
            ).fetchall()

            for row in label_rows:
                results.append(
                    {
                        "type": "tag",
                        "kind": row["kind"],
                        "name": row["name"],
                        "count": row["count"],
                    }
                )

    return results[:limit]


@router.get("/genres")
def list_genres():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT g.name, COUNT(mg.media_id) as count
            FROM genres g
            LEFT JOIN media_genres mg ON mg.genre_id = g.id
            GROUP BY g.id
            ORDER BY g.name
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/providers")
def list_providers():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                provider_id,
                provider_name,
                logo_local,
                COUNT(DISTINCT media_id) as count
            FROM streaming_providers
            WHERE provider_type IN ('flatrate', 'free', 'ads', 'rent', 'buy')
            GROUP BY provider_id
            ORDER BY provider_name
            """
        ).fetchall()

    return [
        {
            "provider_id": row["provider_id"],
            "provider_name": row["provider_name"],
            "logo_url": local_image_url(row["logo_local"]),
            "count": row["count"],
        }
        for row in rows
    ]


@router.get("/recent")
def list_recently_added(days: int = Query(30, ge=1, le=365)):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT m.* FROM media m
            WHERE m.created_at >= datetime('now', ?)
            ORDER BY m.created_at DESC
            LIMIT 50
            """,
            (f"-{days} days",),
        ).fetchall()
        results = []
        for row in rows:
            results.append(
                _enrich_media(
                    row_to_dict(row),
                    genres=_get_media_genres(conn, row["id"]),
                    tags=_get_media_tags(conn, row["id"]),
                )
            )

    return results


@router.get("/tags")
def list_tags():
    with get_db() as conn:
        genre_rows = conn.execute(
            """
            SELECT g.name, COUNT(mg.media_id) as count, 'genre' as kind
            FROM genres g
            LEFT JOIN media_genres mg ON mg.genre_id = g.id
            GROUP BY g.id
            """
        ).fetchall()
        tag_rows = conn.execute(
            """
            SELECT t.name, COUNT(mt.media_id) as count, 'category' as kind
            FROM tags t
            LEFT JOIN media_tags mt ON mt.tag_id = t.id
            GROUP BY t.id
            """
        ).fetchall()
    combined = [dict(r) for r in genre_rows] + [dict(r) for r in tag_rows]
    combined.sort(key=lambda x: x["name"].lower())
    return combined


@router.get("/export/all")
def export_media():
    return build_export()


@router.post("/export/import")
async def import_export_data(data: dict):
    items_raw = data.get("items")
    if not items_raw:
        raise HTTPException(400, "No items found")
    stubs = [
        MediaStub(
            title=item["title"],
            year=item.get("year"),
            media_type=item["media_type"],
            seasons=item.get("seasons") or [],
            tags=item.get("tags") or [],
        )
        for item in items_raw
    ]
    return await import_media(
        ImportRequest(items=stubs, fetch_metadata=data.get("fetch_metadata", True))
    )


@router.post("/import")
async def import_media(body: ImportRequest):
    from app.services.metadata import _upsert_media
    from app.services.import_jobs import start_metadata_job

    imported = 0
    stub_ids: list[tuple] = []
    with get_db() as conn:
        for stub in body.items:
            media_id = _upsert_media(
                conn,
                {
                    "title": stub.title,
                    "year": stub.year,
                    "media_type": stub.media_type,
                    "seasons": _serialize_seasons(stub.seasons),
                },
            )
            if stub.tags:
                conn.execute("DELETE FROM media_tags WHERE media_id = ?", (media_id,))
                _link_tags(conn, media_id, stub.tags)
            stub_ids.append((stub, media_id))
            imported += 1

    metadata_queued = False
    if body.fetch_metadata and tmdb_client.configured and body.items:
        metadata_queued = start_metadata_job(stub_ids)

    return {
        "imported": imported,
        "metadata_queued": metadata_queued,
        "metadata_total": len(body.items) if metadata_queued else 0,
    }


@router.post("/add")
async def add_media(body: AddMediaRequest):
    from app.services.metadata import MetadataFetchError, fetch_and_store_by_tmdb_id
    from app.services.metadata_errors import clear_metadata_error

    if not tmdb_client.configured:
        raise HTTPException(400, "TMDB API key not configured")

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM media WHERE tmdb_id = ?", (body.tmdb_id,)
        ).fetchone()
        if existing:
            raise HTTPException(409, "This title is already in your collection")

    try:
        result = await fetch_and_store_by_tmdb_id(
            body.tmdb_id,
            body.media_type,
            seasons=body.seasons,
            tags=body.tags,
        )
        clear_metadata_error(result["id"])
    except MetadataFetchError as exc:
        raise HTTPException(400, exc.message) from exc

    return result


@router.get("/errors")
def list_metadata_errors():
    from app.services.metadata_errors import list_unresolved_errors

    return list_unresolved_errors()


@router.post("/refresh-providers")
async def refresh_all_providers():
    from app.services.import_jobs import get_queue_info, start_provider_refresh_job

    if not tmdb_client.configured:
        raise HTTPException(400, "TMDB API key not configured")

    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM media WHERE tmdb_id IS NOT NULL"
        ).fetchone()[0]

    if total == 0:
        return {"queued": False, "total": 0}

    queued = start_provider_refresh_job()
    return {"queued": queued, "total": total, "queue": get_queue_info()}


@router.post("/refresh-metadata")
async def refresh_all_metadata():
    from app.services.import_jobs import get_queue_info, start_metadata_rescan_job

    if not tmdb_client.configured:
        raise HTTPException(400, "TMDB API key not configured")

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]

    if total == 0:
        return {"queued": False, "total": 0}

    queued = start_metadata_rescan_job()
    return {"queued": queued, "total": total, "queue": get_queue_info()}


@router.get("/jobs/status")
def jobs_status():
    from app.services.import_jobs import get_job_status, get_queue_info
    from app.services.metadata_errors import get_setting
    from app.services.scheduler import get_schedule_info

    status = get_job_status()
    if status is None:
        status = {"running": False, "total": 0, "completed": 0, "failed": 0}
    return {
        **status,
        "queue": get_queue_info(),
        "schedule": get_schedule_info(),
        "last_provider_refresh": get_setting("last_provider_refresh"),
        "last_metadata_rescan": get_setting("last_metadata_rescan"),
    }


@router.get("/import/status")
def import_status():
    from app.services.import_jobs import get_job_status

    status = get_job_status()
    if status is None:
        return {"running": False, "total": 0, "completed": 0, "failed": 0}
    return status


@router.post("/{media_id}/resolve")
async def resolve_media_error(media_id: int, body: ResolveErrorRequest):
    from app.services.metadata import MetadataFetchError, fetch_and_store_by_tmdb_id
    from app.services.metadata_errors import resolve_metadata_error

    with get_db() as conn:
        media = row_to_dict(conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone())
    if not media:
        raise HTTPException(404, "Media not found")

    if body.tmdb_id:
        if not tmdb_client.configured:
            raise HTTPException(400, "TMDB API key not configured")
        stub_tags = []
        with get_db() as conn:
            stub_tags = _get_media_tags(conn, media_id)
        try:
            await fetch_and_store_by_tmdb_id(
                body.tmdb_id,
                media["media_type"],
                media_id=media_id,
                seasons=_deserialize_seasons(media.get("seasons")),
                tags=stub_tags,
            )
        except MetadataFetchError as exc:
            raise HTTPException(400, exc.message) from exc

    if not resolve_metadata_error(media_id, body.notes):
        raise HTTPException(404, "No unresolved error for this title")

    return {"resolved": True, "media_id": media_id}


def _queue_metadata_refresh(media_id: int) -> dict:
    from app.services.import_jobs import enqueue_single_metadata

    with get_db() as conn:
        media = row_to_dict(conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone())
    if not media:
        raise HTTPException(404, "Media not found")
    if not tmdb_client.configured:
        raise HTTPException(400, "TMDB API key not configured")

    with get_db() as conn:
        stub_tags = _get_media_tags(conn, media_id)
    stub = MediaStub(
        title=media["title"],
        year=media["year"],
        media_type=media["media_type"],
        seasons=_deserialize_seasons(media.get("seasons")),
        tags=stub_tags,
    )
    enqueue_single_metadata(stub, media_id)
    return {"queued": True, "media_id": media_id}


@router.post("/{media_id}/retry")
async def retry_media_metadata(media_id: int):
    return _queue_metadata_refresh(media_id)


@router.post("/dedupe")
def dedupe_collection():
    from app.services.metadata import dedupe_media

    removed = dedupe_media()
    return {"removed": removed}


@router.delete("/{media_id}")
def delete_media(media_id: int):
    with get_db() as conn:
        media = conn.execute("SELECT id FROM media WHERE id = ?", (media_id,)).fetchone()
        if not media:
            raise HTTPException(404, "Media not found")
        conn.execute("DELETE FROM media WHERE id = ?", (media_id,))

    return {"deleted": True, "id": media_id}


@router.get("/{media_id}")
async def get_media(media_id: int):
    with get_db() as conn:
        media = row_to_dict(conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone())
        if not media:
            raise HTTPException(404, "Media not found")

        genres = _get_media_genres(conn, media_id)
        tags = _get_media_tags(conn, media_id)

        cast = [
            {
                **dict(r),
                "profile_url": local_image_url(r["profile_local"]),
            }
            for r in conn.execute(
                """
                SELECT p.id, p.name, p.tmdb_id, p.profile_local, mp.role, mp.character_name, mp.sort_order
                FROM media_people mp
                JOIN people p ON p.id = mp.person_id
                WHERE mp.media_id = ? AND mp.role = 'actor'
                ORDER BY mp.sort_order
                """,
                (media_id,),
            ).fetchall()
        ]

        crew = [
            {
                **dict(r),
                "profile_url": local_image_url(r["profile_local"]),
            }
            for r in conn.execute(
                """
                SELECT p.id, p.name, p.tmdb_id, p.profile_local, mp.role
                FROM media_people mp
                JOIN people p ON p.id = mp.person_id
                WHERE mp.media_id = ? AND mp.role IN ('director', 'creator', 'writer')
                ORDER BY mp.role, p.name
                """,
                (media_id,),
            ).fetchall()
        ]

        providers = [
            {
                **dict(r),
                "logo_url": local_image_url(r["logo_local"]),
            }
            for r in conn.execute(
                "SELECT * FROM streaming_providers WHERE media_id = ? ORDER BY provider_type, provider_name",
                (media_id,),
            ).fetchall()
        ]

        related = _find_related_media(conn, media_id)

    result = _enrich_media(media, genres=genres, tags=tags)
    result["cast"] = cast
    result["crew"] = crew
    result["streaming_providers"] = providers
    result["related"] = related

    if media["media_type"] == "tv" and media.get("tmdb_id"):
        owned = result.get("seasons") or []
        if owned:
            result["season_details"] = await _fetch_owned_seasons(media["tmdb_id"], owned)

    return result


@router.post("/{media_id}/refresh")
async def refresh_metadata(media_id: int):
    return _queue_metadata_refresh(media_id)
