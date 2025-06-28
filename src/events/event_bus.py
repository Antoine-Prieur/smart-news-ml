import asyncio
import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from redis.asyncio import Redis

from src.core.logger import Logger
from src.events.event_types import BaseEvent, EventHandler, EventType


@dataclass
class QueueParams:
    concurrent_calls: int
    batch_size: int


class EventBus:
    def __init__(self, logger: Logger, redis: "Redis[Any]"):
        self._queues: dict[str, QueueParams] = {}
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._event_to_queue: dict[EventType, str] = {}

        self._redis_client: Redis[Any] = redis
        self._running: bool = False
        self.logger = logger

    async def start(self) -> None:
        if self._running:
            self.logger.warning("EventBus: Already running")

        try:
            await self._redis_client.ping()
        except Exception as e:
            self.logger.error(f"EventBus: Cannot connect to Redis: {e}")
            raise

        self._running = True

        for queue_name in self._queues.keys():
            asyncio.create_task(self._start_event_queue(queue_name))

    async def publish_async(self, event_data: BaseEvent) -> None:
        try:
            queue_name = self._event_to_queue[event_data.event_type]
            await self._redis_client.rpush(queue_name, event_data.model_dump_json())
            self.logger.debug(
                f"EventBus: Published {event_data.event_type} to {queue_name}"
            )
        except KeyError as e:
            self.logger.error(
                f"EventBus: Failed to publish event, event {event_data.event_type} not registered: {e}"
            )
            raise
        except Exception as e:
            self.logger.error(f"EventBus: Failed to publish event: {e}")
            raise

    def publish(self, event_data: BaseEvent) -> None:
        """Synchronously publish an event (creates async task)."""
        asyncio.create_task(self.publish_async(event_data))

    def register_queue(self, queue_name: str, queue_params: QueueParams) -> None:
        if queue_name in self._queues:
            self.logger.warning(f"EventBus: queue {queue_name} already registered")
            return

        self._queues[queue_name] = queue_params

    def subscribe(self, queue_name: str, handler: EventHandler) -> None:
        event_types = handler.event_types

        if queue_name not in self._queues:
            raise Exception(
                f"EventBus: Queue '{queue_name}' must be registered before subscribing handlers. Available queues: {list(self._queues.keys())}"
            )

        for event_type in event_types:
            if event_type in self._event_to_queue:
                raise Exception(
                    f"EventBus: EventType conflict error subscribing handler to {queue_name} - {event_type} has already been linked to queue {self._event_to_queue[event_type]}"
                )

            self._event_to_queue[event_type] = queue_name

            if event_type not in self._handlers:
                self._handlers[event_type] = []

            self._handlers[event_type].append(handler)

        self.logger.debug(
            f"EventBus: Registered handler {handler.__class__.__name__} for types {event_types}"
        )

    async def _start_event_queue(self, queue_name: str) -> None:
        if queue_name not in self._queues:
            raise Exception(f"EventBus: Could not find queue named {queue_name}")

        queue_params = self._queues[queue_name]
        semaphore = asyncio.Semaphore(queue_params.concurrent_calls)

        async def process_event() -> None:
            async with semaphore:
                try:
                    result = await self._redis_client.blpop([queue_name], timeout=1)

                    if result is None:
                        return None

                    _, event_data = result
                    try:
                        message_data = json.loads(event_data)

                    except json.JSONDecodeError as e:
                        self.logger.error(
                            f"EventBus: Failed to decode JSON from message: {e}"
                        )
                        return

                    try:
                        event = BaseEvent.model_validate(message_data)

                    except ValidationError as e:
                        self.logger.error(
                            f"EventBus: Failed to parse message into BaseEvent: {e}"
                        )
                        return

                    await self._route_to_handlers(event)

                except Exception as e:
                    self.logger.error(
                        f"EventBus: Unexpected error handling message: {e}"
                    )

        while self._running:
            try:
                # TODO: implement real batch processing
                tasks = [process_event() for _ in range(queue_params.batch_size)]
                await asyncio.gather(*tasks, return_exceptions=True)

            except asyncio.CancelledError:
                self.logger.warning(
                    f"EventBus: Processing loop for {queue_name} cancelled"
                )
                break
            except Exception as e:
                self.logger.error(
                    f"EventBus: Unexpected error in {queue_name} loop: {e}"
                )
                await asyncio.sleep(0.1)

    async def _route_to_handlers(self, event_data: BaseEvent) -> None:
        handlers = self._handlers.get(event_data.event_type, [])

        if not handlers:
            self.logger.debug(
                f"EventBus: No handlers for event type {event_data.event_type}"
            )
            return

        tasks = [self._handle_event(handler, event_data) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_event(self, handler: EventHandler, event_data: BaseEvent) -> None:
        try:
            await handler.handle(event_data)
        except Exception as e:
            self.logger.error(
                f"EventBus: Handler {handler.__class__.__name__} failed: {e}"
            )
            raise
