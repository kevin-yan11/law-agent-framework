"""Minimal deterministic stage provider for framework pluggability demos."""

from __future__ import annotations

from typing import Any, Callable, Literal

from langchain_core.messages import AIMessage

from legal_agent_framework import has_stage_provider, register_stage_provider


def demo_safety_check_node(state: dict[str, Any], _config: dict | None = None) -> dict[str, Any]:
    """Very small safety gate for demo purposes."""
    query = (state.get("current_query") or "").lower()
    escalation_terms = ("emergency", "suicide", "self-harm", "hurt me", "in danger")

    if any(term in query for term in escalation_terms):
        return {
            "safety_result": "escalate",
            "crisis_resources": [
                {
                    "name": "Emergency Services",
                    "phone": "000",
                    "description": "Immediate danger support",
                }
            ],
        }

    return {
        "safety_result": "safe",
        "crisis_resources": None,
    }


def demo_route_after_safety(state: dict[str, Any]) -> Literal["escalate", "continue"]:
    """Route based on demo safety result."""
    if state.get("safety_result") == "escalate":
        return "escalate"
    return "continue"


def demo_escalation_response_node(state: dict[str, Any]) -> dict[str, Any]:
    """Deterministic escalation response."""
    resources = state.get("crisis_resources") or []
    if resources and isinstance(resources, list):
        first = resources[0] if isinstance(resources[0], dict) else {}
        phone = first.get("phone", "000")
    else:
        phone = "000"

    return {
        "messages": [
            AIMessage(
                content=(
                    "Demo provider escalation path triggered. "
                    f"If this is urgent, call {phone} immediately."
                )
            )
        ],
        "quick_replies": ["Continue when safe"],
        "suggest_brief": False,
    }


def demo_chat_response_node(state: dict[str, Any], _config: dict | None = None) -> dict[str, Any]:
    """Deterministic chat response for provider switching tests."""
    user_state = state.get("user_state") or "unknown"
    topic = state.get("legal_topic") or "general"
    query = (state.get("current_query") or "").strip()

    text = (
        "Demo stage provider is active. "
        f"state={user_state}, topic={topic}. "
        f"You asked: {query or '[empty query]'}"
    )

    return {
        "messages": [AIMessage(content=text)],
        "quick_replies": ["Use default provider", "Generate brief"],
        "suggest_brief": True,
    }


def demo_brief_check_info_node(state: dict[str, Any], _config: dict | None = None) -> dict[str, Any]:
    """Mark demo brief info as complete for simple flow."""
    return {
        "brief_info_complete": True,
        "brief_missing_info": [],
        "brief_unknown_info": [],
    }


def demo_brief_ask_questions_node(state: dict[str, Any]) -> dict[str, Any]:
    """Fallback ask node for completeness."""
    return {
        "messages": [AIMessage(content="Demo provider asks: what is your main legal goal?")],
        "quick_replies": ["Compensation", "Information only"],
    }


def demo_brief_generate_node(state: dict[str, Any], _config: dict | None = None) -> dict[str, Any]:
    """Deterministic demo brief output."""
    user_state = state.get("user_state") or "unknown"
    topic = state.get("legal_topic") or "general"
    query = state.get("current_query") or ""

    content = (
        "# Demo Brief\n\n"
        f"- State: {user_state}\n"
        f"- Topic: {topic}\n"
        f"- User query: {query}\n"
        "- Summary: Demo provider generated this deterministic brief."
    )

    return {
        "messages": [AIMessage(content=content)],
        "quick_replies": ["Switch back to default provider"],
        "suggest_brief": False,
    }


class DemoStageProvider:
    """Provides minimal deterministic stage handlers."""

    def get_stage_nodes(self) -> dict[str, Callable[..., Any]]:
        return {
            "safety_check": demo_safety_check_node,
            "escalation_response": demo_escalation_response_node,
            "chat_response": demo_chat_response_node,
            "brief_check_info": demo_brief_check_info_node,
            "brief_ask_questions": demo_brief_ask_questions_node,
            "brief_generate": demo_brief_generate_node,
        }

    def get_route_handlers(self) -> dict[str, Callable[..., Any]]:
        return {
            "route_after_safety": demo_route_after_safety,
        }


def register_demo_stage_provider() -> None:
    """Register demo stage provider once."""
    name = "demo_minimal"
    if has_stage_provider(name):
        return
    register_stage_provider(name, DemoStageProvider(), is_default=False)
