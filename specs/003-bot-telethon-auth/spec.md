# Feature Specification: Bot-Assisted Telethon Authentication

**Feature Branch**: `003-bot-telethon-auth`
**Created**: 2026-02-11
**Status**: Draft
**Input**: User description: "Сделай подтверждение кода через бота"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - First-Time Login via Bot (Priority: P1)

The owner deploys the application for the first time (or after session expiry). There is no valid Telethon session file. Instead of crashing or hanging on stdin, the application starts the bot and sends the owner a message asking for their phone number. The owner replies with their phone number, receives a Telegram verification code, enters it via the bot, and the application completes authentication and begins normal operation.

**Why this priority**: Without this, the application cannot start in a headless environment (Docker container, server) when no pre-existing session exists. This is the core blocker for deployment.

**Independent Test**: Can be fully tested by deploying the application without a session file and completing the login flow entirely through the bot conversation. Delivers a fully operational application after authentication.

**Acceptance Scenarios**:

1. **Given** the application starts with no session file, **When** the bot initializes, **Then** the bot sends a message to the owner requesting their phone number.
2. **Given** the bot has sent a phone request, **When** the owner replies with a valid phone number, **Then** the system requests a verification code from Telegram and the bot asks the owner to enter the code.
3. **Given** the bot has asked for the verification code, **When** the owner replies with the correct code, **Then** the session is created, persisted to disk, and the application transitions to normal operation.
4. **Given** the bot has asked for the verification code, **When** the owner replies with an incorrect code, **Then** the bot informs the owner and allows them to retry.

---

### User Story 2 - Two-Factor Authentication Support (Priority: P1)

The owner's Telegram account has two-factor authentication (2FA / cloud password) enabled. After entering the verification code, the bot asks for the 2FA password before completing authentication.

**Why this priority**: Many security-conscious users enable 2FA. Without this, those users cannot authenticate at all.

**Independent Test**: Can be tested by using a Telegram account with 2FA enabled and completing the full login flow through the bot.

**Acceptance Scenarios**:

1. **Given** the owner has entered a correct verification code and their account has 2FA enabled, **When** the system detects 2FA is required, **Then** the bot asks the owner for their cloud password.
2. **Given** the bot has asked for the 2FA password, **When** the owner provides the correct password, **Then** the session is created and the application starts normally.
3. **Given** the bot has asked for the 2FA password, **When** the owner provides an incorrect password, **Then** the bot informs the owner and allows them to retry.

---

### User Story 3 - Existing Valid Session (Priority: P1)

The application starts and a valid, authorized session file already exists (e.g., from a previous run, persisted via a Docker volume). The application skips the login flow entirely and starts normally without bothering the owner.

**Why this priority**: This is the normal steady-state. The login flow should only trigger when actually needed.

**Independent Test**: Can be tested by deploying with a valid session file mounted and verifying the application starts without sending any login-related messages.

**Acceptance Scenarios**:

1. **Given** a valid session file exists, **When** the application starts, **Then** it connects using the existing session and begins normal operation without prompting the owner.

---

### User Story 4 - Login Timeout (Priority: P2)

The owner does not respond to the login prompts within a reasonable time. The application does not hang indefinitely — it logs the situation and retries or waits gracefully.

**Why this priority**: Prevents the application from being stuck in an unresponsive state if the owner is unavailable when deployment happens.

**Independent Test**: Can be tested by starting the application without a session and not responding to the bot's messages, then verifying the application handles the timeout gracefully.

**Acceptance Scenarios**:

1. **Given** the bot has sent a login prompt, **When** the owner does not respond within 5 minutes, **Then** the bot sends a reminder message.
2. **Given** the owner still has not responded after the reminder, **When** the total wait exceeds 10 minutes, **Then** the application logs a warning and continues waiting (the bot remains available for the owner to respond later).

---

### Edge Cases

- What happens if the owner sends an unrelated command (e.g., `/digest_now`) while the login flow is in progress? The bot should inform them that login must be completed first.
- What happens if the session file becomes invalid between restarts (e.g., session revoked by Telegram)? The application should detect this and re-initiate the login flow.
- What happens if multiple messages arrive during the login flow from other users? Only messages from the owner should be processed; others should be ignored.
- What happens if the owner sends the phone number in an unexpected format (e.g., with spaces or dashes)? The system should normalize common formats.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect whether a valid, authorized session exists at startup.
- **FR-002**: When no valid session exists, the system MUST start the bot and initiate a login conversation with the owner.
- **FR-003**: The bot MUST send the owner a message requesting their phone number when login is needed.
- **FR-004**: The bot MUST accept the owner's phone number and trigger the verification code delivery.
- **FR-005**: The bot MUST ask the owner for the verification code after it is sent.
- **FR-006**: The bot MUST handle two-factor authentication by requesting the cloud password when required.
- **FR-007**: The bot MUST allow the owner up to 3 retries per step (code or password) on incorrect entries. After 3 failed attempts, the login flow restarts from the phone number step.
- **FR-008**: When no valid session exists, the system MUST block all regular bot commands (digest, channels, health) until login is complete.
- **FR-009**: After successful authentication, the session MUST be persisted so that subsequent restarts do not require re-authentication.
- **FR-010**: After successful authentication, the system MUST transition seamlessly to normal operation (scheduler, command handlers) without requiring a restart.
- **FR-011**: The system MUST handle expired or revoked sessions by re-initiating the login flow.
- **FR-012**: The bot MUST delete the owner's messages containing sensitive data (phone number, verification code, 2FA password) from the chat immediately after processing them.

### Key Entities

- **Login Session**: Represents the in-progress authentication flow — tracks current step (awaiting phone, awaiting code, awaiting 2FA password), number of retry attempts, and timestamps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Owner can complete first-time authentication entirely through the bot in under 2 minutes (assuming immediate responses).
- **SC-002**: Application starts without any login prompts when a valid session exists.
- **SC-003**: Application successfully recovers from an invalid/expired session by re-initiating the login flow without manual intervention.
- **SC-004**: All regular bot commands are blocked during the login flow and resume immediately after successful authentication.

## Clarifications

### Session 2026-02-11

- Q: What is the maximum number of retries for incorrect code or password? → A: 3 retries per step, then restart the login flow from the beginning.
- Q: Should the bot delete sensitive messages (phone, code, password) from chat after processing? → A: Yes, bot deletes the owner's messages containing phone/code/password after processing.

## Assumptions

- The bot token and owner user ID are always configured correctly — the bot can always reach the owner.
- The Telegram Bot API is accessible from the deployment environment.
- The session file is persisted across container restarts via a Docker volume mount.
- Phone number format: the system will accept international format with or without the `+` prefix, stripping spaces and dashes.
