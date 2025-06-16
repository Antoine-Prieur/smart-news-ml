from dataclasses import dataclass
from datetime import datetime

from bson import ObjectId


@dataclass(frozen=True)
class MLPredictor:
    """Domain model representing an ML Model business entity"""

    id: ObjectId
    predictor_name: str
    predictor_version: int
    active: bool
    created_at: datetime
    updated_at: datetime
