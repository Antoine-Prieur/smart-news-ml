from src.database.repositories.models.ml_predictor_repository_models import (
    MLPredictorDocument,
)
from src.ml.ml_predictor_models import MLPredictor


def db_to_domain_ml_predictor(db_model: MLPredictorDocument) -> MLPredictor:
    """Convert database document to domain model"""
    if db_model.id is None:
        raise ValueError("DB models should always have an ID")

    return MLPredictor(
        id=db_model.id,
        predictor_name=db_model.predictor_name,
        predictor_version=db_model.predictor_version,
        predictor_weights_path=db_model.predictor_weights_path,
        active=db_model.active,
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )


def domain_to_db_ml_predictor(domain_model: MLPredictor) -> MLPredictorDocument:
    """Convert domain model to database document"""
    from bson import ObjectId

    return MLPredictorDocument(
        _id=ObjectId(domain_model.id),
        predictor_name=domain_model.predictor_name,
        predictor_version=domain_model.predictor_version,
        predictor_weights_path=domain_model.predictor_weights_path,
        active=domain_model.active,
        created_at=domain_model.created_at,
        updated_at=domain_model.updated_at,
    )
