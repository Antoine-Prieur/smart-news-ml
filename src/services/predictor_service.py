import random
import shutil
from pathlib import Path

from bson import ObjectId
from motor.core import AgnosticClientSession

from src.core.settings import Settings
from src.database.repositories.metrics_repository import MetricsRepository
from src.database.repositories.predictor_repository import PredictorRepository
from src.services.mappers.predictor_mapper import db_to_domain_predictor
from src.services.models.predictor_models import Predictor, PredictorMetrics


class PredictorService:
    def __init__(
        self,
        settings: Settings,
        predictor_repository: PredictorRepository,
        metrics_repository: MetricsRepository,
    ) -> None:
        self.settings = settings
        self.predictor_repository = predictor_repository
        self.metrics_repository = metrics_repository

    async def find_predictor_by_id(self, predictor_id: ObjectId | str) -> Predictor:
        if isinstance(predictor_id, str):
            predictor_id = ObjectId(predictor_id)

        predictor_document = await self.predictor_repository.find_by_id(
            doc_id=predictor_id
        )

        return db_to_domain_predictor(predictor_document)

    async def find_predictor_by_type_and_version(
        self, prediction_type: str, predictor_version: int
    ) -> Predictor | None:
        predictor_document = await self.predictor_repository.find_predictor(
            prediction_type=prediction_type, predictor_version=predictor_version
        )

        if predictor_document is None:
            return None

        return db_to_domain_predictor(predictor_document)

    async def find_predictors_by_prediction_type(
        self,
        prediction_type: str,
        only_actives: bool = False,
    ) -> list[Predictor]:
        predictor_documents = (
            await self.predictor_repository.find_predictors_by_prediction_type(
                prediction_type=prediction_type, only_actives=only_actives
            )
        )
        return [
            db_to_domain_predictor(predictor_document)
            for predictor_document in predictor_documents
        ]

    def get_predictor_weights_path(self, predictor_id: ObjectId | str) -> Path:
        if isinstance(predictor_id, ObjectId):
            predictor_id = str(predictor_id)

        return self.settings.WEIGHTS_PATH.joinpath(predictor_id)

    def copy_weights(
        self, predictor_id: ObjectId, predictor_weights_path: Path
    ) -> None:
        destination_path = self.get_predictor_weights_path(predictor_id)

        if predictor_weights_path.is_file():
            destination_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(predictor_weights_path, destination_path)
        elif predictor_weights_path.is_dir():
            shutil.copytree(
                predictor_weights_path, destination_path, dirs_exist_ok=True
            )

    async def register_predictor(
        self, predictor_weights_path: Path, prediction_type: str, predictor_version: int
    ) -> Predictor:
        if not predictor_weights_path.exists():
            raise ValueError(
                f"The weights path {predictor_weights_path} does not exist"
            )
        predictor_document = await self.predictor_repository.create_predictor(
            prediction_type, predictor_version
        )

        predictor_domain = db_to_domain_predictor(predictor_document)

        self.copy_weights(predictor_domain.id, predictor_weights_path)

        return predictor_domain

    @staticmethod
    def build_tags(prediction_type: str, predictor_version: int) -> dict[str, str]:
        return {
            "prediction_type": prediction_type,
            "predictor_version": str(predictor_version),
        }

    # A/B testing
    def _redistribute_traffic(
        self, distributions: dict[ObjectId, float], traffic_to_redistribute: float
    ) -> dict[ObjectId, float]:
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

    def _calculate_traffic_distribution(
        self,
        current_distributions: dict[ObjectId, float],
        target_predictor_id: ObjectId,
        target_traffic: float,
    ) -> dict[ObjectId, float]:
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
        target_predictor_id: ObjectId,
        target_traffic: float,
    ) -> None:
        async def transaction(session: AgnosticClientSession) -> None:
            target_predictor = db_to_domain_predictor(
                await self.predictor_repository.find_by_id(target_predictor_id)
            )

            predictor_docs = (
                await self.predictor_repository.find_predictors_by_prediction_type(
                    target_predictor.prediction_type, only_actives=True, session=session
                )
            )

            predictors = {
                db_to_domain_predictor(doc).id: db_to_domain_predictor(doc)
                for doc in predictor_docs
            }
            predictors[target_predictor.id] = target_predictor

            current_distributions = {
                predictor_id: predictor.traffic_percentage
                for predictor_id, predictor in predictors.items()
            }

            if target_predictor_id not in current_distributions:
                raise ValueError(f"Target predictor {target_predictor_id} not found")

            new_distributions = self._calculate_traffic_distribution(
                current_distributions, target_predictor_id, target_traffic
            )

            for predictor_id, new_percentage in new_distributions.items():
                await self.metrics_repository.create_metric(
                    PredictorMetrics.PREDICTOR_TRAFFIC_UPDATE,
                    new_percentage,
                    self.build_tags(
                        target_predictor.prediction_type,
                        predictors[predictor_id].predictor_version,
                    ),
                    session=session,
                )
                await self.predictor_repository.update_traffic_percentage(
                    predictor_id, new_percentage, session=session
                )

        await self.predictor_repository.start_transaction(transaction)

    async def get_predictors_and_select_randomly(
        self,
        prediction_type: str,
    ) -> tuple[list[Predictor], Predictor]:
        active_predictors = await self.find_predictors_by_prediction_type(
            prediction_type=prediction_type, only_actives=True
        )

        if not active_predictors:
            raise ValueError("No active predictors found")

        weights = [predictor.traffic_percentage for predictor in active_predictors]

        selected_predictor = random.choices(active_predictors, weights=weights, k=1)[0]

        return active_predictors, selected_predictor
