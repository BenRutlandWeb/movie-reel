import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_LIMITS = httpx.Limits(max_connections=4, max_keepalive_connections=2)

TRANSIENT_ERRORS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
    OSError,
)

MAX_RETRIES = 4
RETRY_BASE_DELAY = 2.0


async def get_http_client() -> httpx.AsyncClient:
    global _client
    async with _client_lock:
        if _client is None or _client.is_closed:
            _client = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                limits=DEFAULT_LIMITS,
                follow_redirects=True,
            )
        return _client


async def close_http_client() -> None:
    global _client
    async with _client_lock:
        if _client is not None and not _client.is_closed:
            await _client.aclose()
        _client = None


async def request_with_retry(
    method: str,
    url: str,
    *,
    timeout: httpx.Timeout | None = None,
    **kwargs,
) -> httpx.Response:
    client = await get_http_client()
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            return await client.request(method, url, timeout=timeout or DEFAULT_TIMEOUT, **kwargs)
        except TRANSIENT_ERRORS as exc:
            last_exc = exc
            delay = RETRY_BASE_DELAY * (2**attempt)
            logger.warning(
                "HTTP %s %s failed (attempt %d/%d): %s — retrying in %.1fs",
                method,
                url,
                attempt + 1,
                MAX_RETRIES,
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc
