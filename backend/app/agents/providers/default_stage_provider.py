"""Default stage provider for the current AusLaw conversational app."""

from __future__ import annotations

from typing import Any, Callable

from app.agents.stages.safety_check_lite import (
    safety_check_lite_node,
    route_after_safety_lite,
    format_escalation_response_lite,
)
from app.agents.stages.chat_response import chat_response_node
from app.agents.stages.brief_flow import (
    brief_check_info_node,
    brief_ask_questions_node,
    brief_generate_node,
)
from legal_agent_framework import (
    has_stage_provider,
    register_stage_provider,
)


class AusLawStageProvider:
    """Concrete stage provider bound to current stage implementations."""

    def get_stage_nodes(self) -> dict[str, Callable[..., Any]]:
        return {
            "safety_check": safety_check_lite_node,
            "escalation_response": format_escalation_response_lite,
            "chat_response": chat_response_node,
            "brief_check_info": brief_check_info_node,
            "brief_ask_questions": brief_ask_questions_node,
            "brief_generate": brief_generate_node,
        }

    def get_route_handlers(self) -> dict[str, Callable[..., Any]]:
        return {
            "route_after_safety": route_after_safety_lite,
        }


def register_default_stage_provider() -> None:
    """Register default stage provider once."""
    name = "auslaw_default"
    if has_stage_provider(name):
        return
    register_stage_provider(name, AusLawStageProvider(), is_default=True)
