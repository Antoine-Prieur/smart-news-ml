from pydantic import BaseModel, Field


class TrafficShiftRequest(BaseModel):
    prediction_type: str = Field(
        ..., description="Type of prediction (e.g., 'sentiment_analysis')"
    )


class TrafficDistribution(BaseModel):
    predictor_id: str
    traffic_percentage: int


class TrafficShiftResponse(BaseModel):
    prediction_type: str
    traffic_distribution: list[TrafficDistribution]
