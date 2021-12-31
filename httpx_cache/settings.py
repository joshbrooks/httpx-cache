from pathlib import Path

from pydantic import BaseSettings


class RedisSettings(BaseSettings):
    url: str = "redis://localhost"
    encoding: str = "utf-8"
    decode_responses = True


class Settings(BaseSettings):
    meta_db: str = "cache.db"
    content_path: Path = Path("cache")
    redis: RedisSettings = RedisSettings()
