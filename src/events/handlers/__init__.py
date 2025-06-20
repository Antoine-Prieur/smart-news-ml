from dependency_injector.wiring import Provide, inject

from src.container import Container
from src.core.logger import Logger
from src.events.event_bus import EventBus
from src.events.handlers.metrics_handler import MetricsHandler


@inject
def setup_event_handlers(
    event_bus: EventBus = Provide[Container.event_bus],
    metrics_handler: MetricsHandler = Provide[Container.metrics_handler],
    logger: Logger = Provide[Container.logger],
) -> None:
    event_bus.subscribe(metrics_handler)
    logger.info("Event handlers registered")
