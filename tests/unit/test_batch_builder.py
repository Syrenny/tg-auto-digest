from datetime import datetime, timezone

from telegram_radar.batch_builder import BatchBuilder
from telegram_radar.models import Comment, Post


def _make_post(
    text: str = "Hello world",
    post_id: int = 1,
    comments: list[Comment] | None = None,
) -> Post:
    return Post(
        id=post_id,
        channel_id=100,
        channel_title="TestChannel",
        channel_username="test",
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        text=text,
        permalink="https://t.me/test/1",
        comments=comments or [],
    )


def _make_comment(text: str = "Nice post", comment_id: int = 1) -> Comment:
    return Comment(
        id=comment_id,
        author_name="User",
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        text=text,
    )


class TestBatchBuilder:
    def setup_method(self) -> None:
        self.builder = BatchBuilder()

    def test_single_post_fits_in_batch(self) -> None:
        posts = [_make_post("Short post")]
        batches = self.builder.build_batches(posts, max_chars_per_batch=5000)
        assert len(batches) == 1
        assert batches[0].post_count == 1

    def test_multiple_posts_split_across_batches(self) -> None:
        posts = [
            _make_post("A" * 400, post_id=i) for i in range(10)
        ]
        batches = self.builder.build_batches(posts, max_chars_per_batch=1000)
        assert len(batches) > 1
        total_posts = sum(b.post_count for b in batches)
        assert total_posts == 10

    def test_post_exceeding_budget_is_skipped(self) -> None:
        posts = [_make_post("X" * 6000)]
        batches = self.builder.build_batches(posts, max_chars_per_batch=5000)
        assert len(batches) == 0

    def test_comments_trimmed_to_fit_budget(self) -> None:
        comments = [
            _make_comment("C" * 200, comment_id=i) for i in range(20)
        ]
        posts = [_make_post("Short", comments=comments)]
        batches = self.builder.build_batches(posts, max_chars_per_batch=1000)
        assert len(batches) == 1
        payload = batches[0].payloads[0]
        assert len(payload.comments) < 20

    def test_empty_post_list_returns_empty(self) -> None:
        batches = self.builder.build_batches([], max_chars_per_batch=5000)
        assert len(batches) == 0

    def test_batch_stats_correct(self) -> None:
        comments = [_make_comment("C1"), _make_comment("C2", comment_id=2)]
        posts = [_make_post("Hello", comments=comments)]
        batches = self.builder.build_batches(posts, max_chars_per_batch=5000)
        assert len(batches) == 1
        b = batches[0]
        assert b.post_count == 1
        assert b.comment_count == 2
        assert b.total_chars > 0
