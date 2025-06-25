from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field


class ArticleQueueMessage(BaseModel):
    id: ObjectId = Field(alias="_id")
    title: str | None = None
    description: str | None = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


@dataclass
class Prediction:
    prediction_confidence: float | None
    prediction_value: Any


@dataclass
class ArticlePredictions:
    id: str
    article_id: str
    prediction_type: str
    selected_predictor_id: str
    selected_prediction: Prediction
    predictions: dict[str, Prediction]
    created_at: datetime
    updated_at: datetime
