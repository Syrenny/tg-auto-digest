<!--
Sync Impact Report
===========================
Version change: 1.0.0 → 1.2.0 (two new principles)
Modified principles: None
Added principles:
  - VII. Test-Driven Development (TDD)
  - VIII. Clean Architecture
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md — ✅ compatible (Constitution Check section accepts dynamic gates; new principles VII and VIII will appear as additional gates automatically)
  - .specify/templates/spec-template.md — ✅ compatible (no constitution-specific references to update)
  - .specify/templates/tasks-template.md — ✅ compatible (task template already supports test-first ordering in "Within Each User Story" section; Clean Architecture aligns with existing isolation guidance)
Follow-up TODOs:
  - Future specs MUST include Constitution Check gates for Principles VII and VIII
  - Existing implementation (001-telegram-radar-digest) was built before these principles; retroactive compliance is not required but recommended for new features
-->

# Telegram Radar Digest Constitution

## Core Principles

### I. MVP-First Delivery

Every feature MUST target the simplest viable implementation.
Overengineering is prohibited: no abstractions for hypothetical
future requirements, no feature flags, no backwards-compatibility
shims. If a requirement is not in `docs/initial.md`, it does not
exist. Three similar lines of code are preferable to a premature
abstraction.

**Rationale**: The project is a personal tool with a single user.
Speed of delivery and maintainability outweigh extensibility.

### II. Fully Async, Single Service

All I/O operations MUST be async (`asyncio`). The application runs
as a single containerized service — no microservices, no separate
workers, no message queues. Telethon for the Telegram user client,
Bot API for the bot interface, and an async LLM client MUST all
share one event loop.

**Rationale**: A single-service async architecture minimizes
deployment complexity and operational overhead for a personal tool.

### III. Strict Isolation of Concerns

Each architectural component (`TelegramClientGateway`,
`BatchBuilder`, `LLMSummarizer`, `DigestBuilder`,
`TelegramBotController`, `Scheduler`) MUST be a dedicated class
with a clear, narrow interface. Cross-component coupling MUST go
through explicit method calls — no shared mutable state, no global
singletons.

**Rationale**: Isolation enables unit testing of each component
independently and makes the codebase navigable.

### IV. Explicit Configuration, No Secrets in Code

All configuration MUST flow through `pydantic-settings` from
environment variables. Secrets (API keys, tokens, session paths)
MUST never appear in source code, logs, or CI output. The `.env`
file is generated at deploy time from GitHub Secrets and MUST be
listed in `.gitignore`.

**Rationale**: A single configuration entry point prevents
scattered defaults and ensures secrets remain outside version
control.

### V. Structured LLM Outputs

LLM interactions MUST use `instructor` with Pydantic models to
enforce structured outputs. The summarizer MUST NOT return
free-form text — every LLM response MUST validate against the
`DigestBatchResult` schema. Quotes MUST be verbatim extractions;
hallucinated quotes are a defect.

**Rationale**: Structured outputs eliminate parsing fragility and
make the summarization pipeline deterministic and testable.

### VI. Observable Logging

All key operations MUST be logged via `loguru`: channel discovery
count, posts fetched per channel, comment fetch success rate, batch
sizes (posts, comments, chars), LLM call durations, and digest
delivery status. Logs MUST be concise by default — no debug-level
noise in production. Warnings MUST be emitted for skipped posts
(exceeding batch budget) and failed comment fetches.

**Rationale**: For a self-hosted personal tool without monitoring
infrastructure, structured logs are the primary observability
mechanism.

### VII. Test-Driven Development (TDD)

New functionality MUST follow the Red-Green-Refactor cycle:
1. **Red**: Write a failing test that defines the expected behavior.
2. **Green**: Write the minimal code to make the test pass.
3. **Refactor**: Clean up the implementation while keeping tests green.

Tests MUST be written before the production code they verify. Unit
tests are required for all pure-logic components (deterministic
functions with no external dependencies). Integration and contract
tests are added when the feature spec explicitly requests them.
Test files MUST mirror the source structure under `tests/`.

**Rationale**: Writing tests first forces clear interface design,
catches regressions immediately, and produces a reliable safety net
for refactoring.

### VIII. Clean Architecture

The codebase MUST follow dependency inversion: high-level domain
logic MUST NOT depend on low-level infrastructure details. Concrete
rules:
- **Domain layer** (models, pure-logic builders) MUST have zero
  imports from external libraries beyond Pydantic and the standard
  library.
- **Application layer** (orchestrators, pipeline) depends on domain
  abstractions, not on concrete gateways or clients.
- **Infrastructure layer** (Telegram clients, LLM clients, bot
  framework, scheduler) implements interfaces consumed by the
  application layer.
- Dependencies flow inward: Infrastructure → Application → Domain.
  Never the reverse.

**Rationale**: Clean Architecture keeps the core business logic
testable and portable, independent of any specific Telegram library,
LLM provider, or bot framework.

## Technology & Infrastructure Constraints

- **Language**: Python >= 3.13
- **Package manager**: `uv` (`pyproject.toml` + `uv.lock`)
- **Async runtime**: `asyncio` (via Telethon and Bot API)
- **Telegram user client**: Telethon (isolated behind
  `TelegramClientGateway`)
- **Telegram bot**: Bot API (not Telethon) for commands/messages
- **LLM integration**: `instructor` + provider-agnostic async
  client
- **Configuration**: `pydantic-settings` (env vars only)
- **Logging**: `loguru`
- **Scheduling**: APScheduler (single daily job + manual trigger)
- **Domain models**: Pydantic
- **Paths**: `pathlib.Path` exclusively
- **State**: `data/state.json` (local JSON, no database)
- **Docker**: `docker/Dockerfile` + `docker/compose.yaml`
- **CI/CD**: GitHub Actions on self-hosted runner; secrets rendered
  to `docker/.env` at deploy time
- **Entry point**: `python -m telegram_radar`

## Development Workflow

- Code MUST be readable, minimal, and explicit. Small functions.
  No magic. Type annotations on all public interfaces.
- Pydantic models MUST be used for all domain objects and LLM I/O.
- Pure-logic components (`BatchBuilder`, `DigestBuilder`,
  `StateManager`) MUST be deterministic and unit-testable with no
  external dependencies — this is enforced by Clean Architecture
  (Principle VIII).
- New features MUST follow the TDD cycle (Principle VII): write
  failing test → implement → refactor.
- The `data/` directory MUST be created automatically at runtime
  if absent.
- Commit after each logical unit of work.
- Owner-only access: only `TG_OWNER_USER_ID` can execute bot
  commands.

## Governance

This constitution is the authoritative reference for architectural
and process decisions in the Telegram Radar Digest project. All
implementation work MUST comply with these principles.

**Amendment procedure**: Any change to this constitution MUST be
documented with a version bump, a rationale, and a sync impact
report. Amendments follow semantic versioning:
- **MAJOR**: Principle removal or backward-incompatible redefinition.
- **MINOR**: New principle or materially expanded guidance.
- **PATCH**: Clarifications, wording, typo fixes.

**Compliance review**: Each feature spec and implementation plan
MUST include a Constitution Check section verifying alignment with
all active principles before work begins.

**Version**: 1.2.0 | **Ratified**: 2026-02-10 | **Last Amended**: 2026-02-10
