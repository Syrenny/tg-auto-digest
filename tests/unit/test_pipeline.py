from datetime import datetime, timezone

import pytest

from telegram_radar.batch_builder import BatchBuilder
from telegram_radar.digest_builder import DigestBuilder
from telegram_radar.models import (
    AppState,
    Batch,
    ChannelInfo,
    ChannelState,
    Comment,
    DigestBatchResult,
    DigestItem,
    Post,
)
from telegram_radar.pipeline import run_digest
from telegram_radar.settings import Settings


# --- Fake Protocol implementations (concrete stubs) ---


class FakeGateway:
    def __init__(
        self,
        channels: list[ChannelInfo] | None = None,
        posts_by_channel: dict[int, list[Post]] | None = None,
        comments_by_post: dict[int, list[Comment]] | None = None,
    ) -> None:
        self._channels = channels or []
        self._posts = posts_by_channel or {}
        self._comments = comments_by_post or {}

    async def get_radar_channels(self) -> list[ChannelInfo]:
        return self._channels

    async def fetch_posts(
        self,
        channel: ChannelInfo,
        since_message_id: int | None,
        since_hours: int,
        limit: int,
    ) -> list[Post]:
        return self._posts.get(channel.id, [])

    async def fetch_comments(
        self,
        channel: ChannelInfo,
        post: Post,
        limit: int,
        max_comment_len: int,
    ) -> list[Comment]:
        return self._comments.get(post.id, [])

    async def check_health(self) -> bool:
        return True


class FakeSummarizer:
    def __init__(
        self,
        results: list[DigestBatchResult] | None = None,
        error_on_call: int | None = None,
    ) -> None:
        self._results = results or []
        self._call_count = 0
        self._error_on_call = error_on_call

    async def summarize_batch(self, batch: Batch) -> DigestBatchResult:
        idx = self._call_count
        self._call_count += 1
        if self._error_on_call is not None and idx == self._error_on_call:
            raise RuntimeError("LLM summarization failed")
        return self._results[idx]

    async def check_health(self) -> bool:
        return True


class FakeStateRepository:
    def __init__(self) -> None:
        self._state = AppState()
        self._save_count = 0
        self._last_run_calls: list[list[str]] = []

    def load(self) -> AppState:
        return self._state

    def save(self) -> None:
        self._save_count += 1

    def get_last_message_id(self, channel_id: int) -> int | None:
        ch = self._state.channels.get(str(channel_id))
        return ch.last_processed_message_id if ch else None

    def update_channel(
        self,
        channel_id: int,
        last_message_id: int,
        post_count: int,
    ) -> None:
        self._state.channels[str(channel_id)] = ChannelState(
            last_processed_message_id=last_message_id,
            last_run_post_count=post_count,
        )

    def record_last_run(self, channels_parsed: list[str]) -> None:
        self._last_run_calls.append(channels_parsed)

    def get_channel_state(self, channel_id: int) -> ChannelState | None:
        return self._state.channels.get(str(channel_id))


# --- Helpers ---


def _make_settings() -> Settings:
    return Settings(
        telegram_api_id=12345,
        telegram_api_hash="testhash",
        tg_bot_token="bot:token",
        tg_owner_user_id=1,
        llm_model="test-model",
        llm_api_key="test-key",
        llm_max_chars_per_batch=50000,
    )


def _make_post(post_id: int, channel_id: int, channel_title: str) -> Post:
    return Post(
        id=post_id,
        channel_id=channel_id,
        channel_title=channel_title,
        date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        text=f"Post {post_id} content for testing",
        permalink=f"https://t.me/test/{post_id}",
    )


def _make_comment(comment_id: int) -> Comment:
    return Comment(
        id=comment_id,
        author_name="Tester",
        date=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        text=f"Comment {comment_id} text",
    )


def _make_digest_item(title: str, priority: float = 0.5) -> DigestItem:
    return DigestItem(
        title=title,
        why_relevant="Test relevance",
        source_url="https://t.me/test/1",
        post_quote="Test quote here",
        channel="Test Channel",
        date="2026-01-15",
        priority=priority,
    )


# --- Tests ---


class TestRunDigest:
    async def test_digest_successful_flow(self) -> None:
        channel = ChannelInfo(id=1, title="Test Channel", username="testch")
        post1 = _make_post(101, channel.id, channel.title)
        post2 = _make_post(102, channel.id, channel.title)
        comment = _make_comment(201)

        gateway = FakeGateway(
            channels=[channel],
            posts_by_channel={1: [post1, post2]},
            comments_by_post={101: [comment], 102: []},
        )
        batch_result = DigestBatchResult(
            items=[
                _make_digest_item("Item 1", 0.9),
                _make_digest_item("Item 2", 0.7),
            ],
            batch_summary="Test batch summary",
        )
        summarizer = FakeSummarizer(results=[batch_result])
        state = FakeStateRepository()
        settings = _make_settings()

        result = await run_digest(
            gateway=gateway,
            batch_builder=BatchBuilder(),
            summarizer=summarizer,
            digest_builder=DigestBuilder(),
            state=state,
            settings=settings,
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain digest formatting
        assert "Item 1" in result or "Item 2" in result
        # State should have been updated
        assert state._save_count == 1
        assert len(state._last_run_calls) == 1
        assert state._last_run_calls[0] == ["Test Channel"]
        # Channel state updated with max post id
        ch_state = state.get_channel_state(1)
        assert ch_state is not None
        assert ch_state.last_processed_message_id == 102

    async def test_digest_no_channels(self) -> None:
        gateway = FakeGateway(channels=[])
        summarizer = FakeSummarizer()
        state = FakeStateRepository()
        settings = _make_settings()

        result = await run_digest(
            gateway=gateway,
            batch_builder=BatchBuilder(),
            summarizer=summarizer,
            digest_builder=DigestBuilder(),
            state=state,
            settings=settings,
        )

        assert "No channels found" in result or "Error" in result
        # State should not have been saved
        assert state._save_count == 0

    async def test_digest_no_new_posts(self) -> None:
        channel = ChannelInfo(id=1, title="Empty Channel")
        gateway = FakeGateway(
            channels=[channel],
            posts_by_channel={1: []},
        )
        summarizer = FakeSummarizer()
        state = FakeStateRepository()
        settings = _make_settings()

        result = await run_digest(
            gateway=gateway,
            batch_builder=BatchBuilder(),
            summarizer=summarizer,
            digest_builder=DigestBuilder(),
            state=state,
            settings=settings,
        )

        assert "No new posts" in result
        # State should have been saved (last_run recorded)
        assert state._save_count == 1
        assert len(state._last_run_calls) == 1

    async def test_digest_summarizer_error_propagates(self) -> None:
        channel = ChannelInfo(id=1, title="Test Channel")
        post = _make_post(101, channel.id, channel.title)

        gateway = FakeGateway(
            channels=[channel],
            posts_by_channel={1: [post]},
        )
        summarizer = FakeSummarizer(error_on_call=0)
        state = FakeStateRepository()
        settings = _make_settings()

        with pytest.raises(RuntimeError, match="LLM summarization failed"):
            await run_digest(
                gateway=gateway,
                batch_builder=BatchBuilder(),
                summarizer=summarizer,
                digest_builder=DigestBuilder(),
                state=state,
                settings=settings,
            )
