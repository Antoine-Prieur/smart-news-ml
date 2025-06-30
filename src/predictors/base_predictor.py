import asyncio
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.core.logger import Logger
from src.database.repositories.metrics_repository import MetricsRepository
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
        metrics_repository: MetricsRepository,
        logger: Logger,
        unload_timeout_seconds: int = 300,
    ) -> None:
        self.predictor_service = predictor_service
        self.metrics_repository = metrics_repository
        self.logger = logger

        self._initialized = False
        self._loaded = False

        self._init_lock = asyncio.Lock()
        self._load_lock = asyncio.Lock()

        self.unload_timeout_seconds = unload_timeout_seconds
        self._last_used: float = 0.0
        self._unload_task: asyncio.Task[Any] | None = None

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                f"{self.__class__.__name__} not initialized. "
                "Call initialize() or use create() factory method."
            )

    async def get_predictor(self) -> Predictor | None:
        return await self.predictor_service.find_predictor_by_type_and_version(
            prediction_type=self.prediction_type,
            predictor_version=self.predictor_version,
        )

    async def setup(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return

            self.logger.info(
                f"Initializing predictor {self.prediction_type}.{self.predictor_version}"
            )

            predictor = await self.get_predictor()

            if predictor:
                predictor_weights_path = (
                    self.predictor_service.get_predictor_weights_path(predictor.id)
                )

                if predictor_weights_path.exists():
                    self.logger.info("Predictor initalized successfully...")
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

            self._initialized = True

    def tags(self) -> dict[str, str]:
        return self.predictor_service.build_tags(
            self.prediction_type, self.predictor_version
        )

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
                self.logger.info(
                    f"Predictor {self.prediction_type}.{self.predictor_version} already loaded"
                )
                return

            predictor = await self.get_predictor()

            if not predictor:
                raise ValueError(
                    f"Failed to load predictor {self.prediction_type}.{self.predictor_version}: document not found"
                )

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
                await self.metrics_repository.create_metric(
                    metric_name=PredictorMetrics.PREDICTOR_LOADING_ERROR,
                    metric_value=1,
                    tags=self.tags(),
                )

                raise ValueError(
                    f"Failed to load predictor {self.prediction_type}.{self.predictor_version}: {exc}"
                )

            end_time = time.perf_counter()

            latency = end_time - start_time

            await self.metrics_repository.create_metric(
                metric_name=PredictorMetrics.PREDICTOR_LOADING_LATENCY,
                metric_value=latency,
                tags=self.tags(),
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
                await self.metrics_repository.create_metric(
                    metric_name=PredictorMetrics.PREDICTOR_UNLOADING_ERROR,
                    metric_value=1,
                    tags=self.tags(),
                )

                raise ValueError(
                    f"Failed to unload predictor {self.prediction_type}.{self.predictor_version}: {exc}"
                )

            end_time = time.perf_counter()

            latency = end_time - start_time

            await self.metrics_repository.create_metric(
                metric_name=PredictorMetrics.PREDICTOR_UNLOADING_LATENCY,
                metric_value=latency,
                tags=self.tags(),
            )

            self._loaded = False

    async def forward(self, predictor_input: Any) -> Any:
        self._ensure_initialized()

        if not self._loaded:
            await self.load_predictor()

        start_time = time.perf_counter()

        self._last_used = time.time()
        if self._unload_task and not self._unload_task.done():
            self._unload_task.cancel()

        try:
            result = await self._forward(predictor_input)
            end_time = time.perf_counter()
            latency = end_time - start_time

            await self.metrics_repository.create_metric(
                metric_name=PredictorMetrics.PREDICTOR_LATENCY,
                metric_value=latency,
                tags=self.tags(),
            )

            await self.metrics_repository.create_metric(
                metric_name=PredictorMetrics.PREDICTOR_PRICE,
                metric_value=result.price,
                tags=self.tags(),
            )

            self._schedule_unload()

            return result

        except Exception:
            end_time = time.perf_counter()
            latency = end_time - start_time

            await self.metrics_repository.create_metric(
                metric_name=PredictorMetrics.PREDICTOR_ERROR,
                metric_value=1,
                tags=self.tags(),
            )

            raise

    # Memory
    def _schedule_unload(self) -> None:
        if self._unload_task and not self._unload_task.done():
            self._unload_task.cancel()

        self._unload_task = asyncio.create_task(self._unload_after_timeout())

    async def _unload_after_timeout(self) -> None:
        try:
            await asyncio.sleep(self.unload_timeout_seconds)

            if self._loaded:
                await self.unload_predictor()
                self.logger.info(
                    f"Auto-unloaded predictor {self.prediction_type}.{self.predictor_version} "
                    f"after {self.unload_timeout_seconds}s timeout"
                )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error in auto-unload: {e}")

    async def manual_unload(self) -> None:
        if self._unload_task and not self._unload_task.done():
            self._unload_task.cancel()

        if self._loaded:
            await self.unload_predictor()
