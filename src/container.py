import redis.asyncio as redis
from dependency_injector import containers, providers
from motor.motor_asyncio import AsyncIOMotorClient

from src.core.logger import Logger
from src.core.settings import Settings
from src.database.client import MongoClient
from src.database.repositories.articles_predictions_repository import (
    ArticlePredictionsRepository,
)
from src.database.repositories.articles_repository import ArticleRepository
from src.database.repositories.metrics_repository import MetricsRepository
from src.database.repositories.predictor_repository import PredictorRepository
from src.events.event_bus import EventBus
from src.events.handlers.articles_handler import ArticlesHandler
from src.predictors.predictors.sentiment_analysis_predictor_v1 import (
    SentimentAnalysisPredictorV1,
)
from src.predictors.predictors.sentiment_analysis_predictor_v2 import (
    SentimentAnalysisPredictorV2,
)
from src.services.article_service import ArticleService
from src.services.predictor_service import PredictorService


class Container(containers.DeclarativeContainer):
    # Core
    settings = providers.Singleton(Settings)
    logger = providers.Singleton(Logger, settings=settings)

    # Database
    motor_client = providers.Singleton(
        AsyncIOMotorClient,
        host=settings.provided.MONGO_URL,
    )

    mongo_client = providers.Singleton(
        MongoClient, client=motor_client, settings=settings, logger=logger
    )

    # Repositories
    articles_repository = providers.Singleton(
        ArticleRepository, mongo_client=mongo_client
    )
    metrics_repository = providers.Singleton(
        MetricsRepository, mongo_client=mongo_client
    )
    predictor_repository = providers.Singleton(
        PredictorRepository, mongo_client=mongo_client
    )

    article_predictions_repository = providers.Singleton(
        ArticlePredictionsRepository, mongo_client=mongo_client
    )

    # Services
    predictor_service = providers.Singleton(
        PredictorService,
        settings=settings,
        predictor_repository=predictor_repository,
        metrics_repository=metrics_repository,
    )

    # Event
    redis_client = providers.Singleton(
        redis.from_url,  # type: ignore
        url=settings.provided.REDIS_URL,
        decode_responses=False,
    )
    event_bus = providers.Singleton(EventBus, logger=logger, redis=redis_client)

    # Predictors
    sentiment_analysis_predictor_v1 = providers.Singleton(
        SentimentAnalysisPredictorV1,
        predictor_service=predictor_service,
        metrics_repository=metrics_repository,
        logger=logger,
    )

    sentiment_analysis_predictor_v2 = providers.Singleton(
        SentimentAnalysisPredictorV2,
        predictor_service=predictor_service,
        metrics_repository=metrics_repository,
        logger=logger,
    )

    # Services which depend on predictors
    article_service = providers.Singleton(
        ArticleService,
        logger=logger,
        sentiment_predictor_v1=sentiment_analysis_predictor_v1,
        sentiment_predictor_v2=sentiment_analysis_predictor_v2,
        article_predictions_repository=article_predictions_repository,
        predictor_service=predictor_service,
    )

    # Handlers
    articles_handler = providers.Singleton(
        ArticlesHandler, article_service=article_service
    )
