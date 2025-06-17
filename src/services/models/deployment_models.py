from dataclasses import dataclass
from datetime import datetime
from typing import List

from bson import ObjectId


@dataclass
class MLActiveDeployment:
    predictor_id: ObjectId
    traffic_percentage: float


@dataclass
class MLDeployment:
    id: ObjectId
    predictor_name: str
    active_deployments: List[MLActiveDeployment]
    created_at: datetime
    updated_at: datetime
