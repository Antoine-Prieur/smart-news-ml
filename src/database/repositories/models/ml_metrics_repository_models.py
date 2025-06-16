from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field


class MLMetricsDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    ml_predictor_id: ObjectId
    metric_name: str
    metric_value: float
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
