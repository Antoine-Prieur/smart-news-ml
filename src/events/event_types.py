from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class EventType(Enum):
    METRICS_EVENT = "metrics_event"


@dataclass
class BaseEvent:
    event_type: EventType = field(init=False)
    timestamp: datetime = field(init=False)

    def __post_init__(self):
        self.timestamp = datetime.now(timezone.utc)


class EventHandler(Protocol):
    @property
    def event_types(self) -> list[EventType]: ...
    async def handle(self, event_data: BaseEvent) -> None: ...


@dataclass
class MetricsEvent(BaseEvent):
    metric_name: str
    metric_value: float
    tags: dict[str, str]

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.METRICS_EVENT
