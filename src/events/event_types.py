from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, cast

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator


class EventType(Enum):
    METRICS_EVENT = "metrics_event"
    ARTICLES_EVENT = "articles_event"


class BaseEvent(BaseModel):
    """Base event model for all events in the system."""

    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content: Any

    class Config:
        arbitrary_types_allowed = True


class EventHandler(Protocol):
    @property
    def event_types(self) -> list[EventType]: ...

    async def handle(self, events_data: list[BaseEvent]) -> None: ...


# Events
class ArticleEvent(BaseModel):
    id: ObjectId
    title: str | None = None
    description: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def parse_object_id(cls, v: Any) -> ObjectId | None:
        """Convert MongoDB ObjectId format to ObjectId"""
        if v is None:
            return None

        if isinstance(v, dict) and "$oid" in v:
            v = cast(dict[Any, Any], v)
            return ObjectId(v["$oid"])

        if isinstance(v, str):
            return ObjectId(v)

        if isinstance(v, ObjectId):
            return v

        raise ValueError(f"Could not parse the _id {v}")

    @classmethod
    def create_base_event(
        cls, id: ObjectId, title: str | None, description: str | None
    ) -> BaseEvent:
        instance = cls(id=id, title=title, description=description)

        return BaseEvent(event_type=EventType.ARTICLES_EVENT, content=instance)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
