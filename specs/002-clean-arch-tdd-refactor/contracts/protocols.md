# Protocol Contracts: Clean Architecture & TDD Refactor

**Date**: 2026-02-10
**Branch**: `002-clean-arch-tdd-refactor`

## File: `src/telegram_radar/protocols.py`

All Protocol definitions. Imports only from `typing`, `models.py`,
and stdlib. No infrastructure imports.

### TelegramGateway

```python
class TelegramGateway(Protocol):
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
```

### Summarizer

```python
class Summarizer(Protocol):
    async def summarize_batch(self, batch: Batch) -> DigestBatchResult: ...

    async def check_health(self) -> bool: ...
```

### StateRepository

```python
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
```

## Consumer Import Patterns

### `pipeline.py` (application layer)

```python
# BEFORE (concrete imports)
from telegram_radar.gateway import TelegramClientGateway
from telegram_radar.summarizer import LLMSummarizer
from telegram_radar.state import StateManager

# AFTER (abstract imports)
from telegram_radar.protocols import TelegramGateway, Summarizer, StateRepository
```

### `bot.py` (presentation layer)

```python
# BEFORE (concrete imports)
from telegram_radar.gateway import TelegramClientGateway
from telegram_radar.summarizer import LLMSummarizer
from telegram_radar.state import StateManager

# AFTER (abstract imports)
from telegram_radar.protocols import TelegramGateway, Summarizer, StateRepository
```

### `__main__.py` (composition root)

```python
# UNCHANGED — continues importing concrete classes
from telegram_radar.gateway import TelegramClientGateway
from telegram_radar.summarizer import LLMSummarizer
from telegram_radar.state import StateManager
```

## StateManager API Changes

### Before

```python
class StateManager:
    def save(self, state: AppState) -> None: ...
    # No record_last_run method
    # No get_channel_state method
```

Callers use:
```python
state._state.last_run = LastRun(...)
state.save(state._state)
ch_state = state._state.channels.get(str(ch.id))
```

### After

```python
class StateManager:
    def save(self) -> None: ...  # no args, persists internal _state
    def record_last_run(self, channels_parsed: list[str]) -> None: ...
    def get_channel_state(self, channel_id: int) -> ChannelState | None: ...
```

Callers use:
```python
state.record_last_run(channels_parsed=parsed_names)
state.save()
ch_state = state.get_channel_state(ch.id)
```
