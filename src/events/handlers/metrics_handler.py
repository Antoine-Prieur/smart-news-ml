from typing import Any

from pydantic import BaseModel

from src.events.event_types import BaseEvent, EventType
from src.services.metrics_service import MetricsService


class MetricsEvent(BaseModel):
    metric_name: str
    metric_value: Any
    tags: dict[str, str]

    @classmethod
    def create_base_event(
        cls, metric_name: str, metric_value: Any, tags: dict[str, str]
    ) -> BaseEvent:
        instance = cls(metric_name=metric_name, metric_value=metric_value, tags=tags)

        return BaseEvent(event_type=EventType.METRICS_EVENT, content=instance)


class MetricsHandler:
    def __init__(self, metrics_service: MetricsService) -> None:
        self.metrics_service = metrics_service

    @property
    def event_types(self) -> list[EventType]:
        return [EventType.METRICS_EVENT]

    async def handle(self, events_data: list[BaseEvent]) -> None:
        events_content = [
            MetricsEvent.model_validate(event_data.content)
            for event_data in events_data
        ]

        for event_content in events_content:
            await self.metrics_service.create_metric(
                event_content.metric_name,
                event_content.metric_value,
                event_content.tags,
            )

        return None
