from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field


class MetricDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    metric_name: str
    metric_value: float
    tags: dict[str, str] = Field(default_factory=dict[str, str])
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
