import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from dependency_injector.wiring import Provide, inject
from fastapi import FastAPI

from src.api.routes import traffic_routers
from src.container import Container
from src.core.logger import Logger
from src.core.logging_filters import EndpointFilter
from src.core.settings import Settings
from src.events.event_bus import EventBus
from src.setup import MLPlatformSetup

settings = Settings()


@inject
async def start_event_bus(
    event_bus: EventBus = Provide[Container.event_bus],
    logger: Logger = Provide[Container.logger],
) -> None:
    logger.info("Event system initialized and started")
    await event_bus.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_platform_setup = MLPlatformSetup()

    try:
        await ml_platform_setup.setup()

        ml_platform_setup.container.wire(
            modules=["src.api.routes.traffic_routers", __name__]
        )

        event_task = asyncio.create_task(start_event_bus())

        app.state.ml_platform_setup = ml_platform_setup
        app.state.event_task = event_task

        yield

    finally:
        if hasattr(app.state, "event_task") and not app.state.event_task.done():
            app.state.event_task.cancel()
            try:
                await app.state.event_task
            except asyncio.CancelledError:
                pass

        await ml_platform_setup.cleanup_resources()


app = FastAPI(title=settings.NAME, lifespan=lifespan)

app.include_router(traffic_routers.router)


@app.get("/health/check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    console_handler = logging.StreamHandler(sys.stdout)
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.addFilter(EndpointFilter(paths=["/health/check"]))
    uvicorn_logger.addHandler(console_handler)

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        log_level=logging.INFO,
        port=settings.API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
