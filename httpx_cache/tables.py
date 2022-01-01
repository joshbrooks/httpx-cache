from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

import aiofiles
import aioredis
import httpx
from httpx import AsyncClient
from pydantic import BaseModel, Field

from .settings import Settings

logger = logging.getLogger("httpx_cache.tables")


timeout = httpx.Timeout(10.0, connect=60.0)
settings = Settings()


def nowutc():
    return datetime.now(timezone.utc)


class Request(BaseModel):

    url: str
    headers: List[Tuple[str, str]]
    date: datetime = Field(default_factory=nowutc)

    encoding: Optional[str]
    apparent_encoding: Optional[str]
    charset_encoding: Optional[str]

    @property
    def path(self) -> Path:
        """
        Return the filests
        """
        file_hash = hashlib.md5(str(self.url).encode()).hexdigest()[:8]
        logger.debug(file_hash)
        os.makedirs(settings.content_path, exist_ok=True)
        return settings.content_path / f"{file_hash}.gz"

    @classmethod
    async def from_response(cls, response: httpx.Response, pool: Any) -> Request:
        response.raise_for_status()
        instance = cls(
            url=f"{response.url}",
            headers=[(h, response.headers[h]) for h in response.headers],
            encoding=response.encoding,
            apparent_encoding=response.apparent_encoding,
            charset_encoding=response.charset_encoding,
        )
        logger.debug("Setting content")
        await instance.save(response, pool)
        return instance

    @classmethod
    async def from_url(cls, url: str, *, pool: Optional[Any] = None, client: Optional[AsyncClient] = None) -> Request:

        if not pool:

            pool = await aioredis.create_redis(**settings.redis.dict())
            try:
                result = await cls.from_url(url, pool=pool, client=client)
            except Exception as E:
                pool.close()
                raise

            pool.close()

            return result

        if not client:
            async with AsyncClient() as client:
                result = await cls.from_url(url, pool=pool, client=client)
                return result

        logger.debug("Async Caching content of %s", url)
        response = await client.get(url)
        instance = await cls.from_response(response, pool)
        return instance

    async def get_content(self) -> bytes:
        async with aiofiles.open(self.path, mode="rb") as f:
            content = await f.read()
            decompressed = gzip.decompress(content)
            return decompressed

    async def set_content(self, response) -> None:
        async with aiofiles.open(self.path, mode="wb") as f:
            content = response.content  # type: bytes
            await f.write(gzip.compress(content))
            return

    def del_content(self):
        os.remove(self.path)

    async def set_metadata(self, pool: Any):
        """
        Save the URL and metadata to a redis db
        """
        await pool.set(self.url, self.json())

    async def save(self, response, pool: Any):
        await self.set_content(response)
        await self.set_metadata(pool=pool)

    @staticmethod
    async def get(url: str, pool: Optional[Any] = None) -> Optional[Request]:
        if not pool:
            pool = await aioredis.create_redis(**settings.redis.dict())
            try:
                request = await Request.get(url, pool=pool)
            except:
                pool.close()
                raise
            pool.close()
            return request
        content = await pool.get(url)
        if content:
            return Request(**json.loads(content))
        return None


def from_url(url: str, *, pool: Optional[Any] = None, client: Optional[AsyncClient] = None) -> Request:
    return Request.from_url(url, pool=pool, client=client)
