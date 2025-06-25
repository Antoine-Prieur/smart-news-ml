import asyncio
from typing import Any

from src.core.logger import Logger
from src.database.repositories.articles_predictions_repository import (
    ArticlePredictionsRepository,
)
from src.predictors.predictors.sentiment_analysis_predictor_v1 import (
    SentimentAnalysisPredictorV1,
)
from src.services.mappers.articles_mapper import db_to_domain_article_predictions
from src.services.models.article_models import ArticlePredictions, ArticleQueueMessage


class ArticleService:
    def __init__(
        self,
        logger: Logger,
        sentiment_predictor: SentimentAnalysisPredictorV1,
        article_predictions_repository: ArticlePredictionsRepository,
        concurrent_predictions: int = 1,
    ):
        self.logger = logger

        self.sentiment_predictor = sentiment_predictor
        self.article_predictions_repository = article_predictions_repository
        self.concurrent_predictions = concurrent_predictions

    def parse_message(self, raw_data: Any) -> ArticleQueueMessage:
        return ArticleQueueMessage(**raw_data)

    async def make_prediction_and_save(
        self, article: ArticleQueueMessage
    ) -> ArticlePredictions:
        text_to_analyze = article.title or article.description or ""
        sentiment_prediction = await self.sentiment_predictor.forward(text_to_analyze)

        predictor = self.sentiment_predictor.get_predictor()

        stored_prediction = await self.article_predictions_repository.upsert_prediction(
            article_id=article.id,
            prediction_type=predictor.prediction_type,
            predictor_id=predictor.id,
            prediction_value=sentiment_prediction.prediction_value,
            prediction_confidence=sentiment_prediction.prediction_confidence,
            set_as_selected=True,
        )

        return db_to_domain_article_predictions(stored_prediction)

    async def process_articles(self, messages: list[Any]) -> list[ArticlePredictions]:
        articles = [self.parse_message(msg) for msg in messages]

        await self.sentiment_predictor.load_predictor()

        try:
            semaphore = asyncio.Semaphore(self.concurrent_predictions)

            async def predict_with_semaphore(
                article: ArticleQueueMessage,
            ) -> ArticlePredictions:
                async with semaphore:
                    return await self.make_prediction_and_save(article)

            tasks = [predict_with_semaphore(article) for article in articles]
            predictions = await asyncio.gather(*tasks)

            return predictions

        finally:
            await self.sentiment_predictor.unload_predictor()
