"""Default tool provider for current AusLaw app."""

from __future__ import annotations

from typing import Any

from app.tools.lookup_law import lookup_law
from app.tools.find_lawyer import find_lawyer
from app.tools.analyze_document import analyze_document
from app.tools.search_case_law import search_case_law
from app.tools.get_action_template import get_action_template
from legal_agent_framework import (
    has_tool_provider,
    register_tool_provider,
)


class AusLawToolProvider:
    """Default tool set used by conversational chat stage."""

    def get_tools(self, context: dict[str, Any] | None = None) -> list[Any]:
        # Reserved for future context-based tool gating.
        _ = context
        return [
            lookup_law,
            find_lawyer,
            analyze_document,
            search_case_law,
            get_action_template,
        ]


def register_default_tool_provider() -> None:
    """Register default tool provider once."""
    name = "auslaw_default"
    if has_tool_provider(name):
        return
    register_tool_provider(name, AusLawToolProvider(), is_default=True)
