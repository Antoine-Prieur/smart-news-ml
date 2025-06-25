import asyncio
import json
from typing import Any

from dependency_injector.wiring import Provide, inject
from redis.asyncio import Redis

from src.container import Container
from src.core.logger import Logger
from src.services.article_service import ArticleService
from src.setup import MLPlatformSetup


@inject
async def consume_articles_batch(
    redis_client: "Redis[Any]" = Provide[
        Container.redis_client
    ],  # redis type does not work in runtime
    article_service: ArticleService = Provide[Container.article_service],
    logger: Logger = Provide[Container.logger],
) -> None:
    """Consume articles from Redis queue in batches"""

    QUEUE_NAME = "articles_queue"
    BATCH_SIZE = 50
    BATCH_TIMEOUT = 5.0

    logger.info("Starting batch articles consumer...")

    while True:
        try:
            messages: list[Any] = []
            start_time = asyncio.get_event_loop().time()

            while len(messages) < BATCH_SIZE:
                remaining_time = BATCH_TIMEOUT - (
                    asyncio.get_event_loop().time() - start_time
                )
                if remaining_time <= 0:
                    break

                result = await redis_client.brpop(
                    QUEUE_NAME, timeout=int(remaining_time)
                )
                if result:
                    _, message_data = result
                    message_json = json.loads(message_data.decode("utf-8"))
                    messages.append(message_json)
                else:
                    await asyncio.sleep(1)
                    break

            if messages:
                logger.info(f"Processing batch of {len(messages)} articles")
                predictions = await article_service.process_articles(messages)
                logger.info(f"Successfully processed {len(predictions)} articles")

        except Exception as e:
            logger.error(f"Error in batch consumer: {e}")
            await asyncio.sleep(1)


async def main():
    """Setup application and start consumer"""
    setup = MLPlatformSetup()
    await setup.setup()

    setup.container.wire(modules=[__name__])

    try:
        await consume_articles_batch()
    except KeyboardInterrupt:
        print("Shutting down consumer...")
    finally:
        await setup.cleanup_resources()


if __name__ == "__main__":
    asyncio.run(main())
