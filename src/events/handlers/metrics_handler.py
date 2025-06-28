from typing import Any

from pydantic import BaseModel

from src.events.event_types import BaseEvent, EventType
from src.services.metrics_service import MetricsService


class MetricsEvent(BaseModel):
    metric_name: str
    metric_value: Any
    tags: dict[str, str]


class MetricsHandler:
    def __init__(self, metrics_service: MetricsService) -> None:
        self.metrics_service = metrics_service

    @property
    def event_types(self) -> list[EventType]:
        return [EventType.METRICS_EVENT]

    async def handle(self, event_data: BaseEvent) -> None:
        event_content = MetricsEvent.model_validate(event_data.content)

        await self.metrics_service.create_metric(
            event_content.metric_name, event_content.metric_value, event_content.tags
        )

        return None
