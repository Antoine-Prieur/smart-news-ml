import random

from bson import ObjectId

from src.database.repositories.deployment_repository import DeploymentRepository
from src.services.mappers.deployment_mapper import (
    db_to_domain_deployment,
    domain_to_db_active_deployment,
)
from src.services.models.deployment_models import Deployment


class DeploymentService:
    def __init__(self, deployment_repository: DeploymentRepository) -> None:
        self.deployment_repository = deployment_repository

    def _redistribute_traffic(
        self, distributions: dict[ObjectId, float], traffic_to_redistribute: float
    ) -> dict[ObjectId, float]:
        """Redistribute traffic among predictors proportionally."""
        if not distributions or traffic_to_redistribute == 0:
            return distributions.copy()

        sorted_items = sorted(distributions.items(), key=lambda x: x[1])
        result: dict[ObjectId, float] = {}
        remaining_traffic = traffic_to_redistribute
        remaining_predictors = len(sorted_items)

        for predictor_id, current_traffic in sorted_items:
            avg_adjustment = remaining_traffic / remaining_predictors

            if current_traffic >= avg_adjustment:
                result[predictor_id] = current_traffic - avg_adjustment
                remaining_traffic -= avg_adjustment
            else:
                result[predictor_id] = 0
                remaining_traffic -= current_traffic

            remaining_predictors -= 1

        return result

    def calculate_traffic_distribution(
        self,
        current_distributions: dict[ObjectId, float],
        target_predictor_id: ObjectId,
        target_traffic: float,
    ) -> dict[ObjectId, float]:
        """Calculate new traffic distribution

        Returns:
            New traffic distribution mapping predictor_id -> traffic_percentage
        """
        if target_traffic < 0:
            raise ValueError(f"Traffic must be >= 0%. Got: {target_traffic}")
        if target_traffic > 100:
            raise ValueError(f"Traffic cannot exceed 100%. Got: {target_traffic}")

        if target_predictor_id not in current_distributions:
            return current_distributions.copy()

        old_target_traffic = current_distributions[target_predictor_id]
        traffic_delta = target_traffic - old_target_traffic

        other_predictors = {
            pid: traffic
            for pid, traffic in current_distributions.items()
            if pid != target_predictor_id
        }

        if not other_predictors:
            return {target_predictor_id: target_traffic}

        adjusted_others = self._redistribute_traffic(other_predictors, -traffic_delta)

        return {target_predictor_id: target_traffic, **adjusted_others}

    async def adjust_traffic_distribution(
        self,
        deployment_id: ObjectId,
        target_predictor_id: ObjectId,
        target_traffic: float,
    ) -> None:
        """Adjust traffic distribution among active deployments."""
        deployment_doc = await self.deployment_repository.find_by_id(deployment_id)

        deployment_domain = db_to_domain_deployment(deployment_doc)

        if not deployment_domain.active_deployments:
            return

        current_distributions = {
            dep.predictor_id: dep.traffic_percentage
            for dep in deployment_domain.active_deployments
        }

        new_distributions = self.calculate_traffic_distribution(
            current_distributions, target_predictor_id, target_traffic
        )

        for deployment in deployment_domain.active_deployments:
            if deployment.predictor_id in new_distributions:
                deployment.traffic_percentage = new_distributions[
                    deployment.predictor_id
                ]

        active_deployment_docs = [
            domain_to_db_active_deployment(active_deployment)
            for active_deployment in deployment_domain.active_deployments
        ]

        await self.deployment_repository.update_active_deployments(
            deployment_id, active_deployment_docs
        )

    async def find_deployment_by_name(self, prediction_type: str) -> Deployment:
        deployment_doc = await self.deployment_repository.find_deployment_by_name(
            prediction_type
        )
        return db_to_domain_deployment(deployment_doc)

    async def select_predictor_randomly(self, prediction_type: str) -> ObjectId:
        deployment_doc = await self.deployment_repository.find_deployment_by_name(
            prediction_type
        )
        deployment_domain = db_to_domain_deployment(deployment_doc)

        if not deployment_domain.active_deployments:
            raise ValueError(f"No active deployments for predictor: {prediction_type}")

        cumulative_weights: list[float] = []
        predictor_ids: list[ObjectId] = []
        cumulative_sum = 0

        for active_deployment in deployment_domain.active_deployments:
            cumulative_sum += active_deployment.traffic_percentage
            cumulative_weights.append(cumulative_sum)
            predictor_ids.append(active_deployment.predictor_id)

        random_value = random.uniform(0, 100)

        for i, weight in enumerate(cumulative_weights):
            if random_value <= weight:
                return predictor_ids[i]

        return predictor_ids[-1]
