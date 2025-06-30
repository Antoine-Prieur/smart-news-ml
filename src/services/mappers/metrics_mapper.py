from src.database.repositories.models.metrics_repository_models import MetricDocument
from src.services.models.metrics_models import Metric


def db_to_domain_metrics(db_model: MetricDocument) -> Metric:
    if db_model.id is None:
        raise ValueError("DB models should always have an ID")

    return Metric(
        id=db_model.id,
        metric_name=db_model.metric_name,
        metric_value=db_model.metric_value,
        tags=db_model.tags,
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )


def domain_to_db_metric(domain_model: Metric) -> MetricDocument:
    return MetricDocument(
        _id=domain_model.id,
        metric_name=domain_model.metric_name,
        metric_value=domain_model.metric_value,
        tags=domain_model.tags,
        created_at=domain_model.created_at,
        updated_at=domain_model.updated_at,
    )
