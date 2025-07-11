from datetime import datetime, timezone
from typing import Any

from motor.core import AgnosticClientSession

from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.metrics_repository_models import MetricDocument


class MetricsRepository(BaseRepository[MetricDocument]):
    @property
    def collection_name(self) -> str:
        return "metrics"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            model_class=MetricDocument,
        )

    async def find_metrics_by_name(
        self,
        metric_name: str,
        tags: dict[str, str] | None = None,
        session: AgnosticClientSession | None = None,
    ) -> list[MetricDocument]:
        """Find metrics by tags"""

        filters: dict[str, Any] = {}

        filters["metric_name"] = metric_name

        if tags:
            for key, value in tags.items():
                filters[f"tags.{key}"] = value

        cursor = self.collection.find(filters, session=session)
        docs = await cursor.to_list(None)

        return [self._to_model(doc) for doc in docs]

    async def insert_metric(
        self, metric: MetricDocument, session: AgnosticClientSession | None = None
    ) -> MetricDocument:
        """Insert a new  metric document"""
        doc_dict = self._to_document(metric)

        if doc_dict.get("_id") is None:
            doc_dict.pop("_id", None)

        result = await self.collection.insert_one(doc_dict, session=session)

        metric.id = result.inserted_id
        return metric

    async def create_metric(
        self,
        metric_name: str,
        metric_value: float,
        tags: dict[str, str] | None = None,
        description: str | None = None,
        session: AgnosticClientSession | None = None,
    ) -> MetricDocument:
        """Create and insert a new  metric with automatic timestamps"""
        now = datetime.now(timezone.utc)

        tags = tags or {}

        metric = MetricDocument(
            metric_name=metric_name,
            metric_value=metric_value,
            description=description,
            tags=tags,
            created_at=now,
            updated_at=now,
        )

        return await self.insert_metric(metric, session=session)
