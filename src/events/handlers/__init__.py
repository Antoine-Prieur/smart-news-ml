from src.database import get_metrics_repository
from src.events import get_event_bus
from src.events.handlers.metrics_handler import MetricsHandler


def setup_event_handlers():
    """Register all handlers with the event bus"""
    event_bus = get_event_bus()

    # Create handlers with their dependencies
    metrics_handler = MetricsHandler(get_metrics_repository())

    # Register handlers for specific events
    event_bus.subscribe(EventType.TRAFFIC_ADJUSTED, metrics_handler)
    event_bus.subscribe(EventType.PREDICTION_COMPLETED, metrics_handler)
