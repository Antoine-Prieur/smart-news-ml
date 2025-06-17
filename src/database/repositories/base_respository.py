from abc import ABC
from typing import Any, Generic, List, Optional, Type, TypeVar

from bson import ObjectId
from pydantic import BaseModel

from src.database.client import MongoClient

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T], ABC):
    def __init__(
        self, mongo_client: MongoClient, collection_name: str, model_class: Type[T]
    ):
        self.mongo_client = mongo_client
        self.collection = mongo_client.database[collection_name]
        self.model_class = model_class

    def _to_model(self, document: dict[str, Any]) -> T:
        """Convert MongoDB document to Pydantic model"""
        return self.model_class(**document)

    def _to_document(self, model: T, exclude_id: bool = True) -> dict[str, Any]:
        """Convert Pydantic model to MongoDB document"""
        exclude_fields: set[str] = {"id"} if exclude_id else set()
        return model.model_dump(by_alias=True, exclude=exclude_fields)

    async def find_by_id(self, doc_id: ObjectId | str) -> Optional[T]:
        if isinstance(doc_id, str):
            doc = ObjectId(doc_id)

        doc = await self.collection.find_one({"_id": doc_id})
        return self._to_model(doc) if doc else None

    async def insert_one(self, model: T) -> str:
        doc = self._to_document(model)
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def find_all(self) -> List[T]:
        cursor = self.collection.find()
        docs = await cursor.to_list(None)
        return [self._to_model(doc) for doc in docs]
