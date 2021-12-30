from pathlib import Path
import httpx

import pytest
from pytest_httpx import HTTPXMock

from httpx_cache.tables import Request
import logging

logger = logging.getLogger("httpx_cache.tests")


def test_cache(httpx_mock: HTTPXMock):

    path = Path("httpx_cache") / "data" / "sample" / "iatiregistry.org" / "action" / "package_search.json"
    url = "https://iatiregistry.org/api/3/action/package_search"
    with open(path) as content:
        httpx_mock.add_response(url=url, content=content.read().encode())

    Request.from_url(url)


@pytest.mark.asyncio
async def test_acache(httpx_mock: HTTPXMock):

    path = Path("httpx_cache") / "data" / "sample" / "iatiregistry.org" / "action" / "package_search.json"
    url = "https://iatiregistry.org/api/3/action/package_search"
    with open(path) as content:
        httpx_mock.add_response(url=url, content=content.read().encode())

    request_awaitable = Request.afrom_url(url)
    r = await request_awaitable  # type: Request
    r.json()

    cached_request = Request.get(url)
    logger.debug(cached_request)
    print(cached_request)


def test_uncached(httpx_mock: HTTPXMock):
    url = "https://iatiregistry.org/api/3/action/package_search-does-not-exist"
    cached_request = Request.get(f"{url}-does-not-exist")
    assert not cached_request


def test_cache_forbidden(httpx_mock: HTTPXMock):
    """
    Expect an error if a non success http code received
    """

    path = Path("httpx_cache") / "data" / "sample" / "iatiregistry.org" / "action" / "package_search.json"
    url = "https://iatiregistry.org/api/3/action/package_search"
    with open(path) as content:
        httpx_mock.add_response(url=url, content=content.read().encode(), status_code=403)

    with pytest.raises(httpx.HTTPStatusError):
        Request.from_url(url)
