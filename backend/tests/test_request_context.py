"""Tests for transport-agnostic request context resolution."""

from app.context import resolve_request_context


def test_resolve_request_context_prefers_request_context_field():
    state = {
        "request_context": {
            "user_state": "NSW",
            "uploaded_document_url": "https://example.com/doc.pdf",
            "ui_mode": "analysis",
            "legal_topic": "parking_ticket",
        },
        "copilotkit": {
            "context": [
                {"description": "User's state/territory", "value": "VIC"},
            ]
        },
    }
    context = resolve_request_context(state)
    assert context.user_state == "NSW"
    assert context.uploaded_document_url == "https://example.com/doc.pdf"
    assert context.ui_mode == "analysis"
    assert context.legal_topic == "parking_ticket"


def test_resolve_request_context_uses_runtime_context_legacy():
    state = {
        "runtime_context": {
            "user_state": "QLD",
            "ui_mode": "chat",
            "legal_topic": "insurance-claim",
        }
    }
    context = resolve_request_context(state)
    assert context.user_state == "QLD"
    assert context.ui_mode == "chat"
    assert context.legal_topic == "insurance_claim"


def test_resolve_request_context_falls_back_to_copilotkit_adapter():
    state = {
        "copilotkit": {
            "context": [
                {"description": "User's state/territory", "value": "User is in WA"},
                {"description": "The UI mode the user has selected", "value": "ANALYSIS MODE"},
                {"description": "The legal topic the user has selected", "value": "Insurance Claim"},
            ]
        }
    }
    context = resolve_request_context(state)
    assert context.user_state == "WA"
    assert context.ui_mode == "analysis"
    assert context.legal_topic == "insurance_claim"


def test_resolve_request_context_defaults_when_missing():
    context = resolve_request_context({})
    assert context.user_state is None
    assert context.uploaded_document_url is None
    assert context.ui_mode == "chat"
    assert context.legal_topic == "general"
