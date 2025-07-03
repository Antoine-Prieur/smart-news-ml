from bson import ObjectId

from src.api.schemas.traffic_schemas import TrafficDistribution


def to_traffic_distribution(
    predictor_id: ObjectId, traffic_percentage: int
) -> TrafficDistribution:
    return TrafficDistribution(
        predictor_id=str(predictor_id), traffic_percentage=traffic_percentage
    )
