# Quickstart: Clean Architecture & TDD Refactor

**Branch**: `002-clean-arch-tdd-refactor`

## Prerequisites

- Working `telegram_radar` project (from `001-telegram-radar-digest`)
- `uv sync` passes
- All 17 existing unit tests pass: `uv run pytest tests/unit/`

## Validation Steps

### After Phase 1 (Protocols + State Methods)

```bash
# 1. Verify protocols.py exists and has no infrastructure imports
grep -c "from telethon\|from openai\|import instructor" src/telegram_radar/protocols.py
# Expected: 0

# 2. Verify pipeline.py has no concrete infrastructure imports
grep -c "from telegram_radar.gateway\|from telegram_radar.summarizer\|from telegram_radar.state" src/telegram_radar/pipeline.py
# Expected: 0

# 3. Verify bot.py has no concrete infrastructure imports
grep -c "from telegram_radar.gateway\|from telegram_radar.summarizer\|from telegram_radar.state" src/telegram_radar/bot.py
# Expected: 0

# 4. Verify no _state access outside state.py
grep -rn "_state\." src/telegram_radar/pipeline.py src/telegram_radar/bot.py
# Expected: no output

# 5. All existing tests pass
uv run pytest tests/unit/ -v
# Expected: 17 passed (state tests updated for new save() signature)
```

### After Phase 2 (Pipeline Tests)

```bash
# 6. New pipeline tests pass
uv run pytest tests/unit/test_pipeline.py -v
# Expected: 4+ tests passed

# 7. Full test suite passes
uv run pytest tests/unit/ -v
# Expected: 21+ tests passed, <5 seconds
```

### After Full Refactor

```bash
# 8. Application imports cleanly
uv run python -c "from telegram_radar.pipeline import run_digest; print('OK')"
# Expected: OK

# 9. All modules importable
uv run python -c "
from telegram_radar import protocols, models, settings
from telegram_radar import batch_builder, digest_builder
from telegram_radar import state, gateway, summarizer
from telegram_radar import pipeline, bot, scheduler
print('All imports OK')
"
# Expected: All imports OK
```
