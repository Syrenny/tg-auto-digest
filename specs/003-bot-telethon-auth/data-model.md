# Data Model: Bot-Assisted Telethon Authentication

## Entities

### AuthState (enum)

Represents the current step of the login conversation.

| Value | Description |
|-------|-------------|
| `AWAITING_PHONE` | Initial state — waiting for owner to send phone number |
| `AWAITING_CODE` | Phone submitted, verification code sent — waiting for code |
| `AWAITING_PASSWORD` | Code accepted, 2FA required — waiting for cloud password |

Maps directly to `ConversationHandler` state constants.

### State Transitions

```
App starts → gateway.connect() → is_authorized()?
  ├─ YES → normal operation (no auth flow)
  └─ NO → bot sends prompt → AWAITING_PHONE
      │
      ├─ owner sends phone → send_code_request() → AWAITING_CODE
      │
      ├─ owner sends code → sign_in(code)
      │   ├─ success → auth complete → normal operation
      │   ├─ SessionPasswordNeededError → AWAITING_PASSWORD
      │   ├─ PhoneCodeInvalidError → retry (up to 3) → AWAITING_CODE
      │   └─ 3 failures → restart → AWAITING_PHONE
      │
      └─ owner sends password → sign_in(password)
          ├─ success → auth complete → normal operation
          ├─ PasswordHashInvalidError → retry (up to 3) → AWAITING_PASSWORD
          └─ 3 failures → restart → AWAITING_PHONE
```

### Internal Tracking (in-memory only, not persisted)

- `phone: str` — owner's phone number (kept for sign_in calls)
- `phone_code_hash: str` — hash from send_code_request (Telethon caches internally)
- `retry_count: int` — retries for current step (reset on state transition)

No new persistent storage needed — the Telethon session file is the only persisted artifact.
