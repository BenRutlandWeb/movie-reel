import json
import re
from typing import Any

from app.database import get_db
from app.schemas import ExportData, MediaStub
from app.services.image_tasks import enqueue_media_images, enqueue_person_profile, enqueue_provider_logos
from app.services.tmdb import tmdb_client


class MetadataFetchError(Exception):
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


def _upsert_genre(conn, tmdb_id: int | None, name: str) -> int:
    if tmdb_id:
        conn.execute(
            "INSERT INTO genres (tmdb_id, name) VALUES (?, ?) ON CONFLICT(tmdb_id) DO UPDATE SET name = excluded.name",
            (tmdb_id, name),
        )
        row = conn.execute("SELECT id FROM genres WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
    else:
        conn.execute(
            "INSERT INTO genres (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
            (name,),
        )
        row = conn.execute("SELECT id FROM genres WHERE name = ?", (name,)).fetchone()
    return row["id"]


def _upsert_tag(conn, name: str) -> int:
    conn.execute("INSERT INTO tags (name) VALUES (?) ON CONFLICT(name) DO NOTHING", (name,))
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    return row["id"]


def _link_tags(conn, media_id: int, tag_names: list[str]) -> None:
    for name in tag_names:
        if not name or not name.strip():
            continue
        tag_id = _upsert_tag(conn, name.strip())
        conn.execute(
            "INSERT OR IGNORE INTO media_tags (media_id, tag_id) VALUES (?, ?)",
            (media_id, tag_id),
        )


def _get_media_tags(conn, media_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT t.name FROM tags t
        JOIN media_tags mt ON mt.tag_id = t.id
        WHERE mt.media_id = ?
        ORDER BY t.name
        """,
        (media_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def _get_media_genres(conn, media_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT g.name FROM genres g
        JOIN media_genres mg ON mg.genre_id = g.id
        WHERE mg.media_id = ?
        ORDER BY g.name
        """,
        (media_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def _upsert_person(
    conn,
    name: str,
    tmdb_id: int | None,
    profile_path: str | None,
    profile_local: str | None,
    *,
    biography: str | None = None,
    birthday: str | None = None,
    deathday: str | None = None,
    place_of_birth: str | None = None,
    known_for_department: str | None = None,
) -> int:
    if tmdb_id:
        conn.execute(
            """
            INSERT INTO people (
                name, tmdb_id, profile_path, profile_local,
                biography, birthday, deathday, place_of_birth, known_for_department
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tmdb_id) DO UPDATE SET
                name = excluded.name,
                profile_path = COALESCE(excluded.profile_path, people.profile_path),
                profile_local = COALESCE(excluded.profile_local, people.profile_local),
                biography = COALESCE(excluded.biography, people.biography),
                birthday = COALESCE(excluded.birthday, people.birthday),
                deathday = COALESCE(excluded.deathday, people.deathday),
                place_of_birth = COALESCE(excluded.place_of_birth, people.place_of_birth),
                known_for_department = COALESCE(
                    excluded.known_for_department, people.known_for_department
                )
            """,
            (
                name,
                tmdb_id,
                profile_path,
                profile_local,
                biography,
                birthday,
                deathday,
                place_of_birth,
                known_for_department,
            ),
        )
        row = conn.execute("SELECT id FROM people WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
    else:
        row = conn.execute("SELECT id FROM people WHERE name = ?", (name,)).fetchone()
        if row:
            if any(
                value
                for value in (
                    biography,
                    birthday,
                    deathday,
                    place_of_birth,
                    known_for_department,
                    profile_path,
                    profile_local,
                )
            ):
                conn.execute(
                    """
                    UPDATE people SET
                        profile_path = COALESCE(?, profile_path),
                        profile_local = COALESCE(?, profile_local),
                        biography = COALESCE(?, biography),
                        birthday = COALESCE(?, birthday),
                        deathday = COALESCE(?, deathday),
                        place_of_birth = COALESCE(?, place_of_birth),
                        known_for_department = COALESCE(?, known_for_department)
                    WHERE id = ?
                    """,
                    (
                        profile_path,
                        profile_local,
                        biography,
                        birthday,
                        deathday,
                        place_of_birth,
                        known_for_department,
                        row["id"],
                    ),
                )
            return row["id"]
        cursor = conn.execute(
            """
            INSERT INTO people (
                name, profile_path, profile_local,
                biography, birthday, deathday, place_of_birth, known_for_department
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                profile_path,
                profile_local,
                biography,
                birthday,
                deathday,
                place_of_birth,
                known_for_department,
            ),
        )
        return cursor.lastrowid
    return row["id"]


def _serialize_seasons(seasons: list[int | str] | None) -> str | None:
    if not seasons:
        return None
    return json.dumps(seasons)


def _deserialize_seasons(value: str | list | None) -> list[int | str]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def normalize_title(title: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", title.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _find_media_id(conn, title: str, year: int | None, media_type: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM media WHERE title = ? AND year IS ? AND media_type = ?",
        (title, year, media_type),
    ).fetchone()
    return row["id"] if row else None


def _find_media_by_tmdb_id(conn, tmdb_id: int) -> int | None:
    row = conn.execute("SELECT id FROM media WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
    return row["id"] if row else None


def _media_richness(row) -> int:
    score = 0
    for field in ("tmdb_id", "overview", "poster_local", "backdrop_local", "runtime"):
        if row[field]:
            score += 1
    return score


def _update_media_by_id(conn, media_id: int, item: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE media SET
            title = ?, year = ?, tmdb_id = ?, overview = ?, poster_path = ?, backdrop_path = ?,
            poster_local = COALESCE(?, poster_local), backdrop_local = COALESCE(?, backdrop_local),
            runtime = ?, status = ?, seasons = COALESCE(?, seasons),
            vote_average = ?, vote_count = ?, certification = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            item["title"],
            item.get("year"),
            item.get("tmdb_id"),
            item.get("overview"),
            item.get("poster_path"),
            item.get("backdrop_path"),
            item.get("poster_local"),
            item.get("backdrop_local"),
            item.get("runtime"),
            item.get("status"),
            item.get("seasons"),
            item.get("vote_average"),
            item.get("vote_count"),
            item.get("certification"),
            media_id,
        ),
    )


def dedupe_media() -> int:
    """Remove duplicate rows created when folder titles differ from TMDB titles."""
    removed = 0
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM media ORDER BY id").fetchall()
        to_delete: set[int] = set()
        by_tmdb: dict[int, Any] = {}

        for row in rows:
            if not row["tmdb_id"]:
                continue
            tmdb_id = row["tmdb_id"]
            if tmdb_id in by_tmdb:
                keep, drop = (
                    (row, by_tmdb[tmdb_id])
                    if _media_richness(row) >= _media_richness(by_tmdb[tmdb_id])
                    else (by_tmdb[tmdb_id], row)
                )
                by_tmdb[tmdb_id] = keep
                to_delete.add(drop["id"])
            else:
                by_tmdb[tmdb_id] = row

        enriched = list(by_tmdb.values())
        for row in rows:
            if row["id"] in to_delete or row["tmdb_id"]:
                continue
            key = (normalize_title(row["title"]), row["year"], row["media_type"])
            for match in enriched:
                if (
                    normalize_title(match["title"]) == key[0]
                    and match["year"] == key[1]
                    and match["media_type"] == key[2]
                ):
                    to_delete.add(row["id"])
                    break

        for media_id in to_delete:
            conn.execute("DELETE FROM media WHERE id = ?", (media_id,))
            removed += 1

    return removed


def _upsert_media(conn, item: dict[str, Any]) -> int:
    conn.execute(
        """
        INSERT INTO media (
            title, year, media_type, tmdb_id, overview, poster_path, backdrop_path,
            poster_local, backdrop_local, runtime, status, seasons,
            vote_average, vote_count, certification, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(title, year, media_type) DO UPDATE SET
            tmdb_id = COALESCE(excluded.tmdb_id, media.tmdb_id),
            overview = COALESCE(excluded.overview, media.overview),
            poster_path = COALESCE(excluded.poster_path, media.poster_path),
            backdrop_path = COALESCE(excluded.backdrop_path, media.backdrop_path),
            poster_local = COALESCE(excluded.poster_local, media.poster_local),
            backdrop_local = COALESCE(excluded.backdrop_local, media.backdrop_local),
            runtime = COALESCE(excluded.runtime, media.runtime),
            status = COALESCE(excluded.status, media.status),
            seasons = COALESCE(excluded.seasons, media.seasons),
            vote_average = COALESCE(excluded.vote_average, media.vote_average),
            vote_count = COALESCE(excluded.vote_count, media.vote_count),
            certification = COALESCE(excluded.certification, media.certification),
            updated_at = datetime('now')
        """,
        (
            item["title"],
            item.get("year"),
            item["media_type"],
            item.get("tmdb_id"),
            item.get("overview"),
            item.get("poster_path"),
            item.get("backdrop_path"),
            item.get("poster_local"),
            item.get("backdrop_local"),
            item.get("runtime"),
            item.get("status"),
            item.get("seasons"),
            item.get("vote_average"),
            item.get("vote_count"),
            item.get("certification"),
        ),
    )
    row = conn.execute(
        "SELECT id FROM media WHERE title = ? AND year IS ? AND media_type = ?",
        (item["title"], item.get("year"), item["media_type"]),
    ).fetchone()
    return row["id"]


def _link_people_from_tmdb(conn, media_id: int, details: dict, media_type: str) -> list[tuple[int, str | None]]:
    credits = details.get("credits", {})
    crew = credits.get("crew", [])
    cast = credits.get("cast", [])
    profiles: list[tuple[int, str | None]] = []

    director_roles = {"Director"}
    creator_roles = {"Creator", "Executive Producer"} if media_type == "tv" else set()

    for member in crew:
        if member.get("job") in director_roles:
            person_id = _upsert_person(
                conn, member["name"], member.get("id"), member.get("profile_path"), None
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO media_people (media_id, person_id, role, sort_order)
                VALUES (?, ?, 'director', ?)
                """,
                (media_id, person_id, member.get("order", 0)),
            )
            profiles.append((person_id, member.get("profile_path")))
        elif member.get("job") in creator_roles:
            person_id = _upsert_person(
                conn, member["name"], member.get("id"), member.get("profile_path"), None
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO media_people (media_id, person_id, role, sort_order)
                VALUES (?, ?, 'creator', ?)
                """,
                (media_id, person_id, member.get("order", 0)),
            )
            profiles.append((person_id, member.get("profile_path")))

    for i, member in enumerate(cast):
        person_id = _upsert_person(
            conn, member["name"], member.get("id"), member.get("profile_path"), None
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO media_people (media_id, person_id, role, character_name, sort_order)
            VALUES (?, ?, 'actor', ?, ?)
            """,
            (media_id, person_id, member.get("character"), i),
        )
        profiles.append((person_id, member.get("profile_path")))

    return profiles


def _link_providers_from_tmdb(conn, media_id: int, details: dict) -> list[dict]:
    providers_data = details.get("watch/providers", {}).get("results", {})
    region_data = providers_data.get(tmdb_client.region, {})
    pending: list[dict] = []

    for provider_type in ("flatrate", "free", "ads", "rent", "buy"):
        for provider in region_data.get(provider_type, []):
            conn.execute(
                """
                INSERT INTO streaming_providers (
                    media_id, provider_id, provider_name, logo_path, logo_local, provider_type, region
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(media_id, provider_id, provider_type, region) DO UPDATE SET
                    provider_name = excluded.provider_name,
                    logo_path = excluded.logo_path
                """,
                (
                    media_id,
                    provider["provider_id"],
                    provider["provider_name"],
                    provider.get("logo_path"),
                    None,
                    provider_type,
                    tmdb_client.region,
                ),
            )
            pending.append(
                {
                    "media_id": media_id,
                    "provider_id": provider["provider_id"],
                    "provider_type": provider_type,
                    "logo_path": provider.get("logo_path"),
                    "provider_name": provider["provider_name"],
                }
            )

    return pending


async def fetch_and_store_person_details(person_id: int, *, force: bool = False) -> None:
    with get_db() as conn:
        person = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
        if not person:
            return
        tmdb_id = person["tmdb_id"]
        if not tmdb_id or not tmdb_client.configured:
            return
        if person["biography"] and not force:
            return

    details = await tmdb_client.get_person_details(tmdb_id)
    if not details:
        return

    profile_path = details.get("profile_path")
    with get_db() as conn:
        _upsert_person(
            conn,
            details.get("name") or person["name"],
            tmdb_id,
            profile_path,
            person["profile_local"],
            biography=details.get("biography") or None,
            birthday=details.get("birthday") or None,
            deathday=details.get("deathday") or None,
            place_of_birth=details.get("place_of_birth") or None,
            known_for_department=details.get("known_for_department") or None,
        )

    if profile_path and not person["profile_local"]:
        enqueue_person_profile(person_id)



async def _store_tmdb_details(
    stub: MediaStub,
    details: dict,
    media_id: int | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "title": stub.title,
        "year": stub.year,
        "media_type": stub.media_type,
    }
    if stub.seasons:
        result["seasons"] = _serialize_seasons(stub.seasons)
    elif media_id:
        with get_db() as conn:
            row = conn.execute("SELECT seasons FROM media WHERE id = ?", (media_id,)).fetchone()
            if row and row["seasons"]:
                result["seasons"] = row["seasons"]

    year = stub.year
    if stub.media_type == "movie":
        release = details.get("release_date", "")
        year = int(release[:4]) if release else stub.year
        runtime = details.get("runtime")
    else:
        first_air = details.get("first_air_date", "")
        year = int(first_air[:4]) if first_air else stub.year
        run_times = details.get("episode_run_time") or []
        runtime = run_times[0] if run_times else None

    tmdb_id = details.get("id")
    result.update(
        {
            "title": details.get("title") or details.get("name") or stub.title,
            "year": year,
            "tmdb_id": tmdb_id,
            "overview": details.get("overview"),
            "poster_path": details.get("poster_path"),
            "backdrop_path": details.get("backdrop_path"),
            "runtime": runtime,
            "status": details.get("status"),
            "vote_average": details.get("vote_average"),
            "vote_count": details.get("vote_count"),
            "certification": tmdb_client.extract_uk_certification(details, stub.media_type),
        }
    )

    with get_db() as conn:
        if tmdb_id:
            existing = _find_media_by_tmdb_id(conn, tmdb_id)
            if existing and media_id and existing != media_id:
                conn.execute("DELETE FROM media WHERE id = ?", (existing,))
            elif existing and not media_id:
                media_id = existing

        if media_id:
            _update_media_by_id(conn, media_id, result)
        else:
            media_id = _upsert_media(conn, result)
        conn.execute("DELETE FROM media_genres WHERE media_id = ?", (media_id,))
        for genre in details.get("genres", []):
            genre_id = _upsert_genre(conn, genre.get("id"), genre["name"])
            conn.execute(
                "INSERT OR IGNORE INTO media_genres (media_id, genre_id) VALUES (?, ?)",
                (media_id, genre_id),
            )
        conn.execute("DELETE FROM media_people WHERE media_id = ?", (media_id,))
        profiles = _link_people_from_tmdb(conn, media_id, details, stub.media_type)
        conn.execute(
            "DELETE FROM streaming_providers WHERE media_id = ? AND region = ?",
            (media_id, tmdb_client.region),
        )
        pending_providers = _link_providers_from_tmdb(conn, media_id, details)
        if stub.tags:
            conn.execute("DELETE FROM media_tags WHERE media_id = ?", (media_id,))
            _link_tags(conn, media_id, stub.tags)

    title = result["title"]
    enqueue_media_images(media_id, title, result, profiles, pending_providers)
    result["id"] = media_id
    return result


async def fetch_and_store_by_tmdb_id(
    tmdb_id: int,
    media_type: str,
    *,
    media_id: int | None = None,
    seasons: list[int | str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    if not tmdb_client.configured:
        raise MetadataFetchError("config", "TMDB API key not configured")

    if media_type == "movie":
        details = await tmdb_client.get_movie_details(tmdb_id)
    else:
        details = await tmdb_client.get_tv_details(tmdb_id)

    if not details:
        raise MetadataFetchError("tmdb_error", f"Failed to fetch TMDB details for id {tmdb_id}")

    title = details.get("title") or details.get("name") or "Unknown"
    release = details.get("release_date") or details.get("first_air_date") or ""
    year = int(release[:4]) if release else None
    stub = MediaStub(
        title=title,
        year=year,
        media_type=media_type,
        seasons=seasons or [],
        tags=tags or [],
    )
    return await _store_tmdb_details(stub, details, media_id)


async def fetch_and_store_metadata(stub: MediaStub, media_id: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "title": stub.title,
        "year": stub.year,
        "media_type": stub.media_type,
    }
    if stub.seasons:
        result["seasons"] = _serialize_seasons(stub.seasons)

    if media_id is None:
        with get_db() as conn:
            media_id = _find_media_id(conn, stub.title, stub.year, stub.media_type)

    if media_id and not stub.seasons:
        with get_db() as conn:
            row = conn.execute("SELECT seasons FROM media WHERE id = ?", (media_id,)).fetchone()
            if row and row["seasons"]:
                result["seasons"] = row["seasons"]

    if not tmdb_client.configured:
        with get_db() as conn:
            if media_id:
                _update_media_by_id(conn, media_id, result)
            else:
                media_id = _upsert_media(conn, result)
        result["id"] = media_id
        return result

    if stub.media_type == "movie":
        search = await tmdb_client.search_movie(stub.title, stub.year)
        if not search:
            with get_db() as conn:
                if media_id:
                    _update_media_by_id(conn, media_id, result)
                else:
                    media_id = _upsert_media(conn, result)
            result["id"] = media_id
            raise MetadataFetchError(
                "search_miss",
                f"No TMDB match for '{stub.title}'"
                + (f" ({stub.year})" if stub.year else ""),
            )
        details = await tmdb_client.get_movie_details(search["id"])
    else:
        search = await tmdb_client.search_tv(stub.title, stub.year)
        if not search:
            with get_db() as conn:
                if media_id:
                    _update_media_by_id(conn, media_id, result)
                else:
                    media_id = _upsert_media(conn, result)
            result["id"] = media_id
            raise MetadataFetchError(
                "search_miss",
                f"No TMDB match for '{stub.title}'"
                + (f" ({stub.year})" if stub.year else ""),
            )
        details = await tmdb_client.get_tv_details(search["id"])

    if not details:
        with get_db() as conn:
            if media_id:
                _update_media_by_id(conn, media_id, result)
            else:
                media_id = _upsert_media(conn, result)
        result["id"] = media_id
        raise MetadataFetchError(
            "tmdb_error",
            f"Failed to fetch TMDB details for '{stub.title}'",
        )

    return await _store_tmdb_details(stub, details, media_id)


async def refresh_streaming_providers(media_id: int, tmdb_id: int, media_type: str) -> None:
    if media_type == "movie":
        details = await tmdb_client.get_movie_details(tmdb_id)
    else:
        details = await tmdb_client.get_tv_details(tmdb_id)

    if not details:
        raise ValueError("Failed to fetch TMDB provider data")

    with get_db() as conn:
        conn.execute(
            "DELETE FROM streaming_providers WHERE media_id = ? AND region = ?",
            (media_id, tmdb_client.region),
        )
        pending_providers = _link_providers_from_tmdb(conn, media_id, details)

    enqueue_provider_logos(pending_providers)


def build_export() -> ExportData:
    items: list[MediaStub] = []
    with get_db() as conn:
        media_rows = conn.execute(
            "SELECT id, title, year, media_type, seasons FROM media ORDER BY title"
        ).fetchall()
        for media in media_rows:
            items.append(
                MediaStub(
                    title=media["title"],
                    year=media["year"],
                    media_type=media["media_type"],
                    seasons=_deserialize_seasons(media["seasons"]),
                    tags=_get_media_tags(conn, media["id"]),
                )
            )
    return ExportData(items=items)
