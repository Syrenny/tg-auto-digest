from typing import Protocol

from telegram_radar.models import (
    AppState,
    Batch,
    ChannelInfo,
    ChannelState,
    Comment,
    DigestBatchResult,
    Post,
)


class TelegramGateway(Protocol):
    async def connect(self) -> None: ...

    async def is_authorized(self) -> bool: ...

    async def send_code(self, phone: str) -> None: ...

    async def sign_in_code(self, phone: str, code: str) -> None: ...

    async def sign_in_password(self, password: str) -> None: ...

    async def get_radar_channels(self) -> list[ChannelInfo]: ...

    async def fetch_posts(
        self,
        channel: ChannelInfo,
        since_message_id: int | None,
        since_hours: int,
        limit: int,
    ) -> list[Post]: ...

    async def fetch_comments(
        self,
        channel: ChannelInfo,
        post: Post,
        limit: int,
        max_comment_len: int,
    ) -> list[Comment]: ...

    async def check_health(self) -> bool: ...


class Summarizer(Protocol):
    async def summarize_batch(self, batch: Batch) -> DigestBatchResult: ...

    async def check_health(self) -> bool: ...


class StateRepository(Protocol):
    def load(self) -> AppState: ...

    def save(self) -> None: ...

    def get_last_message_id(self, channel_id: int) -> int | None: ...

    def update_channel(
        self,
        channel_id: int,
        last_message_id: int,
        post_count: int,
    ) -> None: ...

    def record_last_run(self, channels_parsed: list[str]) -> None: ...

    def get_channel_state(self, channel_id: int) -> ChannelState | None: ...
