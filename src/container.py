from dependency_injector import containers, providers
from motor.motor_asyncio import AsyncIOMotorClient

from src.core.logger import Logger
from src.core.settings import Settings
from src.database.client import MongoClient
from src.database.repositories.articles_predictions_repository import (
    ArticlePredictionsRepository,
)
from src.database.repositories.articles_repository import ArticleRepository
from src.database.repositories.deployment_repository import DeploymentRepository
from src.database.repositories.metrics_repository import MetricsRepository
from src.database.repositories.predictor_repository import PredictorRepository
from src.events.event_bus import EventBus
from src.events.handlers.metrics_handler import MetricsHandler
from src.services.deployment_service import DeploymentService


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
        MongoClient, client=motor_client, settings=settings
    )

    # Repositories
    articles_repository = providers.Singleton(
        ArticleRepository, mongo_client=mongo_client
    )
    deployment_repository = providers.Singleton(
        DeploymentRepository, mongo_client=mongo_client
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

    # Events
    event_bus = providers.Singleton(EventBus, logger=logger)
    metrics_handler = providers.Singleton(
        MetricsHandler, metrics_repository=metrics_repository
    )

    # Services
    deployment_service = providers.Singleton(
        DeploymentService, deployment_repository=deployment_repository
    )
