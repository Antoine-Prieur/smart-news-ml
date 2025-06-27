from src.events.event_types import BaseEvent, EventType, MetricsEvent
from src.services.metrics_service import MetricsService


class MetricsHandler:
    def __init__(self, metrics_service: MetricsService) -> None:
        self.metrics_service = metrics_service

    @property
    def event_types(self) -> list[EventType]:
        return [EventType.METRICS_EVENT]

    async def handle(self, event_data: BaseEvent) -> None:
        if isinstance(event_data, MetricsEvent):
            await self.metrics_service.create_metric(
                event_data.metric_name, event_data.metric_value, event_data.tags
            )

        return None
