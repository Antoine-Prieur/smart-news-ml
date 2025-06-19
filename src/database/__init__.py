import os
from typing import Any

from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient

from src.database.client import MongoClient
from src.database.repositories.articles_repository import ArticleRepository
from src.database.repositories.metrics_repository import MetricsRepository

# Global instances
_mongo_client: MongoClient | None = None

_article_repository: ArticleRepository | None = None
_metrics_repository: MetricsRepository | None = None


def get_mongo_client() -> MongoClient:
    """Get MongoDB client instance"""
    global _mongo_client

    if _mongo_client is None:
        mongo_url = os.getenv("MONGO_URL")
        database_name = os.getenv("MONGO_DATABASE_NAME")

        if mongo_url is None:
            raise ValueError("MONGO_URL is not defined")

        if database_name is None:
            raise ValueError("MONGO_DATABASE_NAME is not defined")

        motor_client: AgnosticClient[Any] = AsyncIOMotorClient(mongo_url)
        _mongo_client = MongoClient(motor_client, database_name)

    return _mongo_client


def get_article_repository() -> ArticleRepository:
    """Get ArticleRepository instance"""
    global _article_repository
    if _article_repository is None:
        mongo_client = get_mongo_client()
        _article_repository = ArticleRepository(mongo_client)

    return _article_repository


def get_metrics_repository() -> MetricsRepository:
    """Get MetricsRepository instance"""
    global _metrics_repository
    if _metrics_repository is None:
        mongo_client = get_mongo_client()
        _metrics_repository = MetricsRepository(mongo_client)

    return _metrics_repository
