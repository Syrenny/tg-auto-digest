from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from telegram_radar.protocols import StateRepository, Summarizer, TelegramGateway
from telegram_radar.settings import Settings


class TelegramBotController:
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
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._app.add_handler(CommandHandler("digest_now", self._handle_digest_now))
        self._app.add_handler(CommandHandler("channels", self._handle_channels))
        self._app.add_handler(CommandHandler("health", self._handle_health))

    def _is_owner(self, update: Update) -> bool:
        user = update.effective_user
        return user is not None and user.id == self._settings.tg_owner_user_id

    async def _handle_digest_now(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_owner(update):
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
        assert update.effective_chat is not None
        try:
            channels = await self._gateway.get_radar_channels()
            self._state.load()
            lines = ["Radar Channels:"]
            for ch in channels:
                last_id = self._state.get_last_message_id(ch.id)
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
