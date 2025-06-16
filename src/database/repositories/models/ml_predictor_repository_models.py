from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field


class MLPredictorDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    predictor_name: str
    predictor_version: int
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
