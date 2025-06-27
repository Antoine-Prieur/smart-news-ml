from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from bson import ObjectId


class PredictorMetrics(str, Enum):
    PREDICTOR_LATENCY = "predictor_latency"
    PREDICTOR_PRICE = "predictor_price"
    PREDICTOR_ERROR = "predictor_error"
    PREDICTOR_LOADING_LATENCY = "predictor_loading_latency"
    PREDICTOR_UNLOADING_LATENCY = "predictor_unloading_latency"
    PREDICTOR_LOADING_ERROR = "predictor_loading_error"
    PREDICTOR_UNLOADING_ERROR = "predictor_unloading_error"


@dataclass
class Prediction:
    prediction_value: Any
    prediction_confidence: float | None
    price: float


@dataclass
class Predictor:
    """Domain model representing an Predictor business entity"""

    id: ObjectId
    prediction_type: str
    predictor_version: int
    traffic_percentage: float
    created_at: datetime
    updated_at: datetime
