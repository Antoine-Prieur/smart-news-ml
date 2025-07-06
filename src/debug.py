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
        "_id": {"$oid": "68626112738fd4b469393731"},
        "source": {"id": "the-washington-post", "name": "The Washington Post"},
        "author": "Jacob Bogage",
        "title": "What’s in Trump and Senate Republicans’ tax and immigration bill? - The Washington Post",
        "description": "The Senate is on the verge of advancing Trump’s priorities, dubbed the One Big Beautiful Bill. Here’s how it could change the federal government and the U.S. economy.",
        "url": "https://www.washingtonpost.com/business/2025/06/28/republican-senate-trump-tax-immigration-plan/",
        "url_to_image": "https://www.washingtonpost.com/wp-apps/imrs.php?src=https://arc-anglerfish-washpost-prod-washpost.s3.amazonaws.com/public/VGI4RQ5W77W3XELSYRARD2JYPA_size-normalized.JPG&w=1440",
        "published_at": {"$date": "2025-06-29T08:06:27.000Z"},
        "content": "New tax breaks. Massive spending on border security. Cuts to social safety net programs. Pullbacks on investments to fight climate change. New limits on student loans.\r\nIf it becomes law, President D… [+10402 chars]",
        "created_at": {"$date": "2025-06-30T10:04:02.695Z"},
        "updated_at": {"$date": "2025-06-30T10:04:02.695Z"},
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
