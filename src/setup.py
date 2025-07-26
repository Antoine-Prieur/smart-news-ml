from dependency_injector.wiring import Provide, inject

from src.container import Container
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
from src.predictors.predictors.news_classification_v1 import (
    NewsClassificationPredictorV1,
)
from src.predictors.predictors.news_classification_v2 import (
    NewsClassificationPredictorV2,
)
from src.predictors.predictors.sentiment_analysis_predictor_v1 import (
    SentimentAnalysisPredictorV1,
)
from src.predictors.predictors.sentiment_analysis_predictor_v2 import (
    SentimentAnalysisPredictorV2,
)


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
        settings: Settings = Provide[Container.settings],
        event_bus: EventBus = Provide[Container.event_bus],
        articles_handler: ArticlesHandler = Provide[Container.articles_handler],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Initialize event bus and register event handlers"""
        try:
            event_bus.register_queue(settings.QUEUE_ARTICLES, 10)

            event_bus.subscribe(settings.QUEUE_ARTICLES, articles_handler)
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
    async def _setup_predictors(
        self,
        sentiment_analysis_predictor_v1: SentimentAnalysisPredictorV1 = Provide[
            Container.sentiment_analysis_predictor_v1
        ],
        sentiment_analysis_predictor_v2: SentimentAnalysisPredictorV2 = Provide[
            Container.sentiment_analysis_predictor_v2
        ],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Initialize all application predictors"""
        try:
            await sentiment_analysis_predictor_v1.setup()
            await sentiment_analysis_predictor_v2.setup()
            logger.info("Application predictors initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize predictors: {e}")
            raise

    @inject
    async def _setup_volumes(
        self,
        settings: Settings = Provide[Container.settings],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Initialize all volumes"""
        try:
            logger.info("Application volumes initialized successfully")

            settings.WEIGHTS_PATH.mkdir(parents=True, exist_ok=True)

        except Exception as e:
            logger.error(f"Failed to initialize volumes: {e}")
            raise

    @inject
    async def cleanup_resources(
        self,
        mongo_client: MongoClient = Provide[Container.mongo_client],
        event_bus: EventBus = Provide[Container.event_bus],
        sentiment_predictor_v1: SentimentAnalysisPredictorV1 = Provide[
            Container.sentiment_analysis_predictor_v1
        ],
        sentiment_predictor_v2: SentimentAnalysisPredictorV2 = Provide[
            Container.sentiment_analysis_predictor_v1
        ],
        news_classification_predictor_v1: NewsClassificationPredictorV1 = Provide[
            Container.news_classification_predictor_v1
        ],
        news_classification_predictor_v2: NewsClassificationPredictorV2 = Provide[
            Container.news_classification_predictor_v2
        ],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Cleanup resources during shutdown"""
        try:
            await sentiment_predictor_v1.manual_unload()
            await sentiment_predictor_v2.manual_unload()
            await news_classification_predictor_v1.manual_unload()
            await news_classification_predictor_v2.manual_unload()
            logger.info("Predictors unloaded")

            await event_bus.stop()
            logger.info("Event bus stopped")

            mongo_client.close()
            logger.info("Database connections closed")

            logger.info("Resource cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")

    async def setup(self) -> None:
        try:
            self.container.wire(modules=[__name__, "src.events.handlers"])

            await self._setup_volumes()
            await self._setup_database()
            await self._setup_repositories()
            await self._setup_event_system()
            await self._setup_services()
            await self._setup_predictors()

            print("🚀 ML Platform setup completed successfully!")
            print("Platform is ready to serve requests...")

        except Exception as e:
            print(f"❌ Platform setup failed: {e}")
            await self.cleanup_resources()
            raise
