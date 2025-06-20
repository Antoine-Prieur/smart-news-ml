from dataclasses import dataclass
from datetime import datetime

from bson import ObjectId


@dataclass
class ActiveDeployment:
    predictor_id: ObjectId
    traffic_percentage: float


@dataclass
class Deployment:
    id: ObjectId
    predictor_name: str
    active_deployments: list[ActiveDeployment]
    created_at: datetime
    updated_at: datetime
