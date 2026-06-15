import logging
from dataclasses import dataclass
from typing import Literal

from app.config import IMAGES_PATH
from app.database import get_db
from app.services.images import download_image_immediate
from app.services.tmdb import tmdb_client

logger = logging.getLogger(__name__)

_pending_keys: set[str] = set()


@dataclass
class ImageTask:
    kind: Literal["poster", "backdrop", "profile", "provider_logo"]
    label: str
    remote_path: str
    category: str
    filename: str
    size: str
    media_id: int | None = None
    person_id: int | None = None
    provider_id: int | None = None
    provider_type: str | None = None
    region: str | None = None


def task_key(task: ImageTask) -> str:
    return f"{task.category}/{task.filename}"


def release_task_key(task: ImageTask) -> None:
    _pending_keys.discard(task_key(task))


def _file_cached(category: str, filename: str) -> bool:
    return (IMAGES_PATH / category / filename).exists()


async def execute_image_task(task: ImageTask) -> bool:
    if _file_cached(task.category, task.filename):
        local = str((IMAGES_PATH / task.category / task.filename).relative_to(IMAGES_PATH.parent))
    else:
        local = await download_image_immediate(
            task.remote_path, task.category, task.filename, task.size
        )
    if not local:
        return False

    with get_db() as conn:
        if task.kind == "poster" and task.media_id:
            conn.execute(
                "UPDATE media SET poster_local = ? WHERE id = ?",
                (local, task.media_id),
            )
        elif task.kind == "backdrop" and task.media_id:
            conn.execute(
                "UPDATE media SET backdrop_local = ? WHERE id = ?",
                (local, task.media_id),
            )
        elif task.kind == "profile" and task.person_id:
            conn.execute(
                "UPDATE people SET profile_local = ? WHERE id = ?",
                (local, task.person_id),
            )
        elif (
            task.kind == "provider_logo"
            and task.media_id
            and task.provider_id
            and task.provider_type
            and task.region
        ):
            conn.execute(
                """
                UPDATE streaming_providers
                SET logo_local = ?
                WHERE media_id = ? AND provider_id = ? AND provider_type = ? AND region = ?
                """,
                (local, task.media_id, task.provider_id, task.provider_type, task.region),
            )
    return True


def _profile_task(person_id: int, name: str, profile_path: str) -> ImageTask | None:
    if not profile_path:
        return None
    filename = f"{person_id}_profile.jpg"
    if _file_cached("profiles", filename):
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT profile_local FROM people WHERE id = ?", (person_id,)
        ).fetchone()
        if row and row["profile_local"]:
            return None
    return ImageTask(
        kind="profile",
        label=name,
        remote_path=profile_path,
        category="profiles",
        filename=filename,
        size="w185",
        person_id=person_id,
    )


def build_media_image_tasks(
    media_id: int,
    title: str,
    item: dict,
    profiles: list[tuple[int, str | None]],
    providers: list[dict],
) -> list[ImageTask]:
    tasks: list[ImageTask] = []
    seen_profiles: set[int] = set()

    poster_path = item.get("poster_path")
    if poster_path and not item.get("poster_local") and not _file_cached("posters", f"{media_id}_poster.jpg"):
        tasks.append(
            ImageTask(
                kind="poster",
                label=f"{title} (poster)",
                remote_path=poster_path,
                category="posters",
                filename=f"{media_id}_poster.jpg",
                size="w500",
                media_id=media_id,
            )
        )

    backdrop_path = item.get("backdrop_path")
    if backdrop_path and not item.get("backdrop_local") and not _file_cached(
        "backdrops", f"{media_id}_backdrop.jpg"
    ):
        tasks.append(
            ImageTask(
                kind="backdrop",
                label=f"{title} (backdrop)",
                remote_path=backdrop_path,
                category="backdrops",
                filename=f"{media_id}_backdrop.jpg",
                size="w1280",
                media_id=media_id,
            )
        )

    with get_db() as conn:
        for person_id, profile_path in profiles:
            if person_id in seen_profiles or not profile_path:
                continue
            seen_profiles.add(person_id)
            row = conn.execute(
                "SELECT name, profile_local FROM people WHERE id = ?", (person_id,)
            ).fetchone()
            if row and row["profile_local"]:
                continue
            task = _profile_task(person_id, row["name"] if row else "Profile", profile_path)
            if task:
                tasks.append(task)

    region = tmdb_client.region
    for provider in providers:
        logo_path = provider.get("logo_path")
        if not logo_path:
            continue
        filename = f"provider_{provider['provider_id']}.png"
        if _file_cached("providers", filename):
            continue
        tasks.append(
            ImageTask(
                kind="provider_logo",
                label=provider.get("provider_name") or "Provider logo",
                remote_path=logo_path,
                category="providers",
                filename=filename,
                size="w92",
                media_id=provider["media_id"],
                provider_id=provider["provider_id"],
                provider_type=provider["provider_type"],
                region=region,
            )
        )

    return tasks


