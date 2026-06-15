# Movie Reel

A lightweight, self-hosted app for browsing your **physical** movie and TV show collection. Import folder names like `The Matrix (1999)`, fetch metadata and streaming availability, and browse only what you own — no discovery of new releases.

## Features

- Browse movies and TV shows from your collection only
- SQLite database (no external DB server)
- Metadata from [TMDB](https://www.themoviedb.org/) (posters, overviews, cast, crew, genres)
- **Where to watch** — streaming providers for your region
- Local image caching
- Actors and directors link to other titles in your collection
- Import / export JSON for backups and transfers

## Quick start

Get a free TMDB key at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).

### Run from published image (no clone)

After the repo is on GitHub and the [Publish Docker image](.github/workflows/docker-publish.yml) workflow has run, you only need compose and a `.env` file:

```bash
mkdir movie-reel && cd movie-reel
curl -o docker-compose.yml https://raw.githubusercontent.com/BenRutlandWeb/movie-reel/main/docker-compose.yml
echo "TMDB_API_KEY=your_key_here" > .env
docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080).

To pin a release, change the image tag in `docker-compose.yml` (e.g. `ghcr.io/benrutlandweb/movie-reel:v1.0.0`).

**First-time publish:** GitHub Actions pushes to `ghcr.io` on every push to `main`/`master` and on version tags (`v1.0.0`, etc.). New GHCR packages are private by default — open the package under your GitHub profile → **Package settings** → **Change visibility** → **Public** so others can pull without logging in.

### Build from source (development)

1. Clone the repo and copy the environment files:

   ```bash
   cp .env.example .env
   cp docker-compose.override.yml.example docker-compose.override.yml
   ```

2. Start with Docker Compose (override builds from source):

   ```bash
   docker compose up -d --build
   ```

3. Open [http://localhost:8080](http://localhost:8080)

Data (SQLite DB and cached images) is stored in `./data`.

## Importing your collection

**Option A — UI:** Go to **Import / Export** and upload a JSON file.

**Option B — API (stubs + fetch metadata):**

```bash
curl -X POST http://localhost:8080/api/media/import \
  -H "Content-Type: application/json" \
  -d @movies.json
```

The `fetch_metadata` field (default `true`) controls whether TMDB is queried during import.

**Option C — API (full export format):**

```bash
curl -X POST http://localhost:8080/api/media/export/import \
  -H "Content-Type: application/json" \
  -d @backup.json
```

## Export

Export your full collection (metadata, people, providers) from the UI or:

```bash
curl http://localhost:8080/api/media/export/all -o backup.json
```

Copy `./data` to another machine to transfer the database and images directly.

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## Configuration

| Variable        | Default              | Description                    |
|----------------|----------------------|--------------------------------|
| `TMDB_API_KEY` | (empty)              | TMDB API key for metadata      |
| `TMDB_REGION`  | `US`                 | Region for streaming providers |
| `DATABASE_PATH`| `/data/movie-reel.db` | SQLite database path           |
| `IMAGES_PATH`  | `/data/images`       | Cached image storage           |

Without a TMDB key, you can still import stubs and browse titles — metadata and streaming info won't be fetched until you add a key and refresh items.

## API overview

| Endpoint                      | Description              |
|------------------------------|--------------------------|
| `GET /api/media`             | List collection          |
| `GET /api/media/{id}`        | Media detail             |
| `GET /api/people/{id}`       | Person + their titles    |
| `POST /api/media/import`       | Import title stubs       |
| `GET /api/media/export/all`  | Export collection        |
| `POST /api/media/export/import` | Import export file    |
| `POST /api/media/{id}/refresh`  | Re-fetch TMDB metadata |

## License

MIT
