from src.database.repositories.models.article_predictions_repository_models import (
    ArticlePredictionsDocument,
    PredictionDocument,
)
from src.services.models.article_models import ArticlePredictions, Prediction


def db_to_domain_prediction(db_model: PredictionDocument) -> Prediction:
    return Prediction(
        prediction_confidence=db_model.prediction_confidence,
        prediction_value=db_model.prediction_value,
    )


def domain_to_db_prediction(domain_model: Prediction) -> PredictionDocument:
    return PredictionDocument(
        prediction_confidence=domain_model.prediction_confidence,
        prediction_value=domain_model.prediction_value,
    )


def db_to_domain_article_predictions(
    db_model: ArticlePredictionsDocument,
) -> ArticlePredictions:
    if db_model.id is None:
        raise ValueError("DB models should always have an ID")

    predictions = {
        key: db_to_domain_prediction(prediction)
        for key, prediction in db_model.predictions.items()
    }

    return ArticlePredictions(
        id=str(db_model.id),
        article_id=str(db_model.article_id),
        prediction_type=db_model.prediction_type,
        selected_predictor_id=str(db_model.selected_predictor_id),
        selected_prediction=db_to_domain_prediction(db_model.selected_prediction),
        predictions=predictions,
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )


def domain_to_db_article_predictions(
    domain_model: ArticlePredictions,
) -> ArticlePredictionsDocument:
    from bson import ObjectId

    predictions = {
        key: domain_to_db_prediction(prediction)
        for key, prediction in domain_model.predictions.items()
    }

    return ArticlePredictionsDocument(
        _id=ObjectId(domain_model.id),
        article_id=ObjectId(domain_model.article_id),
        prediction_type=domain_model.prediction_type,
        selected_predictor_id=ObjectId(domain_model.selected_predictor_id),
        selected_prediction=domain_to_db_prediction(domain_model.selected_prediction),
        predictions=predictions,
        created_at=domain_model.created_at,
        updated_at=domain_model.updated_at,
    )
