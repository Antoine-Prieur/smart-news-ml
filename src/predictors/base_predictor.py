import asyncio
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.core.logger import Logger
from src.events.event_bus import EventBus
from src.events.handlers.metrics_handler import MetricsEvent
from src.services.models.predictor_models import Prediction, Predictor, PredictorMetrics
from src.services.predictor_service import PredictorService


class BasePredictor(ABC):
    @property
    @abstractmethod
    def prediction_type(self) -> str: ...

    @property
    @abstractmethod
    def predictor_version(self) -> int: ...

    @abstractmethod
    async def _forward(self, predictor_input: Any) -> Prediction: ...

    @abstractmethod
    async def _download_predictor(self) -> Path: ...

    @abstractmethod
    async def _load_predictor(self, predictor_weights_path: Path) -> None: ...

    @abstractmethod
    async def _unload_predictor(self) -> None: ...

    def __init__(
        self,
        predictor_service: PredictorService,
        event_bus: EventBus,
        logger: Logger,
    ) -> None:
        self.predictor_service = predictor_service
        self.event_bus = event_bus
        self.logger = logger

        self._initialized = False
        self._loaded = False
        self._predictor: Predictor | None = None

        self._init_lock = asyncio.Lock()
        self._load_lock = asyncio.Lock()

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                f"{self.__class__.__name__} not initialized. "
                "Call initialize() or use create() factory method."
            )

        if self._predictor is None:
            raise RuntimeError(f"{self.__class__.__name__} initialization incomplete")

    def get_predictor(self) -> Predictor:
        self._ensure_initialized()

        assert self._predictor is not None
        return self._predictor

    async def setup(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return

            self.logger.info(
                f"Initializing predictor {self.prediction_type}.{self.predictor_version}"
            )

            predictor = await self.predictor_service.find_predictor_by_type_and_version(
                prediction_type=self.prediction_type,
                predictor_version=self.predictor_version,
            )

            if predictor:
                self._predictor = predictor
                predictor_weights_path = (
                    self.predictor_service.get_predictor_weights_path(predictor.id)
                )

                if predictor_weights_path.exists():
                    self._initialized = True
                    return

                self.logger.info(
                    "Predictor found but weights missing, re-downloading..."
                )
                await self._setup_predictor_weights(predictor)
            else:
                self.logger.info("Predictor not found, registering new one...")

                weights_path = await self._download_predictor()
                predictor = await self.predictor_service.register_predictor(
                    predictor_weights_path=weights_path,
                    prediction_type=self.prediction_type,
                    predictor_version=self.predictor_version,
                )
                self._predictor = predictor

            self._initialized = True

    def tags(self, predictor_version: int) -> dict[str, str]:
        return {
            "prediction_type": self.prediction_type,
            "predictor_version": str(predictor_version),
        }

    async def _setup_predictor_weights(self, predictor: Predictor) -> None:
        try:
            weights_path = await self._download_predictor()
            self.predictor_service.copy_weights(predictor.id, weights_path)
        except Exception:
            self.logger.error(
                f"Failed to download weights for predictor {self.prediction_type}.{self.predictor_version}"
            )
            raise

    async def load_predictor(self) -> None:
        self._ensure_initialized()

        async with self._load_lock:
            if self._loaded:
                self.logger.warning(
                    f"Predictor {self.prediction_type}.{self.predictor_version} already loaded"
                )
                return

            predictor = self.get_predictor()
            predictor_weights_path = self.predictor_service.get_predictor_weights_path(
                predictor.id
            )

            if not predictor_weights_path.exists():
                raise ValueError(
                    f"The path {predictor_weights_path} does not exist: cannot load predictor"
                )

            start_time = time.perf_counter()

            try:
                await self._load_predictor(predictor_weights_path)
            except Exception as exc:
                self.event_bus.publish(
                    MetricsEvent.create_base_event(
                        metric_name=PredictorMetrics.PREDICTOR_LOADING_ERROR,
                        metric_value=1,
                        tags=self.tags(self.predictor_version),
                    )
                )
                raise ValueError(
                    f"Failed to load predictor {self.prediction_type}.{self.predictor_version}: {exc}"
                )

            end_time = time.perf_counter()

            latency = end_time - start_time

            self.event_bus.publish(
                MetricsEvent.create_base_event(
                    metric_name=PredictorMetrics.PREDICTOR_LOADING_LATENCY,
                    metric_value=latency,
                    tags=self.tags(self.predictor_version),
                )
            )
            self._loaded = True

    async def unload_predictor(self) -> None:
        self._ensure_initialized()

        async with self._load_lock:
            if not self._loaded:
                self.logger.warning(
                    f"Predictor {self.prediction_type}.{self.predictor_version} already unloaded"
                )
                return

            start_time = time.perf_counter()

            try:
                await self._unload_predictor()
            except Exception as exc:
                self.event_bus.publish(
                    MetricsEvent.create_base_event(
                        metric_name=PredictorMetrics.PREDICTOR_UNLOADING_ERROR,
                        metric_value=1,
                        tags=self.tags(self.predictor_version),
                    )
                )
                raise ValueError(
                    f"Failed to unload predictor {self.prediction_type}.{self.predictor_version}: {exc}"
                )

            end_time = time.perf_counter()

            latency = end_time - start_time

            self.event_bus.publish(
                MetricsEvent.create_base_event(
                    metric_name=PredictorMetrics.PREDICTOR_UNLOADING_LATENCY,
                    metric_value=latency,
                    tags=self.tags(self.predictor_version),
                )
            )
            self._loaded = False

    async def forward(self, predictor_input: Any) -> Any:
        self._ensure_initialized()

        if not self._loaded:
            await self.load_predictor()

        start_time = time.perf_counter()

        try:
            result = await self._forward(predictor_input)
            end_time = time.perf_counter()
            latency = end_time - start_time

            self.event_bus.publish(
                MetricsEvent.create_base_event(
                    metric_name=PredictorMetrics.PREDICTOR_LATENCY,
                    metric_value=latency,
                    tags=self.tags(self.predictor_version),
                )
            )

            self.event_bus.publish(
                MetricsEvent.create_base_event(
                    metric_name=PredictorMetrics.PREDICTOR_PRICE,
                    metric_value=result.price,
                    tags=self.tags(self.predictor_version),
                )
            )

            return result

        except Exception:
            end_time = time.perf_counter()
            latency = end_time - start_time

            self.event_bus.publish(
                MetricsEvent.create_base_event(
                    metric_name=PredictorMetrics.PREDICTOR_ERROR,
                    metric_value=1,
                    tags=self.tags(self.predictor_version),
                )
            )
            raise
