from src.database.repositories.metrics_repository import MetricsRepository
from src.events.event_types import BaseEvent, MetricsEvent


class MetricsHandler:
    def __init__(self, metrics_repository: MetricsRepository) -> None:
        self.metrics_repository = metrics_repository

    async def handle(self, event_data: BaseEvent) -> None:
        if isinstance(event_data, MetricsEvent):
            await self.metrics_repository.create_metric(
                event_data.metric_name, event_data.metric_value, event_data.tags
            )

        return None
