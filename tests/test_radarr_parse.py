"""Tests for Radarr movie JSON parsing (no HTTP)."""

from bot import _radarr_quality_and_folder


def test_radarr_quality_nested_quality_object():
    movie = {
        "path": "/movies/Example (2020)",
        "movieFile": {
            "quality": {"quality": {"name": "Bluray-1080p"}, "revision": {"version": 1}}
        },
    }
    q, folder = _radarr_quality_and_folder(movie)
    assert q == "Bluray-1080p"
    assert folder == "/movies/Example (2020)"


def test_radarr_no_movie_file():
    movie = {"path": "/movies/Only Path"}
    q, folder = _radarr_quality_and_folder(movie)
    assert q is None
    assert folder == "/movies/Only Path"


def test_radarr_invalid_movie():
    assert _radarr_quality_and_folder({}) == (None, None)
    assert _radarr_quality_and_folder(None) == (None, None)  # type: ignore[arg-type]
