import logging

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NAME: str = "smart-news-ml"
    LOGGING_LEVEL: int = logging.INFO

    MONGO_URL: str = "mongodb://admin:password123@localhost:27017"
    MONGO_DATABASE_NAME: str = "news"
