from typing import Any

from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.ml_predictor_repository_models import (
    MLPredictorDocument,
)


class MLPredictorRepository(BaseRepository[MLPredictorDocument]):
    COLLECTION_NAME: str = "ml_predictors"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            collection_name=self.COLLECTION_NAME,
            model_class=MLPredictorDocument,
        )

    async def find_ml_predictor_by_name(
        self, ml_predictor_name: str, active: bool | None = None
    ) -> list[MLPredictorDocument]:
        """Find ML models by source name"""
        filters: dict[str, Any] = {}

        filters["model_name"] = ml_predictor_name

        if active is not None:
            filters["active"] = active

        cursor = self.collection.find(filters)
        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]
