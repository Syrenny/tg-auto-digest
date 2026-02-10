from datetime import datetime

from pydantic import BaseModel, Field


class ChannelInfo(BaseModel):
    id: int
    title: str
    username: str | None = None


class Comment(BaseModel):
    id: int
    author_name: str | None = None
    date: datetime
    text: str
    link: str | None = None


class Post(BaseModel):
    id: int
    channel_id: int
    channel_title: str
    channel_username: str | None = None
    date: datetime
    text: str
    permalink: str
    comments: list[Comment] = Field(default_factory=list)


class PostPayload(BaseModel):
    post: Post
    comments: list[Comment]
    char_count: int


class Batch(BaseModel):
    payloads: list[PostPayload]
    total_chars: int
    post_count: int
    comment_count: int


# LLM output models (used with instructor)

class DigestItem(BaseModel):
    title: str
    why_relevant: str
    source_url: str
    post_quote: str = Field(max_length=160)
    comment_quote: str | None = Field(default=None, max_length=160)
    deadline: str | None = None
    action: str | None = None
    channel: str
    date: str
    priority: float = Field(ge=0.0, le=1.0)


class DigestBatchResult(BaseModel):
    items: list[DigestItem]
    batch_summary: str


# State persistence models

class ChannelState(BaseModel):
    last_processed_message_id: int
    last_run_post_count: int = 0


class LastRun(BaseModel):
    timestamp: str = ""
    channels_parsed: list[str] = Field(default_factory=list)


class AppState(BaseModel):
    channels: dict[str, ChannelState] = Field(default_factory=dict)
    last_run: LastRun = Field(default_factory=LastRun)
