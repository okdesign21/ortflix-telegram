"""Shared webhook authentication helpers."""

from typing import Optional

from fastapi import HTTPException, status


def _normalize_expected_token(token: Optional[str]) -> Optional[str]:
    """Treat empty or whitespace-only token values as disabled auth."""
    if token is None:
        return None
    cleaned = str(token).strip()
    return cleaned or None


def require_valid_webhook_token(
    expected_token: Optional[str], provided_token: Optional[str]
) -> None:
    """Validate webhook token when token auth is enabled."""
    normalized_expected = _normalize_expected_token(expected_token)
    if normalized_expected and provided_token != normalized_expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook token",
        )
