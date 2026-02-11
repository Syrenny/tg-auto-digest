# Research: Bot-Assisted Telethon Authentication

## Decision 1: Telethon Auth Method

**Decision**: Use low-level `connect()` + `send_code_request()` + `sign_in()` instead of high-level `start()`.

**Rationale**: `start()` uses `input()` by default for interactive auth, which crashes in Docker (EOFError). The low-level methods allow programmatic control — phone/code/password can come from bot messages instead of stdin.

**Alternatives considered**:
- `start(phone=callable, code_callback=callable, password=callable)` with async callables bridged via `asyncio.Event`. Works but couples Telethon's internal retry logic with our bot flow, making error handling less transparent.
- Pre-creating session locally and mounting into container. Works for initial deploy but doesn't handle session expiry.

## Decision 2: Bot Conversation Pattern

**Decision**: Use `ConversationHandler` from python-telegram-bot with state machine (PHONE → CODE → PASSWORD → END).

**Rationale**: `ConversationHandler` is the library's built-in pattern for multi-step conversations. It manages state transitions, handles fallbacks, and integrates naturally with the existing handler registration pattern in `bot.py`.

**Alternatives considered**:
- Manual state tracking with `MessageHandler` + a state variable. Works but reinvents what `ConversationHandler` already provides.
- Separate auth bot instance. Unnecessary complexity for a single-user tool.

## Decision 3: Bot-Gateway Coordination

**Decision**: Bot's ConversationHandler callbacks directly call gateway auth methods. An `asyncio.Event` signals auth completion to `__main__`.

**Rationale**: Simplest approach — no intermediate queues or event bridges for each step. The bot handler receives the message, calls the gateway method, handles the result, and transitions state. Only one event needed: "auth is done, start the rest of the app."

**Alternatives considered**:
- Orchestrator coroutine with `asyncio.Event` per step (phone_event, code_event, password_event). More decoupled but adds 3x coordination objects for a flow that only runs once at startup.
- Callback-based approach where gateway drives the flow and calls back into bot. Inverts control unnecessarily.

## Decision 4: Startup Sequence Change

**Decision**: Change startup order from `gateway.start()` → `bot.start()` → `scheduler.start()` to `gateway.connect()` → `bot.start()` → (auth if needed) → `scheduler.start()`.

**Rationale**: The bot must be running before auth can happen (it collects the credentials). The gateway only needs a network connection to check authorization status. Full gateway "start" (auth + connect) is split into separate steps.

**Alternatives considered**:
- Starting bot and gateway in parallel. Adds complexity for no benefit since auth check is fast.

## Decision 5: Command Blocking During Auth

**Decision**: Use a boolean flag (`_auth_complete`) in the bot. Existing command handlers check the flag and reply "Login required" if auth is pending.

**Rationale**: Simpler than dynamically adding/removing handlers. One `if` check at the top of each command handler.

**Alternatives considered**:
- Removing command handlers and re-adding after auth. More code, harder to test, risk of handler registration bugs.
- Using ConversationHandler's built-in blocking (it consumes matching messages). Only works for text, not for /commands outside the conversation.

## Decision 6: Message Deletion

**Decision**: Delete the owner's message containing sensitive data immediately after reading it, using `bot.delete_message()`. Wrap in try/except since deletion can fail.

**Rationale**: Per clarification FR-012. Deletion is best-effort — if it fails (permissions, message too old), log a warning but continue the auth flow.

**Alternatives considered**:
- Not deleting (left to user). Rejected per clarification.

## Telethon Error Types Reference

| Error | When | Action |
|-------|------|--------|
| `SessionPasswordNeededError` | After valid code, 2FA enabled | Ask for password |
| `PhoneCodeInvalidError` | Wrong code | Retry (up to 3) |
| `PhoneCodeExpiredError` | Code timeout | Request new code |
| `PasswordHashInvalidError` | Wrong 2FA password | Retry (up to 3) |
| `PhoneNumberInvalidError` | Bad phone format | Ask again |
| `FloodWaitError` | Too many requests | Log wait time, inform user |
