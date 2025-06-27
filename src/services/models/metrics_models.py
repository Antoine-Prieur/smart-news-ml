from dataclasses import dataclass
from datetime import datetime

from bson import ObjectId


@dataclass
class Metric:
    id: ObjectId
    metric_name: str
    metric_value: float
    tags: dict[str, str]
    created_at: datetime
    updated_at: datetime
