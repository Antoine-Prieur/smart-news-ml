from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.deployment_repository_models import (
    ActiveDeploymentDocument,
    DeploymentDocument,
)
from src.utils.traffic_distribution_utils import validate_traffic_distribution


class DeploymentRepository(BaseRepository[DeploymentDocument]):
    COLLECTION_NAME: str = "deployments"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            collection_name=self.COLLECTION_NAME,
            model_class=DeploymentDocument,
        )

    async def find_deployment_by_name(
        self, predictor_name: str
    ) -> list[DeploymentDocument]:
        """Find  deployment by source name"""
        filters: dict[str, Any] = {}

        filters["predictor_name"] = predictor_name

        cursor = self.collection.find(filters)
        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]

    async def insert_deployment(
        self, deployment: DeploymentDocument
    ) -> DeploymentDocument:
        """Insert a new  predictor document"""
        doc_dict = self._to_document(deployment)

        if doc_dict.get("_id") is None:
            doc_dict.pop("_id", None)

        result = await self.collection.insert_one(doc_dict)

        deployment.id = result.inserted_id
        return deployment

    async def create_deployment(
        self,
        predictor_name: str,
    ) -> DeploymentDocument:
        """Create and insert a new  predictor with automatic timestamps"""

        now = datetime.now(timezone.utc)

        deployment = DeploymentDocument(
            predictor_name=predictor_name,
            created_at=now,
            updated_at=now,
        )

        return await self.insert_deployment(deployment)

    async def update_active_deployments(
        self,
        deployment_id: str | ObjectId,
        active_deployments: list[ActiveDeploymentDocument],
    ) -> DeploymentDocument:
        """Update active deployments and return updated document"""
        if isinstance(deployment_id, str):
            deployment_id = ObjectId(deployment_id)

        traffic_distribution = [
            deployment.traffic_percentage for deployment in active_deployments
        ]
        validate_traffic_distribution(traffic_distribution)

        now = datetime.now(timezone.utc)
        active_deployments_dict = [
            deployment.model_dump() for deployment in active_deployments
        ]

        result = await self.collection.find_one_and_update(
            {"_id": deployment_id},
            {
                "$set": {
                    "active_deployments": active_deployments_dict,
                    "updated_at": now,
                }
            },
            return_document=True,
        )

        if not result:
            raise ValueError(f"Deployment with id {deployment_id} not found")

        return self._to_model(result)
