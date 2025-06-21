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
                [("predictor_name", ASCENDING), ("predictor_version", ASCENDING)],
                unique=True,
                name="predictor_name_version_unique"
            ),
            IndexModel(
                [("predictor_name", ASCENDING)],
                name="predictor_name_index"
            )
        ]

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

    async def _insert_predictor(self, predictor: PredictorDocument) -> PredictorDocument:
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
        predictor_weights_path: str | Path,
    ) -> PredictorDocument:
        now = datetime.now(timezone.utc)

        if isinstance(predictor_weights_path, str):
            predictor_weights_path = Path(predictor_weights_path)

        max_version = await self.get_max_version(predictor_name)

        predictor = PredictorDocument(
            predictor_name=predictor_name,
            predictor_version=max_version + 1,
            predictor_weights_path=predictor_weights_path,
            created_at=now,
            updated_at=now,
        )

        return await self._insert_predictor(predictor)

    async def get_max_version(self, predictor_name: str) -> int:
        if not predictor_name or not predictor_name.strip():
            raise ValueError("Predictor name cannot be empty or None")

        pipeline = [
            {"$match": {"predictor_name": predictor_name}},
            {"$group": {"_id": None, "max_version": {"$max": "$predictor_version"}}}
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(1)
        
        if not result or result[0]["max_version"] is None:
            return 0
            
        return result[0]["max_version"]

    async def find_predictors_by_name(self, predictor_name: str) -> list[PredictorDocument]:
        filters: dict[str, Any] = {"predictor_name": predictor_name}
        
        cursor = self.collection.find(filters).sort("predictor_version", -1)
        docs = await cursor.to_list(None)
        
        return [self._to_model(doc) for doc in docs]
