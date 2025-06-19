from src.database import get_metrics_repository
from src.events import get_event_bus
from src.events.event_types import EventType
from src.events.handlers.metrics_handler import MetricsHandler


def setup_event_handlers():
    """Register all handlers with the event bus"""
    event_bus = get_event_bus()

    metrics_handler = MetricsHandler(get_metrics_repository())

    event_bus.subscribe(EventType.METRICS_EVENT, metrics_handler)
