# Implementation Plan: Session Reset via /start & Bot Command Menu

**Branch**: `004-start-reset-bot-menu` | **Date**: 2026-02-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-start-reset-bot-menu/spec.md`

## Summary

Add `/start` command that logs out the current Telethon session and restarts the auth flow, plus register a bot command menu on startup so all commands are visible in Telegram's menu button. Key architectural constraint: Telethon client is unusable after `log_out()` — gateway must recreate the client instance.

## Technical Context

**Language/Version**: Python >= 3.13
**Primary Dependencies**: telethon (user client), python-telegram-bot v20+ (bot), pydantic-settings, loguru
**Storage**: `data/state.json` (local JSON), Telethon session file (SQLite, managed by Telethon)
**Testing**: pytest (with unittest.mock)
**Target Platform**: Linux server (Docker container)
**Project Type**: Single project
**Performance Goals**: N/A (single-user bot)
**Constraints**: Bot must remain responsive during session reset; Telethon client instance must be recreated after `log_out()`
**Scale/Scope**: Single user (owner), 4 bot commands

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. MVP-First Delivery | PASS | Minimal changes: one new command handler, one `set_my_commands` call. No abstractions. |
| II. Fully Async, Single Service | PASS | All new code is async. Single service unchanged. |
| III. Strict Isolation of Concerns | PASS | Gateway handles logout + client recreation. Bot handles `/start` command + menu registration. Clear separation. |
| IV. Explicit Configuration | PASS | No new config needed. Uses existing `tg_owner_user_id`, `tg_bot_token`, Telethon settings. |
| V. Structured LLM Outputs | N/A | No LLM interaction in this feature. |
| VI. Observable Logging | PASS | Log session logout, client recreation, auth flow restart, menu registration. |
| VII. TDD | PASS | Tests written first for `/start` handler, gateway `log_out`, and menu registration. |
| VIII. Clean Architecture | PASS | `log_out()` added to `TelegramGateway` protocol. Bot depends on protocol, not concrete gateway. |

## Project Structure

### Documentation (this feature)

```text
specs/004-start-reset-bot-menu/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── bot-commands.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
src/telegram_radar/
├── protocols.py        # Add log_out() to TelegramGateway protocol
├── gateway.py          # Implement log_out() + client recreation
├── bot.py              # Add /start handler + set_my_commands on startup
└── __main__.py         # No changes expected

tests/
├── test_gateway_auth.py  # Add log_out tests
└── test_bot_auth.py      # Add /start handler + menu registration tests
```

**Structure Decision**: Existing single-project structure. Changes touch 4 source files and 2 test files. No new files needed.
