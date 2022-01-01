import logging
from pathlib import Path

import aioredis
import pytest
from aioredis.client import Redis
from httpx import AsyncClient, HTTPStatusError
from pytest_httpx import HTTPXMock

from httpx_cache.tables import Request

from ..settings import Settings

settings = Settings()

logger = logging.getLogger("httpx_cache.tests")


@pytest.fixture
def pool() -> Redis:
    return aioredis.from_url(**settings.redis.dict())


@pytest.mark.asyncio
async def test_cache(httpx_mock: HTTPXMock, pool: Redis):
    path = Path("httpx_cache") / "data" / "sample" / "iatiregistry.org" / "action" / "package_search.json"
    url = "https://iatiregistry.org/api/3/action/package_search"
    with open(path) as content:
        httpx_mock.add_response(url=url, content=content.read().encode())
    async with AsyncClient() as client:
        await Request.from_url(url, pool, client)


@pytest.mark.asyncio
async def test_acache(httpx_mock: HTTPXMock, pool):
    pool = await aioredis.from_url(**settings.redis.dict())
    path = Path("httpx_cache") / "data" / "sample" / "iatiregistry.org" / "action" / "package_search.json"
    url = "https://iatiregistry.org/api/3/action/package_search"
    with open(path) as content:
        httpx_mock.add_response(url=url, content=content.read().encode())
    async with AsyncClient() as client:
        request_awaitable = Request.from_url(url, pool, client)
        r = await request_awaitable  # type: Request
        r.json()

    cached_request = await Request.get(url, pool)
    logger.debug(cached_request)
    print(cached_request)


@pytest.mark.asyncio
async def test_uncached(httpx_mock: HTTPXMock, pool: Redis):
    url = "https://iatiregistry.org/api/3/action/package_search-does-not-exist"
    cached_request = await Request.get(f"{url}-does-not-exist", pool)
    assert not cached_request


@pytest.mark.asyncio
async def test_cache_forbidden(httpx_mock: HTTPXMock, pool: Redis):
    """
    Expect an error if a non success http code received
    """

    path = Path("httpx_cache") / "data" / "sample" / "iatiregistry.org" / "action" / "package_search.json"
    url = "https://iatiregistry.org/api/3/action/package_search"
    with open(path) as content:
        httpx_mock.add_response(url=url, content=content.read().encode(), status_code=403)
    async with AsyncClient() as client:
        with pytest.raises(HTTPStatusError):
            await Request.from_url(url, pool, client)
