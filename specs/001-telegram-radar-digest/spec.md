# Feature Specification: Telegram Radar Digest MVP

**Feature Branch**: `001-telegram-radar-digest`
**Created**: 2026-02-10
**Status**: Draft
**Input**: User description: "Personal tool that reads Telegram channels from a folder, fetches posts and comments, summarizes via LLM, and sends a daily digest via Telegram bot"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive Daily Digest (Priority: P1)

As the sole user, I want to receive a daily Telegram message containing
a prioritized summary of recent posts from my "Radar" folder channels,
so I can stay informed without reading every channel manually.

The system automatically discovers channels from my Telegram folder,
fetches new posts since the last run, groups them into batches,
summarizes each batch via an LLM, and delivers a formatted digest
message to me through a Telegram bot.

**Why this priority**: This is the core value proposition — without the
daily digest, the tool has no purpose. Every other feature depends on
this pipeline working end to end.

**Independent Test**: Can be fully tested by triggering a digest run
and verifying that a formatted summary message arrives via the
Telegram bot, containing titles, relevance explanations, quotes, and
source links for recent channel posts.

**Acceptance Scenarios**:

1. **Given** the "Radar" folder contains 5 channels with new posts,
   **When** the scheduled daily job fires,
   **Then** I receive a single Telegram message with a summarized
   digest covering posts from all 5 channels.

2. **Given** a channel has posts with comments in a linked discussion
   group,
   **When** the system fetches that channel's posts,
   **Then** the digest includes insights from comments where relevant,
   with quotes attributed to the comment source.

3. **Given** total post volume exceeds the LLM's per-batch character
   budget,
   **When** the system builds batches,
   **Then** posts are split across multiple batches, each summarized
   independently, and results are combined into a single digest.

4. **Given** a post's text alone exceeds the batch character budget,
   **When** the system encounters this post,
   **Then** the post is skipped, a warning is logged, and the
   remaining posts are processed normally.

5. **Given** the system has previously run and recorded state,
   **When** a new run starts,
   **Then** only posts newer than the last processed message ID (per
   channel) are fetched.

6. **Given** no previous state exists for a channel,
   **When** the system fetches posts for the first time,
   **Then** it fetches posts from the last 24 hours.

---

### User Story 2 - Trigger Digest on Demand (Priority: P2)

As the user, I want to send a `/digest_now` command to the bot and
immediately receive a fresh digest, so I can get an update whenever
I want without waiting for the scheduled run.

**Why this priority**: On-demand access is essential for the tool to
feel useful beyond the automated schedule. It reuses the entire
pipeline from US1 with minimal additional work.

**Independent Test**: Can be tested by sending `/digest_now` to the
bot and verifying a digest message is returned within a reasonable
time.

**Acceptance Scenarios**:

1. **Given** I am the authorized owner,
   **When** I send `/digest_now` to the bot,
   **Then** the system runs the full digest pipeline and sends me the
   result.

2. **Given** a non-owner user sends `/digest_now`,
   **When** the bot receives the command,
   **Then** the command is ignored or rejected (no digest is sent).

---

### User Story 3 - View Monitored Channels (Priority: P3)

As the user, I want to send a `/channels` command to see which
channels are in my Radar folder and how many posts were fetched in
the last run, so I can verify the system is tracking the right
sources.

**Why this priority**: Diagnostic visibility helps me trust the
system is working correctly and monitoring the channels I expect.

**Independent Test**: Can be tested by sending `/channels` to the bot
and verifying the response lists all Radar folder channels with
their last-run post counts.

**Acceptance Scenarios**:

1. **Given** the Radar folder contains channels A, B, C,
   **When** I send `/channels` to the bot,
   **Then** I receive a list showing channel names and the number of
   posts fetched in the most recent run.

2. **Given** the system has never run a digest,
   **When** I send `/channels`,
   **Then** I see the channel list with "0 posts" or "no data yet"
   for each channel.

---

### User Story 4 - Check System Health (Priority: P4)

As the user, I want to send `/health` to verify that the Telegram
client and LLM provider are connected and operational.

**Why this priority**: Health checks are a convenience for debugging
but are not required for core digest functionality.

**Independent Test**: Can be tested by sending `/health` and verifying
the response reports connection status for both Telegram and the LLM
provider.

**Acceptance Scenarios**:

1. **Given** Telegram client and LLM are both reachable,
   **When** I send `/health`,
   **Then** I receive a message confirming both services are healthy.

2. **Given** the LLM provider is unreachable,
   **When** I send `/health`,
   **Then** I receive a message indicating LLM is down while Telegram
   is healthy.

---

### Edge Cases

- What happens when the Radar folder does not exist or has been
  renamed? The system MUST log an error and send a notification to
  the owner via the bot.
- What happens when all channels in the folder have zero new posts?
  The system MUST skip summarization and send a short "no new posts"
  message to the user via the bot.
- What happens when comment fetching fails for a post? The system
  MUST continue processing without comments for that post, logging
  the failure.
- What happens when the LLM returns output that does not match the
  expected schema? The schema validation layer MUST enforce
  compliance; invalid responses trigger a retry (up to the provider's
  retry policy).
- What happens when the state file is missing or corrupted? The
  system MUST treat it as a fresh start (no prior state) and recreate
  the file after the run.
- What happens when credentials are invalid? The system MUST fail
  fast at startup with a clear error message.
- What happens when a post has no text (media-only)? The system MUST
  ignore empty/service messages and log a debug-level note.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST discover channels by reading Telegram
  dialog filters and finding the folder matching the configured name
  (default "Radar").
