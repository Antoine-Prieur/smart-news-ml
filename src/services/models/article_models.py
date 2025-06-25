from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator


class ArticleQueueMessage(BaseModel):
    id: ObjectId = Field(alias="_id")
    title: str | None = None
    description: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def parse_object_id(cls, v: Any) -> ObjectId | None:
        """Convert MongoDB ObjectId format to ObjectId"""
        if v is None:
            return None

        if isinstance(v, dict) and "$oid" in v:
            v = cast(dict[Any, Any], v)
            return ObjectId(v["$oid"])

        if isinstance(v, str):
            return ObjectId(v)

        if isinstance(v, ObjectId):
            return v

        raise ValueError(f"Could not parse the _id {v}")

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
