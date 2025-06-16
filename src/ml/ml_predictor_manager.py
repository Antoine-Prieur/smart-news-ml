import time
from abc import ABC, abstractmethod
from typing import Any, Literal

from bson import ObjectId

from src.database.repositories.ml_metrics_repository import MLMetricsRepository
from src.database.repositories.ml_predictor_repository import MLPredictorRepository
from src.database.repositories.models.ml_metrics_repository_models import (
    MLMetricsDocument,
)
from src.ml.mappers.ml_predictor_mapper import db_to_domain_ml_predictor
from src.ml.ml_predictor_models import MLPredictor


class MLPredictorManager(ABC):
    METRICS_LITERAL = Literal["latency", "predictor_loading", "error"]

    @property
    @abstractmethod
    def predictor_name(self) -> str: ...

    async def __init__(
        self,
        ml_predictor_repository: MLPredictorRepository,
        ml_metrics_repository: MLMetricsRepository,
    ) -> None:
        self.ml_predictor_repository = ml_predictor_repository
        self.ml_metrics_repository = ml_metrics_repository

        self.active_ml_predictors = await self._load_active_predictors()

    async def _load_active_predictors(self) -> dict[int, MLPredictor]:
        ml_predictors = await self.ml_predictor_repository.find_ml_predictor_by_name(
            self.predictor_name, active=True
        )
        ml_domain_predictors = [
            db_to_domain_ml_predictor(ml_predictor) for ml_predictor in ml_predictors
        ]

        return {
            ml_domain_predictor.predictor_version: ml_domain_predictor
            for ml_domain_predictor in ml_domain_predictors
        }

    @abstractmethod
    def _forward(self, predictor_input: Any) -> Any: ...

    async def _save_ml_metric(
        self,
        metric_name: METRICS_LITERAL,
        metric_value: float,
        ml_predictor_id: ObjectId,
    ) -> MLMetricsDocument:
        return await self.ml_metrics_repository.create_ml_metric(
            metric_name, metric_value, ml_predictor_id
        )

    async def forward(self, predictor_input: Any, predictor_version: int) -> Any:
        """Public method that handles latency tracking automatically"""
        if predictor_version not in self.active_ml_predictors:
            raise ValueError(
                f"The predictor {self.predictor_name}.{predictor_version} is not active / does not exist"
            )

        ml_predictor_id = self.active_ml_predictors[predictor_version].id

        start_time = time.perf_counter()

        try:
            result = self._forward(predictor_input)
            end_time = time.perf_counter()
            latency = end_time - start_time

            # Save latency to database
            await self._save_ml_metric("latency", latency, ml_predictor_id)

            return result
        except Exception:
            end_time = time.perf_counter()
            latency = end_time - start_time
            await self._save_ml_metric("error", 1, ml_predictor_id)
            raise
