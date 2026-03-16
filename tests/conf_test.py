"""Test fixtures for telegram bot tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from telegram import Bot, Update
from telegram.ext import Application


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "test_token_123")
    monkeypatch.setenv("OVERSEERR_API_KEY", "test_api_key_123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setenv("OVERSEERR_URL", "http://localhost:5055")
    monkeypatch.setenv("WEBHOOK_PORT", "7777")
    monkeypatch.setenv("WEBHOOK_HOST", "0.0.0.0")


@pytest.fixture
def mock_telegram_bot():
    """Create a mock Telegram bot."""
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot


@pytest.fixture
def mock_telegram_app(mock_telegram_bot):
    """Create a mock Telegram application."""
    app = MagicMock(spec=Application)
    app.bot = mock_telegram_bot
    return app


@pytest.fixture
def sample_webhook_payload():
    """Sample webhook payload from Overseerr."""
    return {
        "notification_type": "MEDIA_PENDING",
        "subject": "Test Movie",
        "image": "https://example.com/poster.jpg",
        "media": {"media_type": "movie"},
        "request": {
            "request_id": "123",
            "requestedBy_username": "testuser",
        },
    }


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update object."""
    update = MagicMock(spec=Update)
    update.callback_query = MagicMock()
    update.callback_query.data = "approve_123"
    update.callback_query.message = MagicMock()
    update.callback_query.message.chat = MagicMock()
    update.callback_query.message.chat.id = 12345
    update.callback_query.id = "callback_123"
    return update


@pytest.fixture
async def test_app(mock_env, mock_telegram_bot):
    """Create a FastAPI test client with mocked bot."""
    # Mock the bot globally
    import bot as bot_module
    from bot import app

    bot_module.bot = mock_telegram_bot
    bot_module.app_telegram = MagicMock()
    bot_module.app_telegram.bot = mock_telegram_bot

    async with TestClient(app) as client:
        yield client
