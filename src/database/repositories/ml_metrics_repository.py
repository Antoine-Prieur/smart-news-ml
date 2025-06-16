from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.ml_metrics_repository_models import (
    MLMetricsDocument,
)


class MLMetricsRepository(BaseRepository[MLMetricsDocument]):
    COLLECTION_NAME: str = "ml_metrics"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            collection_name=self.COLLECTION_NAME,
            model_class=MLMetricsDocument,
        )

    async def find_ml_metrics_by_model_predictor_id(
        self, metric_name: str, model_predictor_id: ObjectId | str
    ) -> list[MLMetricsDocument]:
        """Find ML models by source name"""
        if isinstance(model_predictor_id, str):
            model_predictor_id = ObjectId(model_predictor_id)

        filters: dict[str, Any] = {}

        filters["metric_name"] = metric_name
        filters["model_predictor_id"] = model_predictor_id

        cursor = self.collection.find(filters)
        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]

    async def insert_ml_metric(self, ml_metric: MLMetricsDocument) -> MLMetricsDocument:
        """Insert a new ML metric document"""
        doc_dict = self._to_document(ml_metric)

        if doc_dict.get("_id") is None:
            doc_dict.pop("_id", None)

        result = await self.collection.insert_one(doc_dict)

        ml_metric.id = result.inserted_id
        return ml_metric

    async def create_ml_metric(
        self,
        metric_name: str,
        metric_value: float,
        model_predictor_id: ObjectId | str,
    ) -> MLMetricsDocument:
        """Create and insert a new ML metric with automatic timestamps"""
        if isinstance(model_predictor_id, str):
            model_predictor_id = ObjectId(model_predictor_id)

        now = datetime.now(timezone.utc)

        ml_metric = MLMetricsDocument(
            ml_predictor_id=model_predictor_id,
            metric_name=metric_name,
            metric_value=metric_value,
            created_at=now,
            updated_at=now,
        )

        return await self.insert_ml_metric(ml_metric)
