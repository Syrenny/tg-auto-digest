# Quickstart: Session Reset via /start & Bot Command Menu

## Dev Setup

```bash
uv sync
```

## Running Tests

```bash
pytest tests/test_bot_auth.py tests/test_gateway_auth.py -v
```

## Testing Scenarios

### 1. Session Reset (/start)

**Automated tests** (in `tests/test_bot_auth.py`):
- `/start` from owner triggers `gateway.log_out()` + auth flow restart
- `/start` from non-owner is ignored
- `/start` during active auth flow restarts from phone prompt
- Commands blocked after `/start` until re-auth completes
- Logout failure doesn't block auth flow

**Manual test** (in Docker):
1. Deploy with active session (bot running, commands working)
2. Send `/start` to bot
3. Verify bot replies with session reset message + phone prompt
4. Complete re-authentication (phone → code → optional 2FA)
5. Verify `/digest_now`, `/channels`, `/health` work again

### 2. Command Menu

**Automated test** (in `tests/test_bot_auth.py`):
- `set_my_commands` called during bot `start()` with correct command list

**Manual test**:
1. Open bot chat in Telegram
2. Tap the menu button (bottom-left, hamburger icon)
3. Verify 4 commands listed: `/start`, `/digest_now`, `/channels`, `/health`
4. Tap any command — verify it executes
