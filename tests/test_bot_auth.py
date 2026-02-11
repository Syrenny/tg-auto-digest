import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.ext import ConversationHandler
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)

from telegram_radar.bot import TelegramBotController
from telegram_radar.settings import Settings

# --- Helpers ---


def _make_settings() -> Settings:
    return Settings(
        telegram_api_id=12345,
        telegram_api_hash="testhash",
        tg_bot_token="bot:token",
        tg_owner_user_id=42,
        llm_model="test-model",
        llm_api_key="test-key",
    )


class FakeGateway:
    def __init__(self, *, authorized: bool = False) -> None:
        self.authorized = authorized
        self.send_code = AsyncMock()
        self.sign_in_code = AsyncMock()
        self.sign_in_password = AsyncMock()

    async def connect(self) -> None:
        pass

    async def is_authorized(self) -> bool:
        return self.authorized

    async def get_radar_channels(self):
        return []

    async def fetch_posts(self, *a, **kw):
        return []

    async def fetch_comments(self, *a, **kw):
        return []

    async def check_health(self) -> bool:
        return True


class FakeSummarizer:
    async def summarize_batch(self, batch):
        pass

    async def check_health(self) -> bool:
        return True


class FakeStateRepository:
    def load(self):
        pass

    def save(self):
        pass

    def get_last_message_id(self, channel_id):
        return None

    def update_channel(self, *a, **kw):
        pass

    def record_last_run(self, *a, **kw):
        pass

    def get_channel_state(self, channel_id):
        return None


