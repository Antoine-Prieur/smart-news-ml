from datetime import datetime
from typing import Any, Self

from bson import ObjectId
from pydantic import BaseModel, Field, model_validator


class PredictionDocument(BaseModel):
    prediction_confidence: float | None = Field(default=None)
    prediction_value: Any


class ArticlePredictionsDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    article_id: ObjectId
    prediction_type: str
    selected_predictor_id: ObjectId
    selected_prediction: PredictionDocument | None = Field(default=None)
    predictions: dict[str, PredictionDocument] = Field(
        default_factory=dict[str, PredictionDocument]
    )
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_selected_prediction(self) -> Self:
        if str(self.selected_predictor_id) not in self.predictions:
            raise ValueError(
                f"Selected prediction {self.selected_predictor_id} should be a valid ObjectId from predictions"
            )

        return self

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
