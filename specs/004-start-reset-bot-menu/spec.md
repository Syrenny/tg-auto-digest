# Feature Specification: Session Reset via /start & Bot Command Menu

**Feature Branch**: `004-start-reset-bot-menu`
**Created**: 2026-02-11
**Status**: Draft
**Input**: User description: "Сделай так, чтобы при /start сессия Telegram обнулялась, еще сделай так, чтобы было видно меню из команд бота"

## User Scenarios & Testing

### User Story 1 - Session Reset via /start Command (Priority: P1)

The bot owner sends the `/start` command to the bot. The system invalidates and deletes the current Telegram user session, then initiates the authentication flow from scratch (phone number prompt). This allows the owner to re-authenticate with a different account or fix a broken session without redeploying.

**Why this priority**: Core operational need. If a session becomes stale, corrupted, or the owner wants to switch accounts, there must be a way to reset without server access.

**Independent Test**: Send `/start` to the bot while authenticated. Verify the session is cleared, commands become blocked, and the login flow restarts with a phone number prompt.

**Acceptance Scenarios**:

1. **Given** the bot is running with an active authenticated session, **When** the owner sends `/start`, **Then** the system logs out the current Telegram user session, resets the authentication state, and prompts the owner for a phone number to re-authenticate.
2. **Given** the bot is running without an active session (not authenticated), **When** the owner sends `/start`, **Then** the system starts the authentication flow (phone number prompt) as usual.
3. **Given** the bot is running, **When** a non-owner user sends `/start`, **Then** the command is ignored.
4. **Given** the owner has sent `/start` and the session is being reset, **When** the owner sends `/digest_now`, `/channels`, or `/health`, **Then** the bot replies with "Please complete the login first."

---

### User Story 2 - Visible Bot Command Menu (Priority: P1)

When the owner opens the bot chat, they see a menu button (hamburger menu) with all available commands and their descriptions. This eliminates the need to remember command names and makes the bot discoverable.

**Why this priority**: Equal to US1 — improves usability for all bot interactions. Without a menu, the owner must remember exact command names.

**Independent Test**: Open the bot chat in Telegram. Tap the menu button (bottom-left). Verify all commands are listed with descriptions.

**Acceptance Scenarios**:

1. **Given** the bot is running, **When** the owner opens the bot chat and taps the menu button, **Then** a list of all bot commands is displayed with short descriptions.
2. **Given** the bot is running, **When** the command menu is displayed, **Then** it includes: `/start`, `/digest_now`, `/channels`, `/health`.
3. **Given** the owner sees the command menu, **When** they tap any command, **Then** it is sent to the bot and executed normally.

---

### Edge Cases

- What happens if `/start` is sent while the authentication flow is already in progress? The current flow is cancelled and restarted from scratch.
- What happens if the session logout fails (network error, already disconnected)? The system proceeds with clearing local state and starting re-authentication regardless.
- What happens if the command menu registration fails on startup? The bot continues operating normally; the menu is a convenience, not a requirement.

## Requirements

### Functional Requirements

- **FR-001**: System MUST handle the `/start` command from the owner by logging out the current Telegram user session and clearing local authentication state.
- **FR-002**: After session reset via `/start`, system MUST automatically initiate the authentication flow (phone number prompt), reusing the existing login conversation.
- **FR-003**: System MUST ignore `/start` from non-owner users.
- **FR-004**: While re-authentication is in progress after `/start`, system MUST block `/digest_now`, `/channels`, and `/health` commands with "Please complete the login first."
- **FR-005**: If `/start` is sent during an active authentication flow, system MUST restart the flow from the beginning (phone number prompt).
- **FR-006**: System MUST register a command menu with the messaging platform on startup, listing all available commands with descriptions.
- **FR-007**: The command menu MUST include the following commands and descriptions:
  - `/start` — Reset session and re-authenticate
  - `/digest_now` — Generate digest immediately
  - `/channels` — List monitored channels
  - `/health` — Check system health
- **FR-008**: If session logout fails during `/start`, system MUST still clear local authentication state and proceed with the login flow.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Owner can reset their session and re-authenticate within 2 minutes by sending `/start`.
- **SC-002**: All 4 commands are visible in the bot menu immediately after opening the chat.
- **SC-003**: After `/start`, the full re-authentication flow (phone, code, optional 2FA) completes successfully.
- **SC-004**: Commands are blocked during re-authentication and resume working after successful login.

## Assumptions

- Only the designated owner (by user ID) can trigger session reset. Non-owners are silently ignored.
- The session logout disconnects the Telegram user client; the bot itself remains running and responsive throughout.
- The command menu is registered once on bot startup via the platform's set-commands mechanism.
- The existing authentication flow (phone, code, 2FA, retries, reminders) is reused without modification after session reset.
