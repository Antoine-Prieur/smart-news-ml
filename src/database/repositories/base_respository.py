from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Generic, Type, TypeVar

from bson import ObjectId
from motor.core import AgnosticClientSession
from pydantic import BaseModel
from pymongo import IndexModel

from src.database.client import MongoClient

T = TypeVar("T", bound=BaseModel)
V = TypeVar("V")


class BaseRepository(Generic[T], ABC):
    @property
    @abstractmethod
    def collection_name(self) -> str: ...

    def __init__(self, mongo_client: MongoClient, model_class: Type[T]):
        self.mongo_client = mongo_client
        self.collection = mongo_client.database[self.collection_name]
        self.model_class = model_class

        self._initialized = False

    async def start_transaction(
        self,
        transaction: Callable[[AgnosticClientSession], Awaitable[V]],
    ) -> V:
        return await self.mongo_client.start_transaction(transaction=transaction)

    async def setup(self) -> None:
        await self._create_indexes()

    def _to_model(self, document: dict[str, Any]) -> T:
        """Convert MongoDB document to Pydantic model"""
        return self.model_class(**document)

    def _to_document(self, model: T, exclude_id: bool = True) -> dict[str, Any]:
        """Convert Pydantic model to MongoDB document"""
        exclude_fields: set[str] = {"id"} if exclude_id else set()
        return model.model_dump(by_alias=True, exclude=exclude_fields)

    async def find_by_id(
        self,
        doc_id: ObjectId | str,
        session: AgnosticClientSession | None = None,
    ) -> T:
        if isinstance(doc_id, str):
            doc_id = ObjectId(doc_id)

        doc = await self.collection.find_one({"_id": doc_id}, session=session)

        if not doc:
            raise ValueError(
                f"Document with ObjectId {doc_id} in collection {self.collection_name} not found"
            )

        return self._to_model(doc)

    async def insert_one(
        self,
        model: T,
        session: AgnosticClientSession | None = None,
    ) -> str:
        doc = self._to_document(model)
        result = await self.collection.insert_one(doc, session=session)
        return str(result.inserted_id)

    async def find_all(
        self,
        session: AgnosticClientSession | None = None,
    ) -> list[T]:
        cursor = self.collection.find(session=session)
        docs = await cursor.to_list(None)
        return [self._to_model(doc) for doc in docs]

    @property
    def indexes(self) -> list[IndexModel]:
        return []

    async def _create_indexes(
        self,
        session: AgnosticClientSession | None = None,
    ) -> None:
        if self._initialized:
            return

        if self.indexes:
            await self.collection.create_indexes(self.indexes, session=session)

        self._initialized = True
