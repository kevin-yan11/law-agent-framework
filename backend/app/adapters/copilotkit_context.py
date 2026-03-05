"""CopilotKit context adapter.

This module isolates CopilotKit-specific context parsing from graph/runtime code.
"""

from dataclasses import dataclass
import re
from typing import Optional


# Australian state codes
STATE_CODES = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"]


@dataclass(frozen=True)
class CopilotKitContext:
    """Normalized context values extracted from CopilotKit payload."""

    user_state: Optional[str]
    uploaded_document_url: Optional[str]
    ui_mode: str
    legal_topic: str


def parse_copilotkit_context(state: dict) -> CopilotKitContext:
    """Extract normalized context fields needed by the legal agent graph."""
    return CopilotKitContext(
        user_state=extract_user_state(state),
        uploaded_document_url=extract_document_url(state),
        ui_mode=extract_ui_mode(state),
        legal_topic=extract_legal_topic(state),
    )


def extract_context_item(state: dict, keyword: str) -> Optional[str]:
    """
    Extract a context item from CopilotKit context by keyword in description.

    Args:
        state: Agent state dict containing 'copilotkit' key
        keyword: Keyword to search for in context item descriptions

    Returns:
        The value of the matching context item, or None if not found
    """
    copilotkit_data = state.get("copilotkit", {})
    if not copilotkit_data:
        return None

    context_items = copilotkit_data.get("context", [])

    for item in context_items:
        try:
            description = item.get("description", "") if isinstance(item, dict) else getattr(item, "description", "")
            value = item.get("value", "") if isinstance(item, dict) else getattr(item, "value", "")

            if keyword.lower() in description.lower():
                return value
        except Exception:
            continue

    return None


def clean_context_value(value: Optional[str]) -> Optional[str]:
    """
    Remove extra quotes from context values if present.

    AG-UI protocol double-serializes strings (e.g., '"NSW"' instead of 'NSW').
    This function cleans them to get the actual value.
    """
    if value and isinstance(value, str):
        # Remove surrounding quotes
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        # Unescape inner quotes
        value = value.replace('\\"', '"')
    return value


def extract_user_state(state: dict) -> Optional[str]:
    """Extract user's Australian state/territory from CopilotKit context."""
    raw_value = extract_context_item(state, "state/territory")
    cleaned = clean_context_value(raw_value)

    if not cleaned:
        return None

    # Extract state code (e.g., "NSW" from "User is in NSW")
    for code in STATE_CODES:
        if code in cleaned.upper():
            return code

    return cleaned


def extract_document_url(state: dict) -> Optional[str]:
    """Extract uploaded document URL from CopilotKit context."""
    raw_value = extract_context_item(state, "document")
    cleaned = clean_context_value(raw_value)

    if not cleaned:
        return None

    # Extract URL from context string
    url_match = re.search(r'https?://[^\s"]+', cleaned)
    if url_match:
        return url_match.group(0)

    return None


def extract_legal_topic(state: dict) -> str:
    """Extract legal topic from CopilotKit context."""
    raw_value = extract_context_item(state, "legal topic")
    cleaned = clean_context_value(raw_value)

    if not cleaned:
        return "general"

    upper = cleaned.upper()
    if "PARKING" in upper or "TICKET" in upper or "FINE" in upper:
        return "parking_ticket"
    if "INSURANCE" in upper or "CLAIM" in upper:
        return "insurance_claim"

    return "general"


def extract_ui_mode(state: dict) -> str:
    """Extract UI mode from CopilotKit context."""
    raw_value = extract_context_item(state, "UI mode")
    cleaned = clean_context_value(raw_value)

    if not cleaned:
        return "chat"

    # Check for analysis mode indicator
    if "ANALYSIS MODE" in cleaned.upper():
        return "analysis"

    return "chat"
