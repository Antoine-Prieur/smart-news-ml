from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class EventType(Enum):
    METRICS_EVENT = "metrics_event"
    ARTICLES_EVENT = "articles_event"


class BaseEvent(BaseModel):
    """Base event model for all events in the system."""

    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content: Any

    class Config:
        arbitrary_types_allowed = True


class EventHandler(Protocol):
    @property
    def event_types(self) -> list[EventType]: ...

    async def handle(self, events_data: list[BaseEvent]) -> None: ...
