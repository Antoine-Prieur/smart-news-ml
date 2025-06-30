from src.database.repositories.models.predictor_repository_models import (
    PredictorDocument,
)
from src.services.models.predictor_models import Predictor


def db_to_domain_predictor(db_model: PredictorDocument) -> Predictor:
    """Convert database document to domain model"""
    if db_model.id is None:
        raise ValueError("DB models should always have an ID")

    return Predictor(
        id=db_model.id,
        prediction_type=db_model.prediction_type,
        predictor_version=db_model.predictor_version,
        traffic_percentage=db_model.traffic_percentage,
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )


def domain_to_db_predictor(domain_model: Predictor) -> PredictorDocument:
    """Convert domain model to database document"""
    from bson import ObjectId

    return PredictorDocument(
        _id=ObjectId(domain_model.id),
        prediction_type=domain_model.prediction_type,
        predictor_version=domain_model.predictor_version,
        traffic_percentage=domain_model.traffic_percentage,
        created_at=domain_model.created_at,
        updated_at=domain_model.updated_at,
    )
