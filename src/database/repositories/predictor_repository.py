from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo import ASCENDING, IndexModel

from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.predictor_repository_models import (
    PredictorDocument,
)


class PredictorRepository(BaseRepository[PredictorDocument]):
    @property
    def collection_name(self) -> str:
        return "predictors"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            model_class=PredictorDocument,
        )

    @property
    def indexes(self) -> list[IndexModel]:
        return [
            IndexModel(
                [("prediction_type", ASCENDING), ("predictor_version", ASCENDING)],
                unique=True,
                name="prediction_type_version_unique",
            ),
            IndexModel([("prediction_type", ASCENDING)], name="prediction_type_index"),
        ]

    async def find_predictor(
        self, prediction_type: str, predictor_version: int
    ) -> PredictorDocument:
        """Find  predictors by source name"""
        filters: dict[str, Any] = {}

        filters["prediction_type"] = prediction_type
        filters["predictor_version"] = predictor_version

        doc = await self.collection.find_one(filters)

        if not doc:
            raise ValueError(
                f"Predictor with name {prediction_type} and version {predictor_version} not found"
            )

        return self._to_model(doc)

    async def _insert_predictor(
        self, predictor: PredictorDocument
    ) -> PredictorDocument:
        """Insert a new  predictor document"""
        doc_dict = self._to_document(predictor)

        if doc_dict.get("_id") is None:
            doc_dict.pop("_id", None)

        result = await self.collection.insert_one(doc_dict)

        predictor.id = result.inserted_id
        return predictor

    async def create_predictor(
        self,
        prediction_type: str,
        predictor_weights_path: str | Path,
    ) -> PredictorDocument:
        now = datetime.now(timezone.utc)

        if isinstance(predictor_weights_path, str):
            predictor_weights_path = Path(predictor_weights_path)

        max_version = await self.get_max_version(prediction_type)

        predictor = PredictorDocument(
            prediction_type=prediction_type,
            predictor_version=max_version + 1,
            predictor_weights_path=predictor_weights_path,
            created_at=now,
            updated_at=now,
        )

        return await self._insert_predictor(predictor)

    async def get_max_version(self, prediction_type: str) -> int:
        if not prediction_type or not prediction_type.strip():
            raise ValueError("Predictor name cannot be empty or None")

        pipeline = [
            {"$match": {"prediction_type": prediction_type}},
            {"$group": {"_id": None, "max_version": {"$max": "$predictor_version"}}},
        ]

        result = await self.collection.aggregate(pipeline).to_list(1)

        if not result or result[0]["max_version"] is None:
            return 0

        return result[0]["max_version"]

    async def find_predictors_by_name(
        self, prediction_type: str
    ) -> list[PredictorDocument]:
        filters: dict[str, Any] = {"prediction_type": prediction_type}

        cursor = self.collection.find(filters).sort("predictor_version", -1)
        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]
