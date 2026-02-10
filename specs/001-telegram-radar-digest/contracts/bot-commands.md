# Bot Commands Contract

**Date**: 2026-02-10

This project uses Telegram Bot API (not REST/GraphQL), so contracts
are defined as bot command specifications.

## Authorization

All commands require `update.effective_user.id == TG_OWNER_USER_ID`.
Unauthorized requests are silently ignored.

## Commands

### /health

**Purpose**: Check connectivity of Telegram client and LLM provider.

**Input**: None.

**Response** (Markdown):
```
Health Status:
• Telegram: ✅ Connected / ❌ Disconnected
• LLM: ✅ Reachable / ❌ Unreachable
```

**Checks**:
- Telegram: Call a lightweight Telethon method (e.g., `get_me()`).
- LLM: Send a minimal completion request and verify response.

### /channels

**Purpose**: List monitored channels and last-run post counts.

**Input**: None.

**Response** (Markdown):
```
Radar Channels:
• Channel Name (@username) — 12 posts last run
• Private Channel — 5 posts last run
• Another Channel (@another) — no data yet
```

**Data source**: Current Radar folder channels + `state.json`
last-run stats.

### /digest_now

**Purpose**: Trigger immediate digest generation and delivery.

**Input**: None.

**Response**:
1. Acknowledgment: "Generating digest..."
2. Full digest message (same format as scheduled digest).
3. On error: "Digest failed: {error summary}".

**Behavior**:
- Runs the same pipeline as the scheduled job.
- Updates `state.json` after completion.
- Does NOT reset the scheduled job timer.

## Digest Message Format

Sent by both scheduled job and `/digest_now`.

```markdown
📋 Digest — 2026-02-10

🔴 Urgent (deadline within 7 days):
• **Title** — Why relevant
  📅 Deadline: 2026-02-15 | Action: Register
  💬 "post quote here..."
  🔗 [Source](https://t.me/channel/123)

📌 Other highlights:
• **Title** — Why relevant
  💬 "post quote here..."
  💬 Comment: "comment quote here..."
  🔗 [Source](https://t.me/channel/456)

...and 5 more items
```

**Ordering**: Urgent items (deadline within `DEADLINE_URGENT_DAYS`)
first, sorted by deadline ascending. Remaining items sorted by
priority descending.

**Truncation**: At `DIGEST_MAX_ITEMS`, append "+N more items".

## No-Posts Message

When all channels have zero new posts:

```
No new posts found in Radar channels since last check.
```
