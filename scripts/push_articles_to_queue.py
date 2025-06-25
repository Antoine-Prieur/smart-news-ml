import asyncio
from typing import Any

from dependency_injector.wiring import Provide, inject
from redis.asyncio import Redis

from src.container import Container
from src.database.repositories.articles_repository import ArticleRepository
from src.setup import MLPlatformSetup


@inject
async def push_articles_to_queue(
    redis_client: "Redis[Any]" = Provide[Container.redis_client],
    articles_repository: ArticleRepository = Provide[Container.articles_repository],
) -> None:
    """Push all articles from MongoDB to Redis queue"""

    QUEUE_NAME = "articles_queue"

    articles = await articles_repository.find_all()

    for article in articles:
        article_json = article.model_dump_json(by_alias=True)

        await redis_client.lpush(QUEUE_NAME, article_json)


async def main():
    setup = MLPlatformSetup()
    await setup.setup()

    setup.container.wire(modules=[__name__])

    try:
        await push_articles_to_queue()
    except KeyboardInterrupt:
        print("Shutting down consumer...")
    finally:
        await setup.cleanup_resources()


if __name__ == "__main__":
    asyncio.run(main())
