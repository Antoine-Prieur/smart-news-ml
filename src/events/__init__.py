from src.events.event_bus import EventBus
from src.events.event_types import BaseEvent, EventType

# Global instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
