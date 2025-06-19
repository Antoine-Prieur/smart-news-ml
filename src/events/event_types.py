from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class EventType(Enum):
    METRICS_EVENT = "metrics_event"


@dataclass
class BaseEvent:
    event_type: EventType
    timestamp: float


class EventHandler(Protocol):
    async def handle(self, event_data: BaseEvent) -> None: ...


@dataclass
class MetricsEvent(BaseEvent):
    metric_name: str
    metric_value: float
    tags: dict[str, str]
