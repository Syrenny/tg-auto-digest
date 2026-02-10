import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from telegram_radar.models import AppState, ChannelState, LastRun


class StateManager:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._state: AppState | None = None

    def load(self) -> AppState:
        if self._path.exists():
            try:
                raw = self._path.read_text(encoding="utf-8")
                self._state = AppState.model_validate_json(raw)
                logger.debug("State loaded from {}", self._path)
            except (json.JSONDecodeError, ValueError):
                logger.warning(
                    "Corrupted state file at {}, starting fresh", self._path
                )
                self._state = AppState()
        else:
            logger.info("No state file at {}, starting fresh", self._path)
            self._state = AppState()
        return self._state

    def save(self) -> None:
        if self._state is None:
            self.load()
        assert self._state is not None
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to temp file in same directory, then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=self._path.parent, suffix=".tmp"
        )
        try:
            with open(fd, "w", encoding="utf-8") as f:
                f.write(self._state.model_dump_json(indent=2))
            Path(tmp_path).replace(self._path)
            logger.debug("State saved to {}", self._path)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def get_last_message_id(self, channel_id: int) -> int | None:
        if self._state is None:
            self.load()
        assert self._state is not None
        ch = self._state.channels.get(str(channel_id))
        return ch.last_processed_message_id if ch else None

    def update_channel(
        self,
        channel_id: int,
        last_message_id: int,
        post_count: int,
    ) -> None:
        if self._state is None:
            self.load()
        assert self._state is not None
        self._state.channels[str(channel_id)] = ChannelState(
            last_processed_message_id=last_message_id,
            last_run_post_count=post_count,
        )

    def record_last_run(self, channels_parsed: list[str]) -> None:
        if self._state is None:
            self.load()
        assert self._state is not None
        self._state.last_run = LastRun(
            timestamp=datetime.now(timezone.utc).isoformat(),
            channels_parsed=channels_parsed,
        )

    def get_channel_state(self, channel_id: int) -> ChannelState | None:
        if self._state is None:
            self.load()
        assert self._state is not None
        return self._state.channels.get(str(channel_id))
