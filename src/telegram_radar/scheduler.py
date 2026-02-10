from collections.abc import Callable, Coroutine
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger


class Scheduler:
    def __init__(
        self,
        digest_callback: Callable[[], Coroutine[Any, Any, str]],
        send_callback: Callable[[str], Coroutine[Any, Any, None]],
        hour: int = 9,
        minute: int = 0,
    ) -> None:
        self._digest_callback = digest_callback
        self._send_callback = send_callback
        self._scheduler = AsyncIOScheduler()
        self._hour = hour
        self._minute = minute

    async def _run_and_send(self) -> None:
        try:
            logger.info("Scheduled digest job firing")
            digest = await self._digest_callback()
            await self._send_callback(digest)
            logger.info("Scheduled digest delivered")
        except Exception:
            logger.exception("Scheduled digest job failed")

    def setup(self) -> None:
        self._scheduler.add_job(
            self._run_and_send,
            trigger=CronTrigger(hour=self._hour, minute=self._minute),
            id="daily_digest",
            replace_existing=True,
        )

    def start(self) -> None:
        self.setup()
        self._scheduler.start()
        logger.info(
            "Scheduler started — daily digest at {:02d}:{:02d}",
            self._hour,
            self._minute,
        )

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
