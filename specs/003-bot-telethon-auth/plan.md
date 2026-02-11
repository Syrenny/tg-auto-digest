# Implementation Plan: Bot-Assisted Telethon Authentication

**Branch**: `003-bot-telethon-auth` | **Date**: 2026-02-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-bot-telethon-auth/spec.md`

## Summary

The app crashes on first deploy in Docker because Telethon's `start()` calls `input()` for phone/code, which fails without stdin. This plan replaces the interactive auth with a bot-driven conversation: the bot collects phone, verification code, and optional 2FA password from the owner via Telegram messages, then completes Telethon authentication programmatically. No new files — modifications to 4 existing files.

## Technical Context

**Language/Version**: Python >= 3.13
**Primary Dependencies**: Telethon (user client auth), python-telegram-bot (ConversationHandler), pydantic-settings, loguru
**Storage**: Telethon session file at `data/telethon.session` (persisted via Docker volume), `data/state.json` (unchanged)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux Docker container (self-hosted runner)
**Project Type**: Single service
**Performance Goals**: Auth completion in < 2 minutes (user-dependent)
**Constraints**: Single async event loop, single user (owner only)
**Scale/Scope**: 1 user, runs once per deploy (or session expiry)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. MVP-First Delivery | PASS | No new files, no abstractions. Bot-driven auth is the simplest viable approach. |
| II. Fully Async, Single Service | PASS | All auth methods are async. Bot and Telethon share one event loop. |
| III. Strict Isolation of Concerns | PASS | Gateway handles Telethon auth primitives. Bot handles conversation UI. `__main__` orchestrates startup. |
| IV. Explicit Configuration | PASS | No new config needed. Uses existing `telegram_api_id`, `telegram_api_hash`, `tg_bot_token`, `tg_owner_user_id`. |
| V. Structured LLM Outputs | N/A | No LLM interaction in this feature. |
| VI. Observable Logging | PASS | Auth flow steps logged: connect, auth check, code sent, sign-in success/failure, retries. |
| VII. TDD | PASS | Tests written before implementation for auth state machine and retry logic. |
| VIII. Clean Architecture | PASS | Gateway (infrastructure) exposes auth primitives. Bot (infrastructure) drives conversation. Protocol updated for auth interface. Domain layer untouched. |

## Project Structure

### Documentation (this feature)

```text
specs/003-bot-telethon-auth/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── bot-auth-flow.md # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/telegram_radar/
├── __main__.py          # MODIFY: new startup sequence
├── bot.py               # MODIFY: add auth ConversationHandler + command blocking
├── gateway.py           # MODIFY: split start() into connect() + auth methods
├── protocols.py         # MODIFY: add auth methods to TelegramGateway protocol
├── settings.py          # unchanged
├── models.py            # unchanged
├── pipeline.py          # unchanged
├── batch_builder.py     # unchanged
├── digest_builder.py    # unchanged
├── summarizer.py        # unchanged
├── scheduler.py         # unchanged
└── state.py             # unchanged

tests/
├── test_gateway_auth.py # NEW: unit tests for gateway auth methods
└── test_bot_auth.py     # NEW: unit tests for bot auth conversation
```

**Structure Decision**: Single project, existing layout. Only 4 source files modified, 2 test files added.

## Complexity Tracking

No constitution violations to justify.
