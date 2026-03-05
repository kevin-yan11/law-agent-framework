"""Backward-compatible context utilities.

Context parsing now lives in `app.adapters.copilotkit_context` to decouple
transport-specific parsing from agent and framework logic.
"""

from typing import Optional

from app.adapters.copilotkit_context import (
    clean_context_value as _clean_context_value,
    extract_context_item as _extract_context_item,
    extract_document_url as _extract_document_url,
    extract_legal_topic as _extract_legal_topic,
    extract_ui_mode as _extract_ui_mode,
    extract_user_state as _extract_user_state,
)


def extract_context_item(state: dict, keyword: str) -> Optional[str]:
    """Compatibility wrapper around adapter implementation."""
    return _extract_context_item(state, keyword)


def clean_context_value(value: Optional[str]) -> Optional[str]:
    """Compatibility wrapper around adapter implementation."""
    return _clean_context_value(value)


def extract_user_state(state: dict) -> Optional[str]:
    """Compatibility wrapper around adapter implementation."""
    return _extract_user_state(state)


def extract_document_url(state: dict) -> Optional[str]:
    """Compatibility wrapper around adapter implementation."""
    return _extract_document_url(state)


def extract_legal_topic(state: dict) -> str:
    """Compatibility wrapper around adapter implementation."""
    return _extract_legal_topic(state)


def extract_ui_mode(state: dict) -> str:
    """Compatibility wrapper around adapter implementation."""
    return _extract_ui_mode(state)
