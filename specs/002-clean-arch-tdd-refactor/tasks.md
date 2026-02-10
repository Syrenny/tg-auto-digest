# Tasks: Clean Architecture & TDD Refactor

**Input**: Design documents from `/specs/002-clean-arch-tdd-refactor/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Unit tests included for the pipeline orchestrator (US3) as explicitly requested in the spec (FR-012, FR-013). Existing test modifications included where API changes require them.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/telegram_radar/`, `tests/unit/` at repository root

---

## Phase 1: Setup

**Purpose**: Configuration changes required before any refactoring begins

- [x] T001 Add `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` in `pyproject.toml` per research R-006. Verify existing 17 tests still pass with `uv run pytest tests/unit/ -v`

**Checkpoint**: pytest-asyncio auto mode enabled, all existing tests pass

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the Protocol definitions that ALL user stories depend on

- [x] T002 Create `src/telegram_radar/protocols.py` with three Protocol classes per contracts/protocols.md: `TelegramGateway` (4 async methods: `get_radar_channels`, `fetch_posts`, `fetch_comments`, `check_health`), `Summarizer` (2 async methods: `summarize_batch`, `check_health`), `StateRepository` (6 methods: `load`, `save`, `get_last_message_id`, `update_channel`, `record_last_run`, `get_channel_state`). Import only from `typing.Protocol` and `telegram_radar.models`. No `@runtime_checkable`. Use `...` (ellipsis) body for all methods. Parameter names MUST match existing concrete class signatures exactly (per research R-004)

**Checkpoint**: `protocols.py` exists with all three Protocols. No infrastructure imports. All existing tests still pass (no files modified yet)

---

## Phase 3: User Story 1 — Introduce Abstraction Layer (Priority: P1)

**Goal**: Application and presentation layers depend on abstract Protocols instead of concrete infrastructure classes

**Independent Test**: `grep` for concrete infrastructure imports in `pipeline.py` and `bot.py` returns zero matches. All existing tests pass

### Implementation for User Story 1

- [x] T003 [US1] Refactor `src/telegram_radar/pipeline.py`: replace imports of `TelegramClientGateway`, `LLMSummarizer`, `StateManager` with `TelegramGateway`, `Summarizer`, `StateRepository` from `protocols.py`. Update `run_digest()` function signature to use Protocol types. Keep all other logic unchanged. Do NOT yet fix `_state` access — that is US2
- [x] T004 [US1] Refactor `src/telegram_radar/bot.py`: replace imports of `TelegramClientGateway`, `LLMSummarizer`, `StateManager` with `TelegramGateway`, `Summarizer`, `StateRepository` from `protocols.py`. Update `TelegramBotController.__init__()` signature to use Protocol types. Keep all other logic unchanged. Do NOT yet fix `_state` access — that is US2
- [x] T005 [US1] Verify all modules import cleanly: run `uv run python -c "from telegram_radar import protocols, pipeline, bot; print('OK')"`. Run existing tests `uv run pytest tests/unit/ -v` — all 17 must pass

**Checkpoint**: `pipeline.py` and `bot.py` import only Protocol types. Concrete classes only in `__main__.py`. All existing tests pass

---

## Phase 4: User Story 2 — Eliminate State Encapsulation Violations (Priority: P2)

**Goal**: All state interactions go through public methods. Zero `_state` access outside `state.py`

**Independent Test**: `grep -rn "_state\." src/telegram_radar/pipeline.py src/telegram_radar/bot.py` returns no output. All tests pass

### Implementation for User Story 2

- [x] T006 [US2] Add `record_last_run()` and `get_channel_state()` methods to `src/telegram_radar/state.py` per data-model.md: `record_last_run(self, channels_parsed: list[str]) -> None` sets `self._state.last_run = LastRun(timestamp=datetime.now(timezone.utc).isoformat(), channels_parsed=channels_parsed)` and requires `from datetime import datetime, timezone` import. `get_channel_state(self, channel_id: int) -> ChannelState | None` returns `self._state.channels.get(str(channel_id))`. Also ensure `_state` is loaded (call `self.load()` if `self._state is None`), matching existing pattern in `get_last_message_id()`
- [x] T007 [US2] Change `save()` signature in `src/telegram_radar/state.py`: remove `state: AppState` parameter, persist `self._state` directly. Update the method body to use `self._state` instead of the `state` parameter. Ensure `_state` is loaded before saving (guard against None)
- [x] T008 [US2] Update `src/telegram_radar/pipeline.py` to use new StateManager API: replace `state._state.last_run = LastRun(...)` + `state.save(state._state)` with `state.record_last_run(channels_parsed=parsed_names)` + `state.save()`. Apply in both the no-posts path (line ~67-72) and the successful-digest path (line ~91-95). Remove `LastRun` import since it's no longer needed in pipeline
- [x] T009 [US2] Update `src/telegram_radar/bot.py` to use new StateManager API: replace `self._state._state.channels.get(str(ch.id))` with `self._state.get_channel_state(ch.id)` in `_handle_channels()`. The returned `ChannelState | None` replaces the current dict lookup pattern
- [x] T010 [US2] Update `tests/unit/test_state.py` for new `save()` signature: change all `manager.save(state)` calls to use the pattern: `manager.load()` → mutate via `update_channel()` / `record_last_run()` → `manager.save()`. Add tests for the two new methods: `test_record_last_run_sets_timestamp_and_channels`, `test_get_channel_state_returns_none_for_unknown`. Run `uv run pytest tests/unit/ -v` — all tests must pass
- [x] T011 [US2] Verify zero `_state` access outside state.py: run `grep -rn "_state\." src/telegram_radar/pipeline.py src/telegram_radar/bot.py` — must return no output. Run full test suite

