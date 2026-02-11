from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from telegram_radar.gateway import TelegramClientGateway
from telegram_radar.settings import Settings


def _make_settings() -> Settings:
    return Settings(
        telegram_api_id=12345,
        telegram_api_hash="testhash",
        tg_bot_token="bot:token",
        tg_owner_user_id=1,
        llm_model="test-model",
        llm_api_key="test-key",
    )


@pytest.fixture
def mock_client():
    with patch(
        "telegram_radar.gateway.TelegramClient", autospec=True
    ) as cls:
        client = cls.return_value
        client.connect = AsyncMock()
        client.is_user_authorized = AsyncMock(return_value=True)
        client.send_code_request = AsyncMock()
        client.sign_in = AsyncMock()
        client.disconnect = AsyncMock()
        client.get_me = AsyncMock()
        yield client


@pytest.fixture
def gateway(mock_client):
    return TelegramClientGateway(_make_settings())


class TestConnect:
    async def test_connect_calls_client_connect(self, gateway, mock_client):
        await gateway.connect()
        mock_client.connect.assert_awaited_once()

    async def test_connect_does_not_authorize(self, gateway, mock_client):
        await gateway.connect()
        mock_client.is_user_authorized.assert_not_awaited()


class TestIsAuthorized:
    async def test_returns_true_when_authorized(self, gateway, mock_client):
        mock_client.is_user_authorized.return_value = True
        assert await gateway.is_authorized() is True

    async def test_returns_false_when_not_authorized(
        self, gateway, mock_client
    ):
        mock_client.is_user_authorized.return_value = False
        assert await gateway.is_authorized() is False


class TestSendCode:
    async def test_calls_send_code_request(self, gateway, mock_client):
        await gateway.send_code("+79991234567")
        mock_client.send_code_request.assert_awaited_once_with("+79991234567")


class TestSignInCode:
    async def test_success(self, gateway, mock_client):
        mock_client.sign_in.return_value = MagicMock()
        await gateway.sign_in_code("+79991234567", "12345")
        mock_client.sign_in.assert_awaited_once_with("+79991234567", code="12345")

    async def test_reraises_phone_code_invalid(self, gateway, mock_client):
        mock_client.sign_in.side_effect = PhoneCodeInvalidError(None)
        with pytest.raises(PhoneCodeInvalidError):
            await gateway.sign_in_code("+79991234567", "wrong")

    async def test_reraises_session_password_needed(
        self, gateway, mock_client
    ):
        mock_client.sign_in.side_effect = SessionPasswordNeededError(None)
        with pytest.raises(SessionPasswordNeededError):
            await gateway.sign_in_code("+79991234567", "12345")


class TestSignInPassword:
    async def test_success(self, gateway, mock_client):
        mock_client.sign_in.return_value = MagicMock()
        await gateway.sign_in_password("mypassword")
        mock_client.sign_in.assert_awaited_once_with(password="mypassword")

    async def test_reraises_password_hash_invalid(
        self, gateway, mock_client
    ):
        mock_client.sign_in.side_effect = PasswordHashInvalidError(None)
        with pytest.raises(PasswordHashInvalidError):
            await gateway.sign_in_password("wrong")


class TestLogOut:
    async def test_log_out_calls_client_log_out_and_reconnects(self):
        with patch(
            "telegram_radar.gateway.TelegramClient", autospec=True
        ) as cls:
            old_client = MagicMock()
            old_client.connect = AsyncMock()
            old_client.log_out = AsyncMock()
            old_client.disconnect = AsyncMock()
            new_client = MagicMock()
            new_client.connect = AsyncMock()
            cls.side_effect = [old_client, new_client]

            gateway = TelegramClientGateway(_make_settings())
            await gateway.log_out()

            old_client.log_out.assert_awaited_once()
            old_client.disconnect.assert_awaited_once()
            new_client.connect.assert_awaited_once()

    async def test_log_out_succeeds_when_client_log_out_raises(self):
        with patch(
            "telegram_radar.gateway.TelegramClient", autospec=True
        ) as cls:
            old_client = MagicMock()
            old_client.connect = AsyncMock()
            old_client.log_out = AsyncMock(side_effect=Exception("network"))
            old_client.disconnect = AsyncMock(
                side_effect=Exception("already disconnected")
            )
            new_client = MagicMock()
            new_client.connect = AsyncMock()
            cls.side_effect = [old_client, new_client]

            gateway = TelegramClientGateway(_make_settings())
            await gateway.log_out()

            new_client.connect.assert_awaited_once()
