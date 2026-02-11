# Research: Session Reset via /start & Bot Command Menu

## Decision 1: Telethon Session Logout Mechanism

**Decision**: Use `client.log_out()` followed by creating a new `TelegramClient` instance.

**Rationale**: `log_out()` both invalidates the session server-side and deletes the local `.session` file. After `log_out()`, the client instance is unusable — Telethon documentation explicitly states a new instance must be created. The gateway must therefore recreate its internal `_client` after logout.

**Alternatives considered**:
- Delete session file manually + disconnect: Doesn't invalidate server-side, session could still be active elsewhere. Rejected.
- Call `disconnect()` only: Preserves the session, doesn't actually log out. Not what the user wants. Rejected.

**Key details**:
- `await client.log_out()` — returns `True` on success
- Deletes the `*.session` file from disk automatically
- Client is unusable after — must create new `TelegramClient` instance
- No known RPC errors from the API call itself
- Wrap in try/except for network errors; proceed with local cleanup regardless

## Decision 2: Gateway Client Recreation Strategy

**Decision**: Add `log_out()` method to gateway that calls `client.log_out()`, then recreates `self._client` as a new `TelegramClient` instance and calls `connect()`.

**Rationale**: The gateway owns the client lifecycle. After logout, it must provide a fresh connected client for the re-authentication flow. The bot and `__main__` should not need to know about client recreation — the gateway handles it internally.

**Alternatives considered**:
- Expose client recreation to `__main__.py`: Violates isolation of concerns (Principle III). Rejected.
- Restart the entire application: Overkill for a session reset. Rejected.

## Decision 3: Bot Command Menu Registration

**Decision**: Call `bot.set_my_commands()` after `app.initialize()` + `app.start()`, inside the bot's `start()` method.

**Rationale**: Commands are persistent at the Telegram API level but should be set on every startup to stay in sync with code. The `start()` method in `TelegramBotController` already runs `initialize()` + `start()` + `start_polling()` — adding `set_my_commands` there is the natural place.

**Alternatives considered**:
- Use `Application.builder().post_init()`: Would work, but our bot already has a custom `start()` method that controls the sequence. Adding it there is simpler and more explicit. Rejected.
- Set commands only once manually via BotFather: Wouldn't stay in sync with code changes. Rejected.

**Key details**:
- `BotCommand(command, description)` — command is lowercase, 1-32 chars
- `await bot.set_my_commands([...])` — simple list of BotCommand objects
- No scope needed — this is a single-user bot, default scope is fine
- Telegram caches menus ~5 minutes; changes visible after reopening chat
