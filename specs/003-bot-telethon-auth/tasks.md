# Tasks: Bot-Assisted Telethon Authentication

**Input**: Design documents from `/specs/003-bot-telethon-auth/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Required per Constitution Principle VII (TDD). Tests written before implementation in each phase.

**Organization**: Tasks grouped by user story. US1 and US3 are combined (US3 is the "already authorized" branch of the same startup check).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Foundational (Gateway Auth Primitives)

**Purpose**: Split gateway's `start()` into discrete auth methods usable by all user stories. Update protocol to match.

- [x] T001 [P] Add auth methods to TelegramGateway protocol in src/telegram_radar/protocols.py — add `connect()`, `is_authorized()`, `send_code(phone)`, `sign_in_code(phone, code)`, `sign_in_password(password)`
- [x] T002 [P] Write failing tests for gateway auth methods in tests/test_gateway_auth.py — test connect, is_authorized (true/false), send_code, sign_in_code (success + PhoneCodeInvalidError), sign_in_password (success + PasswordHashInvalidError). Mock TelegramClient.
- [x] T003 Implement gateway auth methods in src/telegram_radar/gateway.py — replace `start()` with `connect()` (calls `self._client.connect()`), `is_authorized()` (calls `self._client.is_user_authorized()`), `send_code(phone)` (calls `self._client.send_code_request(phone)`), `sign_in_code(phone, code)` (calls `self._client.sign_in(phone, code)`, re-raises SessionPasswordNeededError), `sign_in_password(password)` (calls `self._client.sign_in(password=password)`). Keep existing `stop()`, `check_health()`, fetch methods unchanged.
- [x] T004 Run tests — verify T002 tests pass with T003 implementation

**Checkpoint**: Gateway exposes auth primitives. Protocol updated. All existing functionality preserved.

---

## Phase 2: US1 + US3 — First-Time Login via Bot + Existing Valid Session (Priority: P1) 🎯 MVP

**Goal**: When no session exists, bot collects phone + code from owner and completes Telethon auth. When session exists, app starts silently.

**Independent Test**: Deploy without session file → complete login via bot → app runs. Deploy with valid session → app starts without prompts.

### Tests (write FIRST, ensure they FAIL)

- [x] T005 [P] [US1] Write failing tests for bot auth conversation in tests/test_bot_auth.py — test: (a) auth prompt sent on start_auth_flow, (b) phone handler calls gateway.send_code + replies with code prompt + deletes user message, (c) code handler calls gateway.sign_in_code + signals completion on success + deletes user message, (d) invalid code retry (up to 3) then restart, (e) PhoneNumberInvalidError stays in phone state
- [x] T006 [P] [US3] Write failing test for session skip in tests/test_bot_auth.py — test: when is_authorized() returns True, no auth prompt is sent and auth_complete event is set immediately
- [x] T007 [P] [US1] Write failing test for command blocking in tests/test_bot_auth.py — test: /digest_now, /channels, /health reply "Please complete the login first." when auth is not complete

### Implementation

- [x] T008 [US1] Implement auth ConversationHandler in src/telegram_radar/bot.py — add state constants AWAITING_PHONE, AWAITING_CODE. Add `start_auth_flow(auth_complete_event)` method that sends phone prompt to owner and registers ConversationHandler. Phone handler: normalize phone (strip spaces/dashes), call `gateway.send_code()`, delete user message, reply with code prompt, return AWAITING_CODE. Code handler: call `gateway.sign_in_code()`, delete user message, on success set auth_complete event + send success message + return ConversationHandler.END, on PhoneCodeInvalidError decrement retries + reply with error.
- [x] T009 [US1] Implement retry logic and flow restart in src/telegram_radar/bot.py — track retry_count per state (max 3). On 3 failures: reset retry_count, send "Too many failed attempts" message, return to AWAITING_PHONE state. On PhoneCodeExpiredError: re-request code, stay in AWAITING_CODE.
- [x] T010 [US1] Implement command blocking in src/telegram_radar/bot.py — add `_auth_complete: bool` flag (default False). In `_handle_digest_now`, `_handle_channels`, `_handle_health`: if not `_auth_complete`, reply "Please complete the login first." and return. Set flag to True after successful auth.
- [x] T011 [US1] Implement sensitive message deletion in src/telegram_radar/bot.py — in phone, code handlers: after reading message text, call `await context.bot.delete_message(chat_id, message_id)` wrapped in try/except (log warning on failure).
- [x] T012 [US1] Update startup sequence in src/telegram_radar/__main__.py — new order: (1) `await gateway.connect()`, (2) `await bot.start()`, (3) if `not await gateway.is_authorized()`: create `asyncio.Event`, call `bot.start_auth_flow(event)`, `await event.wait()`, (4) `scheduler.start()`. Keep shutdown sequence unchanged.
- [x] T013 [US1] Run tests — verify T005, T006, T007 all pass

**Checkpoint**: Core login flow works end-to-end. Existing sessions skip login. Commands blocked during auth. MVP complete.

---

## Phase 3: US2 — Two-Factor Authentication Support (Priority: P1)

**Goal**: After correct verification code, if 2FA is enabled, bot asks for cloud password and completes auth.

**Independent Test**: Use a 2FA-enabled account → complete full login via bot including password step.

### Tests (write FIRST, ensure they FAIL)

- [x] T014 [P] [US2] Write failing tests for 2FA flow in tests/test_bot_auth.py — test: (a) sign_in_code raises SessionPasswordNeededError → bot sends password prompt + transitions to AWAITING_PASSWORD, (b) password handler calls gateway.sign_in_password → success → auth complete, (c) PasswordHashInvalidError → retry (up to 3) then restart to phone, (d) user message deleted after password entry

### Implementation

- [x] T015 [US2] Add AWAITING_PASSWORD state to ConversationHandler in src/telegram_radar/bot.py — in code handler: catch SessionPasswordNeededError → send "Two-factor authentication is enabled" prompt → return AWAITING_PASSWORD. Add password handler: call `gateway.sign_in_password(password)`, delete user message, on success set auth_complete + return END, on PasswordHashInvalidError decrement retries + reply with error. On 3 failures → restart to AWAITING_PHONE.
- [x] T016 [US2] Run tests — verify T014 tests pass

**Checkpoint**: Full auth flow including 2FA works. US1 + US2 + US3 all functional.

---

## Phase 4: US4 — Login Timeout Reminders (Priority: P2)

**Goal**: If owner doesn't respond within 5 minutes, bot sends a reminder. App never hangs — keeps waiting gracefully.

**Independent Test**: Start without session, don't respond → verify reminder arrives after 5 minutes. Respond after reminder → login completes normally.

### Tests (write FIRST, ensure they FAIL)

- [x] T017 [P] [US4] Write failing test for timeout reminder in tests/test_bot_auth.py — test: after starting auth flow, if no response for 5 minutes, bot sends reminder message to owner. Test that reminder includes context about what's being awaited (phone/code/password).

### Implementation

- [x] T018 [US4] Implement timeout reminder in src/telegram_radar/bot.py — after sending each auth prompt, schedule a one-shot delayed task (5 min) using `asyncio.get_event_loop().call_later()` or `Application.job_queue.run_once()`. Callback sends reminder message. Cancel timer when owner responds. Log warning if total wait exceeds 10 minutes.
- [x] T019 [US4] Run tests — verify T017 passes

**Checkpoint**: All 4 user stories complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Logging, edge cases, final validation

- [x] T020 Add auth flow logging in src/telegram_radar/gateway.py and src/telegram_radar/bot.py — log: "Telethon connected", "Session authorized / not authorized", "Code sent to {phone}", "Sign-in successful", "Sign-in failed: {error}", "Auth flow started", "Auth flow completed", retry attempts, reminder sent
- [x] T021 Handle edge case: expired/revoked session at startup in src/telegram_radar/gateway.py — in `is_authorized()`, catch exceptions from `is_user_authorized()` (e.g., AuthKeyError) and return False to trigger re-auth
- [x] T022 Run full test suite and validate all tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: No dependencies — start immediately
- **Phase 2 (US1 + US3)**: Depends on Phase 1 — core login flow
- **Phase 3 (US2)**: Depends on Phase 2 — extends code handler with 2FA
- **Phase 4 (US4)**: Depends on Phase 2 — adds timeout to existing flow
- **Phase 5 (Polish)**: Depends on Phase 2 (minimum), ideally after Phase 3+4

### User Story Dependencies

- **US1 + US3 (P1)**: Can start after Phase 1. No dependencies on US2/US4.
- **US2 (P1)**: Depends on US1 (extends the code verification step)
- **US4 (P2)**: Depends on US1 (adds timeout to existing prompts). Can run in parallel with US2.

### Within Each Phase

- Tests MUST be written and FAIL before implementation
- Gateway before bot (bot calls gateway)
- Bot before __main__ (main orchestrates bot)

### Parallel Opportunities

- Phase 1: T001 (protocol) and T002 (tests) can run in parallel
- Phase 2: T005, T006, T007 (all test files) can run in parallel
- Phase 3 and Phase 4 can run in parallel after Phase 2

---

## Parallel Example: Phase 2 Tests

```bash
# Launch all US1/US3 tests together:
Task: "T005 — Write failing tests for bot auth conversation in tests/test_bot_auth.py"
Task: "T006 — Write failing test for session skip in tests/test_bot_auth.py"
Task: "T007 — Write failing test for command blocking in tests/test_bot_auth.py"
```

## Parallel Example: Phase 1

```bash
# Launch foundational tasks together:
Task: "T001 — Add auth methods to protocol in src/telegram_radar/protocols.py"
Task: "T002 — Write failing tests for gateway auth in tests/test_gateway_auth.py"
```

---

## Implementation Strategy

### MVP First (US1 + US3 Only)

1. Complete Phase 1: Gateway auth primitives
2. Complete Phase 2: Bot login flow + session skip
3. **STOP and VALIDATE**: Test manually in Docker — no session → login via bot → app runs
4. Deploy if ready — 2FA and timeout can follow

### Incremental Delivery

1. Phase 1 → Gateway ready
2. Phase 2 → MVP deployed (login + session skip)
3. Phase 3 → 2FA support added
4. Phase 4 → Timeout reminders added
5. Phase 5 → Polish and validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Constitution Principle VII (TDD): write tests first, ensure they fail, then implement
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- US1 and US3 are combined because US3 is the trivial `is_authorized() == True` branch of the same startup check
