from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.api.mappers.traffic_mappers import to_traffic_distribution
from src.api.schemas.traffic_schemas import TrafficShiftRequest, TrafficShiftResponse
from src.services.predictor_service import PredictorService

router = APIRouter(prefix="/traffic", tags=["traffic"])


def get_predictor_service(request: Request) -> PredictorService:
    return request.app.state.ml_platform_setup.container.predictor_service()


@router.post("/shift", response_model=TrafficShiftResponse)
async def shift_traffic(
    request: TrafficShiftRequest,
    predictor_service: Annotated[PredictorService, Depends(get_predictor_service)],
) -> TrafficShiftResponse:
    new_distribution = await predictor_service.shift_traffic_to_newest(
        prediction_type=request.prediction_type
    )

    traffic_distribution = [
        to_traffic_distribution(predictor_id, traffic_percentage)
        for predictor_id, traffic_percentage in new_distribution.items()
    ]

    return TrafficShiftResponse(
        prediction_type=request.prediction_type,
        traffic_distribution=traffic_distribution,
    )
