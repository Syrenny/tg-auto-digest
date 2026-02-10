# Quickstart: Telegram Radar Digest MVP

## Prerequisites

- Python >= 3.13
- `uv` package manager installed
- Telegram account with a "Radar" folder containing channels
- Telegram Bot created via @BotFather (get token)
- Telegram API credentials from https://my.telegram.org
- OpenAI API key (or compatible LLM provider)

## Local Setup

1. Clone and install:
   ```bash
   git clone <repo-url>
   cd tg-auto-digest
   uv sync
   ```

2. Create `docker/.env` (or export env vars):
   ```env
   TELEGRAM_API_ID=12345
   TELEGRAM_API_HASH=abcdef1234567890
   TELETHON_SESSION_PATH=data/telethon.session
   TG_BOT_TOKEN=123456:ABC-DEF
   TG_OWNER_USER_ID=987654321
   RADAR_FOLDER_NAME=Radar
   LLM_MODEL=gpt-4o-mini
   LLM_API_KEY=sk-...
   ```

3. Create Telethon session (one-time, interactive):
   ```bash
   uv run python -m telegram_radar --create-session
   ```
   This prompts for phone number and 2FA code. The session file is
   saved to `data/telethon.session`.

4. Run the application:
   ```bash
   uv run python -m telegram_radar
   ```
   The bot starts listening for commands and the scheduler runs a
   daily digest.

## Docker Setup

1. Prepare `docker/.env` as above.

2. Ensure `data/telethon.session` exists (created in local setup).

3. Build and run:
   ```bash
   docker compose -f docker/compose.yaml up -d --build
   ```

4. Check logs:
   ```bash
   docker compose -f docker/compose.yaml logs -f
   ```

## Verify It Works

1. Open Telegram and send `/health` to your bot.
   Expected: both Telegram and LLM show as connected.

2. Send `/channels` to see the Radar folder contents.

3. Send `/digest_now` to trigger an immediate digest.

## Deploy via GitHub Actions

1. Add all env vars as GitHub Secrets in your repository.

2. Push to `main`. The workflow:
   - Checks out on self-hosted runner
   - Writes `docker/.env` from secrets
   - Runs `docker compose up -d --build`

## Troubleshooting

- **"Radar folder not found"**: Verify folder name in Telegram
  matches `RADAR_FOLDER_NAME` exactly.
- **Session expired**: Re-run session creation locally, then
  redeploy.
- **LLM errors**: Check `LLM_API_KEY` and `LLM_MODEL` are valid.
  View logs for detailed error messages.
