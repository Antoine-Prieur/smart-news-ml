from src.events.event_types import ArticleEvent, BaseEvent, EventType
from src.services.article_service import ArticleService


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
