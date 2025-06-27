from src.database.repositories.metrics_repository import MetricsRepository
from src.services.mappers.metrics_mapper import db_to_domain_metrics
from src.services.models.metrics_models import Metric


class MetricsService:
    def __init__(self, metrics_repository: MetricsRepository) -> None:
        self.metrics_repository = metrics_repository

    async def create_metric(
        self,
        metric_name: str,
        metric_value: float,
        tags: dict[str, str] | None = None,
    ) -> Metric:
        metric_document = await self.metrics_repository.create_metric(
            metric_name=metric_name, metric_value=metric_value, tags=tags
        )
        return db_to_domain_metrics(metric_document)
