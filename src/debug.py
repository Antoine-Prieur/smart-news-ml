import asyncio

from dependency_injector.wiring import Provide, inject

from src.container import Container
from src.core.logger import Logger
from src.events.event_bus import EventBus
from src.events.event_types import BaseEvent, EventType
from src.setup import MLPlatformSetup


@inject
async def publish_test_event(
    event_bus: EventBus = Provide[Container.event_bus],
    logger: Logger = Provide[Container.logger],
) -> None:
    test_content = {
        "_id": {"$oid": "685a5d35a821629c2f060ae4"},
        "source": {"id": "the-washington-post", "name": "the washington post"},
        "author": "trisha thadani, joshua partlow",
        "title": "tesla launches long-awaited robotaxi in austin - the washington post",
        "description": "the test, limited in scope and shrouded in secrecy, is a crucial step for a company still struggling with the fallout from its founder's foray into politics.",
        "url": "https://www.washingtonpost.com/technology/2025/06/22/tesla-robotaxi-launch-austin/",
        "url_to_image": "https://www.washingtonpost.com/wp-apps/imrs.php?src=https://arc-anglerfish-washpost-prod-washpost.s3.amazonaws.com/public/yizcmwh2jtqhdlzsucxhpajmyy_size-normalized.jpg&w=1440",
        "published_at": {"$date": "2025-06-23t04:42:53.000z"},
        "content": "tesla held its first robotaxi rides in austin on sunday, a cautious and modest launch that came more than a decade after ceo elon musk first pitched the idea.\r\na group of social media influencers and… [+3648 chars]",
        "created_at": {"$date": "2025-06-24t08:09:25.691z"},
        "updated_at": {"$date": "2025-06-24t08:09:25.691z"},
    }

    event = BaseEvent(
        event_type=EventType.ARTICLES_EVENT,
        content=test_content,
    )

    await event_bus.publish(event)
    print("✅ Event published successfully!")


async def debug_loop():
    ml_platform_setup = MLPlatformSetup()
    await ml_platform_setup.setup()
    ml_platform_setup.container.wire(modules=[__name__])

    print("Type 'y' to publish test event, 'q' to quit")

    try:
        while True:
            user_input = input(">>> ").strip().lower()

            if user_input == "y":
                try:
                    await publish_test_event()
                except Exception as e:
                    print(f"❌ Error publishing event: {e}")
            elif user_input == "q":
                break
            else:
                print("Type 'y' to publish, 'q' to quit")

    finally:
        await ml_platform_setup.cleanup_resources()


if __name__ == "__main__":
    asyncio.run(debug_loop())
