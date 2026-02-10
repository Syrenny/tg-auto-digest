import json
from pathlib import Path

from telegram_radar.models import AppState, ChannelState
from telegram_radar.state import StateManager


class TestStateManager:
    def test_load_valid_json(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        data = {
            "channels": {
                "123": {
                    "last_processed_message_id": 42,
                    "last_run_post_count": 5,
                }
            },
            "last_run": {
                "timestamp": "2026-01-01T00:00:00Z",
                "channels_parsed": ["Test"],
            },
        }
        state_file.write_text(json.dumps(data))
        mgr = StateManager(state_file)
        state = mgr.load()
        assert "123" in state.channels
        assert state.channels["123"].last_processed_message_id == 42

    def test_load_missing_file(self, tmp_path: Path) -> None:
        state_file = tmp_path / "missing.json"
        mgr = StateManager(state_file)
        state = mgr.load()
        assert state.channels == {}
        assert state.last_run.timestamp == ""

    def test_load_corrupted_json(self, tmp_path: Path) -> None:
        state_file = tmp_path / "bad.json"
        state_file.write_text("{not valid json!!!")
        mgr = StateManager(state_file)
        state = mgr.load()
        assert state.channels == {}

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        state_file = tmp_path / "subdir" / "state.json"
        mgr = StateManager(state_file)
        mgr.load()
        mgr.save()
        assert state_file.exists()
        loaded = json.loads(state_file.read_text())
        assert "channels" in loaded

    def test_update_and_get_round_trip(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        mgr = StateManager(state_file)
        mgr.load()
        mgr.update_channel(123, last_message_id=99, post_count=7)
        assert mgr.get_last_message_id(123) == 99
        # Save and reload to verify persistence
        mgr.save()
        mgr2 = StateManager(state_file)
        mgr2.load()
        assert mgr2.get_last_message_id(123) == 99

    def test_get_last_message_id_missing_channel(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        mgr = StateManager(state_file)
        mgr.load()
        assert mgr.get_last_message_id(999) is None

    def test_record_last_run_sets_timestamp_and_channels(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        mgr = StateManager(state_file)
        mgr.load()
        mgr.record_last_run(channels_parsed=["Channel A", "Channel B"])
        mgr.save()
        # Reload and verify
        mgr2 = StateManager(state_file)
        state = mgr2.load()
        assert state.last_run.timestamp != ""
        assert state.last_run.channels_parsed == ["Channel A", "Channel B"]

    def test_get_channel_state_returns_none_for_unknown(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        mgr = StateManager(state_file)
        mgr.load()
        assert mgr.get_channel_state(999) is None

    def test_get_channel_state_returns_state_for_known(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        mgr = StateManager(state_file)
        mgr.load()
        mgr.update_channel(123, last_message_id=50, post_count=3)
        ch_state = mgr.get_channel_state(123)
        assert ch_state is not None
        assert ch_state.last_processed_message_id == 50
        assert ch_state.last_run_post_count == 3
