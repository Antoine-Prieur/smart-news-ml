from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, IndexModel

from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.article_predictions_repository_models import (
    ArticlePredictionsDocument,
    PredictionDocument,
)


class ArticlePredictionsRepository(BaseRepository[ArticlePredictionsDocument]):
    @property
    def collection_name(self) -> str:
        return "article_predictions"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            model_class=ArticlePredictionsDocument,
        )

    @property
    def indexes(self) -> list[IndexModel]:
        return [
            IndexModel(
                [("article_id", ASCENDING)],
                name="article_id",
            ),
            IndexModel(
                [("article_id", ASCENDING), ("prediction_type", ASCENDING)],
                unique=True,
                name="article_id_prediction_type_unique",
            ),
        ]

    async def find_by_article_id(
        self, article_id: ObjectId | str
    ) -> list[ArticlePredictionsDocument]:
        if isinstance(article_id, str):
            article_id = ObjectId(article_id)

        cursor = self.collection.find({"article_id": article_id})

        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]

    async def find_by_article_id_and_prediction_type(
        self, article_id: ObjectId | str, prediction_type: str
    ) -> ArticlePredictionsDocument:
        if isinstance(article_id, str):
            article_id = ObjectId(article_id)

        doc = await self.collection.find_one(
            {"article_id": article_id, "prediction_type": prediction_type}
        )

        if not doc:
            raise ValueError(
                f"Article prediction with article_id {article_id} and prediction type {prediction_type} not found"
            )

        return self._to_model(doc)

    async def upsert_prediction(
        self,
        article_id: ObjectId | str,
        prediction_type: str,
        predictor_id: ObjectId | str,
        prediction_value: Any,
        prediction_confidence: float | None = None,
        set_as_selected: bool = True,
    ) -> ArticlePredictionsDocument:
        """Insert or update a prediction for an article"""
        if isinstance(article_id, str):
            article_id = ObjectId(article_id)

        if isinstance(predictor_id, str):
            predictor_id = ObjectId(predictor_id)

        now = datetime.now(timezone.utc)

        prediction_doc = PredictionDocument(
            prediction_confidence=prediction_confidence,
            prediction_value=prediction_value,
        )

        update_doc: dict[str, Any] = {
            "$set": {
                f"predictions.{predictor_id}": prediction_doc.model_dump(),
                "updated_at": now,
            },
            "$setOnInsert": {
                "article_id": article_id,
                "prediction_type": prediction_type,
                "created_at": now,
            },
        }

        if set_as_selected:
            update_doc["$set"]["selected_prediction"] = predictor_id

        result = await self.collection.find_one_and_update(
            {"article_id": article_id, "prediction_type": prediction_type},
            update_doc,
            upsert=True,
            return_document=True,
        )

        return self._to_model(result)
