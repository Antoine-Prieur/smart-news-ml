from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

    async def find_predictor(
        self, predictor_name: str, predictor_version: int
    ) -> PredictorDocument:
        """Find  predictors by source name"""
        filters: dict[str, Any] = {}

        filters["predictor_name"] = predictor_name
        filters["predictor_version"] = predictor_version

        doc = await self.collection.find_one(filters)

        if not doc:
            raise ValueError(
                f"Predictor with name {predictor_name} and version {predictor_version} not found"
            )

        return self._to_model(doc)

    async def insert_predictor(self, predictor: PredictorDocument) -> PredictorDocument:
        """Insert a new  predictor document"""
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
    ) -> PredictorDocument:
        """Create and insert a new  predictor with automatic timestamps"""
        from pathlib import Path

        now = datetime.now(timezone.utc)

        if isinstance(predictor_weights_path, str):
            predictor_weights_path = Path(predictor_weights_path)

        predictor = PredictorDocument(
            predictor_name=predictor_name,
            predictor_version=predictor_version,
            predictor_weights_path=predictor_weights_path,
            created_at=now,
            updated_at=now,
        )

        return await self.insert_predictor(predictor)
