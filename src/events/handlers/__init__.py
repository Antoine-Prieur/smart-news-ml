from dependency_injector.wiring import Provide, inject

from src.container import Container
from src.database.repositories.metrics_repository import MetricsRepository
from src.events import get_event_bus
from src.events.event_types import EventType
from src.events.handlers.metrics_handler import MetricsHandler


@inject
def setup_event_handlers(
    metrics_repository: MetricsRepository = Provide[Container.metrics_repository],
) -> None:
    """Register all handlers with the event bus"""
    event_bus = get_event_bus()

    metrics_handler = MetricsHandler(metrics_repository)

    event_bus.subscribe(EventType.METRICS_EVENT, metrics_handler)
