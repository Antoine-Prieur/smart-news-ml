from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.ml_deployment_repository_models import (
    MLActiveDeploymentDocument,
    MLDeploymentDocument,
)


class MLDeploymentRepository(BaseRepository[MLDeploymentDocument]):
    COLLECTION_NAME: str = "ml_deployments"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            collection_name=self.COLLECTION_NAME,
            model_class=MLDeploymentDocument,
        )

    def _adjust_traffic_distribution(
        self,
        active_deployments: list[MLActiveDeploymentDocument],
        target_predictor_id: ObjectId,
        target_traffic: float,
    ) -> None:
        """Adjust traffic distribution among active deployments.

        Args:
            active_deployments: List of active deployments to adjust
            target_predictor_id: The predictor ID to set specific traffic for
            target_traffic: The traffic percentage to set for the target predictor
        """
        if not active_deployments:
            return

        if target_traffic > 100:
            raise ValueError(
                f"Traffic distribution cannot exceed 100%. Target traffic: {target_traffic}"
            )

        target_deployment = None
        other_deployments: list[MLActiveDeploymentDocument] = []

        for active_deployment in active_deployments:
            if active_deployment.predictor_id == target_predictor_id:
                target_deployment = active_deployment
            else:
                other_deployments.append(active_deployment)

        if not target_deployment:
            return

        target_deployment.traffic_distribution = target_traffic

        if not other_deployments:
            return

        old_target_traffic = target_deployment.traffic_distribution

        traffic_difference = target_traffic - old_target_traffic

        remaining_traffic = 100 - target_traffic

        # If there are other deployments, adjust them proportionally
        if other_deployments:
            # Calculate remaining traffic for other deployments
            remaining_traffic = 100.0 - target_traffic

            if remaining_traffic < 0:
                raise ValueError(
                    f"Traffic distribution cannot exceed 100%. Target traffic: {target_traffic}"
                )

            # If remaining traffic is 0, set all others to 0
            if remaining_traffic == 0:
                for ad in other_deployments:
                    ad.traffic_distribution = 0.0
            else:
                # Get current total of other deployments
                current_other_total = sum(
                    ad.traffic_distribution for ad in other_deployments
                )

                # If current total is 0, distribute equally
                if current_other_total == 0:
                    traffic_per_deployment = remaining_traffic / len(other_deployments)
                    for ad in other_deployments:
                        ad.traffic_distribution = traffic_per_deployment
                else:
                    # Scale proportionally to fit remaining traffic
                    scale_factor = remaining_traffic / current_other_total
                    for ad in other_deployments:
                        ad.traffic_distribution *= scale_factor
        else:
            # If this is the only deployment, it should get 100% traffic
            target_deployment.traffic_distribution = 100.0

    async def find_ml_deployment_by_name(
        self, ml_predictor_name: str
    ) -> list[MLDeploymentDocument]:
        """Find ML deployment by source name"""
        filters: dict[str, Any] = {}

        filters["predictor_name"] = ml_predictor_name

        cursor = self.collection.find(filters)
        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]

    async def insert_ml_deployment(
        self, ml_deployment: MLDeploymentDocument
    ) -> MLDeploymentDocument:
        """Insert a new ML predictor document"""
        doc_dict = self._to_document(ml_deployment)

        if doc_dict.get("_id") is None:
            doc_dict.pop("_id", None)

        result = await self.collection.insert_one(doc_dict)

        ml_deployment.id = result.inserted_id
        return ml_deployment

    async def create_ml_deployment(
        self,
        predictor_name: str,
    ) -> MLDeploymentDocument:
        """Create and insert a new ML predictor with automatic timestamps"""

        now = datetime.now(timezone.utc)

        ml_deployment = MLDeploymentDocument(
            predictor_name=predictor_name,
            created_at=now,
            updated_at=now,
        )

        return await self.insert_ml_deployment(ml_deployment)
