# Tasks: Session Reset via /start & Bot Command Menu

**Input**: Design documents from `/specs/004-start-reset-bot-menu/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Required per Constitution Principle VII (TDD). Tests written before implementation in each phase.

**Organization**: Tasks grouped by user story. US1 and US2 are independent (different files, no cross-dependencies).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Phase 1: Foundational (Gateway log_out Primitive)

**Purpose**: Add `log_out()` to gateway protocol and implementation so both user stories can build on it.

- [x] T001 [P] Add `log_out()` method to TelegramGateway protocol in src/telegram_radar/protocols.py
- [x] T002 [P] Write failing tests for gateway `log_out()` in tests/test_gateway_auth.py — test: (a) log_out calls `client.log_out()` + `client.disconnect()`, recreates client, calls `client.connect()`, (b) log_out succeeds even when `client.log_out()` raises an exception (logs warning, still recreates client and connects)
- [x] T003 Implement gateway `log_out()` in src/telegram_radar/gateway.py — call `self._client.log_out()`, `self._client.disconnect()` (both wrapped in try/except with warning log), recreate `self._client = TelegramClient(...)` with same settings, call `await self._client.connect()`, log "Session logged out and client reconnected"
- [x] T004 Run tests — verify T002 tests pass with T003 implementation

**Checkpoint**: Gateway exposes `log_out()`. Protocol updated. Existing functionality preserved.

---

## Phase 2: US1 — Session Reset via /start Command (Priority: P1) 🎯 MVP

**Goal**: Owner sends `/start` → session is logged out → auth flow restarts. Commands blocked until re-auth completes.

**Independent Test**: Send `/start` while authenticated → session cleared → phone prompt appears → complete re-auth → commands work again.

### Tests (write FIRST, ensure they FAIL)

- [x] T005 [P] [US1] Write failing tests for /start handler in tests/test_bot_auth.py — test: (a) /start from owner calls `gateway.log_out()`, sets `_auth_complete = False`, calls `start_auth_flow`, (b) /start from non-owner is ignored, (c) /start when not authenticated skips logout and starts auth flow, (d) /start during active auth flow restarts from phone prompt, (e) logout failure doesn't block auth flow (logs warning, proceeds)

### Implementation

- [x] T006 [US1] Implement /start handler in src/telegram_radar/bot.py — add `_handle_start(update, context)` method: check owner, call `gateway.log_out()` (wrapped in try/except), set `_auth_complete = False`, send "Session reset. Starting re-authentication...", create new `asyncio.Event`, call `start_auth_flow(event)`. Register `CommandHandler("start", self._handle_start)` in `_register_handlers()`.
- [x] T007 [US1] Handle /start during active auth flow in src/telegram_radar/bot.py — if auth flow is in progress (conversation handler active), cancel reminder timer, reset `_retry_count` and `_phone`, then proceed with logout + restart. Ensure `start_auth_flow` can be called again cleanly.
- [x] T008 [US1] Run tests — verify T005 tests pass

**Checkpoint**: /start resets session and restarts auth. Commands blocked until re-auth. MVP complete.

---

## Phase 3: US2 — Visible Bot Command Menu (Priority: P1)

**Goal**: Bot registers command menu on startup so all 4 commands are visible in Telegram's menu button.

**Independent Test**: Open bot chat → tap menu button → see /start, /digest_now, /channels, /health with descriptions.

### Tests (write FIRST, ensure they FAIL)

- [x] T009 [P] [US2] Write failing test for command menu registration in tests/test_bot_auth.py — test: (a) during bot `start()`, `set_my_commands` is called with 4 commands (/start, /digest_now, /channels, /health) and correct descriptions, (b) if `set_my_commands` raises an exception, bot continues to start normally (logs warning)

### Implementation

- [x] T010 [US2] Implement command menu registration in src/telegram_radar/bot.py — in `start()` method, after `start_polling()`, call `await self._app.bot.set_my_commands([...])` with `BotCommand("start", "Reset session and re-authenticate")`, `BotCommand("digest_now", "Generate digest immediately")`, `BotCommand("channels", "List monitored channels")`, `BotCommand("health", "Check system health")`. Wrap in try/except (log warning on failure). Import `BotCommand` from `telegram`.
- [x] T011 [US2] Run tests — verify T009 tests pass

**Checkpoint**: All 4 commands visible in bot menu. Both user stories complete.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Logging, validation, final checks.

- [x] T012 Add logging for /start flow in src/telegram_radar/bot.py — log: "Session reset requested by owner", "Logout failed: {error}, proceeding", "Auth flow restarted after /start", "Bot command menu registered"
- [x] T013 Run full test suite and validate all tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: No dependencies — start immediately
- **Phase 2 (US1)**: Depends on Phase 1 — uses `gateway.log_out()`
- **Phase 3 (US2)**: No dependencies on Phase 1 or 2 — independent feature
- **Phase 4 (Polish)**: Depends on Phase 2 + 3

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 1 (gateway `log_out()`). No dependency on US2.
- **US2 (P1)**: No dependencies on Phase 1 or US1. Can run in parallel with Phase 1 + US1.

### Within Each Phase

- Tests MUST be written and FAIL before implementation
- Gateway before bot (bot calls gateway)

### Parallel Opportunities

- Phase 1: T001 (protocol) and T002 (tests) can run in parallel
- Phase 2 and Phase 3 can run in parallel (different features, different code paths)
- T005 (US1 tests) and T009 (US2 tests) can run in parallel

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Gateway `log_out()` primitive
2. Complete Phase 2: /start handler
3. **STOP and VALIDATE**: Test /start → logout → re-auth manually
4. Deploy if ready — command menu can follow

### Incremental Delivery

1. Phase 1 → Gateway ready
2. Phase 2 → /start works (MVP)
3. Phase 3 → Command menu visible
4. Phase 4 → Polish and validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Constitution Principle VII (TDD): write tests first, ensure they fail, then implement
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Key constraint: Telethon client unusable after `log_out()` — gateway recreates it internally
