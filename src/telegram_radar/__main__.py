import asyncio
import signal
from functools import partial
from pathlib import Path

from loguru import logger

from telegram_radar.batch_builder import BatchBuilder
from telegram_radar.bot import TelegramBotController
from telegram_radar.digest_builder import DigestBuilder
from telegram_radar.gateway import TelegramClientGateway
from telegram_radar.pipeline import run_digest
from telegram_radar.scheduler import Scheduler
from telegram_radar.settings import Settings
from telegram_radar.state import StateManager
from telegram_radar.summarizer import LLMSummarizer


async def main() -> None:
    settings = Settings()

    # Ensure data directory exists
    Path(settings.telethon_session_path).parent.mkdir(
        parents=True, exist_ok=True
    )

    state = StateManager(Path("data/state.json"))
    gateway = TelegramClientGateway(settings)
    batch_builder = BatchBuilder()
    summarizer = LLMSummarizer(settings)
    digest_builder = DigestBuilder()

    # Create the digest callable that captures all dependencies
    async def digest_fn() -> str:
        return await run_digest(
            gateway=gateway,
            batch_builder=batch_builder,
            summarizer=summarizer,
            digest_builder=digest_builder,
            state=state,
            settings=settings,
        )

    bot = TelegramBotController(
        settings=settings,
        gateway=gateway,
        summarizer=summarizer,
        state=state,
        run_digest=digest_fn,
    )

    scheduler = Scheduler(
        digest_callback=digest_fn,
        send_callback=bot.send_message,
    )

    # Start services
    await gateway.start()
    await bot.start()
    scheduler.start()

    logger.info("Telegram Radar Digest is running")

    # Graceful shutdown
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()

    logger.info("Shutting down...")
    scheduler.stop()
    await bot.stop()
    await gateway.stop()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
