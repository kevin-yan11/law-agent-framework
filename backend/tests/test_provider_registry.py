"""Tests for framework provider registries."""

from legal_agent_framework.providers import (
    register_stage_provider,
    get_stage_provider,
    register_tool_provider,
    get_tool_provider,
    resolve_stage_provider,
    resolve_tool_provider,
)
from legal_agent_framework.config import (
    get_configured_stage_provider_name,
    get_configured_tool_provider_name,
)
from app.agents.providers import (
    ensure_builtin_stage_providers_registered,
    ensure_builtin_tool_providers_registered,
)


class _DummyStageProvider:
    def get_stage_nodes(self):
        return {"dummy_stage": lambda state: {"ok": True}}

    def get_route_handlers(self):
        return {"dummy_route": lambda state: "ok"}


class _DummyToolProvider:
    def get_tools(self, context=None):
        _ = context
        return ["tool_a", "tool_b"]


def test_stage_provider_registry_register_and_get():
    provider_name = "unit_test_stage_provider"
    register_stage_provider(provider_name, _DummyStageProvider(), is_default=False)

    provider = get_stage_provider(provider_name)
    nodes = provider.get_stage_nodes()
    routes = provider.get_route_handlers()

    assert "dummy_stage" in nodes
    assert "dummy_route" in routes


def test_tool_provider_registry_register_and_get():
    provider_name = "unit_test_tool_provider"
    register_tool_provider(provider_name, _DummyToolProvider(), is_default=False)

    provider = get_tool_provider(provider_name)
    tools = provider.get_tools({"mode": "chat"})

    assert tools == ["tool_a", "tool_b"]


def test_resolve_stage_provider_falls_back_to_default():
    ensure_builtin_stage_providers_registered()

    provider = resolve_stage_provider("unknown_stage_provider_name")
    nodes = provider.get_stage_nodes()
    assert "safety_check" in nodes
    assert "chat_response" in nodes


def test_resolve_tool_provider_falls_back_to_default():
    ensure_builtin_tool_providers_registered()

    provider = resolve_tool_provider("unknown_tool_provider_name")
    tools = provider.get_tools()
    assert isinstance(tools, list)
    assert len(tools) >= 1


def test_provider_name_env_helpers(monkeypatch):
    monkeypatch.setenv("LAW_FRAMEWORK_STAGE_PROVIDER", "my_stage_provider")
    monkeypatch.setenv("LAW_FRAMEWORK_TOOL_PROVIDER", "my_tool_provider")

    assert get_configured_stage_provider_name() == "my_stage_provider"
    assert get_configured_tool_provider_name() == "my_tool_provider"
