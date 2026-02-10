# Implementation Plan: Clean Architecture & TDD Refactor

**Branch**: `002-clean-arch-tdd-refactor` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-clean-arch-tdd-refactor/spec.md`

## Summary

Refactor the existing Telegram Radar Digest codebase to comply with
Constitution Principles VII (TDD) and VIII (Clean Architecture).
Introduce `typing.Protocol` definitions for the three infrastructure
classes (`TelegramClientGateway`, `LLMSummarizer`, `StateManager`),
replace concrete imports in the application and presentation layers
with Protocol types, fix state encapsulation violations via CQS
methods, and add pipeline orchestrator unit tests using mock Protocol
implementations.

## Technical Context

**Language/Version**: Python >= 3.13
**Primary Dependencies**: telethon, python-telegram-bot, instructor, openai, apscheduler, pydantic, pydantic-settings, loguru (all unchanged)
**Storage**: `data/state.json` (local JSON, no database)
**Testing**: pytest + pytest-asyncio with `asyncio_mode = "auto"`
**Target Platform**: Linux (Docker container, self-hosted runner)
**Project Type**: Single project
**Performance Goals**: N/A (structural refactor, no performance changes)
**Constraints**: All existing 17 unit tests must pass; no functional behavior changes
**Scale/Scope**: ~10 source files, ~3 new/modified files, ~1 new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | MVP-First Delivery | PASS | Protocols are the minimal abstraction needed to satisfy Principle VIII. No extra patterns (DI container, factory, etc.) |
| II | Fully Async, Single Service | PASS | No architecture change. Async methods in Protocols match existing async signatures |
| III | Strict Isolation of Concerns | PASS | Protocols formalize the isolation already expressed by separate classes. No new coupling |
| IV | Explicit Configuration | PASS | No configuration changes |
| V | Structured LLM Outputs | PASS | LLM interaction unchanged. `Summarizer` Protocol wraps the same `summarize_batch` method |
| VI | Observable Logging | PASS | Logging unchanged. loguru remains in all layers as cross-cutting concern |
| VII | Test-Driven Development | PASS | New pipeline tests follow TDD pattern. Existing tests preserved |
| VIII | Clean Architecture | PASS | This feature IS the Clean Architecture implementation. Protocols = ports, infrastructure = adapters |

All 8 gates PASS. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-clean-arch-tdd-refactor/
├── plan.md              # This file
├── research.md          # Phase 0: Protocol patterns, test doubles, state encapsulation
├── data-model.md        # Phase 1: Protocol definitions, StateManager changes
├── quickstart.md        # Validation commands
├── contracts/
│   └── protocols.md     # Protocol method signatures and import patterns
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
src/telegram_radar/
├── __init__.py          # (unchanged)
├── __main__.py          # (unchanged — composition root, concrete imports OK)
├── models.py            # (unchanged — domain layer)
├── settings.py          # (unchanged — configuration)
├── protocols.py         # NEW — Protocol definitions for TelegramGateway, Summarizer, StateRepository
├── batch_builder.py     # (unchanged — domain layer)
├── digest_builder.py    # (unchanged — domain layer)
├── state.py             # MODIFIED — add record_last_run(), get_channel_state(), change save() signature
├── gateway.py           # (unchanged — infrastructure, satisfies TelegramGateway structurally)
├── summarizer.py        # (unchanged — infrastructure, satisfies Summarizer structurally)
├── pipeline.py          # MODIFIED — import Protocols instead of concrete classes
├── bot.py               # MODIFIED — import Protocols instead of concrete classes
└── scheduler.py         # (unchanged)

tests/
└── unit/
    ├── test_batch_builder.py   # (unchanged)
    ├── test_digest_builder.py  # (unchanged)
    ├── test_state.py           # MODIFIED — update save() calls for new signature
    └── test_pipeline.py        # NEW — pipeline orchestrator tests with mock Protocols
```

**Structure Decision**: Flat single-project layout preserved. One new
file (`protocols.py`) added at the same level as existing modules.
No sub-packages introduced.

## Complexity Tracking

> No violations. All changes are minimal and directly required by
> Constitution Principles VII and VIII.
