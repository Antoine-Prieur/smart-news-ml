from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.predictor_repository_models import (
    MLPredictorDocument,
)


class MLPredictorRepository(BaseRepository[MLPredictorDocument]):
    COLLECTION_NAME: str = "predictors"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            collection_name=self.COLLECTION_NAME,
            model_class=MLPredictorDocument,
        )

    async def find_predictor_by_name(
        self, predictor_name: str, active: bool | None = None
    ) -> list[MLPredictorDocument]:
        """Find ML predictors by source name"""
        filters: dict[str, Any] = {}

        filters["predictor_name"] = predictor_name

        if active is not None:
            filters["active"] = active

        cursor = self.collection.find(filters)
        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]

    async def insert_predictor(
        self, predictor: MLPredictorDocument
    ) -> MLPredictorDocument:
        """Insert a new ML predictor document"""
        doc_dict = self._to_document(predictor)

        if doc_dict.get("_id") is None:
            doc_dict.pop("_id", None)

        result = await self.collection.insert_one(doc_dict)

        predictor.id = result.inserted_id
        return predictor

    async def create_predictor(
        self,
        predictor_name: str,
        predictor_version: int,
        predictor_weights_path: str | Path,
        traffic_percentage: float = 0,
        active: bool = True,
    ) -> MLPredictorDocument:
        """Create and insert a new ML predictor with automatic timestamps"""
        from pathlib import Path

        now = datetime.now(timezone.utc)

        if isinstance(predictor_weights_path, str):
            predictor_weights_path = Path(predictor_weights_path)

        predictor = MLPredictorDocument(
            predictor_name=predictor_name,
            predictor_version=predictor_version,
            predictor_weights_path=predictor_weights_path,
            active=active,
            created_at=now,
            updated_at=now,
        )

        return await self.insert_predictor(predictor)
