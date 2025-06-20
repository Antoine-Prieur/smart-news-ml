from dependency_injector import containers, providers
from motor.motor_asyncio import AsyncIOMotorClient

from src.core.logger import Logger
from src.core.settings import Settings
from src.database.client import MongoClient
from src.database.repositories.articles_repository import ArticleRepository
from src.database.repositories.deployment_repository import DeploymentRepository
from src.database.repositories.metrics_repository import MetricsRepository
from src.database.repositories.predictor_repository import PredictorRepository


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)

    logger = providers.Singleton(Logger, settings=settings)

    mongo_client = providers.Singleton(
        MongoClient,
        motor_client=providers.Singleton(
            AsyncIOMotorClient,
            host=settings.provided.MONGO_URL,
        ),
        database_name=settings.provided.MONGO_DATABASE_NAME,
    )

    articles_repository = providers.Singleton(
        ArticleRepository, mongo_client=mongo_client
    )
    deployments_repository = providers.Singleton(
        DeploymentRepository, mongo_client=mongo_client
    )
    metrics_repository = providers.Singleton(
        MetricsRepository, mongo_client=mongo_client
    )
    predictors_repository = providers.Singleton(
        PredictorRepository, mongo_client=mongo_client
    )
