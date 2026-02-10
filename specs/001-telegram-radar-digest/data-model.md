# Data Model: Telegram Radar Digest MVP

**Date**: 2026-02-10
**Branch**: `001-telegram-radar-digest`

## Domain Entities

### ChannelInfo

Represents a Telegram channel discovered from the Radar folder.

| Field    | Type       | Required | Description                        |
|----------|------------|----------|------------------------------------|
| id       | int        | yes      | Telegram channel ID                |
| title    | str        | yes      | Channel display name               |
| username | str | None | no       | Channel username (for public channels) |

**Identity**: Unique by `id`.
**Source**: Resolved from `DialogFilter.include_peers`.

### Post

A message fetched from a channel.

| Field      | Type          | Required | Description                     |
|------------|---------------|----------|---------------------------------|
| id         | int           | yes      | Message ID within channel       |
| channel_id | int           | yes      | Parent channel ID               |
| channel_title | str        | yes      | Channel display name            |
| channel_username | str | None | no  | Channel username if public      |
| date       | datetime      | yes      | Message timestamp (UTC)         |
| text       | str           | yes      | Raw message text (untrimmed)    |
| permalink  | str           | yes      | Working t.me link               |
| comments   | list[Comment] | yes      | Fetched comments (may be empty) |

**Identity**: Unique by (`channel_id`, `id`).
**Lifecycle**: Created during fetch, consumed by BatchBuilder,
discarded after digest run.
**Validation**: Posts with empty `text` are filtered out during
fetch.

### Comment

A reply to a post, fetched from the discussion group.

| Field        | Type       | Required | Description                    |
|--------------|------------|----------|--------------------------------|
| id           | int        | yes      | Comment message ID             |
| author_name  | str | None | no       | Author display name            |
| date         | datetime   | yes      | Comment timestamp (UTC)        |
| text         | str        | yes      | Comment text (trimmed to max)  |
| link         | str | None | no       | Link to comment (best effort)  |

**Identity**: Unique by `id` within discussion group.
**Validation**: `text` trimmed to `COMMENT_MAX_LEN` (default 500
chars) at fetch time.

### PostPayload

A post with its comments serialized for batch building. This is
an intermediate representation.

| Field      | Type | Required | Description                       |
|------------|------|----------|-----------------------------------|
| post       | Post | yes      | The source post                   |
| comments   | list[Comment] | yes | Comments included within budget |
| char_count | int  | yes      | Total character count of payload  |

**Lifecycle**: Created by BatchBuilder, consumed during batching.

### Batch

A group of PostPayloads that fits within the character budget.

| Field      | Type              | Required | Description                |
|------------|-------------------|----------|----------------------------|
| payloads   | list[PostPayload] | yes      | Posts in this batch        |
| total_chars | int              | yes      | Total characters in batch  |
| post_count | int               | yes      | Number of posts            |
| comment_count | int            | yes      | Total comments across posts |

**Validation**: `total_chars <= LLM_MAX_CHARS_PER_BATCH`.
**Lifecycle**: Created by BatchBuilder, consumed by LLMSummarizer.

### DigestItem (LLM Output)

A structured summary item produced by the LLM for one or more
posts.

| Field         | Type         | Required | Constraints          |
|---------------|--------------|----------|----------------------|
| title         | str          | yes      |                      |
| why_relevant  | str          | yes      |                      |
| source_url    | str          | yes      | Valid URL            |
| post_quote    | str          | yes      | max 160 chars        |
| comment_quote | str | None   | no       | max 160 chars        |
| deadline      | str | None   | no       | ISO date YYYY-MM-DD  |
| action        | str | None   | no       |                      |
| channel       | str          | yes      |                      |
| date          | str          | yes      | ISO date YYYY-MM-DD  |
| priority      | float        | yes      | 0.0 to 1.0          |

**Validation**: Enforced by Pydantic v2 `Field` constraints +
`instructor` auto-retry on schema violation.

### DigestBatchResult (LLM Output)

The complete LLM response for one batch.

| Field         | Type             | Required | Description          |
|---------------|------------------|----------|----------------------|
| items         | list[DigestItem] | yes      | Summarized items     |
| batch_summary | str              | yes      | 1-3 line summary     |

### AppState (Persistent)

Stored in `data/state.json`.

```json
{
  "channels": {
    "<channel_id>": {
      "last_processed_message_id": 12345,
      "last_run_post_count": 8
    }
  },
  "last_run": {
    "timestamp": "2026-02-10T09:00:00Z",
    "channels_parsed": ["Channel A", "Channel B"]
  }
}
```

| Field                      | Type   | Description                      |
|----------------------------|--------|----------------------------------|
| channels                   | dict   | Per-channel state keyed by ID    |
| channels[].last_processed_message_id | int | Last fetched message ID |
| channels[].last_run_post_count | int | Posts fetched in last run      |
| last_run.timestamp         | str    | ISO timestamp of last run        |
| last_run.channels_parsed   | list   | Channel names from last run      |

**Lifecycle**: Loaded at run start, updated after successful digest,
written atomically. If missing or corrupted, treated as empty
(fresh start).

## Entity Relationships

```text
Folder "Radar"
  └── 1..N ChannelInfo
         └── 0..N Post
                └── 0..N Comment

BatchBuilder groups:
  Post + Comments → PostPayload
  PostPayloads → Batch (within char budget)

LLMSummarizer:
  Batch → DigestBatchResult → list[DigestItem]

DigestBuilder:
  list[DigestBatchResult] → formatted Markdown message
```

## Configuration Entity

All values from environment via `pydantic-settings`.

| Variable                | Type  | Default               |
|-------------------------|-------|-----------------------|
| TELEGRAM_API_ID         | int   | (required)            |
| TELEGRAM_API_HASH       | str   | (required)            |
| TELETHON_SESSION_PATH   | Path  | data/telethon.session |
| TG_BOT_TOKEN            | str   | (required)            |
| TG_OWNER_USER_ID        | int   | (required)            |
| RADAR_FOLDER_NAME       | str   | Radar                 |
| FETCH_SINCE_HOURS       | int   | 24                    |
| FETCH_LIMIT_PER_CHANNEL | int   | 50                    |
| COMMENTS_LIMIT_PER_POST | int   | 10                    |
| COMMENT_MAX_LEN         | int   | 500                   |
| POST_MAX_LEN            | int   | 4000                  |
| DIGEST_MAX_ITEMS        | int   | 20                    |
| DEADLINE_URGENT_DAYS    | int   | 7                     |
| LLM_PROVIDER            | str   | openai                |
| LLM_MODEL               | str   | (required)            |
| LLM_API_KEY             | str   | (required)            |
| LLM_MAX_CHARS_PER_BATCH | int   | 12000                 |
