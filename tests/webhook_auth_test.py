"""Auth behavior tests for webhook routers."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

pytest_plugins = ["conf_test"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,payload,expected",
    [
        ("/api/v1/webhooks/overseerr", {"notification_type": "PING"}, 200),
        (
            "/api/v1/webhooks/radarr",
            {"eventType": "MovieAdded", "movie": {"id": 10, "title": "Test Movie"}},
            200,
        ),
        (
            "/api/v1/webhooks/sonarr",
            {"eventType": "Download", "series": {"id": 20, "title": "Test Show"}},
            200,
        ),
        (
            "/api/v1/webhooks/tautulli",
            {"event": "watched", "title": "Some Movie", "year": 2020, "username": "alice"},
            200,
        ),
        (
            "/api/v1/webhooks/media-check",
            {"notification_type": "CORRUPTION_DETECTED", "count": 0, "files": []},
            200,
        ),
    ],
)
async def test_webhook_token_disabled_accepts_requests(
    mock_env, mock_telegram_bot, endpoint, payload, expected
):
    """When WEBHOOK_TOKEN is disabled, requests should not require auth header."""
    import bot as bot_module
    from bot import app

    bot_module.bot = mock_telegram_bot
    bot_module.app_telegram = MagicMock()

    with patch("bot.WEBHOOK_TOKEN", None):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(endpoint, json=payload)

    assert response.status_code == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,payload",
    [
        ("/api/v1/webhooks/overseerr", {"notification_type": "PING"}),
        (
            "/api/v1/webhooks/radarr",
            {"eventType": "MovieAdded", "movie": {"id": 10, "title": "Test Movie"}},
        ),
        (
            "/api/v1/webhooks/sonarr",
            {"eventType": "Download", "series": {"id": 20, "title": "Test Show"}},
        ),
        (
            "/api/v1/webhooks/tautulli",
            {"event": "watched", "title": "Some Movie", "year": 2020, "username": "alice"},
        ),
        (
            "/api/v1/webhooks/media-check",
            {"notification_type": "CORRUPTION_DETECTED", "count": 0, "files": []},
        ),
    ],
)
async def test_webhook_token_enabled_requires_valid_header(
    mock_env, mock_telegram_bot, endpoint, payload
):
    """When WEBHOOK_TOKEN is enabled, missing/wrong header should fail and correct should pass."""
    import bot as bot_module
    from bot import app

    bot_module.bot = mock_telegram_bot
    bot_module.app_telegram = MagicMock()

    with patch("bot.WEBHOOK_TOKEN", "secret_token_123"):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            missing_header_response = await client.post(endpoint, json=payload)
            wrong_header_response = await client.post(
                endpoint,
                json=payload,
                headers={"x-webhook-token": "wrong"},
            )
            ok_response = await client.post(
                endpoint,
                json=payload,
                headers={"x-webhook-token": "secret_token_123"},
            )

    assert missing_header_response.status_code == 401
    assert wrong_header_response.status_code == 401
    assert ok_response.status_code == 200
