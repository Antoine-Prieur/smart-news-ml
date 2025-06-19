from src.database.repositories.models.predictor_repository_models import (
    PredictorDocument,
)
from src.services.models.predictor_models import Predictor


def db_to_domain_predictor(
    db_model: PredictorDocument, loaded: bool = False
) -> Predictor:
    """Convert database document to domain model"""
    if db_model.id is None:
        raise ValueError("DB models should always have an ID")

    return Predictor(
        id=db_model.id,
        predictor_name=db_model.predictor_name,
        predictor_version=db_model.predictor_version,
        predictor_weights_path=db_model.predictor_weights_path,
        loaded=loaded,
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )


def domain_to_db_predictor(domain_model: Predictor) -> PredictorDocument:
    """Convert domain model to database document"""
    from bson import ObjectId

    return PredictorDocument(
        _id=ObjectId(domain_model.id),
        predictor_name=domain_model.predictor_name,
        predictor_version=domain_model.predictor_version,
        predictor_weights_path=domain_model.predictor_weights_path,
        created_at=domain_model.created_at,
        updated_at=domain_model.updated_at,
    )
