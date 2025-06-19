from src.database.client import MongoClient
from src.database.repositories.base_respository import BaseRepository
from src.database.repositories.models.articles_repository_models import ArticleDocument


class ArticleRepository(BaseRepository[ArticleDocument]):
    @property
    def collection_name(self) -> str:
        return "articles"

    def __init__(self, mongo_client: MongoClient):
        super().__init__(
            mongo_client=mongo_client,
            model_class=ArticleDocument,
        )

    async def find_by_source_name(self, source_name: str) -> list[ArticleDocument]:
        """Find articles by source name"""
        cursor = self.collection.find({"source.name": source_name})
        docs = await cursor.to_list(None)
        return [self._to_model(doc) for doc in docs]

    async def find_by_author(self, author: str) -> list[ArticleDocument]:
        """Find articles by author"""
        cursor = self.collection.find({"author": author})
        docs = await cursor.to_list(None)
        return [self._to_model(doc) for doc in docs]

    async def find_published_after(self, date: str) -> list[ArticleDocument]:
        """Find articles published after a specific date"""
        cursor = self.collection.find({"published_at": {"$gte": date}})
        docs = await cursor.to_list(None)
        return [self._to_model(doc) for doc in docs]
