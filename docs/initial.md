# Project: Telegram Radar Digest (MVP)

You are implementing a small personal tool that:
1) reads Telegram channels from a Telegram folder named "Radar"
2) fetches recent posts
3) fetches comments for those posts (when available)
4) summarizes in batches using an LLM
5) sends a daily digest to me via a Telegram bot
6) provides a bot command to show which channels are actually parsed

## Constraints
- Implementable fast (MVP). Avoid overengineering.
- Python >= 3.13
- Fully async (Telethon + async LLM client).
- Logging via `loguru`.
- Telegram client/session must be isolated behind a dedicated class.
- Summarize in batches to avoid context overflows.
- Keep code readable, minimal, explicit. Small functions. No magic.
- Paths via `pathlib.Path`.
- Config via env + `pydantic-settings`. No secrets in code.
- Python package manager: `uv` (use `pyproject.toml`, `uv.lock`).
- Deployment via GitHub Actions on a self-hosted runner. Secrets come from GitHub Secrets.
- Docker artifacts live in `docker/` directory (`docker/Dockerfile`, `docker/compose.yaml`).
- At deploy time, workflow must render a `.env` file for docker compose from GitHub Secrets.

## High-level Architecture (single service)
- `TelegramClientGateway` (Telethon): reads folder "Radar", fetches posts and comments.
- `BatchBuilder`: groups posts into batches using char budget rules (see below).
- `LLMSummarizer` (LLM provider): summarizes batches of posts (including comments); returns structured output.
- `DigestBuilder`: formats final digest message (markdown).
- `TelegramBotController` (Bot API): handles commands and sends messages to me.
- `Scheduler`: simple daily job (APScheduler) + manual `/digest_now`.

No separate services, no Mini App, no DB for MVP.
State allowed: local JSON cache in `data/state.json`.

## Functional Requirements

### 1) Folder-based channel discovery
- Read Telegram dialog filters and find folder by title "Radar" (configurable).
- Extract included peers and resolve them to channel entities.
- Provide a method returning a list of channels (id, title, username if present).

### 2) Fetch recent posts (no keyword filtering)
- For each channel in Radar:
  - fetch posts since `last_processed_message_id` stored in state (per channel).
  - if no state exists, fetch a last 24 hours window.
  - ignore empty / service messages.
  - capture per post:
    - channel title, channel username/id
    - post id, post date
    - post text (raw)
    - permalink to the original post (must be a working t.me link where possible)
- Do not trim post text at fetch time; trimming is applied for LLM batching rules.

### 3) Fetch comments for posts (MVP-safe)
Goal: include the most informative discussion without exploding volume.

- For each fetched post, attempt to fetch comments:
  - Fetch up to `COMMENTS_LIMIT_PER_POST` newest comments (default 10).
  - For each comment capture:
    - comment_id, author display name (if available), date, text (trim to `COMMENT_MAX_LEN`, default 500).
    - a link to the original comment if possible. If a stable link is hard, at least store `comment_id` + post link and mention it.
- If comments are unavailable for a post, continue silently.

Important implementation notes:
- Comments in Telegram are replies. In many channels comments are located in a linked discussion group.
- Prefer robust approach:
  - Detect replies via Telethon message fields; attempt to iterate replies using Telethon helpers (e.g. `client.iter_messages(..., reply_to=post_id)` when feasible).
  - If a direct reply iteration is not possible due to channel/discussion linkage, gracefully skip for MVP.
- Do NOT attempt to fetch deep threads or all replies. Only top-level newest comments.

### 4) Batch building rules (strict)
We must build batches that fit into `LLM_MAX_CHARS_PER_BATCH` (default 12_000) using a char heuristic.

Definitions:
- A "post payload" = post text + metadata + selected comments (trimmed).
- We build batches sequentially in the order of posts (by channel, then by time descending .

Rules:
1) If a post text alone (with metadata) exceeds `LLM_MAX_CHARS_PER_BATCH`  -> SKIP ENTIRE POST and log warning.
2) Otherwise, attempt to include post + as many comments as fit:
   - Start with post metadata + post text.
   - Then add comments one by one until adding the next comment would exceed the `LLM_MAX_CHARS_PER_BATCH` .
   - If post + ALL comments exceeds budget, include only the subset of comments that fit.
1) Build a batch by adding post payloads until the next post payload would exceed `LLM_MAX_CHARS_PER_BATCH`:
   - Add payloads sequentially.
   - When the next payload does not fit, finalize the current batch and start a new batch.
4) Summarization flow:
   - Summarize batch #1 -> result #1
   - Summarize batch #2 -> result #2
   - ...
   - Combine results at the end.
5) No “retry by halving batch size” is required for MVP. Batch builder must already enforce sizes.
6) Log batch stats:
   - number of posts, number of comments, total chars per batch.


