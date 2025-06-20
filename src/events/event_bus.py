import asyncio

from src.core.logger import Logger
from src.events.event_types import BaseEvent, EventHandler, EventType


class EventBus:
    """
    Asynchronous event bus for decoupled communication between components.

    Provides publish-subscribe pattern with async event handling, automatic error
    isolation, and graceful lifecycle management. Events are processed in order
    through an internal queue with concurrent handler execution per event.

    Features:
    - Type-safe event routing based on EventType
    - Concurrent handler execution with error isolation
    - Graceful start/stop with queue draining
    - Automatic error logging and recovery
    """

    def __init__(self, logger: Logger):
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._event_queue: asyncio.Queue[BaseEvent] = asyncio.Queue()
        self._running: bool = False
        self.logger = logger

    def _register_handlers(self) -> None:
        pass

    async def _drain_queue(self):
        while not self._event_queue.empty():
            try:
                event_data = self._event_queue.get_nowait()
                await self._handle_event(event_data)
                self._event_queue.task_done()
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                print(f"EventBus: Error draining queue: {e}")

    async def _safe_handle(self, handler: EventHandler, event_data: BaseEvent):
        try:
            await handler.handle(event_data)
        except Exception as e:
            self.logger.error(
                f"EventBus: Handler {handler.__class__.__name__} failed: {e}"
            )

    async def _handle_event(self, event_data: BaseEvent) -> None:
        handlers = self._handlers.get(event_data.event_type, [])

        if not handlers:
            return

        tasks = [self._safe_handle(handler, event_data) for handler in handlers]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_events_loop(self):
        while self._running:
            try:
                queued_event = await self._event_queue.get()

                await self._handle_event(queued_event)

                self._event_queue.task_done()

            except asyncio.CancelledError:
                self.logger.warning("EventBus: Processing loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"EventBus: Error processing event: {e}")

    def subscribe(self, handler: EventHandler):
        event_types = handler.event_types

        for event_type in event_types:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def publish(self, event_data: BaseEvent) -> None:
        self._event_queue.put_nowait(event_data)

    async def start(self):
        if self._running:
            self.logger.warning("EventBus: Already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._process_events_loop())
        self.logger.info("EventBus: Started")

    async def stop(self):
        if not self._running:
            self.logger.warning("EventBus: Already stopped")
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._drain_queue()
        self.logger.info("EventBus: Stopped")
