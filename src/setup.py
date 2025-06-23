from dependency_injector.wiring import Provide, inject

from src.container import Container
from src.core.logger import Logger
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


class MLPlatformSetup:
    def __init__(self):
        self.container = Container()

    @inject
    async def _setup_database(
        self,
        mongo_client: MongoClient = Provide[Container.mongo_client],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Initialize database connection and test connectivity"""
        try:
            await mongo_client.test_connection()
            logger.info("Database connection established successfully")

            collections = await mongo_client.list_collection_names()
            logger.info(f"Available collections: {collections}")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    @inject
    async def _setup_repositories(
        self,
        articles_repository: ArticleRepository = Provide[Container.articles_repository],
        deployment_repository: DeploymentRepository = Provide[
            Container.deployment_repository
        ],
        metrics_repository: MetricsRepository = Provide[Container.metrics_repository],
        predictor_repository: PredictorRepository = Provide[
            Container.predictor_repository
        ],
        article_predictions_repository: ArticlePredictionsRepository = Provide[
            Container.article_predictions_repository
        ],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Initialize all repositories and create database indexes"""
        repositories = [
            ("Articles", articles_repository),
            ("Deployment", deployment_repository),
            ("Metrics", metrics_repository),
            ("Predictor", predictor_repository),
            ("Article Predictions", article_predictions_repository),
        ]

        for name, repo in repositories:
            try:
                await repo.setup()
                logger.info(f"{name} repository initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize {name} repository: {e}")
                raise

    @inject
    async def _setup_event_system(
        self,
        event_bus: EventBus = Provide[Container.event_bus],
        metrics_handler: MetricsHandler = Provide[Container.metrics_handler],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Initialize event bus and register event handlers"""
        try:
            await event_bus.start()
            logger.info("Event system initialized and started")

            event_bus.subscribe(metrics_handler)
            logger.info("Event handlers registered")

        except Exception as e:
            logger.error(f"Failed to initialize event system: {e}")
            raise

    @inject
    async def _setup_services(
        self,
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Initialize all application services"""
        try:
            logger.info("Application services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    @inject
    async def _cleanup_resources(
        self,
        mongo_client: MongoClient = Provide[Container.mongo_client],
        event_bus: EventBus = Provide[Container.event_bus],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Cleanup resources during shutdown"""
        try:
            await event_bus.stop()
            logger.info("Event bus stopped")

            mongo_client.close()
            logger.info("Database connections closed")

            logger.info("Resource cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")

    async def setup(self) -> None:
        """
        Complete platform setup sequence.

        Initializes all components in the correct dependency order:
        1. Dependency injection container and wiring
        2. Database connection and testing
        3. Repository initialization and index creation
        4. Event system setup and handler registration
        5. Service initialization
        """
        try:
            self.container.wire(modules=[__name__, "src.events.handlers"])

            await self._setup_database()
            await self._setup_repositories()
            await self._setup_event_system()
            await self._setup_services()

            print("🚀 ML Platform setup completed successfully!")
            print("Platform is ready to serve requests...")

        except Exception as e:
            print(f"❌ Platform setup failed: {e}")
            await self._cleanup_resources()
            raise
