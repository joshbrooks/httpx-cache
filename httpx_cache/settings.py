from pydantic import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    meta_db: str = "cache.db"
    content_path: Path = Path("cache")
