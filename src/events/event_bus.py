import asyncio
import json
from typing import Any

from redis.asyncio import Redis

from src.core.logger import Logger
from src.events.event_types import BaseEvent, EventHandler, EventType


class EventBus:
    def __init__(self, logger: Logger, redis: "Redis[Any]"):
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._redis_client: Redis[Any] = redis
        self._running: bool = False
        self.logger = logger

    async def _handle_message(self, raw_message: Any) -> None:
        try:
            if isinstance(raw_message, bytes):
                message_str = raw_message.decode("utf-8")
            else:
                message_str = str(raw_message)

            try:
                message_data = json.loads(message_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"EventBus: Failed to decode JSON from message: {e}")
                return

            try:
                event = BaseEvent(**message_data)
            except ValidationError as e:
                self.logger.error(
                    f"EventBus: Failed to parse message into BaseEvent: {e}"
                )
                return

            # Step 4: Route to handlers
            await self._route_to_handlers(event)

        except Exception as e:
            self.logger.error(f"EventBus: Unexpected error handling message: {e}")
