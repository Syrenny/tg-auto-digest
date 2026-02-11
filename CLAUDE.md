# tg-auto-digest Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-11

## Active Technologies
- Python >= 3.13 + telethon, python-telegram-bot, instructor, openai, apscheduler, pydantic, pydantic-settings, loguru (all unchanged) (002-clean-arch-tdd-refactor)
- `data/state.json` (local JSON, no database) (002-clean-arch-tdd-refactor)
- Python >= 3.13 + Telethon (user client auth), python-telegram-bot (ConversationHandler), pydantic-settings, loguru (003-bot-telethon-auth)
- Telethon session file at `data/telethon.session` (persisted via Docker volume), `data/state.json` (unchanged) (003-bot-telethon-auth)

- Python >= 3.13 + Telethon (user client), python-telegram-bot (001-telegram-radar-digest)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python >= 3.13: Follow standard conventions

## Recent Changes
- 003-bot-telethon-auth: Added Python >= 3.13 + Telethon (user client auth), python-telegram-bot (ConversationHandler), pydantic-settings, loguru
- 002-clean-arch-tdd-refactor: Added Python >= 3.13 + telethon, python-telegram-bot, instructor, openai, apscheduler, pydantic, pydantic-settings, loguru (all unchanged)

- 001-telegram-radar-digest: Added Python >= 3.13 + Telethon (user client), python-telegram-bot

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
