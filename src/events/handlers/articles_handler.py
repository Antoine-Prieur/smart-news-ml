from typing import Any, cast

from bson import ObjectId
from pydantic import BaseModel, field_validator

from src.events.event_types import BaseEvent, EventType
from src.services.article_service import ArticleService


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


class ArticlesHandler:
    def __init__(self, article_service: ArticleService) -> None:
        self.article_service = article_service

    @property
    def event_types(self) -> list[EventType]:
        return [EventType.ARTICLES_EVENT]

    async def handle(self, events_data: list[BaseEvent]) -> None:
        event_contents = [
            ArticleEvent.model_validate(event_data.content)
            for event_data in events_data
        ]

        await self.article_service.process_articles(event_contents)

        return None
