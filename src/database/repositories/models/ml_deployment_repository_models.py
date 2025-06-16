from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator


class MLActiveDeploymentDocument(BaseModel):
    predictor_id: ObjectId
    traffic_distribution: float


class MLDeploymentDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    predictor_name: str
    active_deployments: list[MLActiveDeploymentDocument] = Field(
        default_factory=list[MLActiveDeploymentDocument]
    )
    created_at: datetime
    updated_at: datetime

    @field_validator("active_deployments")
    def validate_traffic_sum(
        cls, active_deployments: list[MLActiveDeploymentDocument]
    ) -> list[MLActiveDeploymentDocument]:
        total_traffic = sum(
            deployment.traffic_distribution for deployment in active_deployments
        )
        if abs(total_traffic - 100.0) > 1e-6:
            raise ValueError(
                f"Total traffic distribution must equal 100, got {total_traffic}"
            )
        return active_deployments

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
