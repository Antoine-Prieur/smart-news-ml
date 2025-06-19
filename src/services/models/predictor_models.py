from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bson import ObjectId


@dataclass
class Predictor:
    """Domain model representing an Predictor business entity"""

    id: ObjectId
    predictor_name: str
    predictor_version: int
    predictor_weights_path: Path
    active: bool
    created_at: datetime
    updated_at: datetime
