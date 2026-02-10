# Telegram Radar Digest

Personal tool that reads Telegram channels from a "Radar" folder, fetches recent posts and comments, summarizes them via an LLM, and sends a daily digest through a Telegram bot.

## Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- Telegram API credentials from https://my.telegram.org
- Telegram Bot token from [@BotFather](https://t.me/BotFather)
- OpenAI API key (or compatible provider)

## Local Setup

```bash
# Install dependencies
uv sync

# Create .env file (or export env vars)
cp docker/.env.example docker/.env  # then edit with your values

# Required env vars:
# TELEGRAM_API_ID=...
# TELEGRAM_API_HASH=...
# TG_BOT_TOKEN=...
# TG_OWNER_USER_ID=...
# LLM_MODEL=gpt-4o-mini
# LLM_API_KEY=sk-...

# Run the application
uv run python -m telegram_radar
```

On first run, Telethon will prompt for phone number and 2FA code to create the session file at `data/telethon.session`.

## Bot Commands

| Command | Description |
|---------|-------------|
| `/digest_now` | Generate and send digest immediately |
| `/channels` | List monitored channels with last-run post counts |
| `/health` | Check Telegram and LLM connectivity |

All commands are restricted to the configured owner user ID.

## Docker

```bash
# Create .env with your credentials
vi docker/.env

# Build and run
docker compose -f docker/compose.yaml up -d --build

# View logs
docker compose -f docker/compose.yaml logs -f
```

The `data/` directory is mounted as a volume for state persistence and the Telethon session file.

## Deploy via GitHub Actions

1. Add all env vars as GitHub Secrets in your repository.
2. Push to `main` — the workflow checks out on a self-hosted runner, writes `docker/.env` from secrets, and runs `docker compose up -d --build`.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_API_ID` | required | Telegram API ID |
| `TELEGRAM_API_HASH` | required | Telegram API hash |
| `TELETHON_SESSION_PATH` | `data/telethon.session` | Path to session file |
| `TG_BOT_TOKEN` | required | Bot token from BotFather |
| `TG_OWNER_USER_ID` | required | Your Telegram user ID |
| `RADAR_FOLDER_NAME` | `Radar` | Telegram folder name to monitor |
| `FETCH_SINCE_HOURS` | `24` | Fallback fetch window (hours) |
| `FETCH_LIMIT_PER_CHANNEL` | `50` | Max posts per channel per run |
| `COMMENTS_LIMIT_PER_POST` | `10` | Max comments to fetch per post |
| `COMMENT_MAX_LEN` | `500` | Max chars per comment |
| `DIGEST_MAX_ITEMS` | `20` | Max items in digest message |
| `DEADLINE_URGENT_DAYS` | `7` | Days threshold for urgent items |
| `LLM_MODEL` | required | LLM model name |
| `LLM_API_KEY` | required | LLM API key |
| `LLM_MAX_CHARS_PER_BATCH` | `12000` | Char budget per LLM batch |
