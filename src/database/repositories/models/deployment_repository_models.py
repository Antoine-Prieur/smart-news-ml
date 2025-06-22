from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator

from src.utils.traffic_distribution_utils import validate_traffic_distribution


class ActiveDeploymentDocument(BaseModel):
    predictor_id: ObjectId
    traffic_percentage: float

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class DeploymentDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    prediction_type: str
    active_deployments: list[ActiveDeploymentDocument] = Field(
        default_factory=list[ActiveDeploymentDocument]
    )
    created_at: datetime
    updated_at: datetime

    @field_validator("active_deployments")
    def validate_traffic_sum(
        cls, active_deployments: list[ActiveDeploymentDocument]
    ) -> list[ActiveDeploymentDocument]:
        traffic_distribution = [
            deployment.traffic_percentage for deployment in active_deployments
        ]
        validate_traffic_distribution(traffic_distribution)
        return active_deployments

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
