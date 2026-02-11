# Bot Commands Contract

## Command Menu (set_my_commands)

Registered on startup. All commands visible to all users in chat menu.

| Command       | Description                      |
|---------------|----------------------------------|
| /start        | Reset session and re-authenticate |
| /digest_now   | Generate digest immediately       |
| /channels     | List monitored channels           |
| /health       | Check system health               |

## /start Command Handler

**Trigger**: Owner sends `/start`
**Access**: Owner only (by `tg_owner_user_id`). Non-owners silently ignored.

### Behavior

1. Call `gateway.log_out()` (wrapped in try/except — proceed on failure)
2. Set `_auth_complete = False`
3. Send confirmation: "Session reset. Starting re-authentication..."
4. Call `start_auth_flow(event)` to begin phone → code → 2FA flow
5. Block `/digest_now`, `/channels`, `/health` until auth completes

### Edge Cases

- **During active auth flow**: Cancel current flow, restart from step 1
- **Logout fails**: Log warning, proceed with auth flow anyway (local state cleared)
- **Not authenticated**: Skip logout, go directly to auth flow

## Gateway Protocol Extension

```python
class TelegramGateway(Protocol):
    # ... existing methods ...
    async def log_out(self) -> None: ...
```

### log_out() Behavior

1. Call `self._client.log_out()` (invalidates session server-side, deletes session file)
2. Call `self._client.disconnect()`
3. Recreate `self._client = TelegramClient(...)` with same settings
4. Call `self._client.connect()` (network connection only, no auth)
5. Log: "Session logged out and client reconnected"

On failure at step 1-2: log warning, continue with steps 3-5 (ensure fresh client regardless).
