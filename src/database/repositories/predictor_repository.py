from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.core import AgnosticClientSession
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
        self,
        prediction_type: str,
        predictor_version: int,
        session: AgnosticClientSession | None = None,
    ) -> PredictorDocument | None:
        """Find predictor by source name and version"""
        filters: dict[str, Any] = {}

        filters["prediction_type"] = prediction_type
        filters["predictor_version"] = predictor_version

        doc = await self.collection.find_one(filters, session=session)

        if not doc:
            return None

        return self._to_model(doc)

    async def _insert_predictor(
        self, predictor: PredictorDocument, session: AgnosticClientSession | None = None
    ) -> PredictorDocument:
        """Insert a new  predictor document"""
        doc_dict = self._to_document(predictor)

        if doc_dict.get("_id") is None:
            doc_dict.pop("_id", None)

        result = await self.collection.insert_one(doc_dict, session=session)

        predictor.id = result.inserted_id
        return predictor

    async def _create_predictor(
        self,
        prediction_type: str,
        predictor_description: str,
        predictor_version: int,
        session: AgnosticClientSession | None = None,
    ) -> PredictorDocument:
        now = datetime.now(timezone.utc)

        max_version: int = 0
        newest_predictor = await self.get_newest_predictor(prediction_type)

        if newest_predictor:
            max_version = newest_predictor.predictor_version

        if predictor_version <= max_version:
            raise ValueError(
                f"Cannot decrease version number for {prediction_type}: current max version is {max_version}, trying to create version {predictor_version}"
            )

        predictor = PredictorDocument(
            prediction_type=prediction_type,
            predictor_description=predictor_description,
            predictor_version=predictor_version,
            created_at=now,
            updated_at=now,
        )

        return await self._insert_predictor(predictor, session=session)

    async def create_predictor(
        self,
        prediction_type: str,
        predictor_description: str,
        predictor_version: int,
        session: AgnosticClientSession | None = None,
    ) -> PredictorDocument:
        if session is not None:
            return await self._create_predictor(
                prediction_type, predictor_description, predictor_version, session
            )

        async def transaction(session: AgnosticClientSession) -> PredictorDocument:
            return await self._create_predictor(
                prediction_type, predictor_description, predictor_version, session
            )

        return await self.mongo_client.start_transaction(transaction)

    async def get_newest_predictor(
        self, prediction_type: str, session: AgnosticClientSession | None = None
    ) -> PredictorDocument | None:
        cursor = (
            self.collection.find({"prediction_type": prediction_type}, session=session)
            .sort("predictor_version", -1)
            .limit(1)
        )

        docs = await cursor.to_list(1)

        if not docs:
            return None

        return self._to_model(docs[0])

    async def find_predictors_by_prediction_type(
        self,
        prediction_type: str,
        only_actives: bool = False,
        session: AgnosticClientSession | None = None,
    ) -> list[PredictorDocument]:
        filters: dict[str, Any] = {"prediction_type": prediction_type}

        if only_actives:
            filters["traffic_percentage"] = {"$gt": 0}

        cursor = self.collection.find(filters, session=session).sort(
            "predictor_version", -1
        )
        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]

    async def update_traffic_percentage(
        self,
        predictor_id: ObjectId | str,
        traffic_percentage: float,
        session: AgnosticClientSession | None = None,
    ) -> PredictorDocument:
        from datetime import datetime, timezone

        result = await self.collection.find_one_and_update(
            {"_id": predictor_id},
            {
                "$set": {
                    "traffic_percentage": traffic_percentage,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=True,
            session=session,
        )

        if not result:
            raise ValueError(f"Predictor with id {predictor_id} not found")

        return self._to_model(result)

    async def validate_traffic_distribution(
        self, prediction_type: str, session: AgnosticClientSession | None = None
    ) -> bool:
        pipeline = [
            {"$match": {"prediction_type": prediction_type}},
            {"$group": {"_id": None, "total_traffic": {"$sum": "$traffic_percentage"}}},
        ]

        result = await self.collection.aggregate(pipeline, session=session).to_list(1)

        if not result:
            return True

        total_traffic = result[0]["total_traffic"]
        return abs(total_traffic - 100.0) < 1e-6
