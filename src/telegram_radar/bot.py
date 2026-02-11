import asyncio
import re
from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
)

from telegram_radar.protocols import StateRepository, Summarizer, TelegramGateway
from telegram_radar.settings import Settings

# ConversationHandler states
AWAITING_PHONE = 0
AWAITING_CODE = 1
AWAITING_PASSWORD = 2

MAX_RETRIES = 3


class TelegramBotController:
    AWAITING_PHONE = AWAITING_PHONE
    AWAITING_CODE = AWAITING_CODE
    AWAITING_PASSWORD = AWAITING_PASSWORD

    def __init__(
        self,
        settings: Settings,
        gateway: TelegramGateway,
        summarizer: Summarizer,
        state: StateRepository,
        run_digest: Callable[[], Coroutine[Any, Any, str]],
    ) -> None:
        self._settings = settings
        self._gateway = gateway
        self._summarizer = summarizer
        self._state = state
        self._run_digest = run_digest
        self._app = Application.builder().token(settings.tg_bot_token).build()
        self._auth_complete: bool = False
        self._auth_event: asyncio.Event | None = None
        self._phone: str = ""
        self._retry_count: int = 0
        self._reminder_job = None
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._app.add_handler(CommandHandler("digest_now", self._handle_digest_now))
        self._app.add_handler(CommandHandler("channels", self._handle_channels))
        self._app.add_handler(CommandHandler("health", self._handle_health))

    def _is_owner(self, update: Update) -> bool:
        user = update.effective_user
        return user is not None and user.id == self._settings.tg_owner_user_id

    async def start_auth_flow(self, auth_event: asyncio.Event) -> None:
        self._auth_event = auth_event

        if await self._gateway.is_authorized():
            logger.info("Session already authorized, skipping login flow")
            self._auth_complete = True
            auth_event.set()
            return

        logger.info("Session not authorized, starting login flow via bot")
        await self._app.bot.send_message(
            chat_id=self._settings.tg_owner_user_id,
            text=(
                "Telegram Radar needs to log in to your Telegram account.\n"
                "Please send your phone number (international format, e.g. +79991234567):"
            ),
        )

        self._schedule_reminder("phone number")

        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, self._handle_phone
                )
            ],
            states={
                AWAITING_CODE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self._handle_code
                    )
                ],
                AWAITING_PASSWORD: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self._handle_password
                    )
                ],
            },
            fallbacks=[],
        )
        self._app.add_handler(conv_handler)

    def _schedule_reminder(self, awaiting: str) -> None:
        self._cancel_reminder()

        async def _send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
            await context.bot.send_message(
                chat_id=self._settings.tg_owner_user_id,
                text=f"Reminder: Telegram Radar is waiting for your {awaiting} to complete login.",
            )
            logger.warning("Auth reminder sent — still waiting for {}", awaiting)

        self._reminder_job = self._app.job_queue.run_once(
            _send_reminder, when=300
        )

    def _cancel_reminder(self) -> None:
        if self._reminder_job is not None:
            self._reminder_job.schedule_removal()
            self._reminder_job = None

    async def _delete_message(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            logger.warning("Could not delete message {}", message_id)

    async def _handle_phone(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if not self._is_owner(update):
            return AWAITING_PHONE

        text = update.message.text.strip()
        await self._delete_message(context, update.message.chat_id, update.message.message_id)
        self._cancel_reminder()

        # Normalize: strip spaces and dashes
        phone = re.sub(r"[\s\-]", "", text)
        self._phone = phone
        self._retry_count = 0

        try:
            await self._gateway.send_code(phone)
        except PhoneNumberInvalidError:
            self._schedule_reminder("phone number")
            await update.effective_chat.send_message(
                "Invalid phone number. Please try again (international format, e.g. +79991234567):"
            )
            return AWAITING_PHONE

        self._schedule_reminder("verification code")
        await update.effective_chat.send_message(
            "Verification code sent. Please enter the code:"
        )
        return AWAITING_CODE

    async def _handle_code(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if not self._is_owner(update):
            return AWAITING_CODE

        code = update.message.text.strip()
        await self._delete_message(context, update.message.chat_id, update.message.message_id)
        self._cancel_reminder()

        try:
            await self._gateway.sign_in_code(self._phone, code)
        except SessionPasswordNeededError:
            self._retry_count = 0
            self._schedule_reminder("cloud password")
            await update.effective_chat.send_message(
                "Two-factor authentication is enabled. Please enter your cloud password:"
            )
            return AWAITING_PASSWORD
        except PhoneCodeInvalidError:
            self._retry_count += 1
            if self._retry_count >= MAX_RETRIES:
                self._retry_count = 0
                await update.effective_chat.send_message(
                    "Too many failed attempts. Restarting login flow.\n"
                    "Please send your phone number:"
                )
                return AWAITING_PHONE
            remaining = MAX_RETRIES - self._retry_count
            await update.effective_chat.send_message(
                f"Invalid code. Please try again ({remaining} attempts left):"
            )
            return AWAITING_CODE
        except PhoneCodeExpiredError:
            await self._gateway.send_code(self._phone)
            await update.effective_chat.send_message(
                "Code expired. A new code has been sent. Please enter the code:"
            )
            return AWAITING_CODE

        self._auth_complete = True
        await update.effective_chat.send_message(
            "Login successful! Telegram Radar is now running."
        )
        logger.info("Auth flow completed successfully")
        if self._auth_event:
            self._auth_event.set()
        return ConversationHandler.END

    async def _handle_password(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if not self._is_owner(update):
            return AWAITING_PASSWORD

        password = update.message.text.strip()
        await self._delete_message(context, update.message.chat_id, update.message.message_id)
        self._cancel_reminder()

        try:
            await self._gateway.sign_in_password(password)
        except PasswordHashInvalidError:
            self._retry_count += 1
            if self._retry_count >= MAX_RETRIES:
                self._retry_count = 0
                await update.effective_chat.send_message(
                    "Too many failed attempts. Restarting login flow.\n"
                    "Please send your phone number:"
                )
                return AWAITING_PHONE
            remaining = MAX_RETRIES - self._retry_count
            await update.effective_chat.send_message(
                f"Invalid password. Please try again ({remaining} attempts left):"
            )
            return AWAITING_PASSWORD

        self._auth_complete = True
        await update.effective_chat.send_message(
            "Login successful! Telegram Radar is now running."
        )
        logger.info("Auth flow completed successfully (2FA)")
        if self._auth_event:
            self._auth_event.set()
        return ConversationHandler.END

    async def _handle_digest_now(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_owner(update):
            return
        if not self._auth_complete:
            await update.effective_chat.send_message("Please complete the login first.")
            return
        assert update.effective_chat is not None
        await update.effective_chat.send_message("Generating digest...")
        try:
            digest = await self._run_digest()
            await self._send_long_message(update.effective_chat.id, digest)
        except Exception as e:
            logger.exception("Digest failed")
            await update.effective_chat.send_message(
                f"Digest failed: {e}"
            )

    async def _handle_channels(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_owner(update):
            return
        if not self._auth_complete:
            await update.effective_chat.send_message("Please complete the login first.")
            return
        assert update.effective_chat is not None
        try:
            channels = await self._gateway.get_radar_channels()
            self._state.load()
            lines = ["Radar Channels:"]
            for ch in channels:
                ch_state = self._state.get_channel_state(ch.id)
                if ch_state:
                    count = ch_state.last_run_post_count
                    suffix = f"{count} posts last run"
                else:
                    suffix = "no data yet"
                name = ch.title
                if ch.username:
                    name += f" (@{ch.username})"
                lines.append(f"\u2022 {name} \u2014 {suffix}")
            await update.effective_chat.send_message("\n".join(lines))
        except Exception as e:
            logger.exception("Channels command failed")
            await update.effective_chat.send_message(f"Error: {e}")

    async def _handle_health(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_owner(update):
            return
        if not self._auth_complete:
            await update.effective_chat.send_message("Please complete the login first.")
            return
        assert update.effective_chat is not None
        tg_ok = await self._gateway.check_health()
        llm_ok = await self._summarizer.check_health()
        tg_status = "\u2705 Connected" if tg_ok else "\u274c Disconnected"
        llm_status = "\u2705 Reachable" if llm_ok else "\u274c Unreachable"
        msg = (
            "Health Status:\n"
            f"\u2022 Telegram: {tg_status}\n"
            f"\u2022 LLM: {llm_status}"
        )
        await update.effective_chat.send_message(msg)

    async def send_message(self, text: str) -> None:
        await self._send_long_message(self._settings.tg_owner_user_id, text)

    async def _send_long_message(
        self, chat_id: int, text: str, max_len: int = 4096
    ) -> None:
        if len(text) <= max_len:
            await self._app.bot.send_message(
                chat_id=chat_id, text=text, parse_mode="Markdown"
            )
            return
        # Split on line boundaries
        chunks: list[str] = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_len:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line
        if current:
            chunks.append(current)
        for chunk in chunks:
            await self._app.bot.send_message(
                chat_id=chat_id, text=chunk, parse_mode="Markdown"
            )

    async def start(self) -> None:
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        logger.info("Bot started polling")

    async def stop(self) -> None:
        await self._app.updater.stop()
        await self._app.stop()
        await self._app.shutdown()
        logger.info("Bot stopped")