### 5) LLM summarization (structured outputs via `instructor`)
Use `instructor` + Pydantic models for reliable structured outputs.

Output requirements per digest item:
- `title`: concise title
- `why_relevant`: 1–2 sentences explaining relevance (career/opportunity impact)
- `source_url`: MUST be a link to the original post OR to the specific comment if the key insight is from a comment.
- `quotes`: short quotes to justify the item:
  - `post_quote` (required, <= 160 chars)
  - `comment_quote` (optional, <= 160 chars)
- `deadline` (optional): normalized date string if present
- `action` (optional): what to do next (register/apply/etc.)
- `channel`: channel title
- `date`: original post date (ISO string)
- `priority`: float 0..1 (how important/urgent)

The LLM output MUST match this schema:
- `DigestBatchResult`:
  - `items: list[DigestItem]`
  - `batch_summary: str` (1–3 lines)

LLM prompt guidance:
- Prefer extracting real deadlines; if none, omit `deadline`.
- Use quotes as evidence; do not hallucinate quotes.
- `source_url` should prefer exact post or comment URL; if comment URL cannot be formed reliably, use post URL and mention comment_id in `source_url` as fragment-like suffix (best effort).

### 6) Digest building
- Combine all batch results into one final digest message:
  - group by urgency: deadlines within X days first (X config, default 7).
  - limit total items shown (config `DIGEST_MAX_ITEMS` default 20); add “+N more”.
  - Format: Markdown, bullet list with title, why_relevant, deadline/action, source_url, quotes.


### 7) Telegram bot commands
Use Bot API (not Telethon) for UI:
- `/health` -> checks:
  - telethon connected (basic call)
  - llm health (simple request)
- `/channels` -> prints which channels are in Radar folder and how many posts were fetched last run.
- `/digest_now` -> runs digest immediately and sends to me.

Owner-only:
- Only TG_OWNER_USER_ID can execute commands.

### 6) Logging
- Log start/end, number of channels discovered, number fetched per channel, comment fetch success rate,
  batch sizes, retries.
- Loguru formatting; avoid noisy logs by default but include key metrics.

## Configuration (pydantic-settings)
Env vars:
- TELEGRAM_API_ID
- TELEGRAM_API_HASH
- TELETHON_SESSION_PATH (default: data/telethon.session)
- TG_BOT_TOKEN
- TG_OWNER_USER_ID (only this user can run commands)
- RADAR_FOLDER_NAME (default: Radar)

- FETCH_SINCE_HOURS (default: 24) OR use per-channel `state.json`
- FETCH_LIMIT_PER_CHANNEL (default: 50)  # safety

- COMMENTS_LIMIT_PER_POST (default: 10)
- COMMENT_MAX_LEN (default: 500)
- POST_MAX_LEN (default: 4000)

- DIGEST_MAX_ITEMS (default: 20)
- DEADLINE_URGENT_DAYS (default: 7)

- LLM_PROVIDER (default: openai)
- LLM_MODEL
- LLM_API_KEY
- LLM_MAX_CHARS_PER_BATCH (default: 12000)

## Data files
- `data/state.json` to store:
  - per channel: last_processed_message_id (or last_date)
  - last_run stats: channels_parsed list (for `/parsed`)
- Ensure `data/` is created automatically.

## Deployment
### Docker
- Place Docker assets in `docker/`:
  - `docker/Dockerfile`
  - `docker/compose.yaml`
- The app runs as a single container.
- Use `.env` file for configuration (mounted or passed via compose).

### GitHub Actions (self-hosted runner)
- Add workflow `.github/workflows/deploy.yaml` that:
  1) runs on push to `main`
  2) checks out repo on self-hosted runner
  3) creates/overwrites `docker/.env` from GitHub Secrets (write key=value lines)
  4) runs `docker compose -f docker/compose.yaml up -d --build`
- Secrets are stored in GitHub Secrets and must be written into `docker/.env` at deploy time.
- Ensure the workflow never prints secret values.

## Deliverables
- A runnable project with:
  - `pyproject.toml` configured for `uv`
  - `src/telegram_radar/` package
  - `python -m telegram_radar` starts bot and scheduler
  - `docker/` folder with Dockerfile + compose.yaml
  - GitHub Actions workflow for self-hosted deploy
- Include a short README with setup steps (local + docker + deploy).

## Implementation Notes
- Use async everywhere; do not block event loop.
- Telegram gateway must be isolated class with clear methods:
  - `get_radar_channels() -> list[ChannelInfo]`
  - `fetch_posts(channel, since) -> list[Post]`
  - `fetch_comments(post, limit) -> list[Comment]` (best-effort)
- BatchBuilder should be deterministic and unit-testable.
- Use Pydantic models for domain objects and for `instructor` outputs.
- Keep functions small and explicit; type everything.