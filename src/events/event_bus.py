import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable

from pydantic import ValidationError
from redis.asyncio import Redis

from src.core.logger import Logger
from src.events.event_types import BaseEvent, EventHandler, EventType


@dataclass
class QueueParams:
    batch_size: int


class EventBus:
    def __init__(self, logger: Logger, redis: "Redis[Any]"):
        self._queues: dict[str, QueueParams] = {}
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._event_to_queue: dict[EventType, str] = {}

        self._tasks: dict[str, asyncio.Task[Any]] = {}

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
            task = asyncio.create_task(self._start_event_queue(queue_name))
            self._tasks[queue_name] = task

    async def stop(self) -> None:
        if not self._running:
            self.logger.warning("EventBus: Already stopped")
            return

        self.logger.info("EventBus: Stopping...")
        self._running = False

        for task in self._tasks.values():
            if not task.done():
                task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        self._tasks.clear()
        self.logger.info("EventBus: Stopped")

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
        asyncio.create_task(self.publish_async(event_data))

    def register_queue(self, queue_name: str, batch_size: int) -> None:
        if queue_name in self._queues:
            self.logger.warning(f"EventBus: queue {queue_name} already registered")
            return

        self._queues[queue_name] = QueueParams(batch_size=batch_size)

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

        async def process_event_batch(event_batch: list[Any]) -> None:
            base_events: list[BaseEvent] = []

            for event_data in event_batch:
                try:
                    message_data = json.loads(event_data)

                except json.JSONDecodeError as e:
                    self.logger.error(
                        f"EventBus: Failed to decode JSON from message: {e}"
                    )
                    continue

                try:
                    event = BaseEvent.model_validate(message_data)

                except ValidationError as e:
                    self.logger.error(
                        f"EventBus: Failed to parse message into BaseEvent: {e}"
                    )
                    return

                base_events.append(event)

            try:
                await self._route_to_handlers(base_events)
            except Exception as e:
                self.logger.error(f"EventBus: Unexpected error handling message: {e}")

        while self._running:
            try:
                event_batch: list[Any] = []
                for _ in range(queue_params.batch_size):
                    result = await self._redis_client.blpop([queue_name], timeout=0.1)
                    if result:
                        event_batch.append(result[1])
                    else:
                        break

                if event_batch:
                    await process_event_batch(event_batch)

            except asyncio.CancelledError:
                self.logger.warning(
                    f"EventBus: Processing loop for {queue_name} cancelled"
                )
                break
            except Exception as e:
                self.logger.error(
                    f"EventBus: Unexpected error in {queue_name} loop: {e}"
                )
                await asyncio.sleep(1)

    async def _route_to_handlers(self, events_data: list[BaseEvent]) -> None:
        if not events_data:
            return

        events_by_type: dict[EventType, list[BaseEvent]] = {}
        for event in events_data:
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = []
            events_by_type[event.event_type].append(event)

        tasks: list[Awaitable[Any]] = []

        for event_type, events in events_by_type.items():
            handlers = self._handlers.get(event_type, [])

            if not handlers:
                self.logger.debug(
                    f"EventBus: No handlers for event type {event_type} ({len(events)} events)"
                )
                continue

            for handler in handlers:
                tasks.append(self._handle_events(handler, events))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_events(
        self, handler: EventHandler, events_data: list[BaseEvent]
    ) -> None:
        try:
            await handler.handle(events_data)
        except Exception as e:
            self.logger.error(
                f"EventBus: Handler {handler.__class__.__name__} failed: {e}"
            )
            raise
