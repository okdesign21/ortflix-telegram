"""Unit tests for webhook caption text (no Telegram, no FastAPI, no network).

Radarr enrichment populates ``downloaded_quality`` and ``movie_folder`` on the
payload before captions run; see ``bot._enrich_media_available_from_radarr``.

Run from repo root:
  cd ortflix-telegram && python -m pytest tests/test_caption_messages.py -v
"""

from config import (
    _build_media_available_caption,
    _build_media_failed_caption,
    _build_media_pending_caption,
)


def test_media_pending_movie_minimal_webhook():
    """Thin request block like Seerr default template (no profile in webhook)."""
    payload = {
        "notification_type": "MEDIA_PENDING",
        "subject": "Test Movie (2020)",
        "media": {"media_type": "movie", "tmdbId": 123},
        "request": {
            "request_id": "296",
            "requested_by_username": "alice",
            "requested_by_email": "a@example.com",
        },
    }
    out = _build_media_pending_caption(payload)
    assert "Request Pending Approval" in out
    assert "Test Movie (2020)" in out
    assert "Requested by: alice" in out
    assert "Profile" not in out


def test_media_pending_movie_with_enriched_profile_name():
    """After API enrichment, request includes profileName (or profileName camelCase)."""
    payload = {
        "subject": "Space Pirate Captain Harlock (2013)",
        "media": {"mediaType": "movie"},
        "request": {
            "request_id": "296",
            "requested_by_username": "レゼ",
            "requested_by_email": "u@example.com",
            "profileName": "HD",
        },
    }
    out = _build_media_pending_caption(payload)
    assert "🎚 *Profile:* HD" in out
    assert "Space Pirate Captain Harlock (2013)" in out


def test_media_pending_tv_with_seasons():
    payload = {
        "subject": "Some Show",
        "media": {"media_type": "tv"},
        "request": {
            "request_id": "1",
            "requested_by_username": "bob",
            "profileName": "UHD",
        },
        "extra": [{"name": "Requested Seasons", "value": "1, 3"}],
    }
    out = _build_media_pending_caption(payload)
    assert "📺" in out
    assert "Seasons:" in out or "Season" in out
    assert "UHD" in out


def test_media_failed_with_profile():
    payload = {
        "subject": "Failed Title",
        "request": {"profileName": "HD"},
    }
    out = _build_media_failed_caption(payload)
    assert "Request Failed" in out
    assert "Failed Title" in out
    assert "HD" in out


def test_media_available_movie_minimal():
    payload = {
        "notification_type": "MEDIA_AVAILABLE",
        "subject": "Arrival (2016)",
        "media": {"media_type": "movie", "tmdbId": 329865},
    }
    out = _build_media_available_caption(payload)
    assert "Request Available" in out
    assert "Arrival (2016)" in out
    assert "Profile" not in out
    assert "Quality" not in out
    assert "Folder" not in out


def test_media_available_movie_with_profile_quality_folder():
    payload = {
        "subject": "Test Movie (2020)",
        "media": {"mediaType": "movie"},
        "request": {"profileName": "UHD"},
        "downloaded_quality": "Remux-2160p",
        "movie_folder": "/data/movies/Test Movie (2020)",
    }
    out = _build_media_available_caption(payload)
    assert "*Profile:* UHD" in out
    assert "*Quality:* Remux-2160p" in out
    assert "*Folder:* `/data/movies/Test Movie (2020)`" in out


def test_media_available_tv_has_profile_no_folder():
    payload = {
        "subject": "Some Show",
        "media": {"media_type": "tv"},
        "request": {"profileName": "HD"},
        "downloaded_quality": "WEBDL-1080p",
        "movie_folder": "/data/shows/Some Show",
    }
    out = _build_media_available_caption(payload)
    assert "📺" in out
    assert "HD" in out
    assert "WEBDL-1080p" in out
    assert "Folder" not in out