def _make_update(
    text: str, user_id: int = 42, message_id: int = 1
) -> MagicMock:
    """Create a mock Update with effective_user, effective_chat, and message."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat = MagicMock()
    update.effective_chat.id = user_id
    update.effective_chat.send_message = AsyncMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.message_id = message_id
    update.message.chat_id = user_id
    return update


def _make_context():
    ctx = MagicMock()
    ctx.bot = MagicMock()
    ctx.bot.send_message = AsyncMock()
    ctx.bot.delete_message = AsyncMock()
    return ctx


@pytest.fixture
def gateway():
    return FakeGateway(authorized=False)


@pytest.fixture
def bot(gateway):
    settings = _make_settings()
    return TelegramBotController(
        settings=settings,
        gateway=gateway,
        summarizer=FakeSummarizer(),
        state=FakeStateRepository(),
        run_digest=AsyncMock(return_value="digest"),
    )


# --- T005: Bot auth conversation tests ---


class TestAuthPromptSent:
    async def test_start_auth_sends_phone_prompt(self, bot, gateway):
        event = asyncio.Event()
        with patch.object(bot, "_app") as mock_app:
            mock_app.bot = MagicMock()
            mock_app.bot.send_message = AsyncMock()
            await bot.start_auth_flow(event)
            mock_app.bot.send_message.assert_awaited_once()
            msg = mock_app.bot.send_message.call_args.kwargs.get(
                "text", str(mock_app.bot.send_message.call_args)
            )
            assert "phone" in msg.lower()


class TestPhoneHandler:
    async def test_phone_calls_send_code_and_transitions(self, bot, gateway):
        update = _make_update("+79991234567")
        ctx = _make_context()
        result = await bot._handle_phone(update, ctx)
        gateway.send_code.assert_awaited_once_with("+79991234567")
        assert result == bot.AWAITING_CODE

    async def test_phone_deletes_user_message(self, bot, gateway):
        update = _make_update("+79991234567")
        ctx = _make_context()
        await bot._handle_phone(update, ctx)
        ctx.bot.delete_message.assert_awaited_once_with(
            chat_id=42, message_id=1
        )

    async def test_phone_strips_spaces_and_dashes(self, bot, gateway):
        update = _make_update("+7 999-123-4567")
        ctx = _make_context()
        await bot._handle_phone(update, ctx)
        gateway.send_code.assert_awaited_once_with("+79991234567")

    async def test_phone_invalid_stays_in_phone_state(self, bot, gateway):
        gateway.send_code.side_effect = PhoneNumberInvalidError(None)
        update = _make_update("badphone")
        ctx = _make_context()
        result = await bot._handle_phone(update, ctx)
        assert result == bot.AWAITING_PHONE


class TestCodeHandler:
    async def test_code_success_completes_auth(self, bot, gateway):
        bot._phone = "+79991234567"
        event = asyncio.Event()
        bot._auth_event = event

        update = _make_update("12345")
        ctx = _make_context()
        result = await bot._handle_code(update, ctx)
        gateway.sign_in_code.assert_awaited_once_with("+79991234567", "12345")
        assert result == ConversationHandler.END
        assert event.is_set()

    async def test_code_deletes_user_message(self, bot, gateway):
        bot._phone = "+79991234567"
        bot._auth_event = asyncio.Event()
        update = _make_update("12345")
        ctx = _make_context()
        await bot._handle_code(update, ctx)
        ctx.bot.delete_message.assert_awaited_once_with(
            chat_id=42, message_id=1
        )

    async def test_invalid_code_retries(self, bot, gateway):
        bot._phone = "+79991234567"
        bot._auth_event = asyncio.Event()
        bot._retry_count = 0
        gateway.sign_in_code.side_effect = PhoneCodeInvalidError(None)

        update = _make_update("wrong")
        ctx = _make_context()
        result = await bot._handle_code(update, ctx)
        assert result == bot.AWAITING_CODE
        assert bot._retry_count == 1

    async def test_three_failures_restarts_to_phone(self, bot, gateway):
        bot._phone = "+79991234567"
        bot._auth_event = asyncio.Event()
        bot._retry_count = 2
        gateway.sign_in_code.side_effect = PhoneCodeInvalidError(None)

        update = _make_update("wrong")
        ctx = _make_context()
        result = await bot._handle_code(update, ctx)
        assert result == bot.AWAITING_PHONE
        assert bot._retry_count == 0


# --- T006: Session skip test ---


class TestSessionSkip:
    async def test_authorized_sets_event_immediately(self, gateway):
        gateway.authorized = True
        settings = _make_settings()
        bot = TelegramBotController(
            settings=settings,
            gateway=gateway,
            summarizer=FakeSummarizer(),
            state=FakeStateRepository(),
            run_digest=AsyncMock(return_value="digest"),
        )
        event = asyncio.Event()
        with patch.object(bot, "_app") as mock_app:
            mock_app.bot = MagicMock()
            mock_app.bot.send_message = AsyncMock()
            await bot.start_auth_flow(event)
            assert event.is_set()
            assert bot._auth_complete is True
            mock_app.bot.send_message.assert_not_awaited()


# --- T007: Command blocking tests ---


class TestCommandBlocking:
    async def test_digest_blocked_during_auth(self, bot):
        bot._auth_complete = False
        update = _make_update("/digest_now")
        ctx = _make_context()
        await bot._handle_digest_now(update, ctx)
        update.effective_chat.send_message.assert_awaited()
        msg = update.effective_chat.send_message.call_args[0][0]
        assert "login" in msg.lower()

    async def test_channels_blocked_during_auth(self, bot):
        bot._auth_complete = False
        update = _make_update("/channels")
        ctx = _make_context()
        await bot._handle_channels(update, ctx)
        update.effective_chat.send_message.assert_awaited()
        msg = update.effective_chat.send_message.call_args[0][0]
        assert "login" in msg.lower()

    async def test_health_blocked_during_auth(self, bot):
        bot._auth_complete = False
        update = _make_update("/health")
        ctx = _make_context()
        await bot._handle_health(update, ctx)
        update.effective_chat.send_message.assert_awaited()
        msg = update.effective_chat.send_message.call_args[0][0]
        assert "login" in msg.lower()

    async def test_commands_work_after_auth(self, bot):
        bot._auth_complete = True
        update = _make_update("/health")
        ctx = _make_context()
        await bot._handle_health(update, ctx)
        # Should have called check_health (no "login" block message)
        calls = update.effective_chat.send_message.call_args_list
        if calls:
            msg = calls[0][0][0]
            assert "login" not in msg.lower()


# --- T014: 2FA flow tests ---


class TestPasswordHandler:
    async def test_code_raises_session_password_needed_transitions(
        self, bot, gateway
    ):
        bot._phone = "+79991234567"
        bot._auth_event = asyncio.Event()
        gateway.sign_in_code.side_effect = SessionPasswordNeededError(None)

        update = _make_update("12345")
        ctx = _make_context()
        result = await bot._handle_code(update, ctx)
        assert result == bot.AWAITING_PASSWORD
        # Verify prompt sent
        update.effective_chat.send_message.assert_awaited()
        msg = update.effective_chat.send_message.call_args[0][0]
        assert "password" in msg.lower()

    async def test_password_success_completes_auth(self, bot, gateway):
        bot._phone = "+79991234567"
        event = asyncio.Event()
        bot._auth_event = event

        update = _make_update("mypassword")
        ctx = _make_context()
        result = await bot._handle_password(update, ctx)
        gateway.sign_in_password.assert_awaited_once_with("mypassword")
        assert result == ConversationHandler.END
        assert event.is_set()
        assert bot._auth_complete is True

    async def test_password_deletes_user_message(self, bot, gateway):
        bot._auth_event = asyncio.Event()
        update = _make_update("mypassword")
        ctx = _make_context()
        await bot._handle_password(update, ctx)
        ctx.bot.delete_message.assert_awaited_once_with(
            chat_id=42, message_id=1
        )

    async def test_invalid_password_retries(self, bot, gateway):
        bot._auth_event = asyncio.Event()
        bot._retry_count = 0
        gateway.sign_in_password.side_effect = PasswordHashInvalidError(None)

        update = _make_update("wrong")
        ctx = _make_context()
        result = await bot._handle_password(update, ctx)
        assert result == bot.AWAITING_PASSWORD
        assert bot._retry_count == 1

    async def test_three_password_failures_restarts_to_phone(
        self, bot, gateway
    ):
        bot._auth_event = asyncio.Event()
        bot._retry_count = 2
        gateway.sign_in_password.side_effect = PasswordHashInvalidError(None)

        update = _make_update("wrong")
        ctx = _make_context()
        result = await bot._handle_password(update, ctx)
        assert result == bot.AWAITING_PHONE
        assert bot._retry_count == 0


# --- T017: Timeout reminder tests ---


class TestTimeoutReminder:
    async def test_reminder_scheduled_on_auth_start(self, bot, gateway):
        """After starting auth flow, a reminder timer should be scheduled."""
        event = asyncio.Event()
        with patch.object(bot, "_app") as mock_app:
            mock_app.bot = MagicMock()
            mock_app.bot.send_message = AsyncMock()
            mock_app.add_handler = MagicMock()
            mock_app.job_queue = MagicMock()
            mock_app.job_queue.run_once = MagicMock()
            await bot.start_auth_flow(event)
            # Should have scheduled a reminder
            mock_app.job_queue.run_once.assert_called_once()
            # Timer should be ~300 seconds (5 min)
            call_kwargs = mock_app.job_queue.run_once.call_args
            when = call_kwargs.kwargs.get("when") or call_kwargs[1].get("when") or call_kwargs[0][1]
            assert 290 <= when <= 310

    async def test_reminder_cancelled_on_phone_response(self, bot, gateway):
        """When owner responds with phone, pending reminder should be cancelled."""
        old_job = MagicMock()
        old_job.schedule_removal = MagicMock()
        bot._reminder_job = old_job

        # Mock _schedule_reminder so it doesn't access real job_queue
        with patch.object(bot, "_schedule_reminder"):
            update = _make_update("+79991234567")
            ctx = _make_context()
            await bot._handle_phone(update, ctx)
            old_job.schedule_removal.assert_called_once()
