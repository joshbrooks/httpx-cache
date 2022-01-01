from pathlib import Path

from pydantic import BaseSettings


class Redisv2Settings(BaseSettings):
    url: str = "redis://localhost"  # 2.0 +
    encoding: str = "utf-8"
    decode_responses = True


class RedisSettings(BaseSettings):
    address: str = "redis://localhost"


class Settings(BaseSettings):
    meta_db: str = "cache.db"
    content_path: Path = Path("cache")
    redis: RedisSettings = RedisSettings()
