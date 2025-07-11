from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Prediction:
    prediction_confidence: float | None
    prediction_value: Any


@dataclass
class ArticlePredictions:
    id: str
    article_id: str
    prediction_type: str
    selected_predictor_id: str | None
    selected_prediction: Prediction | None
    predictions: dict[str, Prediction]
    created_at: datetime
    updated_at: datetime
