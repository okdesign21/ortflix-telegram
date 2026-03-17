# ruff: noqa: N999
"""Ortflix Telegram Bot - Overseerr integration for media requests."""

try:
    from importlib.metadata import version

    __version__ = version("ortflix-telegram-bot")
except Exception:
    __version__ = "0.0.0+unknown"

__author__ = "okdesign21"
__license__ = "MIT"
__description__ = (
    "Telegram bot for Ortflix - integrates with Overseerr for media "
    "request notifications and approvals"
)


def __getattr__(name: str):
    if name in {"app", "app_telegram"}:
        from .bot import app, app_telegram

        return app if name == "app" else app_telegram
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["app", "app_telegram"]
