import asyncio

from dependency_injector.wiring import Provide, inject

from src.container import Container
from src.core.logger import Logger
from src.events.event_bus import EventBus
from src.setup import MLPlatformSetup


@inject
async def start_event_bus(
    event_bus: EventBus = Provide[Container.event_bus],
    logger: Logger = Provide[Container.logger],
) -> None:
    logger.info("Event system initialized and started")
    await event_bus.start()


async def main():
    """Setup application and start consumer"""
    ml_platform_setup = MLPlatformSetup()
    await ml_platform_setup.setup()

    ml_platform_setup.container.wire(modules=[__name__])

    try:
        await start_event_bus()
    except KeyboardInterrupt:
        print("Shutting down consumer...")
    finally:
        await ml_platform_setup.cleanup_resources()


if __name__ == "__main__":
    asyncio.run(main())
