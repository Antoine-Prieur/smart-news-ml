from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NAME: str = "smart-news-ml"

    MONGO_URL: str = "mongodb://admin:password123@localhost:27017"
    MONGO_DATABASE_NAME: str = "news"
