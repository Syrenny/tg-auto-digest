# Quickstart: Bot-Assisted Telethon Authentication

## What This Feature Does

Enables headless (Docker) deployment by allowing the Telethon session to be created through the Telegram bot instead of requiring interactive stdin input.

## How It Works

1. Deploy the app (Docker Compose) — no session file needed
2. Bot sends you a message: "Please send your phone number"
3. Reply with your phone number → bot deletes your message
4. Enter the verification code Telegram sends you → bot deletes your message
5. If you have 2FA: enter your cloud password → bot deletes your message
6. Done — app starts normally. Session persists across restarts via Docker volume.

## Development Setup

```bash
# Run tests
cd /home/syrenny/Desktop/clones/tg-auto-digest
pytest

# Run locally (will trigger auth flow if no session)
python -m telegram_radar

# Build and run in Docker
docker compose -f docker/compose.yaml up -d --build
```

## Files Modified

| File | Change |
|------|--------|
| `src/telegram_radar/gateway.py` | Split `start()` into `connect()` + auth methods |
| `src/telegram_radar/bot.py` | Add ConversationHandler for auth flow |
| `src/telegram_radar/__main__.py` | Change startup sequence |
| `src/telegram_radar/protocols.py` | Add auth methods to TelegramGateway protocol |

## Testing Strategy

- **Unit tests**: Auth state transitions, retry logic, phone normalization
- **Integration tests**: Mock Telethon client + mock bot to test full flow
- **Manual test**: Deploy to Docker without session, complete auth via bot
