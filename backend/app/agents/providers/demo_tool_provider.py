"""Minimal deterministic tool provider for pluggability demos."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from legal_agent_framework import has_tool_provider, register_tool_provider


@tool
def demo_echo_tool(query: str, state: str = "") -> str:
    """
    Demo tool that echoes the input.

    Args:
        query: User query text.
        state: Optional jurisdiction/state code.
    """
    state_text = state or "unknown"
    return f"[demo_echo_tool] state={state_text}; query={query}"


class DemoToolProvider:
    """Provides a minimal deterministic tool set."""

    def get_tools(self, context: dict[str, Any] | None = None) -> list[Any]:
        _ = context
        return [demo_echo_tool]


def register_demo_tool_provider() -> None:
    """Register demo tool provider once."""
    name = "demo_minimal"
    if has_tool_provider(name):
        return
    register_tool_provider(name, DemoToolProvider(), is_default=False)
