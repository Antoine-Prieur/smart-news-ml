from typing import Any, Awaitable, Callable, TypeVar

from motor.core import AgnosticClient, AgnosticClientSession

from src.core.logger import Logger
from src.core.settings import Settings

T = TypeVar("T")


class MongoClient:
    def __init__(
        self, client: AgnosticClient[Any], settings: Settings, logger: Logger
    ) -> None:
        self.client = client
        self.logger = logger
        self.database = self.client[settings.MONGO_DATABASE_NAME]

    async def test_connection(self) -> None:
        await self.client.admin.command("ping")

    async def list_collection_names(self) -> list[str]:
        return await self.database.list_collection_names()

    def close(self) -> None:
        self.client.close()

    async def start_transaction(
        self,
        transaction: Callable[[AgnosticClientSession], Awaitable[T]],
    ) -> T:
        try:
            # I disabled transactions because my free Mongo cluster is not deployed in a replicaset
            async with await self.client.start_session() as session:
                return await transaction(session)

            # async with await self.client.start_session() as session:
            #     async with session.start_transaction():
            #         return await transaction(session)
        except Exception as e:
            self.logger.error(f"Could not execute transaction: {e}")
            raise
