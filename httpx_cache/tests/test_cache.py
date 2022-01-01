import logging
from pathlib import Path
from typing import Any

import aioredis
import pytest
from httpx import AsyncClient, HTTPStatusError
from pytest_httpx import HTTPXMock

from httpx_cache.tables import Request, from_url

from ..settings import Settings

settings = Settings()

logger = logging.getLogger("httpx_cache.tests")

package_path = Path("httpx_cache") / "data" / "sample" / "iatiregistry.org" / "action" / "package_search.json"
package_url = "https://iatiregistry.org/api/3/action/package_search"


@pytest.fixture
def client() -> AsyncClient:
    """
    client.aclose() after using this
    """
    client = AsyncClient()
    return client


@pytest.mark.asyncio
async def test_cache(httpx_mock: HTTPXMock, client: AsyncClient):
    """
    Test the cache with and without redis / httpx context managers
    """
    pool = await aioredis.create_redis(**settings.redis.dict())
    with open(package_path) as content:
        httpx_mock.add_response(url=package_url, content=content.read().encode())

    await from_url(package_url)
    await from_url(package_url, pool=pool)
    await from_url(package_url, client=client)
    await from_url(package_url, pool=pool, client=client)

    await Request.from_url(package_url)
    await Request.from_url(package_url, pool=pool)
    await Request.from_url(package_url, client=client)
    await Request.from_url(package_url, pool=pool, client=client)

    await client.aclose()

    cached_request = await Request.get(package_url, pool)
    logger.debug(cached_request)
    print(cached_request)
    pool.close()


@pytest.mark.asyncio
async def test_uncached(httpx_mock: HTTPXMock):
    url = "https://iatiregistry.org/api/3/action/package_search-does-not-exist"
    cached_request = await Request.get(f"{url}-does-not-exist")
    assert not cached_request
    pool = await aioredis.create_redis(**settings.redis.dict())
    cached_request = await Request.get(f"{url}-does-not-exist", pool=pool)
    assert not cached_request
    pool.close()


@pytest.mark.asyncio
async def test_cache_forbidden(httpx_mock: HTTPXMock):
    """
    Expect an error if a non success http code received
    """

    path = Path("httpx_cache") / "data" / "sample" / "iatiregistry.org" / "action" / "package_search.json"
    url = "https://iatiregistry.org/api/3/action/package_search"
    with open(package_path) as content:
        httpx_mock.add_response(url=package_url, content=content.read().encode(), status_code=403)
    async with AsyncClient() as client:
        with pytest.raises(HTTPStatusError):
            await Request.from_url(package_url)