**Checkpoint**: All `_state` access eliminated from pipeline and bot. StateManager has clean CQS API. All tests pass

---

## Phase 5: User Story 3 — Expand Test Coverage (Priority: P3)

**Goal**: Pipeline orchestrator has unit tests using mock Protocol implementations, establishing TDD-ready infrastructure

**Independent Test**: `uv run pytest tests/unit/test_pipeline.py -v` passes with 4+ tests in under 2 seconds, using only in-memory mocks

### Unit Tests for User Story 3

- [x] T012 [US3] Write unit tests in `tests/unit/test_pipeline.py` per research R-005 and R-006: create concrete stub classes (`FakeGateway`, `FakeSummarizer`, `FakeStateRepository`) implementing the Protocol method signatures. Use `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed). Tests to include: (1) `test_digest_successful_flow` — mock gateway returns 1 channel with 2 posts with comments, mock summarizer returns DigestBatchResult, assert digest string contains expected markdown formatting; (2) `test_digest_no_channels` — mock gateway returns empty list, assert result contains error message about no channels; (3) `test_digest_no_new_posts` — mock gateway returns channels but fetch_posts returns empty list, assert result contains "No new posts"; (4) `test_digest_summarizer_error` — mock summarizer raises Exception on first batch but succeeds on second, assert pipeline continues and produces partial digest (or handles gracefully). Use real `BatchBuilder` and `DigestBuilder` instances (they are pure domain logic). Use real `Settings` with test values. Run `uv run pytest tests/unit/test_pipeline.py -v` — all 4 tests must pass
- [x] T013 [US3] Run full test suite validation: `uv run pytest tests/unit/ -v` — all 21+ tests must pass in under 5 seconds

**Checkpoint**: Full test suite passes. Pipeline is fully testable with mock Protocols. TDD infrastructure established

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all user stories

- [x] T014 Run quickstart.md validation: execute all 9 validation steps from `specs/002-clean-arch-tdd-refactor/quickstart.md`. Verify: (1) `protocols.py` has zero infrastructure imports, (2) `pipeline.py` has zero concrete infrastructure imports, (3) `bot.py` has zero concrete infrastructure imports, (4) zero `_state` access outside `state.py`, (5) all tests pass, (6) new pipeline tests pass, (7) full suite under 5 seconds, (8) application imports cleanly, (9) all modules importable

**Checkpoint**: All validation steps pass. Refactor is complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 (protocols must exist before importing them)
- **User Story 2 (Phase 4)**: Depends on Phase 3 (pipeline/bot must already use Protocol types so we modify the same file once, not twice)
- **User Story 3 (Phase 5)**: Depends on Phase 4 (pipeline must use new StateManager API before we test it)
- **Polish (Phase 6)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)**: Requires `protocols.py` (Phase 2). Foundational change
- **US2 (P2)**: Requires US1 complete (pipeline.py/bot.py already use Protocol types). Modifies `state.py`, `pipeline.py`, `bot.py`, `test_state.py`
- **US3 (P3)**: Requires US2 complete (pipeline uses clean API). Creates `test_pipeline.py`

### Within Each User Story

- Protocol definitions before consumer refactoring
- State API changes before consumer updates
- Consumer updates before test updates
- Implementation before validation

### Parallel Opportunities

- T003 and T004 can run in parallel (different files: `pipeline.py` and `bot.py`)
- Within US2, T006 and T007 can run in parallel (both modify `state.py` but different methods — however they touch the same file, so sequential is safer)
- US3 is a single test-writing task — no parallelism needed

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002)
3. Complete Phase 3: User Story 1 (T003-T005)
4. **STOP and VALIDATE**: Zero concrete imports in pipeline/bot, all tests pass

### Incremental Delivery

1. Setup + Foundational → Protocols defined
2. Add US1 → Abstract imports in pipeline/bot (MVP refactor!)
3. Add US2 → State encapsulation fixed
4. Add US3 → Pipeline tested with mocks
5. Polish → Full validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This refactor is strictly sequential (US2 depends on US1, US3 depends on US2) because each story modifies files touched by the previous story
- The spec says existing tests must pass "without modification" (FR-011), but `test_state.py` exercises `StateManager`'s public API which intentionally changes. The data-model.md documents this exception
- Commit after each task or logical group
- Total: 14 tasks across 6 phases
