from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from bson import ObjectId


class PredictorMetrics(Enum, str):
    PREDICTOR_LATENCY = "predictor_latency"
    PREDICTOR_PRICE = "predictor_price"
    PREDICTOR_ERROR = "predictor_error"
    PREDICTOR_LOADING_LATENCY = "predictor_loading_latency"
    PREDICTOR_LOADING_ERROR = "predictor_loading_error"


@dataclass
class Prediction:
    result: Any
    price: float


@dataclass
class Predictor:
    """Domain model representing an Predictor business entity"""

    id: ObjectId
    predictor_name: str
    predictor_version: int
    predictor_weights_path: Path
    loaded: bool
    created_at: datetime
    updated_at: datetime
