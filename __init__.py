# ruff: noqa: N999
"""Ortflix integrations service for notifications and media automations."""

try:
    from importlib.metadata import version

    try:
        __version__ = version("ortflix-integrations")
    except Exception:
        __version__ = version("ortflix-telegram-bot")
except Exception:
    __version__ = "0.0.0+unknown"

__author__ = "okdesign21"
__license__ = "MIT"
__description__ = (
    "Ortflix integrations service for Overseerr notifications and Radarr automation hooks"
)


def __getattr__(name: str):
    if name in {"app", "app_telegram"}:
        from .bot import app, app_telegram

        return app if name == "app" else app_telegram
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["app", "app_telegram"]
