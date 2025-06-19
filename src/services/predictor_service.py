import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.database.repositories.predictor_repository import PredictorRepository
from src.events.event_bus import EventBus
from src.events.event_types import MetricsEvent
from src.services.mappers.predictor_mapper import db_to_domain_predictor
from src.services.models.predictor_models import Prediction, Predictor, PredictorMetrics


class PredictorService(ABC):
    @property
    @abstractmethod
    def predictor_name(self) -> str: ...

    @abstractmethod
    def _forward(self, predictor_input: Any) -> Prediction: ...

    @abstractmethod
    def _load_predictor(self, path: Path, predictor_version: int) -> None: ...

    def tags(self, predictor_version: int) -> dict[str, str]:
        return {
            "predictor_name": self.predictor_name,
            "predictor_version": str(predictor_version),
        }

    async def __init__(
        self, predictor_repository: PredictorRepository, event_bus: EventBus
    ) -> None:
        self.predictor_repository = predictor_repository
        self.event_bus = event_bus

        self.active_predictors = await self._get_active_predictors()

    async def _get_active_predictors(self) -> dict[int, Predictor]:
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

    async def load_predictor(self, path: Path, predictor_version: int) -> None:
        if not path.exists():
            raise ValueError(f"The path {path} does not exist: cannot load predictor")

        start_time = time.perf_counter()
        self._load_predictor(path, predictor_version)
        end_time = time.perf_counter()

        latency = end_time - start_time

        self.event_bus.publish(
            MetricsEvent(
                metric_name=PredictorMetrics.PREDICTOR_LOADING_LATENCY,
                metric_value=latency,
                tags=self.tags(predictor_version),
            )
        )

    async def forward(self, predictor_input: Any, predictor_version: int) -> Any:
        """Public method that handles latency tracking automatically"""
        if predictor_version not in self.active_predictors:
            raise ValueError(
                f"The predictor {self.predictor_name}.{predictor_version} is not active / does not exist"
            )

        start_time = time.perf_counter()

        try:
            result = self._forward(predictor_input)
            end_time = time.perf_counter()
            latency = end_time - start_time

            self.event_bus.publish(
                MetricsEvent(
                    metric_name=PredictorMetrics.PREDICTOR_LATENCY,
                    metric_value=latency,
                    tags=self.tags(predictor_version),
                )
            )

            self.event_bus.publish(
                MetricsEvent(
                    metric_name=PredictorMetrics.PREDICTOR_PRICE,
                    metric_value=result.price,
                    tags=self.tags(predictor_version),
                )
            )

            return result

        except Exception:
            end_time = time.perf_counter()
            latency = end_time - start_time

            self.event_bus.publish(
                MetricsEvent(
                    metric_name=PredictorMetrics.PREDICTOR_ERROR,
                    metric_value=1,
                    tags=self.tags(predictor_version),
                )
            )
            raise
