import shutil
from pathlib import Path

from bson import ObjectId

from src.core.settings import Settings
from src.database.repositories.predictor_repository import PredictorRepository
from src.services.mappers.predictor_mapper import db_to_domain_predictor
from src.services.models.predictor_models import Predictor


class PredictorService:
    def __init__(
        self, settings: Settings, predictor_repository: PredictorRepository
    ) -> None:
        self.settings = settings
        self.predictor_repository = predictor_repository

    async def find_predictor_by_id(self, predictor_id: ObjectId | str) -> Predictor:
        if isinstance(predictor_id, str):
            predictor_id = ObjectId(predictor_id)

        predictor_document = await self.predictor_repository.find_by_id(
            doc_id=predictor_id
        )

        return db_to_domain_predictor(predictor_document)

    async def find_predictor_by_type_and_version(
        self, prediction_type: str, predictor_version: int
    ) -> Predictor | None:
        predictor_document = await self.predictor_repository.find_predictor(
            prediction_type=prediction_type, predictor_version=predictor_version
        )

        if predictor_document is None:
            return None

        return db_to_domain_predictor(predictor_document)

    def get_predictor_weights_path(self, predictor_id: ObjectId | str) -> Path:
        if isinstance(predictor_id, ObjectId):
            predictor_id = str(predictor_id)

        return self.settings.WEIGHTS_PATH.joinpath(predictor_id)

    def copy_weights(
        self, predictor_id: ObjectId, predictor_weights_path: Path
    ) -> None:
        destination_path = self.get_predictor_weights_path(predictor_id)

        if predictor_weights_path.is_file():
            destination_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(predictor_weights_path, destination_path)
        elif predictor_weights_path.is_dir():
            shutil.copytree(
                predictor_weights_path, destination_path, dirs_exist_ok=True
            )

    async def register_predictor(
        self, predictor_weights_path: Path, prediction_type: str, predictor_version: int
    ) -> Predictor:
        if not predictor_weights_path.exists():
            raise ValueError(
                f"The weights path {predictor_weights_path} does not exist"
            )
        predictor_document = await self.predictor_repository.create_predictor(
            prediction_type, predictor_version
        )

        predictor_domain = db_to_domain_predictor(predictor_document)

        self.copy_weights(predictor_domain.id, predictor_weights_path)

        return predictor_domain
