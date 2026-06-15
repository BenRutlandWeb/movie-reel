from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.services.images import local_image_url
from app.services.metadata import fetch_and_store_person_details
from app.services.image_tasks import enqueue_person_profile
from app.services.tmdb import tmdb_client

router = APIRouter(prefix="/api/people", tags=["people"])

_PERSON_MEDIA_SQL = """
    SELECT m.id, m.title, m.year, m.media_type, m.poster_local
    FROM media m
    WHERE m.id IN (
        SELECT DISTINCT media_id FROM media_people WHERE person_id = ?
    )
    ORDER BY m.title
"""


def _person_response(person, media) -> dict:
    return {
        "id": person["id"],
        "name": person["name"],
        "tmdb_id": person["tmdb_id"],
        "profile_url": local_image_url(person["profile_local"]),
        "biography": person["biography"],
        "birthday": person["birthday"],
        "deathday": person["deathday"],
        "place_of_birth": person["place_of_birth"],
        "known_for_department": person["known_for_department"],
        "media": [
            {
                **dict(m),
                "poster_url": local_image_url(m["poster_local"]),
            }
            for m in media
        ],
    }


@router.get("/{person_id}")
async def get_person(person_id: int):
    with get_db() as conn:
        person = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
        if not person:
            raise HTTPException(404, "Person not found")

        media = conn.execute(_PERSON_MEDIA_SQL, (person_id,)).fetchall()

    if person["tmdb_id"] and tmdb_client.configured and not person["biography"]:
        await fetch_and_store_person_details(person_id)
        with get_db() as conn:
            person = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    elif person["profile_path"] and not person["profile_local"]:
        enqueue_person_profile(person_id)

    return _person_response(person, media)


@router.post("/{person_id}/refresh")
async def refresh_person(person_id: int):
    with get_db() as conn:
        person = conn.execute("SELECT id FROM people WHERE id = ?", (person_id,)).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")
    if not tmdb_client.configured:
        raise HTTPException(400, "TMDB API key not configured")

    await fetch_and_store_person_details(person_id, force=True)

    with get_db() as conn:
        person = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
        media = conn.execute(_PERSON_MEDIA_SQL, (person_id,)).fetchall()

    return _person_response(person, media)
