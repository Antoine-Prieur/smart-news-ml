from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    id: str | None = None
    name: str


class ArticleDocument(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    source: SourceDocument
    author: str | None = None
    title: str | None = None
    description: str | None = None
    url: str | None = None
    url_to_image: str | None = None
    published_at: datetime | None = None
    content: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
