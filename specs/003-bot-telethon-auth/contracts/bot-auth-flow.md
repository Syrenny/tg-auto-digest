# Contract: Bot Authentication Flow

## Bot → Owner Messages

### Prompt: Phone Number Request
**Trigger**: App starts with no valid session
```
Telegram Radar needs to log in to your Telegram account.
Please send your phone number (international format, e.g. +79991234567):
```

### Prompt: Verification Code Request
**Trigger**: Phone accepted, code sent by Telegram
```
Verification code sent. Please enter the code:
```

### Prompt: 2FA Password Request
**Trigger**: Code accepted, 2FA required
```
Two-factor authentication is enabled. Please enter your cloud password:
```

### Response: Success
**Trigger**: Auth complete
```
Login successful! Telegram Radar is now running.
```

### Response: Invalid Code
**Trigger**: PhoneCodeInvalidError (retries remaining)
```
Invalid code. Please try again ({remaining} attempts left):
```

### Response: Invalid Password
**Trigger**: PasswordHashInvalidError (retries remaining)
```
Invalid password. Please try again ({remaining} attempts left):
```

### Response: Retries Exhausted
**Trigger**: 3 failed attempts at code or password
```
Too many failed attempts. Restarting login flow.
Please send your phone number:
```

### Response: Invalid Phone
**Trigger**: PhoneNumberInvalidError
```
Invalid phone number. Please try again (international format, e.g. +79991234567):
```

### Response: Command Blocked
**Trigger**: Owner sends /digest_now, /channels, or /health during auth
```
Please complete the login first.
```

### Response: Reminder
**Trigger**: No response for 5 minutes
```
Reminder: Telegram Radar is waiting for your {phone/code/password} to complete login.
```

## Gateway Auth Protocol Extension

```python
class TelegramGateway(Protocol):
    # ... existing methods ...

    async def connect(self) -> None: ...
    async def is_authorized(self) -> bool: ...
    async def send_code(self, phone: str) -> None: ...
    async def sign_in_code(self, phone: str, code: str) -> None: ...
    async def sign_in_password(self, password: str) -> None: ...
```

### Error Mapping

| Gateway raises | Bot action |
|---------------|------------|
| `PhoneNumberInvalidError` | Show "Invalid phone" message, stay in PHONE state |
| `PhoneCodeInvalidError` | Show "Invalid code" message, stay in CODE state (decrement retries) |
| `SessionPasswordNeededError` | Transition to PASSWORD state |
| `PasswordHashInvalidError` | Show "Invalid password" message, stay in PASSWORD state (decrement retries) |
| `PhoneCodeExpiredError` | Re-request code, stay in CODE state |
| `FloodWaitError` | Show wait time to user, log warning |
