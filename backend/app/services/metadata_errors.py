from app.database import get_db


def log_metadata_error(media_id: int, error_type: str, message: str) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO metadata_errors (media_id, error_type, message, resolved_at, resolution_notes)
            VALUES (?, ?, ?, NULL, NULL)
            ON CONFLICT(media_id) DO UPDATE SET
                error_type = excluded.error_type,
                message = excluded.message,
                created_at = datetime('now'),
                resolved_at = NULL,
                resolution_notes = NULL
            """,
            (media_id, error_type, message),
        )


def clear_metadata_error(media_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM metadata_errors WHERE media_id = ?", (media_id,))


def resolve_metadata_error(media_id: int, notes: str | None = None) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM metadata_errors WHERE media_id = ? AND resolved_at IS NULL",
            (media_id,),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            """
            UPDATE metadata_errors
            SET resolved_at = datetime('now'), resolution_notes = ?
            WHERE media_id = ?
            """,
            (notes, media_id),
        )
    return True


def list_unresolved_errors() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                e.id, e.media_id, e.error_type, e.message, e.created_at,
                m.title, m.year, m.media_type, m.tmdb_id
            FROM metadata_errors e
            JOIN media m ON m.id = e.media_id
            WHERE e.resolved_at IS NULL
            ORDER BY e.created_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_setting(key: str) -> str | None:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