- **FR-002**: System MUST resolve included peers from the folder to
  channel entities, returning id, title, and username for each.
- **FR-003**: System MUST fetch posts per channel since the last
  processed message ID stored in persistent state, or from the last
  24 hours if no state exists.
- **FR-004**: System MUST ignore empty and service messages during
  post fetching.
- **FR-005**: System MUST capture per post: channel title, channel
  username/id, post id, post date, raw text, and a working permalink.
- **FR-006**: System MUST attempt to fetch up to a configurable
  number of newest comments per post (default 10), trimming each
  comment to a configurable max length (default 500 chars).
- **FR-007**: System MUST silently continue if comments are
  unavailable for a post.
- **FR-008**: System MUST build batches of posts that fit within a
  configurable character budget (default 12,000 chars), including
  post metadata and comments.
- **FR-009**: System MUST skip any individual post whose text plus
  metadata exceeds the batch budget, logging a warning.
- **FR-010**: System MUST include as many comments as fit within the
  remaining budget for each post in a batch.
- **FR-011**: System MUST summarize each batch via an LLM, producing
  structured output conforming to the DigestBatchResult schema
  (items with title, why_relevant, source_url, quotes, optional
  deadline, optional action, channel, date, priority).
- **FR-012**: System MUST enforce structured LLM outputs using
  schema validation (no free-form text accepted).
- **FR-013**: System MUST combine batch results into a single digest
  message, grouping by urgency (deadlines within configurable
  window, default 7 days, shown first).
- **FR-014**: System MUST limit the digest to a configurable maximum
  number of items (default 20) and indicate remaining items count.
- **FR-015**: System MUST format the digest as Markdown with bullet
  points containing title, relevance, deadline/action, source URL,
  and quotes.
- **FR-016**: System MUST run a scheduled daily digest job
  automatically.
- **FR-017**: System MUST support a `/digest_now` bot command to
  trigger an immediate digest run.
- **FR-018**: System MUST support a `/channels` bot command returning
  the list of monitored channels with last-run post counts.
- **FR-019**: System MUST support a `/health` bot command reporting
  connectivity status for Telegram and the LLM provider.
- **FR-020**: System MUST restrict all bot commands to the configured
  owner user ID only.
- **FR-021**: System MUST persist per-channel last processed message
  ID and last-run statistics to local state.
- **FR-022**: System MUST auto-create the data directory at runtime
  if it does not exist.
- **FR-023**: System MUST log key operational metrics: channel
  discovery count, posts per channel, comment fetch success rate,
  batch sizes, and digest delivery status.

### Key Entities

- **Channel**: A Telegram channel discovered from the Radar folder.
  Attributes: id, title, username (optional). Relationship: contains
  Posts.
- **Post**: A message fetched from a Channel. Attributes: id, date,
  raw text, permalink, channel reference. Relationship: may have
  Comments.
- **Comment**: A reply to a Post fetched from a linked discussion
  group. Attributes: id, author display name (optional), date, text
  (trimmed), link (best effort).
- **Batch**: A group of Posts (with their Comments) that fits within
  the character budget. Used as input to a single LLM summarization
  call.
- **DigestItem**: A structured summary of one or more posts produced
  by the LLM. Attributes: title, why_relevant, source_url, quotes
  (post_quote required, comment_quote optional), deadline (optional),
  action (optional), channel, date, priority (0..1).
- **DigestBatchResult**: The LLM output for one Batch. Contains a
  list of DigestItems and a short batch summary.
- **Digest**: The final formatted message sent to the user. Combines
  all DigestBatchResults, ordered by urgency, capped at max items.
- **State**: Persistent record per channel of last_processed_message_id
  and last-run statistics. Stored as local JSON.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The user receives a daily digest message covering all
  channels in the Radar folder without manual intervention.
- **SC-002**: On-demand digest via `/digest_now` delivers results
  within 5 minutes of the command being sent.
- **SC-003**: Every digest item includes a working link to the
  original post or comment.
- **SC-004**: The digest correctly prioritizes items with upcoming
  deadlines (within 7 days) at the top of the message.
- **SC-005**: The system processes at least 50 posts per channel
  per run without failure.
- **SC-006**: Comment fetching succeeds for channels that support
  discussion groups, with graceful degradation for those that do not.
- **SC-007**: No secrets appear in application logs, source code,
  or CI/CD output.
- **SC-008**: The system recovers from a missing or corrupted state
  file by treating it as a fresh start, without crashing.
- **SC-009**: The `/channels` command accurately reflects the current
  Radar folder contents and last-run statistics.
- **SC-010**: Unauthorized users cannot execute any bot commands.

## Clarifications

### Session 2026-02-10

- Q: When all channels have zero new posts, should the system send a message or silently skip? → A: Send a short "no new posts" message to the user.

## Assumptions

- The user has a single Telegram account with access to a folder
  named "Radar" containing the channels to monitor.
- The LLM provider supports async API calls and is accessible from
  the deployment environment.
- The self-hosted GitHub Actions runner has Docker and Docker Compose
  installed.
- The Telethon session is pre-authenticated (session file provided
  at deploy time via volume mount or generated during initial setup).
- Comment fetching uses reply iteration; deeply nested threads and
  inaccessible discussion groups are out of scope for MVP.
- The digest is sent as a single Telegram message (or split only if
  it exceeds Telegram's message length limit — this edge case handling
  is best-effort for MVP).
