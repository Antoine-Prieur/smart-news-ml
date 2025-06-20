from typing import Any, Awaitable, Callable

from motor.core import AgnosticClient, AgnosticClientSession

from src.core.settings import Settings


class MongoClient:
    def __init__(self, client: AgnosticClient[Any], settings: Settings) -> None:
        self.client = client
        self.database = self.client[settings.MONGO_DATABASE_NAME]

    async def test_connection(self) -> None:
        await self.client.admin.command("ping")

    async def list_collection_names(self) -> list[str]:
        return await self.database.list_collection_names()

    def close(self) -> None:
        self.client.close()

    async def multi_documents_transaction(
        self,
        transaction: Callable[[AgnosticClientSession | None], Awaitable[None]],
    ) -> None:
        try:
            async with await self.client.start_session() as session:
                async with session.start_transaction():
                    await transaction(session)
        except Exception as e:
            if str(e) == "Mongomock does not support sessions yet":
                # Yielding nothing to have session=None and continue using the regular client
                await transaction(None)
            else:
                raise e
