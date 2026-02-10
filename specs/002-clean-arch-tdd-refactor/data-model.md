# Data Model: Clean Architecture & TDD Refactor

**Date**: 2026-02-10
**Branch**: `002-clean-arch-tdd-refactor`

## Overview

This refactor introduces no new domain entities. It introduces three
Protocol definitions that abstract existing infrastructure classes,
and adds public methods to `StateManager` to eliminate encapsulation
violations.

## New Protocol Definitions

All Protocols live in `src/telegram_radar/protocols.py`.

### TelegramGateway Protocol

Abstracts the Telegram client gateway. Consumed by `pipeline.py` and
`bot.py`.

| Method | Parameters | Return | Consumed By |
|--------|-----------|--------|-------------|
| `get_radar_channels` | (none) | `list[ChannelInfo]` | pipeline, bot |
| `fetch_posts` | `channel: ChannelInfo, since_message_id: int \| None, since_hours: int, limit: int` | `list[Post]` | pipeline |
| `fetch_comments` | `channel: ChannelInfo, post: Post, limit: int, max_comment_len: int` | `list[Comment]` | pipeline |
| `check_health` | (none) | `bool` | bot |

Note: `start()` and `stop()` are NOT in the Protocol — they are
lifecycle methods consumed only by the composition root
(`__main__.py`), which imports concrete classes.

### Summarizer Protocol

Abstracts the LLM summarizer. Consumed by `pipeline.py` and `bot.py`.

| Method | Parameters | Return | Consumed By |
|--------|-----------|--------|-------------|
| `summarize_batch` | `batch: Batch` | `DigestBatchResult` | pipeline |
| `check_health` | (none) | `bool` | bot |

### StateRepository Protocol

Abstracts state persistence. Consumed by `pipeline.py` and `bot.py`.

| Method | Parameters | Return | Consumed By |
|--------|-----------|--------|-------------|
| `load` | (none) | `AppState` | pipeline, bot |
| `save` | (none) | `None` | pipeline |
| `get_last_message_id` | `channel_id: int` | `int \| None` | pipeline, bot |
| `update_channel` | `channel_id: int, last_message_id: int, post_count: int` | `None` | pipeline |
| `record_last_run` | `channels_parsed: list[str]` | `None` | pipeline |
| `get_channel_state` | `channel_id: int` | `ChannelState \| None` | bot |

Note: `record_last_run` and `get_channel_state` are new methods
that replace current private attribute access.

## Modified Entity: StateManager

### New Public Methods

| Method | Description |
|--------|-------------|
| `record_last_run(channels_parsed: list[str])` | Sets `_state.last_run` with current UTC timestamp and given channel names, then calls `save()` |
| `get_channel_state(channel_id: int) -> ChannelState \| None` | Returns `ChannelState` for the given channel ID, or None if not tracked |

### Modified Method

| Method | Change |
|--------|--------|
| `save()` | Signature changes from `save(state: AppState)` to `save()` (no args). Persists internal `_state`. |

### Impact on Existing Tests

The `tests/unit/test_state.py` file calls `save(state)` with an
explicit `AppState` argument. This call pattern must be updated to:
1. Use `load()` to initialize internal state
2. Use `update_channel()` / `record_last_run()` to mutate
3. Use `save()` (no args) to persist

**Exception to FR-011**: Since `save()` signature changes, the
existing `test_state.py` tests WILL need minor updates to call
`save()` without arguments. This is expected — the test file
exercises the public API of `StateManager`, and that API is
intentionally changing. The tests themselves are for `StateManager`,
not for the pipeline/bot consumers.

## Unchanged Entities

All domain models in `models.py` remain unchanged:
- `ChannelInfo`, `Post`, `Comment`, `PostPayload`, `Batch`
- `DigestItem`, `DigestBatchResult`
- `ChannelState`, `LastRun`, `AppState`

All pure-logic builders remain unchanged:
- `BatchBuilder` (in `batch_builder.py`)
- `DigestBuilder` (in `digest_builder.py`)
