from typing import overload

from src.database.repositories.models.article_predictions_repository_models import (
    ArticlePredictionsDocument,
    PredictionDocument,
)
from src.services.models.article_models import ArticlePredictions, Prediction


@overload
def db_to_domain_prediction(db_model: None) -> None: ...


@overload
def db_to_domain_prediction(db_model: PredictionDocument) -> Prediction: ...


def db_to_domain_prediction(db_model: PredictionDocument | None) -> Prediction | None:
    if db_model is None:
        return None

    return Prediction(
        prediction_confidence=db_model.prediction_confidence,
        prediction_value=db_model.prediction_value,
    )


@overload
def domain_to_db_prediction(domain_model: None) -> None: ...


@overload
def domain_to_db_prediction(domain_model: Prediction) -> PredictionDocument: ...


def domain_to_db_prediction(
    domain_model: Prediction | None,
) -> PredictionDocument | None:
    if domain_model is None:
        return None

    return PredictionDocument(
        prediction_confidence=domain_model.prediction_confidence,
        prediction_value=domain_model.prediction_value,
    )


def db_to_domain_article_predictions(
    db_model: ArticlePredictionsDocument,
) -> ArticlePredictions:
    if db_model.id is None:
        raise ValueError("DB models should always have an ID")

    predictions: dict[str, Prediction] = {
        key: db_to_domain_prediction(prediction)
        for key, prediction in db_model.predictions.items()
    }

    return ArticlePredictions(
        id=str(db_model.id),
        article_id=str(db_model.article_id),
        prediction_type=db_model.prediction_type,
        selected_predictor_id=(
            str(db_model.selected_predictor_id)
            if db_model.selected_predictor_id is not None
            else None
        ),
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
        selected_predictor_id=(
            ObjectId(domain_model.selected_predictor_id)
            if domain_model.selected_predictor_id is not None
            else None
        ),
        selected_prediction=domain_to_db_prediction(domain_model.selected_prediction),
        predictions=predictions,
        created_at=domain_model.created_at,
        updated_at=domain_model.updated_at,
    )
