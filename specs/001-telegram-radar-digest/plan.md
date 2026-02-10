# Implementation Plan: Telegram Radar Digest MVP

**Branch**: `001-telegram-radar-digest` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-telegram-radar-digest/spec.md`

## Summary

Build a personal tool that discovers Telegram channels from a
"Radar" folder, fetches recent posts and comments, summarizes them
in batches via an LLM with structured outputs, and delivers a daily
digest via a Telegram bot. The system is a single async Python
service deployed as a Docker container on a self-hosted runner via
GitHub Actions.

## Technical Context

**Language/Version**: Python >= 3.13
**Primary Dependencies**: Telethon (user client), python-telegram-bot
v20+ (bot API), instructor + openai (structured LLM), APScheduler
v3.x (scheduling), pydantic + pydantic-settings (models + config),
loguru (logging)
**Storage**: Local JSON file (`data/state.json`)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Docker container)
**Project Type**: Single project
**Performance Goals**: Process 50 posts/channel within 5 minutes
per digest run
**Constraints**: Single user, single container, no database
**Scale/Scope**: 1 user, ~10-20 channels, ~50 posts/channel/day

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | MVP-First Delivery | PASS | No abstractions beyond what's needed; no feature flags; direct implementation of `docs/initial.md` requirements only |
| II | Fully Async, Single Service | PASS | All I/O async via Telethon + python-telegram-bot + async OpenAI; single container; one event loop |
| III | Strict Isolation of Concerns | PASS | Six dedicated classes: TelegramClientGateway, BatchBuilder, LLMSummarizer, DigestBuilder, TelegramBotController, Scheduler — see contracts/internal-interfaces.md |
| IV | Explicit Configuration, No Secrets in Code | PASS | All config via pydantic-settings from env vars; .env generated at deploy time from GitHub Secrets; .env in .gitignore |
| V | Structured LLM Outputs | PASS | instructor + Pydantic v2 models with Field constraints; DigestBatchResult schema enforced with max_retries=3 |
| VI | Observable Logging | PASS | loguru for all key metrics: channel count, posts/channel, comment success rate, batch sizes, LLM durations, delivery status |

**Pre-Phase 0 gate**: PASS (no violations)

## Project Structure

### Documentation (this feature)

```text
specs/001-telegram-radar-digest/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── bot-commands.md
│   └── internal-interfaces.md
└── tasks.md                     # Created by /speckit.tasks
```

### Source Code (repository root)

```text
src/telegram_radar/
├── __init__.py
├── __main__.py                  # Entry point: starts bot + scheduler
├── settings.py                  # pydantic-settings config
├── models.py                    # Domain models (Pydantic)
├── gateway.py                   # TelegramClientGateway (Telethon)
├── batch_builder.py             # BatchBuilder (pure logic)
├── summarizer.py                # LLMSummarizer (instructor)
├── digest_builder.py            # DigestBuilder (formatting)
├── bot.py                       # TelegramBotController (Bot API)
├── scheduler.py                 # Scheduler (APScheduler)
├── state.py                     # StateManager (JSON persistence)
└── pipeline.py                  # run_digest orchestrator

tests/
├── unit/
│   ├── test_batch_builder.py
│   ├── test_digest_builder.py
│   └── test_state.py
└── integration/
    └── (deferred to post-MVP)

docker/
├── Dockerfile
└── compose.yaml

.github/
└── workflows/
    └── deploy.yaml

data/                            # Created at runtime
├── state.json
└── telethon.session
```

**Structure Decision**: Single project layout under `src/telegram_radar/`.
Matches `docs/initial.md` requirement for `python -m telegram_radar`
entry point. Flat module structure (no nested packages) for MVP
simplicity.

## Complexity Tracking

> No violations detected. This section is intentionally empty.

## Post-Design Constitution Re-Check

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | MVP-First Delivery | PASS | Flat module structure, no unnecessary abstractions |
| II | Fully Async, Single Service | PASS | Single `__main__.py` runs Telethon + bot + scheduler in one loop |
| III | Strict Isolation of Concerns | PASS | 6 classes with explicit interfaces per contracts |
| IV | Explicit Configuration, No Secrets in Code | PASS | `settings.py` with pydantic-settings; deploy.yaml writes .env |
| V | Structured LLM Outputs | PASS | `models.py` defines DigestItem/DigestBatchResult with Field constraints |
| VI | Observable Logging | PASS | loguru calls planned in gateway, summarizer, pipeline |

**Post-Phase 1 gate**: PASS
