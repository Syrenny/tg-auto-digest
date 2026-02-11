# Data Model: Session Reset via /start & Bot Command Menu

No new entities are introduced. This feature modifies existing behavior only.

## Modified Interfaces

### TelegramGateway Protocol (protocols.py)

New method added:

- `log_out() -> None` — Logs out the current Telethon session (server-side invalidation + session file deletion), recreates the internal client, and reconnects. After this call, `is_authorized()` returns `False`.

### TelegramBotController (bot.py)

New state transitions:

- `/start` command triggers: `_auth_complete = False` → gateway `log_out()` → `start_auth_flow(event)`
- Menu registration happens in `start()` method via `set_my_commands()`

## State Transition: /start Reset Flow

```
[Authenticated] --/start--> [Logging out] --> [Not Authenticated] --> [Auth Flow] --> [Authenticated]
                                                      |
                                            (same as initial startup)
```

The auth flow after `/start` reuses the existing conversation handler (phone → code → optional 2FA → success).
