from telegram_radar.digest_builder import DigestBuilder
from telegram_radar.models import DigestBatchResult, DigestItem


def _make_item(
    title: str = "Test",
    priority: float = 0.5,
    deadline: str | None = None,
    action: str | None = None,
) -> DigestItem:
    return DigestItem(
        title=title,
        why_relevant="Relevant because testing",
        source_url="https://t.me/test/1",
        post_quote="Some quote from post",
        deadline=deadline,
        action=action,
        channel="TestChannel",
        date="2026-01-01",
        priority=priority,
    )


class TestDigestBuilder:
    def setup_method(self) -> None:
        self.builder = DigestBuilder()

    def test_urgent_items_sorted_first(self) -> None:
        items = [
            _make_item("Later", deadline="2026-01-15", priority=0.3),
            _make_item("Sooner", deadline="2026-01-05", priority=0.1),
            _make_item("No deadline", priority=0.9),
        ]
        br = DigestBatchResult(items=items, batch_summary="Test")
        digest = self.builder.build_digest([br], max_items=10, urgent_days=30)
        lines = digest.split("\n")
        # Urgent section should appear before other highlights
        assert any("Urgent" in line for line in lines)
        # "Sooner" (earlier deadline) should appear before "Later"
        sooner_idx = next(
            i for i, line in enumerate(lines) if "Sooner" in line
        )
        later_idx = next(
            i for i, line in enumerate(lines) if "Later" in line
        )
        assert sooner_idx < later_idx

    def test_non_urgent_sorted_by_priority(self) -> None:
        items = [
            _make_item("Low", priority=0.2),
            _make_item("High", priority=0.9),
            _make_item("Mid", priority=0.5),
        ]
        br = DigestBatchResult(items=items, batch_summary="Test")
        digest = self.builder.build_digest([br], max_items=10, urgent_days=7)
        high_idx = digest.index("High")
        mid_idx = digest.index("Mid")
        low_idx = digest.index("Low")
        assert high_idx < mid_idx < low_idx

    def test_truncation_with_more_message(self) -> None:
        items = [_make_item(f"Item {i}", priority=0.5) for i in range(10)]
        br = DigestBatchResult(items=items, batch_summary="Test")
        digest = self.builder.build_digest([br], max_items=3, urgent_days=7)
        assert "7 more items" in digest

    def test_zero_items_produces_no_posts_message(self) -> None:
        digest = self.builder.build_digest([], max_items=10, urgent_days=7)
        assert "No new posts" in digest

    def test_markdown_formatting(self) -> None:
        items = [_make_item("Test Title", priority=0.8)]
        br = DigestBatchResult(items=items, batch_summary="Test")
        digest = self.builder.build_digest([br], max_items=10, urgent_days=7)
        assert "**Test Title**" in digest
        assert "[Source](" in digest
        assert '"Some quote from post"' in digest
