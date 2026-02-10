# Tasks: Telegram Radar Digest MVP

**Input**: Design documents from `/specs/001-telegram-radar-digest/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Unit tests included for pure-logic components (BatchBuilder, DigestBuilder, StateManager) as they are deterministic and testable without external dependencies. Integration tests deferred to post-MVP.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/telegram_radar/`, `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Project initialization, dependencies, and configuration

- [x] T001 Initialize Python project with `pyproject.toml` for `uv`: define package `telegram_radar` under `src/`, add dependencies (telethon, python-telegram-bot, instructor, openai, apscheduler, pydantic, pydantic-settings, loguru), set `python -m telegram_radar` entry point, and run `uv sync` to generate `uv.lock`
- [x] T002 Create package structure: `src/telegram_radar/__init__.py` with empty init, and directory stubs for `tests/unit/`
- [x] T003 Implement Settings class in `src/telegram_radar/settings.py` using `pydantic-settings` with all env vars from data-model.md Configuration Entity table (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELETHON_SESSION_PATH, TG_BOT_TOKEN, TG_OWNER_USER_ID, RADAR_FOLDER_NAME, FETCH_SINCE_HOURS, FETCH_LIMIT_PER_CHANNEL, COMMENTS_LIMIT_PER_POST, COMMENT_MAX_LEN, POST_MAX_LEN, DIGEST_MAX_ITEMS, DEADLINE_URGENT_DAYS, LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, LLM_MAX_CHARS_PER_BATCH) with defaults per data-model.md
- [x] T004 [P] Define all domain Pydantic models in `src/telegram_radar/models.py`: ChannelInfo, Post, Comment, PostPayload, Batch, DigestItem (with Field constraints: post_quote max_length=160, comment_quote max_length=160, priority ge=0.0 le=1.0, date pattern), DigestBatchResult, ChannelState, AppState — all per data-model.md
- [x] T005 [P] Implement StateManager in `src/telegram_radar/state.py` per contracts/internal-interfaces.md: load(), save(), get_last_message_id(), update_channel(). Handle missing/corrupted file as fresh start. Auto-create `data/` directory via pathlib.Path. Use atomic write (write to temp then rename)

**Checkpoint**: Project builds, settings load from env, models importable, state persists to JSON

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**Warning**: No user story work can begin until this phase is complete

- [x] T006 Implement TelegramClientGateway in `src/telegram_radar/gateway.py`: __init__ accepting Settings, start() connecting TelegramClient, stop() disconnecting, check_health() calling get_me(). Use `GetDialogFiltersRequest` for get_radar_channels() to find folder by RADAR_FOLDER_NAME, resolve include_peers to ChannelInfo list. Implement fetch_posts() using iter_messages with min_id/offset_date logic per FR-003/FR-004/FR-005. Implement fetch_comments() using iter_messages with reply_to per research R-002, trimming to COMMENT_MAX_LEN. Build permalinks per research R-003. Log all operations with loguru
- [x] T007 Implement BatchBuilder in `src/telegram_radar/batch_builder.py`: build_batches() method — pure synchronous logic. For each post: compute PostPayload with post text + metadata + as many comments as fit within budget. Skip posts exceeding budget with loguru warning. Group PostPayloads into Batches sequentially until next payload exceeds max_chars_per_batch. Log batch stats (post count, comment count, total chars). Per FR-008 through FR-010 and batch building rules from docs/initial.md
- [x] T008 [P] Implement LLMSummarizer in `src/telegram_radar/summarizer.py`: __init__ accepting Settings, creates instructor client via `instructor.from_openai(AsyncOpenAI(api_key=...))`. summarize_batch() formats batch into prompt messages and calls client.chat.completions.create with response_model=DigestBatchResult, max_retries=3. check_health() sends minimal completion request. Log LLM call duration with loguru. Prompt must instruct: extract real deadlines, use verbatim quotes, prefer exact source_url per FR-011/FR-012
- [x] T009 [P] Implement DigestBuilder in `src/telegram_radar/digest_builder.py`: build_digest() — pure synchronous formatting. Accepts list of DigestBatchResult, max_items, urgent_days. Separate items into urgent (deadline within urgent_days) sorted by deadline ascending, and rest sorted by priority descending. Format as Markdown per contracts/bot-commands.md digest message format. Truncate at max_items with "+N more items" suffix. Handle zero items with "No new posts" message. Per FR-013 through FR-015

**Checkpoint**: All core components exist. Gateway can connect to Telegram, BatchBuilder groups posts, Summarizer calls LLM, DigestBuilder formats output

---

## Phase 3: User Story 1 — Receive Daily Digest (Priority: P1)

**Goal**: End-to-end pipeline that discovers channels, fetches posts/comments, summarizes in batches, and delivers formatted digest

**Independent Test**: Trigger a digest run and verify a formatted summary message arrives via the Telegram bot

### Implementation for User Story 1

- [x] T010 [US1] Implement run_digest orchestrator in `src/telegram_radar/pipeline.py` per contracts/internal-interfaces.md: async function accepting gateway, batch_builder, summarizer, digest_builder, state, settings. Flow: load state → get_radar_channels → for each channel fetch_posts (using last_message_id from state) → for each post fetch_comments → build_batches → for each batch summarize_batch → build_digest → update state → save state → return digest string. Handle edge cases: no channels found (log error), no new posts (return "no new posts" message), comment fetch failures (continue silently). Log channel count, posts per channel, total batches
- [x] T011 [US1] Implement Scheduler in `src/telegram_radar/scheduler.py`: class wrapping AsyncIOScheduler. setup() adds daily CronTrigger job (hour/minute configurable or default 9:00) that calls run_digest and sends result via bot. start()/stop() methods. Per research R-007
- [x] T012 [US1] Implement TelegramBotController in `src/telegram_radar/bot.py`: class wrapping python-telegram-bot Application. __init__ accepting Settings + references to gateway, summarizer, state, and the run_digest callable. Owner-only guard: decorator or check in each handler that compares update.effective_user.id to TG_OWNER_USER_ID, silently ignores unauthorized. Register /digest_now handler (calls run_digest, sends result). send_message() helper for scheduler to push digest. Per FR-017, FR-020, contracts/bot-commands.md
- [x] T013 [US1] Implement application entry point in `src/telegram_radar/__main__.py`: instantiate Settings, StateManager, TelegramClientGateway, BatchBuilder, LLMSummarizer, DigestBuilder, TelegramBotController, Scheduler. Wire dependencies. Start Telethon client, start bot polling, start scheduler, run via asyncio.gather per research R-004. Handle graceful shutdown (SIGINT/SIGTERM). Log startup/shutdown with loguru

### Unit Tests for User Story 1

- [x] T014 [P] [US1] Write unit tests in `tests/unit/test_batch_builder.py`: test single post fits in batch, test multiple posts split across batches, test post exceeding budget is skipped, test comments trimmed to fit budget, test empty post list returns empty batches, test batch stats (post_count, comment_count, total_chars) are correct
- [x] T015 [P] [US1] Write unit tests in `tests/unit/test_digest_builder.py`: test urgent items sorted by deadline first, test non-urgent sorted by priority descending, test truncation at max_items with "+N more" message, test zero items produces "no new posts" message, test Markdown formatting matches expected structure from contracts/bot-commands.md
- [x] T016 [P] [US1] Write unit tests in `tests/unit/test_state.py`: test load from valid JSON, test load from missing file returns empty state, test load from corrupted JSON returns empty state, test save creates data directory if missing, test update_channel and get_last_message_id round-trip

**Checkpoint**: Full digest pipeline works end-to-end. Bot receives /digest_now, runs pipeline, delivers formatted digest. Scheduler fires daily job. Unit tests pass for pure-logic components

---

## Phase 4: User Story 2 — Trigger Digest on Demand (Priority: P2)

**Goal**: `/digest_now` command triggers immediate digest and delivers result

**Independent Test**: Send `/digest_now` to bot and verify digest message is returned

### Implementation for User Story 2

- [x] T017 [US2] Add /digest_now handler acknowledgment in `src/telegram_radar/bot.py`: when command received, immediately reply "Generating digest..." before running pipeline, then send full digest result. On error, send "Digest failed: {error summary}". Per contracts/bot-commands.md /digest_now spec. Ensure owner-only guard applies

**Checkpoint**: /digest_now sends acknowledgment, runs pipeline, delivers result or error message

---

## Phase 5: User Story 3 — View Monitored Channels (Priority: P3)

**Goal**: `/channels` command shows Radar folder channels with last-run post counts

**Independent Test**: Send `/channels` to bot and verify channel list with post counts

### Implementation for User Story 3

- [x] T018 [US3] Add /channels handler in `src/telegram_radar/bot.py`: fetch current channels via gateway.get_radar_channels(), load state for last-run post counts, format response as "Radar Channels:\n• Channel Name (@username) — N posts last run" per contracts/bot-commands.md /channels spec. Show "no data yet" for channels without state. Ensure owner-only guard applies

**Checkpoint**: /channels lists all Radar folder channels with accurate last-run stats

---

## Phase 6: User Story 4 — Check System Health (Priority: P4)

**Goal**: `/health` command reports connectivity status for Telegram and LLM

**Independent Test**: Send `/health` to bot and verify status for both services

### Implementation for User Story 4

- [x] T019 [US4] Add /health handler in `src/telegram_radar/bot.py`: call gateway.check_health() and summarizer.check_health(), format response as "Health Status:\n• Telegram: Connected/Disconnected\n• LLM: Reachable/Unreachable" per contracts/bot-commands.md /health spec. Ensure owner-only guard applies

**Checkpoint**: /health accurately reports connectivity for Telegram client and LLM provider

---

## Phase 7: Deployment

**Purpose**: Docker and CI/CD setup for self-hosted runner

- [x] T020 [P] Create `docker/Dockerfile`: multi-stage build, Python 3.13 base, install uv, copy src + pyproject.toml + uv.lock, run `uv sync --frozen`, set CMD to `python -m telegram_radar`. Mount data/ volume for state.json and telethon.session
- [x] T021 [P] Create `docker/compose.yaml`: single service `telegram_radar`, build from `docker/Dockerfile` with context `..`, env_file from `docker/.env`, volume mount for `./data:/app/data`, restart policy `unless-stopped`
- [x] T022 Create `.github/workflows/deploy.yaml`: trigger on push to main, runs-on self-hosted, steps: checkout → write docker/.env from GitHub Secrets (all env vars from Settings, one per line, using `echo KEY=${{ secrets.KEY }}` — never print values) → `docker compose -f docker/compose.yaml up -d --build`. Per docs/initial.md deployment section
- [x] T023 Add `docker/.env` to `.gitignore` and verify `data/` is in `.gitignore`

**Checkpoint**: `docker compose up -d --build` runs the service. GitHub Actions deploys on push to main

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [x] T024 Write README.md with setup steps: prerequisites, local setup (uv sync, create .env, create Telethon session, run), Docker setup, deploy via GitHub Actions, bot commands reference. Per quickstart.md structure
- [x] T025 Run full validation: verify `uv sync` succeeds, `python -m telegram_radar` starts without errors (with valid env), all unit tests pass with `uv run pytest tests/unit/`, Docker build succeeds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001-T005) completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 (T006-T009)
- **User Story 2 (Phase 4)**: Depends on Phase 3 (T010-T013, since /digest_now reuses the pipeline)
- **User Story 3 (Phase 5)**: Depends on Phase 2 (T006 for gateway) + Phase 1 (T005 for state)
- **User Story 4 (Phase 6)**: Depends on Phase 2 (T006 for gateway health, T008 for summarizer health)
- **Deployment (Phase 7)**: Depends on Phase 3 (working application)
- **Polish (Phase 8)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)**: Requires all foundational components — core pipeline
- **US2 (P2)**: Requires US1 pipeline to be working (T010)
- **US3 (P3)**: Can start after Phase 2 — only needs gateway + state (independent of US1 pipeline, but bot setup from T012 needed)
- **US4 (P4)**: Can start after Phase 2 — only needs gateway + summarizer health checks (bot setup from T012 needed)

### Within Each User Story

- Models before services
- Services before orchestrator
- Orchestrator before bot handlers
- Core implementation before tests

### Parallel Opportunities

- T004 and T005 can run in parallel (different files, no dependencies)
- T008 and T009 can run in parallel (different files)
- T014, T015, T016 can all run in parallel (different test files)
- T020 and T021 can run in parallel (different Docker files)
- US3 and US4 can run in parallel once bot setup exists

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T009)
3. Complete Phase 3: User Story 1 (T010-T016)
4. **STOP and VALIDATE**: Run unit tests, trigger /digest_now manually
5. Deploy if ready (Phase 7)

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → Deploy (MVP!)
3. Add US2 → /digest_now with acknowledgment
4. Add US3 → /channels visibility
5. Add US4 → /health diagnostics
6. Deployment + Polish → Production-ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests pass before moving to next phase
- Commit after each task or logical group
- US2 is minimal (acknowledgment message + error handling in existing handler) since the pipeline from US1 already exists
- US3 and US4 are small additions to the bot handler — can be fast
