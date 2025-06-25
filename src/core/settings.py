import logging
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NAME: str = "smart-news-ml"
    LOGGING_LEVEL: int = logging.INFO

    MONGO_URL: str = "mongodb://admin:password123@localhost:27017"
    MONGO_DATABASE_NAME: str = "news"

    MIGRATION_STATE_PATH: Path = Path("/app/data/migration_state.json")
    WEIGHTS_PATH: Path = Path("/app/data/weights/")

    REDIS_URL: str = "redis://127.0.0.1:6379"
