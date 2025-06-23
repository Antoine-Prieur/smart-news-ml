from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field


class PredictorDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    prediction_type: str
    predictor_version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
