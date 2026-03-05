"""Integration adapters for external transport/runtime layers."""

from app.adapters.copilotkit_context import (
    CopilotKitContext,
    parse_copilotkit_context,
    extract_context_item,
    clean_context_value,
    extract_user_state,
    extract_document_url,
    extract_ui_mode,
    extract_legal_topic,
)

__all__ = [
    "CopilotKitContext",
    "parse_copilotkit_context",
    "extract_context_item",
    "clean_context_value",
    "extract_user_state",
    "extract_document_url",
    "extract_ui_mode",
    "extract_legal_topic",
]
