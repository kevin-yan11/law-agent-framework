"""Transport-agnostic request context resolution.

This module keeps graph/runtime logic independent from transport-specific stacks
such as CopilotKit, while still allowing adapters to populate context.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from app.adapters.copilotkit_context import parse_copilotkit_context


@dataclass(frozen=True)
class AgentRequestContext:
    """Normalized request context used by agent flows."""

    user_state: str | None = None
    uploaded_document_url: str | None = None
    ui_mode: str = "chat"
    legal_topic: str = "general"

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "AgentRequestContext":
        """Create context from a generic mapping payload."""
        if not isinstance(payload, Mapping):
            return cls()

        user_state = _clean_optional_string(payload.get("user_state"))
        uploaded_document_url = _clean_optional_string(payload.get("uploaded_document_url"))
        ui_mode = _normalize_ui_mode(payload.get("ui_mode"))
        legal_topic = _normalize_legal_topic(payload.get("legal_topic"))

        return cls(
            user_state=user_state,
            uploaded_document_url=uploaded_document_url,
            ui_mode=ui_mode,
            legal_topic=legal_topic,
        )


def resolve_request_context(state: Mapping[str, Any] | None) -> AgentRequestContext:
    """Resolve request context using transport-agnostic precedence.

    Resolution order:
    1. `request_context` field (preferred generic integration contract)
    2. Legacy `runtime_context` field
    3. CopilotKit adapter (for current app compatibility)
    4. Defaults
    """
    if not isinstance(state, Mapping):
        return AgentRequestContext()

    request_context = state.get("request_context")
    if isinstance(request_context, Mapping):
        return AgentRequestContext.from_mapping(request_context)

    runtime_context = state.get("runtime_context")
    if isinstance(runtime_context, Mapping):
        return AgentRequestContext.from_mapping(runtime_context)

    if state.get("copilotkit") is not None:
        copilotkit_context = parse_copilotkit_context(dict(state))
        return AgentRequestContext(
            user_state=copilotkit_context.user_state,
            uploaded_document_url=copilotkit_context.uploaded_document_url,
            ui_mode=_normalize_ui_mode(copilotkit_context.ui_mode),
            legal_topic=_normalize_legal_topic(copilotkit_context.legal_topic),
        )

    return AgentRequestContext()


def _normalize_ui_mode(value: Any) -> str:
    text = _clean_optional_string(value) or "chat"
    if text.lower() == "analysis":
        return "analysis"
    return "chat"


def _normalize_legal_topic(value: Any) -> str:
    text = _clean_optional_string(value) or "general"
    normalized = text.lower().replace("-", "_").strip()
    if not normalized:
        return "general"
    return normalized


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    # Fall back to string conversion for non-string transport payloads.
    converted = str(value).strip()
    return converted if converted else None
