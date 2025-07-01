from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator


class PredictorDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    prediction_type: str
    predictor_description: str = Field(
        description="Small description to display in the metrics page"
    )
    predictor_version: int
    traffic_percentage: int = Field(default=0)
    created_at: datetime
    updated_at: datetime

    @field_validator("traffic_percentage")
    @classmethod
    def validate_traffic_percentage(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("Traffic percentage must be between 0 and 100")
        return v

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
