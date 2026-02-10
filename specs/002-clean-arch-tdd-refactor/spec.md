# Feature Specification: Clean Architecture & TDD Refactor

**Feature Branch**: `002-clean-arch-tdd-refactor`
**Created**: 2026-02-10
**Status**: Draft
**Input**: User description: "Update repo according to constitution"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Introduce Abstraction Layer (Priority: P1)

As a developer, I want the application layer (pipeline orchestrator) and presentation layer (bot controller) to depend on abstract interfaces rather than concrete infrastructure classes, so that I can swap implementations and write isolated tests without external dependencies.

**Why this priority**: This is the foundational change. Without interfaces, no other Clean Architecture or TDD improvement is possible. Every subsequent story depends on abstractions existing.

**Independent Test**: After this story is complete, the pipeline orchestrator and bot controller import only abstract types. Running `grep` for concrete infrastructure imports in `pipeline.py` and `bot.py` returns zero matches. All existing unit tests continue to pass unchanged.

**Acceptance Scenarios**:

1. **Given** the codebase has no abstract interfaces, **When** Protocol definitions are introduced for the gateway, summarizer, and state manager, **Then** each infrastructure class implements its corresponding Protocol and passes type checking.
2. **Given** `pipeline.py` currently imports `TelegramClientGateway`, `LLMSummarizer`, and `StateManager` directly, **When** the imports are changed to Protocol types, **Then** the orchestrator function signature uses only abstract types and the application still runs correctly.
3. **Given** `bot.py` currently imports concrete infrastructure classes, **When** the imports are changed to Protocol types, **Then** the bot controller constructor accepts abstract types and the application still runs correctly.
4. **Given** `pipeline.py` accesses `state._state.last_run` (private attribute), **When** proper public methods are added to the state Protocol, **Then** all private attribute access is eliminated from pipeline and bot modules.

---

### User Story 2 — Eliminate State Encapsulation Violations (Priority: P2)

As a developer, I want all state interactions to go through well-defined public methods rather than reaching into private attributes, so that the state manager's internal representation can change without breaking callers.

**Why this priority**: Private attribute access (`state._state.last_run`, `state._state.channels.get(...)`) couples callers to the internal structure. This must be fixed to honor Clean Architecture's dependency inversion and to make state interactions testable.

**Independent Test**: After this story, no module outside `state.py` accesses `_state` directly. Running `grep _state` against `pipeline.py` and `bot.py` returns zero matches. All existing unit tests pass.

**Acceptance Scenarios**:

1. **Given** `pipeline.py` sets `state._state.last_run = LastRun(...)` directly, **When** a public method (e.g., `update_last_run(...)`) is added, **Then** pipeline calls the method instead and the digest result is identical.
2. **Given** `bot.py` reads `state._state.channels.get(str(ch.id))` to show post counts, **When** a public method (e.g., `get_channel_state(channel_id)`) is added, **Then** the `/channels` handler uses the method and the response format is unchanged.
3. **Given** all private attribute access is removed, **When** the state manager's internal data structure changes (e.g., renaming a field), **Then** no code outside `state.py` breaks.

---

### User Story 3 — Expand Test Coverage with TDD-Ready Infrastructure (Priority: P3)

As a developer, I want unit tests for the pipeline orchestrator using mock implementations of the new Protocols, so that future changes can follow the Red-Green-Refactor cycle defined in Constitution Principle VII.

**Why this priority**: With abstractions in place (US1) and encapsulation fixed (US2), the pipeline becomes testable via mock/stub implementations. Adding pipeline tests validates the full refactor and establishes the TDD pattern for future development.

**Independent Test**: New test file(s) for the pipeline orchestrator run with `pytest` using only in-memory mock implementations — no network calls, no file I/O, no external services. All tests pass in under 2 seconds.

**Acceptance Scenarios**:

