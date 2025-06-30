import asyncio

from src.core.logger import Logger
from src.database.repositories.articles_predictions_repository import (
    ArticlePredictionsRepository,
)
from src.events.handlers.articles_handler import ArticleEvent
from src.predictors.base_predictor import BasePredictor
from src.predictors.predictors.sentiment_analysis_predictor_v1 import (
    SentimentAnalysisPredictorV1,
)
from src.predictors.predictors.sentiment_analysis_predictor_v2 import (
    SentimentAnalysisPredictorV2,
)
from src.services.mappers.articles_mapper import db_to_domain_article_predictions
from src.services.models.article_models import ArticlePredictions
from src.services.models.predictor_models import Predictor
from src.services.predictor_service import PredictorService


class ArticleService:
    PREDICTION_TYPE = "sentiment_analysis"

    def __init__(
        self,
        logger: Logger,
        sentiment_predictor_v1: SentimentAnalysisPredictorV1,
        sentiment_predictor_v2: SentimentAnalysisPredictorV2,
        article_predictions_repository: ArticlePredictionsRepository,
        predictor_service: PredictorService,
        concurrent_predictions: int = 1,
    ):
        self.logger = logger

        self.sentiment_predictors: dict[int, BasePredictor] = {
            sentiment_predictor_v1.predictor_version: sentiment_predictor_v1,
            sentiment_predictor_v2.predictor_version: sentiment_predictor_v2,
        }

        self.article_predictions_repository = article_predictions_repository
        self.predictor_service = predictor_service
        self.concurrent_predictions = concurrent_predictions

    async def _make_prediction_and_save(
        self,
        article: ArticleEvent,
        predictor: Predictor,
        predictor_instance: BasePredictor,
        selected_predictor: bool,
    ) -> ArticlePredictions:
        text_to_analyze = article.title or article.description or ""

        sentiment_prediction = await predictor_instance.forward(text_to_analyze)

        stored_prediction = await self.article_predictions_repository.upsert_prediction(
            article_id=article.id,
            prediction_type=predictor.prediction_type,
            predictor_id=predictor.id,
            prediction_value=sentiment_prediction.prediction_value,
            prediction_confidence=sentiment_prediction.prediction_confidence,
            set_as_selected=selected_predictor,
        )

        return db_to_domain_article_predictions(stored_prediction)

    async def process_articles(
        self, articles: list[ArticleEvent]
    ) -> list[ArticlePredictions]:
        self.logger.info(f"Received {len(articles)} articles...")

        active_predictors, selected_predictor = (
            await self.predictor_service.get_predictors_and_select_randomly(
                self.PREDICTION_TYPE,
            )
        )

        semaphore = asyncio.Semaphore(self.concurrent_predictions)

        async def predict_with_semaphore(
            article: ArticleEvent,
            predictor: Predictor,
            predictor_instance: BasePredictor,
        ) -> ArticlePredictions:
            async with semaphore:
                return await self._make_prediction_and_save(
                    article,
                    predictor,
                    predictor_instance,
                    predictor.predictor_version == selected_predictor.predictor_version,
                )

        predictions: list[ArticlePredictions] = []

        for predictor in active_predictors:
            predictor_instance = self.sentiment_predictors.get(
                predictor.predictor_version
            )

            if not predictor_instance:
                self.logger.warning(
                    f"Trying to make a prediction using an unknown predictor {self.PREDICTION_TYPE}.{predictor.predictor_version}"
                )
                continue

            tasks = [
                predict_with_semaphore(article, predictor, predictor_instance)
                for article in articles
            ]
            predictions = await asyncio.gather(*tasks)

        self.logger.info(f"Finished processing {len(articles)} articles...")

        return predictions