def build_provider_logo_tasks(providers: list[dict]) -> list[ImageTask]:
    tasks: list[ImageTask] = []
    region = tmdb_client.region
    for provider in providers:
        logo_path = provider.get("logo_path")
        if not logo_path:
            continue
        filename = f"provider_{provider['provider_id']}.png"
        if _file_cached("providers", filename):
            continue
        tasks.append(
            ImageTask(
                kind="provider_logo",
                label=provider.get("provider_name") or "Provider logo",
                remote_path=logo_path,
                category="providers",
                filename=filename,
                size="w92",
                media_id=provider["media_id"],
                provider_id=provider["provider_id"],
                provider_type=provider["provider_type"],
                region=region,
            )
        )
    return tasks


def enqueue_person_profile(person_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT name, profile_path, profile_local FROM people WHERE id = ?",
            (person_id,),
        ).fetchone()
    if not row or not row["profile_path"] or row["profile_local"]:
        return False
    task = _profile_task(person_id, row["name"], row["profile_path"])
    if not task:
        return False
    return enqueue_image_tasks([task], label=f"Profile: {row['name']}")


def enqueue_media_images(
    media_id: int,
    title: str,
    item: dict,
    profiles: list[tuple[int, str | None]],
    providers: list[dict],
) -> bool:
    tasks = build_media_image_tasks(media_id, title, item, profiles, providers)
    if not tasks:
        return False
    return enqueue_image_tasks(tasks, label=f"Images: {title}")


def enqueue_provider_logos(providers: list[dict], *, label: str = "Provider logos") -> bool:
    tasks = build_provider_logo_tasks(providers)
    if not tasks:
        return False
    return enqueue_image_tasks(tasks, label=label)


def enqueue_missing_media_images(media_id: int) -> bool:
    with get_db() as conn:
        media = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
        if not media:
            return False
        profile_rows = conn.execute(
            """
            SELECT p.id, p.name, p.profile_path, p.profile_local
            FROM media_people mp
            JOIN people p ON p.id = mp.person_id
            WHERE mp.media_id = ?
            """,
            (media_id,),
        ).fetchall()
        provider_rows = conn.execute(
            """
            SELECT media_id, provider_id, provider_type, logo_path, provider_name
            FROM streaming_providers
            WHERE media_id = ? AND region = ?
            """,
            (media_id, tmdb_client.region),
        ).fetchall()

    profiles = [
        (row["id"], row["profile_path"])
        for row in profile_rows
        if row["profile_path"] and not row["profile_local"]
    ]
    providers = [dict(row) for row in provider_rows]
    return enqueue_media_images(media_id, media["title"], dict(media), profiles, providers)


def enqueue_image_tasks(tasks: list[ImageTask], label: str = "Cache images") -> bool:
    from app.services.import_jobs import enqueue_image_job

    filtered: list[ImageTask] = []
    for task in tasks:
        key = task_key(task)
        if key in _pending_keys:
            continue
        _pending_keys.add(key)
        filtered.append(task)

    if not filtered:
        return False
    return enqueue_image_job(filtered, label)
