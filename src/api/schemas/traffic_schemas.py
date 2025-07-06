from pydantic import BaseModel, Field


class TrafficShiftRequest(BaseModel):
    prediction_type: str = Field(
        ..., description="Type of prediction (e.g., 'sentiment_analysis')"
    )
    description: str | None = Field(
        default=None, description="Small description to explain the changes"
    )


class TrafficDeactivationRequest(BaseModel):
    prediction_type: str = Field(
        ..., description="Type of prediction (e.g., 'sentiment_analysis')"
    )
    predictor_version: int = Field(..., description="Predictor version (e.g., 1)")
    description: str | None = Field(
        default=None, description="Small description to explain the changes"
    )


class TrafficDistribution(BaseModel):
    predictor_id: str
    traffic_percentage: int


class TrafficShiftResponse(BaseModel):
    prediction_type: str
    traffic_distribution: list[TrafficDistribution]


class TrafficDeactivartionResponse(BaseModel):
    prediction_type: str
    traffic_distribution: list[TrafficDistribution]
