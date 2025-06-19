import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

from bson import ObjectId

from src.database.repositories.metrics_repository import MetricsRepository
from src.database.repositories.models.metrics_repository_models import MetricsDocument
from src.database.repositories.predictor_repository import PredictorRepository
from src.services.mappers.predictor_mapper import db_to_domain_predictor
from src.services.models.predictor_models import Predictor


class PredictorService(ABC):
    METRICS_LITERAL = Literal["latency", "predictor_loading", "error"]

    @property
    @abstractmethod
    def predictor_name(self) -> str: ...

    @abstractmethod
    def _forward(self, predictor_input: Any) -> Any: ...

    @abstractmethod
    def _load_predictor(self, path: Path) -> Any: ...

    async def __init__(
        self,
        predictor_repository: PredictorRepository,
        metrics_repository: MetricsRepository,
    ) -> None:
        self.predictor_repository = predictor_repository
        self.metrics_repository = metrics_repository

        self.active_predictors = await self._load_active_predictors()

    async def _load_active_predictors(self) -> dict[int, Predictor]:
        predictors = await self.predictor_repository.find_predictor_by_name(
            self.predictor_name, active=True
        )
        domain_predictors = [
            db_to_domain_predictor(predictor) for predictor in predictors
        ]

        return {
            domain_predictor.predictor_version: domain_predictor
            for domain_predictor in domain_predictors
        }

    async def _save_metric(
        self,
        metric_name: METRICS_LITERAL,
        metric_value: float,
        predictor_id: ObjectId,
    ) -> MetricsDocument:
        return await self.metrics_repository.create_metric(
            metric_name, metric_value, predictor_id
        )

    async def forward(self, predictor_input: Any, predictor_version: int) -> Any:
        """Public method that handles latency tracking automatically"""
        if predictor_version not in self.active_predictors:
            raise ValueError(
                f"The predictor {self.predictor_name}.{predictor_version} is not active / does not exist"
            )

        predictor_id = self.active_predictors[predictor_version].id

        start_time = time.perf_counter()

        try:
            result = self._forward(predictor_input)
            end_time = time.perf_counter()
            latency = end_time - start_time

            await self._save_metric("latency", latency, predictor_id)

            return result
        except Exception:
            end_time = time.perf_counter()
            latency = end_time - start_time

            await self._save_metric("error", 1, predictor_id)
            raise
