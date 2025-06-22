import asyncio
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Self

from bson import ObjectId

from src.core.logger import Logger
from src.database.repositories.models.predictor_repository_models import (
    PredictorDocument,
)
from src.database.repositories.predictor_repository import PredictorRepository
from src.events.event_bus import EventBus
from src.events.event_types import MetricsEvent
from src.services.deployment_service import DeploymentService
from src.services.mappers.predictor_mapper import db_to_domain_predictor
from src.services.models.predictor_models import Prediction, Predictor, PredictorMetrics


class PredictorService(ABC):
    """
    Abstract base class for predictor services that manage machine learning model lifecycle and execution.

    This service provides a standardized interface for loading, managing, and executing predictions
    with different versions of predictors. It handles metrics collection, event publishing, and
    maintains active predictor instances with automatic performance monitoring.

    The service integrates with a repository pattern for data persistence and an event bus
    for publishing metrics and monitoring events during predictor operations.

    Attributes:
        predictor_repository (PredictorRepository): Repository for predictor data operations
        event_bus (EventBus): Event bus for publishing metrics and monitoring events
        active_predictors (dict[int, Predictor]): Dictionary mapping predictor versions to active predictor instances

    Abstract Properties:
        prediction_type (str): Unique identifier name for the predictor type

    Abstract Methods:
        _forward(predictor_input: Any) -> Prediction: Execute prediction logic for given input
        _load_predictor(path: Path, predictor_version: int) -> None: Load predictor model from specified path
    """

    @property
    @abstractmethod
    def prediction_type(self) -> str: ...

    @abstractmethod
    def _forward(self, predictor_input: Any) -> Prediction: ...

    @abstractmethod
    def _load_predictor(self, path: Path, predictor_version: int) -> None: ...

    def tags(self, predictor_version: int) -> dict[str, str]:
        return {
            "prediction_type": self.prediction_type,
            "predictor_version": str(predictor_version),
        }

    def __init__(
        self,
        predictor_repository: PredictorRepository,
        deployment_service: DeploymentService,
        event_bus: EventBus,
        logger: Logger,
    ) -> None:
        self.predictor_repository = predictor_repository
        self.deployment_service = deployment_service
        self.event_bus = event_bus
        self.logger = logger

        self._active_predictors: dict[int, Predictor] = {}

        self._initialized = False

        self._active_predictors_lock = asyncio.Lock()

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                f"{self.__class__.__name__} not initialized. "
                "Call initialize() or use create() factory method."
            )

    async def _get_active_predictors(self) -> dict[int, Predictor]:
        async with self._active_predictors_lock:
            return self._active_predictors.copy()

    async def _update_active_predictors(self) -> None:
        deployment_domain = await self.deployment_service.find_deployment_by_name(
            self.prediction_type
        )

        predictors: list[PredictorDocument] = []

        for active_predictor in deployment_domain.active_deployments:
            predictors.append(
                await self.predictor_repository.find_by_id(
                    doc_id=active_predictor.predictor_id
                )
            )

        domain_predictors = [
            db_to_domain_predictor(predictor) for predictor in predictors
        ]

        async with self._active_predictors_lock:
            self._active_predictors = {
                domain_predictor.predictor_version: domain_predictor
                for domain_predictor in domain_predictors
            }

    async def _get_predictor(self, predictor_version: int) -> Predictor | None:
        async with self._active_predictors_lock:
            return self._active_predictors.get(predictor_version)

    async def _get_predictor_by_id(self, predictor_id: ObjectId) -> Predictor | None:
        async with self._active_predictors_lock:
            for predictor in self._active_predictors.values():
                if predictor.id == predictor_id:
                    return predictor
        return None

    async def _update_predictor(self, predictor_version: int, loaded: bool) -> None:
        async with self._active_predictors_lock:
            predictor = self._active_predictors.get(predictor_version)

            if predictor is None:
                raise ValueError(
                    f"Predictor {self.prediction_type}.{predictor_version} does not exists"
                )

            if predictor.loaded == loaded:
                self.logger.warning(
                    f"Predictor {self.prediction_type}.{predictor_version} has already loaded={loaded}"
                )
                return

            predictor.loaded = loaded

    async def initialize(self) -> None:
        if self._initialized:
            return

        try:
            await self._update_active_predictors()
            self._initialized = True

        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            raise

    @classmethod
    async def create(
        cls,
        predictor_repository: PredictorRepository,
        deployment_service: DeploymentService,
        event_bus: EventBus,
        logger: Logger,
    ) -> Self:
        instance = cls(predictor_repository, deployment_service, event_bus, logger)
        await instance.initialize()
        return instance

    async def load_predictor(self, path: Path, predictor_version: int) -> None:
        self._ensure_initialized()

        if not path.exists():
            raise ValueError(f"The path {path} does not exist: cannot load predictor")

        start_time = time.perf_counter()

        try:
            self._load_predictor(path, predictor_version)
        except Exception as exc:
            self.event_bus.publish(
                MetricsEvent(
                    metric_name=PredictorMetrics.PREDICTOR_LOADING_ERROR,
                    metric_value=1,
                    tags=self.tags(predictor_version),
                )
            )
            raise ValueError(
                f"Failed to load predictor {self.prediction_type}.{predictor_version}: {exc}"
            )

        end_time = time.perf_counter()

        latency = end_time - start_time

        self.event_bus.publish(
            MetricsEvent(
                metric_name=PredictorMetrics.PREDICTOR_LOADING_LATENCY,
                metric_value=latency,
                tags=self.tags(predictor_version),
            )
        )

    async def forward(
        self, predictor_input: Any, predictor_version: int | None = None
    ) -> Any:
        self._ensure_initialized()

        if predictor_version is None:
            selected_predictor_id = (
                await self.deployment_service.select_predictor_randomly(
                    self.prediction_type
                )
            )
            predictor = await self._get_predictor_by_id(selected_predictor_id)

            if predictor is None:
                raise ValueError(
                    f"Selected predictor {selected_predictor_id} not found in active predictors"
                )

            selected_version = predictor.predictor_version
            self.logger.info(
                f"A/B testing selected predictor ID: {selected_predictor_id}, version: {selected_version}"
            )
        else:
            predictor = await self._get_predictor(predictor_version)

            if predictor is None:
                raise ValueError(
                    f"The predictor {self.prediction_type}.{predictor_version} is not active / does not exist"
                )

        if not predictor.loaded:
            await self.load_predictor(
                predictor.predictor_weights_path, predictor.predictor_version
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
                    tags=self.tags(predictor.predictor_version),
                )
            )

            self.event_bus.publish(
                MetricsEvent(
                    metric_name=PredictorMetrics.PREDICTOR_PRICE,
                    metric_value=result.price,
                    tags=self.tags(predictor.predictor_version),
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
                    tags=self.tags(predictor.predictor_version),
                )
            )
            raise
