import asyncio
from typing import Any, Awaitable

from src.core.logger import Logger
from src.database.repositories.articles_predictions_repository import (
    ArticlePredictionsRepository,
)
from src.events.handlers.articles_handler import ArticleEvent
from src.predictors.base_predictor import BasePredictor
from src.predictors.predictors.news_classification_v1 import (
    NewsClassificationPredictorV1,
)
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
    SENTIMENT_PREDICTION_TYPE = "sentiment_analysis"
    NEWS_CLASSIFICATION_PREDICTION_TYPE = "news_classification"

    def __init__(
        self,
        logger: Logger,
        sentiment_predictor_v1: SentimentAnalysisPredictorV1,
        sentiment_predictor_v2: SentimentAnalysisPredictorV2,
        news_classification_predictor_v1: NewsClassificationPredictorV1,
        article_predictions_repository: ArticlePredictionsRepository,
        predictor_service: PredictorService,
        concurrent_predictions: int = 1,
    ):
        self.logger = logger

        self.sentiment_predictors: dict[int, BasePredictor] = {
            sentiment_predictor_v1.predictor_version: sentiment_predictor_v1,
            sentiment_predictor_v2.predictor_version: sentiment_predictor_v2,
        }

        self.news_classification_predictors: dict[int, BasePredictor] = {
            news_classification_predictor_v1.predictor_version: news_classification_predictor_v1
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
        text_to_analyze = f"{article.title or ''} {article.description or ''}".strip()

        if not text_to_analyze:
            self.logger.warning(f"No text to analyze for article {article.id}")
            raise ValueError(f"No text available for analysis in article {article.id}")

        prediction = await predictor_instance.forward(text_to_analyze)

        stored_prediction = await self.article_predictions_repository.upsert_prediction(
            article_id=article.id,
            prediction_type=predictor.prediction_type,
            predictor_id=predictor.id,
            prediction_value=prediction.prediction_value,
            prediction_confidence=prediction.prediction_confidence,
            set_as_selected=selected_predictor,
        )

        return db_to_domain_article_predictions(stored_prediction)

    async def _process_prediction_type(
        self,
        articles: list[ArticleEvent],
        prediction_type: str,
        predictor_instances_map: dict[int, BasePredictor],
    ) -> list[ArticlePredictions]:
        """Process articles for a specific prediction type."""
        active_predictors = (
            await self.predictor_service.find_predictors_by_prediction_type(
                prediction_type=prediction_type, only_actives=True
            )
        )

        predictor_instances: list[tuple[Predictor, BasePredictor]] = []

        for predictor in active_predictors:
            predictor_instance = predictor_instances_map.get(
                predictor.predictor_version
            )

            if not predictor_instance:
                self.logger.warning(
                    f"Trying to make a prediction using an unknown predictor {prediction_type}.{predictor.predictor_version}"
                )
                continue

            predictor_instances.append((predictor, predictor_instance))

        if not predictor_instances:
            self.logger.warning(
                f"No valid predictor instances found for {prediction_type}"
            )
            return []

        semaphore = asyncio.Semaphore(self.concurrent_predictions)

        async def predict_with_semaphore(
            article: ArticleEvent,
            predictor: Predictor,
            predictor_instance: BasePredictor,
            is_selected: bool,
        ) -> ArticlePredictions:
            async with semaphore:
                return await self._make_prediction_and_save(
                    article, predictor, predictor_instance, is_selected
                )

        tasks: list[Awaitable[Any]] = []

        for article in articles:
            selected_predictor = await self.predictor_service.get_random_predictor(
                prediction_type=prediction_type,
                active_predictors=active_predictors,
            )

            for predictor, predictor_instance in predictor_instances:
                is_selected = (
                    predictor.predictor_version == selected_predictor.predictor_version
                )
                tasks.append(
                    predict_with_semaphore(
                        article, predictor, predictor_instance, is_selected
                    )
                )

        predictions = await asyncio.gather(*tasks)
        return predictions

    async def process_articles(
        self, articles: list[ArticleEvent]
    ) -> list[ArticlePredictions]:
        if not articles:
            self.logger.warning("No articles to process")
            return []

        self.logger.info(f"Received {len(articles)} articles...")

        all_predictions: list[ArticlePredictions] = []

        self.logger.info("Processing sentiment analysis predictions...")
        sentiment_predictions = await self._process_prediction_type(
            articles, self.SENTIMENT_PREDICTION_TYPE, self.sentiment_predictors
        )
        all_predictions.extend(sentiment_predictions)

        self.logger.info("Processing news classification predictions...")
        news_classification_predictions = await self._process_prediction_type(
            articles,
            self.NEWS_CLASSIFICATION_PREDICTION_TYPE,
            self.news_classification_predictors,
        )
        all_predictions.extend(news_classification_predictions)

        self.logger.info(
            f"Finished processing {len(articles)} articles with "
            f"{len(sentiment_predictions)} sentiment predictions and "
            f"{len(news_classification_predictions)} news classification predictions"
        )

        return all_predictions
