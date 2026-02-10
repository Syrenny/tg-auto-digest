# Research: Telegram Radar Digest MVP

**Date**: 2026-02-10
**Branch**: `001-telegram-radar-digest`

## R-001: Telethon Dialog Filters (Folder Discovery)

**Decision**: Use `GetDialogFiltersRequest()` to read all dialog
filters, iterate to find the folder by `filter.title.text`, then
resolve `include_peers` via `client.get_entity()`.

**Rationale**: This is the only Telethon API for accessing folder
metadata. The `DialogFilter` object exposes `include_peers` as a
list of `InputPeer` objects that can be resolved to full channel
entities.

**Key pattern**:
```python
from telethon import functions, types

result = await client(functions.messages.GetDialogFiltersRequest())
for f in result.filters:
    if hasattr(f, 'title') and f.title.text == folder_name:
        for peer in f.include_peers:
            entity = await client.get_entity(peer)
```

**Alternatives considered**:
- Manual channel list in config: rejected — defeats the purpose of
  folder-based discovery.

## R-002: Fetching Comments on Channel Posts

**Decision**: Use `client.iter_messages(channel, reply_to=post_id)`
to fetch top-level comments. Check `message.replies` before
attempting. Gracefully skip if unavailable.

**Rationale**: Telethon's high-level `iter_messages` with
`reply_to` is the simplest approach. For channels with linked
discussion groups, comments exist in the discussion group — but
Telethon resolves this transparently when using `reply_to` on
the original channel.

**Key pattern**:
```python
if message.replies and message.replies.replies > 0:
    async for comment in client.iter_messages(
        channel, reply_to=message.id, limit=comments_limit
    ):
        # Process comment
```

**Limitations for MVP**:
- Nested replies (replies-to-replies) may appear — take only
  top-level by limiting fetch count.
- Some channels disable comments — `message.replies` will be None.
- `MsgIdInvalidError` possible for deleted posts — catch and skip.

**Alternatives considered**:
- Raw `GetRepliesRequest`: more control but more boilerplate.
  Unnecessary for MVP.
- Fetching from linked discussion group explicitly: more complex,
  not needed since `reply_to` handles this transparently.

## R-003: Building t.me Permalinks

**Decision**: Construct links using `https://t.me/{username}/{msg_id}`
for public channels and `https://t.me/c/{channel_id}/{msg_id}` for
private channels (stripping the `-100` prefix from channel IDs).

**Rationale**: These are the standard Telegram deep link formats.
Public channels have a username; private channels use the numeric
channel ID without the `-100` prefix.

**Key pattern**:
```python
def build_permalink(channel, message_id: int) -> str:
    if channel.username:
        return f"https://t.me/{channel.username}/{message_id}"
    # Private: channel.id might be e.g. 1234567890 (Telethon v2)
    # or -1001234567890 (older). Strip -100 prefix if present.
    cid = str(channel.id)
    if cid.startswith('-100'):
        cid = cid[4:]
    return f"https://t.me/c/{cid}/{message_id}"
```

**Comment links**: Use same pattern with discussion group entity
and comment message ID. Best-effort for MVP.

## R-004: Telethon + Bot API Coexistence

**Decision**: Run Telethon user client and a Bot API library in the
same `asyncio` event loop using `asyncio.gather()` or concurrent
tasks.

**Rationale**: Both libraries are fully async and share the running
event loop without conflicts. No special integration needed beyond
avoiding `telethon.sync` module.

**Key pattern**:
```python
async def main():
    telethon_client = TelegramClient(...)
    await telethon_client.start()

    bot_app = ...  # Bot API application
    await asyncio.gather(
        telethon_client.run_until_disconnected(),
        bot_app.run_polling()
    )
```

## R-005: Bot API Library Choice

**Decision**: Use `python-telegram-bot` v20+ (async).

**Rationale**: Lighter dependencies (only httpx), extensive
documentation, gentler learning curve. For a 3-command bot this is
sufficient. It also has built-in job queue integration with
APScheduler.

**Alternatives considered**:
- `aiogram` v3: more performant but heavier dependencies (aiohttp,
  magic-filter). Overkill for 3 commands in a personal tool.

## R-006: Instructor + Structured LLM Outputs

**Decision**: Use `instructor.from_openai(AsyncOpenAI())` with
Pydantic v2 models and `max_retries=3` for automatic schema
enforcement.

**Rationale**: `instructor` validates LLM output against Pydantic
models and auto-retries on validation failures, sending error
context back to the LLM. This eliminates manual parsing.

**Key pattern**:
```python
import instructor
from openai import AsyncOpenAI

client = instructor.from_openai(AsyncOpenAI())

result = await client.chat.completions.create(
    model=settings.llm_model,
    response_model=DigestBatchResult,
    max_retries=3,
    messages=[...]
)
```

**Field constraints** (Pydantic v2):
```python
post_quote: str = Field(max_length=160)
priority: float = Field(ge=0.0, le=1.0)
date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}")
```

## R-007: APScheduler Async Usage

**Decision**: Use APScheduler v3.x (stable, 3.11.x) with
`AsyncIOScheduler` and `CronTrigger` for the daily job. Manual
trigger calls the digest function directly.

**Rationale**: APScheduler v4 is still alpha. v3's
`AsyncIOScheduler` integrates cleanly with asyncio and is
production-ready.

**Key pattern**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()
scheduler.add_job(
    run_digest,
    trigger=CronTrigger(hour=9, minute=0),
    id='daily_digest',
    replace_existing=True,
)
scheduler.start()
```

**Manual trigger**: Call `await run_digest()` directly from the
`/digest_now` bot handler — no scheduler involvement needed.

**Alternatives considered**:
- APScheduler v4 alpha: unstable API, not production-ready.
- `python-telegram-bot` built-in job queue: possible but ties
  scheduling to bot lifecycle; separate scheduler is cleaner.