1. **Given** Protocol definitions exist for gateway, summarizer, and state, **When** mock implementations are created in test fixtures, **Then** the pipeline orchestrator runs successfully against mocks and produces a digest string.
2. **Given** the pipeline is called with a mock gateway returning zero channels, **When** the pipeline completes, **Then** it returns a "no new posts" message without errors.
3. **Given** the pipeline is called with mock data containing posts and comments, **When** the pipeline completes, **Then** it returns a formatted digest string and the state mock's update methods were called with correct arguments.
4. **Given** the mock summarizer raises an exception for one batch, **When** the pipeline processes multiple batches, **Then** it handles the error gracefully and continues with remaining batches.

---

### Edge Cases

- What happens when existing tests rely on internal implementation details that change? All existing tests must continue to pass without modification — the refactor must be purely structural.
- What happens at the composition root (`__main__.py`)? The composition root is the only place where concrete classes are instantiated and wired together. This is expected and does not violate Clean Architecture.
- What happens to `loguru` imports in domain-layer files? `loguru` is acceptable in domain-layer files (`batch_builder.py`, `digest_builder.py`) as a cross-cutting concern. It is not considered a Clean Architecture violation for this project.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define Protocol classes for `TelegramGateway`, `Summarizer`, and `StateRepository` in a dedicated interfaces module
- **FR-002**: Each Protocol MUST declare only the public methods consumed by the application and presentation layers (no infrastructure-specific methods like `start()`, `stop()`, or `check_health()` unless consumed by those layers)
- **FR-003**: `TelegramClientGateway` MUST satisfy the `TelegramGateway` Protocol without explicit inheritance (structural subtyping)
- **FR-004**: `LLMSummarizer` MUST satisfy the `Summarizer` Protocol without explicit inheritance
- **FR-005**: `StateManager` MUST satisfy the `StateRepository` Protocol without explicit inheritance
- **FR-006**: `pipeline.py` MUST import only Protocol types (not concrete classes) for gateway, summarizer, and state dependencies
- **FR-007**: `bot.py` MUST import only Protocol types (not concrete classes) for gateway, summarizer, and state dependencies
- **FR-008**: `StateManager` MUST expose public methods for all operations currently performed via private attribute access: updating last-run metadata, querying per-channel state
- **FR-009**: All private attribute access (`_state`) from modules outside `state.py` MUST be eliminated
- **FR-010**: The composition root (`__main__.py`) MUST remain the only module that imports and instantiates concrete infrastructure classes
- **FR-011**: All 17 existing unit tests MUST continue to pass without modification after the refactor
- **FR-012**: New unit tests MUST be added for the pipeline orchestrator covering: successful digest flow, zero-channels case, zero-posts case, and summarizer error handling
- **FR-013**: New pipeline tests MUST use mock/stub implementations of Protocols — no external dependencies
- **FR-014**: Domain-layer files (`models.py`, `batch_builder.py`, `digest_builder.py`) MUST NOT be modified (they are already compliant)

### Key Entities

- **Protocol: TelegramGateway** — abstract interface for channel discovery, post fetching, comment fetching, and health checking
- **Protocol: Summarizer** — abstract interface for batch summarization and health checking
- **Protocol: StateRepository** — abstract interface for loading, saving, querying, and updating application state

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero concrete infrastructure class imports in `pipeline.py` and `bot.py` (excluding the composition root)
- **SC-002**: Zero private attribute access (`_state`) outside of `state.py`
- **SC-003**: All 17 existing unit tests pass without modification
- **SC-004**: At least 4 new pipeline orchestrator unit tests pass using mock Protocol implementations
- **SC-005**: Total test suite runs in under 5 seconds with no external dependencies
- **SC-006**: The application starts and runs correctly (bot commands work, digest pipeline produces output) — verified by import checks and existing tests
- **SC-007**: Protocol definitions cover all methods consumed by the application and presentation layers

## Assumptions

- **loguru as cross-cutting concern**: `loguru` imports in domain-layer files are acceptable and do not violate Clean Architecture for this project's scope.
- **Structural subtyping over inheritance**: Python Protocols (structural subtyping) are preferred over ABC inheritance to keep infrastructure classes decoupled from the interface module.
- **No functional changes**: This is a pure structural refactor. No user-facing behavior changes. All bot commands, digest formatting, and scheduling continue to work identically.
- **Composition root exception**: `__main__.py` is explicitly exempt from the "no concrete imports" rule — it is the dependency injection point.
