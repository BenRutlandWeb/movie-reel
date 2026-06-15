import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import DATABASE_PATH, IMAGES_PATH, settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER,
    media_type TEXT NOT NULL CHECK(media_type IN ('movie', 'tv')),
    tmdb_id INTEGER,
    overview TEXT,
    poster_path TEXT,
    backdrop_path TEXT,
    poster_local TEXT,
    backdrop_local TEXT,
    runtime INTEGER,
    status TEXT,
    seasons TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(title, year, media_type)
);

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    tmdb_id INTEGER UNIQUE,
    profile_path TEXT,
    profile_local TEXT,
    biography TEXT,
    birthday TEXT,
    deathday TEXT,
    place_of_birth TEXT,
    known_for_department TEXT
);

CREATE TABLE IF NOT EXISTS media_people (
    media_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('actor', 'director', 'creator', 'writer')),
    character_name TEXT,
    sort_order INTEGER DEFAULT 0,
    PRIMARY KEY (media_id, person_id, role),
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id INTEGER UNIQUE,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS media_genres (
    media_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (media_id, genre_id),
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS streaming_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    provider_name TEXT NOT NULL,
    logo_path TEXT,
    logo_local TEXT,
    provider_type TEXT NOT NULL CHECK(provider_type IN ('flatrate', 'rent', 'buy', 'free', 'ads')),
    region TEXT NOT NULL DEFAULT 'US',
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
    UNIQUE(media_id, provider_id, provider_type, region)
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS media_tags (
    media_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (media_id, tag_id),
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type);
CREATE INDEX IF NOT EXISTS idx_media_year ON media(year);
CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
CREATE INDEX IF NOT EXISTS idx_media_people_person ON media_people(person_id);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_media_tmdb_id ON media(tmdb_id) WHERE tmdb_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS metadata_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL UNIQUE,
    error_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    resolution_notes TEXT,
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metadata_errors_unresolved
    ON metadata_errors(media_id) WHERE resolved_at IS NULL;

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    IMAGES_PATH.mkdir(parents=True, exist_ok=True)
    (IMAGES_PATH / "posters").mkdir(exist_ok=True)
    (IMAGES_PATH / "backdrops").mkdir(exist_ok=True)
    (IMAGES_PATH / "profiles").mkdir(exist_ok=True)
    (IMAGES_PATH / "providers").mkdir(exist_ok=True)

    with get_db() as conn:
        conn.executescript(SCHEMA)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(media)").fetchall()}
        if "seasons" not in columns:
            conn.execute("ALTER TABLE media ADD COLUMN seasons TEXT")
        for column, col_type in (
            ("vote_average", "REAL"),
            ("vote_count", "INTEGER"),
            ("certification", "TEXT"),
        ):
            if column not in columns:
                conn.execute(f"ALTER TABLE media ADD COLUMN {column} {col_type}")

        person_columns = {row[1] for row in conn.execute("PRAGMA table_info(people)").fetchall()}
        for column, col_type in (
            ("biography", "TEXT"),
            ("birthday", "TEXT"),
            ("deathday", "TEXT"),
            ("place_of_birth", "TEXT"),
            ("known_for_department", "TEXT"),
        ):
            if column not in person_columns:
                conn.execute(f"ALTER TABLE people ADD COLUMN {column} {col_type}")

        _migrate_streaming_providers(conn)


def _migrate_streaming_providers(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='streaming_providers'"
    ).fetchone()
    if not row or "'free'" in row[0]:
        return

    conn.executescript(
        """
        CREATE TABLE streaming_providers_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            provider_name TEXT NOT NULL,
            logo_path TEXT,
            logo_local TEXT,
            provider_type TEXT NOT NULL CHECK(provider_type IN ('flatrate', 'rent', 'buy', 'free', 'ads')),
            region TEXT NOT NULL DEFAULT 'US',
            FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
            UNIQUE(media_id, provider_id, provider_type, region)
        );
        INSERT INTO streaming_providers_new
            SELECT * FROM streaming_providers;
        DROP TABLE streaming_providers;
        ALTER TABLE streaming_providers_new RENAME TO streaming_providers;
        """
    )


@contextmanager
def get_db():
    conn = sqlite3.connect(settings.database_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)
