# Internal Component Interfaces

**Date**: 2026-02-10

These are the key method signatures defining component boundaries.
All methods are async.

## TelegramClientGateway

```python
class TelegramClientGateway:
    async def start(self) -> None
    async def stop(self) -> None
    async def get_radar_channels(self) -> list[ChannelInfo]
    async def fetch_posts(
        self,
        channel: ChannelInfo,
        since_message_id: int | None,
        since_hours: int,
        limit: int,
    ) -> list[Post]
    async def fetch_comments(
        self,
        channel: ChannelInfo,
        post: Post,
        limit: int,
        max_comment_len: int,
    ) -> list[Comment]
    async def check_health(self) -> bool
```

## BatchBuilder

```python
class BatchBuilder:
    def build_batches(
        self,
        posts: list[Post],
        max_chars_per_batch: int,
    ) -> list[Batch]
```

**Note**: `build_batches` is synchronous (pure computation, no I/O).
Deterministic and unit-testable.

## LLMSummarizer

```python
class LLMSummarizer:
    async def summarize_batch(
        self,
        batch: Batch,
    ) -> DigestBatchResult

    async def check_health(self) -> bool
```

## DigestBuilder

```python
class DigestBuilder:
    def build_digest(
        self,
        batch_results: list[DigestBatchResult],
        max_items: int,
        urgent_days: int,
    ) -> str
```

**Note**: `build_digest` is synchronous (pure formatting).
Returns Markdown string.

## StateManager

```python
class StateManager:
    def load(self) -> AppState
    def save(self, state: AppState) -> None
    def get_last_message_id(self, channel_id: int) -> int | None
    def update_channel(
        self,
        channel_id: int,
        last_message_id: int,
        post_count: int,
    ) -> None
```

**Note**: Synchronous file I/O (JSON read/write). Acceptable for
MVP since state file is small and accessed infrequently.

## Digest Pipeline (Orchestrator)

```python
async def run_digest(
    gateway: TelegramClientGateway,
    batch_builder: BatchBuilder,
    summarizer: LLMSummarizer,
    digest_builder: DigestBuilder,
    state: StateManager,
    settings: Settings,
) -> str
```

Returns the formatted digest message string. The bot controller
or scheduler calls this and sends the result.
