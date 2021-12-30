from __future__ import annotations

import gzip
import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
import dbm
import httpx
from pydantic import BaseModel, Field
import json
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
    def from_response(cls, response: httpx.Response) -> Request:
        response.raise_for_status()
        instance = cls(
            url=f"{response.url}",
            headers=[(h, response.headers[h]) for h in response.headers],
            encoding=response.encoding,
            apparent_encoding=response.apparent_encoding,
            charset_encoding=response.charset_encoding,
        )
        logger.debug("Setting content")
        instance.save(response)
        return instance

    @classmethod
    def from_url(cls, url: str, client: httpx.Client = None):
        logger.debug("Caching content of %s", url)
        if client:
            return cls.from_response(client.get(url))
        return cls.from_response(httpx.get(url))

    @classmethod
    async def afrom_url(cls, url: str, client: Optional[httpx.AsyncClient] = None) -> Request:
        logger.debug("Async Caching content of %s", url)

        if client:
            response = await client.get(url)
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
        return cls.from_response(response)

    def get_content(self) -> bytes:
        with gzip.open(self.path, "rb") as f:
            file_content = f.read()
        return file_content

    def set_content(self, response) -> None:
        content = response.content  # type: bytes
        with gzip.open(self.path, "wb") as f:
            f.write(content)
            return

    def del_content(self):
        os.remove(self.path)

    content = property(get_content, set_content, del_content, "Derived path of the given response instance")

    def set_metadata(self):
        """
        Save the URL and metadata to a dbm file
        """
        with dbm.open(settings.meta_db, "c") as db:
            db[self.url] = self.json()

    def save(self, response):
        self.set_content(response)
        self.set_metadata()

    @staticmethod
    def get(url: str) -> Optional[Request]:
        with dbm.open(settings.meta_db, "c") as db:
            content = db.get(url, None)
        if not content:
            return None
        return Request(**json.loads(content))
