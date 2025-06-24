# Quick and dirty script to test sentiment analysis

import asyncio

from bson import ObjectId
from dependency_injector.wiring import Provide, inject

from src.container import Container
from src.core.logger import Logger
from src.database.repositories.articles_predictions_repository import (
    ArticlePredictionsRepository,
)
from src.database.repositories.articles_repository import ArticleRepository
from src.database.repositories.metrics_repository import MetricsRepository
from src.events.event_bus import EventBus
from src.events.handlers.metrics_handler import MetricsHandler
from src.services.predictors.sentiment_analysis_predictor_v1 import (
    SentimentAnalysisPredictorV1,
)


class SentimentAnalysisTest:
    def __init__(self):
        self.container = Container()
        self.container.wire(modules=[__name__])

    @inject
    async def test_sentiment_prediction(
        self,
        article_id: str,
        articles_repository: ArticleRepository = Provide[Container.articles_repository],
        article_predictions_repository: ArticlePredictionsRepository = Provide[
            Container.article_predictions_repository
        ],
        sentiment_predictor: SentimentAnalysisPredictorV1 = Provide[
            Container.sentiment_analysis_predictor_v1
        ],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Test the complete sentiment analysis prediction pipeline"""

        try:
            article_object_id = ObjectId(article_id)
            logger.info(f"Testing sentiment analysis for article: {article_object_id}")

            logger.info("Fetching article from database...")
            article = await articles_repository.find_by_id(article_object_id)
            logger.info(f"Found article: '{article.title}' by {article.author}")

            input_text = article.title or ""
            if article.description:
                input_text = f"{article.title}. {article.description}"

            if not input_text.strip():
                logger.error("Article has no title or description to analyze")
                return

            logger.info(
                f"Analyzing text: '{input_text[:100]}{'...' if len(input_text) > 100 else ''}'"
            )

            logger.info("Initializing sentiment analysis predictor...")
            await sentiment_predictor.initialize()

            logger.info("Running sentiment analysis prediction...")
            prediction_result = await sentiment_predictor.forward(input_text)

            logger.info("Prediction result:")
            logger.info(f"  - Sentiment: {prediction_result.prediction_value}")
            logger.info(
                f"  - Confidence: {prediction_result.prediction_confidence:.3f}"
            )
            logger.info(f"  - Price: ${prediction_result.price:.6f}")

            predictor = await sentiment_predictor.predictor_service.find_predictor_by_type_and_version(
                prediction_type=sentiment_predictor.prediction_type,
                predictor_version=sentiment_predictor.predictor_version,
            )

            if not predictor:
                logger.error("Predictor not found in database")
                return

            logger.info("Storing prediction in database...")
            stored_prediction = await article_predictions_repository.upsert_prediction(
                article_id=article_object_id,
                prediction_type=sentiment_predictor.prediction_type,
                predictor_id=predictor.id,
                prediction_value=prediction_result.prediction_value,
                prediction_confidence=prediction_result.prediction_confidence,
                set_as_selected=True,
            )

            logger.info(f"Prediction stored with ID: {stored_prediction.id}")

            logger.info("Verifying stored prediction...")
            retrieved_prediction = await article_predictions_repository.find_by_article_id_and_prediction_type(
                article_id=article_object_id,
                prediction_type=sentiment_predictor.prediction_type,
            )

            selected_prediction = retrieved_prediction.selected_prediction

            logger.info("Verified stored prediction:")
            logger.info(
                f"  - Selected predictor: {retrieved_prediction.selected_prediction}"
            )
            logger.info(f"  - Sentiment: {selected_prediction.prediction_value}")
            logger.info(f"  - Confidence: {selected_prediction.prediction_confidence}")

            logger.info("✅ Sentiment analysis test completed successfully!")

        except ValueError as e:
            logger.error(f"Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during sentiment analysis test: {e}")
            raise

    @inject
    async def list_available_articles(
        self,
        articles_repository: ArticleRepository = Provide[Container.articles_repository],
        logger: Logger = Provide[Container.logger],
    ) -> list[str]:
        """List available articles in the database"""
        result: list[str] = []
        try:
            logger.info("Fetching available articles...")
            articles = await articles_repository.find_all()

            if not articles:
                logger.info("No articles found in database")
                return []

            logger.info(f"Found {len(articles)} articles:")
            for article in articles:
                logger.info(f"  - {article.id}: '{article.title}' by {article.author}")
                if article.id is not None:
                    result.append(str(article.id))

        except Exception as e:
            logger.error(f"Error listing articles: {e}")

        return result

    @inject
    async def display_metrics(
        self,
        metrics_repository: MetricsRepository = Provide[Container.metrics_repository],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Display all metrics generated during the test run"""
        try:
            logger.info("📊 Displaying metrics generated during test run:")

            tags = {"prediction_type": "sentiment_analysis", "predictor_version": "1"}

            metric_types = [
                "predictor_loading_latency",
                "predictor_latency",
                "predictor_price",
                "predictor_error",
                "predictor_loading_error",
            ]

            total_metrics = 0
            for metric_name in metric_types:
                metrics = await metrics_repository.find_metrics_by_name(
                    metric_name, tags
                )
                if metrics:
                    total_metrics += len(metrics)
                    latest_metric = max(metrics, key=lambda m: m.created_at)
                    logger.info(
                        f"  📈 {metric_name}: {latest_metric.metric_value} (count: {len(metrics)})"
                    )
                    if metric_name == "predictor_latency":
                        logger.info(
                            f"     └─ Latest prediction took {latest_metric.metric_value:.4f} seconds"
                        )
                    elif metric_name == "predictor_price":
                        logger.info(
                            f"     └─ Latest cost: ${latest_metric.metric_value:.6f}"
                        )
                    elif metric_name == "predictor_loading_latency":
                        logger.info(
                            f"     └─ Model loading took {latest_metric.metric_value:.4f} seconds"
                        )
                    elif metric_name in ["predictor_error", "predictor_loading_error"]:
                        logger.info(
                            f"     └─ Error count: {int(latest_metric.metric_value)}"
                        )

            logger.info(f"📊 Total metrics recorded: {total_metrics}")

        except Exception as e:
            logger.error(f"Error displaying metrics: {e}")

    @inject
    async def setup_and_run(
        self,
        article_id: str | None = None,
        event_bus: EventBus = Provide[Container.event_bus],
        metrics_handler: MetricsHandler = Provide[Container.metrics_handler],
        logger: Logger = Provide[Container.logger],
    ) -> None:
        """Setup the container and run the test"""
        try:
            await self.container.articles_repository().setup()
            await self.container.article_predictions_repository().setup()
            await self.container.metrics_repository().setup()

            logger.info("Starting event bus and registering metrics handler...")
            await event_bus.start()
            event_bus.subscribe(metrics_handler)
            logger.info("Event system initialized")

            if article_id:
                await self.test_sentiment_prediction(article_id)
            else:
                article_ids = await self.list_available_articles()
                for article_id in article_ids:
                    await self.test_sentiment_prediction(article_id)

            logger.info("Waiting for metrics to be processed...")

            await self.display_metrics()

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
        finally:
            logger.info("Stopping event bus and draining remaining events...")
            await event_bus.stop()
            logger.info("Event bus stopped and queue drained")

            mongo_client = self.container.mongo_client()
            mongo_client.close()
            print("🧹 Cleanup completed")


async def main():
    """Main function to run the sentiment analysis test"""
    test = SentimentAnalysisTest()

    await test.setup_and_run()


if __name__ == "__main__":
    asyncio.run(main())
