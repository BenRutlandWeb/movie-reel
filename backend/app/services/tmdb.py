import httpx

from app.config import settings

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

# Alternate TMDB search queries for titles that differ from folder/library names.
MOVIE_SEARCH_ALIASES: dict[str, list[str]] = {
    "live free or die hard": ["Die Hard 4.0", "Die Hard 4"],
    "die hard 4.0": ["Live Free or Die Hard", "Die Hard 4"],
    "die hard 4": ["Live Free or Die Hard", "Die Hard 4.0"],
}


class TMDBClient:
    def __init__(self) -> None:
        self.api_key = settings.tmdb_api_key
        self.region = settings.tmdb_region

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, path: str, params: dict | None = None) -> dict | list | None:
        if not self.configured:
            return None
        params = params or {}
        params["api_key"] = self.api_key
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{TMDB_BASE}{path}", params=params)
            if response.status_code != 200:
                return None
            return response.json()

    async def _search_movie_query(self, title: str, year: int | None) -> dict | None:
        params: dict = {"query": title}
        if year is not None:
            params["year"] = year
        data = await self._get("/search/movie", params)
        if not data or not data.get("results"):
            return None
        return data["results"][0]

    async def search_movie(self, title: str, year: int | None) -> dict | None:
        queries = [title]
        aliases = MOVIE_SEARCH_ALIASES.get(title.casefold())
        if aliases:
            queries.extend(alias for alias in aliases if alias not in queries)

        for query in queries:
            result = await self._search_movie_query(query, year)
            if result:
                return result
            if year is not None:
                result = await self._search_movie_query(query, None)
                if result:
                    return result
        return None

    async def search_tv(self, title: str, year: int | None) -> dict | None:
        results = await self.search_tv_multi(title, year, limit=1)
        return results[0] if results else None

    async def search_movie_multi(
        self, query: str, year: int | None = None, *, limit: int = 10
    ) -> list[dict]:
        params: dict = {"query": query}
        if year is not None:
            params["year"] = year
        data = await self._get("/search/movie", params)
        if not data or not data.get("results"):
            if year is not None:
                return await self.search_movie_multi(query, None, limit=limit)
            return []
        return data["results"][:limit]

    async def search_tv_multi(
        self, query: str, year: int | None = None, *, limit: int = 10
    ) -> list[dict]:
        params: dict = {"query": query}
        if year:
            params["first_air_date_year"] = year
        data = await self._get("/search/tv", params)
        if not data or not data.get("results"):
            return []
        return data["results"][:limit]

    def format_search_result(self, item: dict, media_type: str) -> dict:
        if media_type == "movie":
            release = item.get("release_date", "")
            year = int(release[:4]) if release else None
            title = item.get("title") or item.get("original_title") or ""
        else:
            first_air = item.get("first_air_date", "")
            year = int(first_air[:4]) if first_air else None
            title = item.get("name") or item.get("original_name") or ""
        return {
            "tmdb_id": item.get("id"),
            "title": title,
            "year": year,
            "media_type": media_type,
            "overview": item.get("overview"),
            "poster_url": self.image_url(item.get("poster_path"), "w185"),
        }

    async def get_movie_details(self, tmdb_id: int) -> dict | None:
        return await self._get(
            f"/movie/{tmdb_id}",
            {"append_to_response": "credits,watch/providers,release_dates"},
        )

    async def get_tv_details(self, tmdb_id: int) -> dict | None:
        return await self._get(
            f"/tv/{tmdb_id}",
            {"append_to_response": "credits,watch/providers,content_ratings"},
        )

    async def get_tv_season(self, tmdb_id: int, season_number: int) -> dict | None:
        return await self._get(f"/tv/{tmdb_id}/season/{season_number}")

    async def get_tv_episode(
        self, tmdb_id: int, season_number: int, episode_number: int
    ) -> dict | None:
        return await self._get(
            f"/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}",
            {"append_to_response": "credits"},
        )

    @staticmethod
    def extract_uk_certification(details: dict, media_type: str) -> str | None:
        if media_type == "movie":
            for country in details.get("release_dates", {}).get("results", []):
                if country.get("iso_3166_1") != "GB":
                    continue
                for release in country.get("release_dates", []):
                    cert = release.get("certification")
                    if cert:
                        return cert
            return None
        for rating in details.get("content_ratings", {}).get("results", []):
            if rating.get("iso_3166_1") == "GB":
                return rating.get("rating") or None
        return None

    async def get_person_details(self, tmdb_id: int) -> dict | None:
        return await self._get(f"/person/{tmdb_id}")

    def image_url(self, path: str | None, size: str = "w500") -> str | None:
        if not path:
            return None
        return f"{TMDB_IMAGE_BASE}/{size}{path}"


tmdb_client = TMDBClient()
