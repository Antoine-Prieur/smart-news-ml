class EventBus:
    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Handlers register themselves for specific event types"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event_type: EventType, event_data) -> None:
        """Route to appropriate handlers automatically"""
        handlers = self._handlers.get(event_type, [])
        # Event bus handles the routing - no manual splitting needed!
