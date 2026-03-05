"""Integration-style tests for env-driven provider switching."""

from legal_agent_framework import FrameworkMessage, FrameworkRunRequest, run_framework_turn


def test_demo_stage_provider_chat_path(monkeypatch):
    monkeypatch.setenv("LAW_FRAMEWORK_STAGE_PROVIDER", "demo_minimal")
    monkeypatch.setenv("LAW_FRAMEWORK_TOOL_PROVIDER", "demo_minimal")

    from app.agents.conversational_graph import create_conversational_agent

    graph = create_conversational_agent()
    payload = FrameworkRunRequest(
        messages=[FrameworkMessage(role="user", content="What are my options?")],
        request_context={"user_state": "NSW", "ui_mode": "chat", "legal_topic": "general"},
    )

    result = _run(run_framework_turn(payload, graph=graph))
    assert "Demo stage provider is active." in result.response
    assert result.quick_replies == ["Use default provider", "Generate brief"]
    assert result.suggest_brief is True


def test_demo_stage_provider_escalation_path(monkeypatch):
    monkeypatch.setenv("LAW_FRAMEWORK_STAGE_PROVIDER", "demo_minimal")
    monkeypatch.setenv("LAW_FRAMEWORK_TOOL_PROVIDER", "demo_minimal")

    from app.agents.conversational_graph import create_conversational_agent

    graph = create_conversational_agent()
    payload = FrameworkRunRequest(
        messages=[FrameworkMessage(role="user", content="This is an emergency, I am in danger")],
        request_context={"user_state": "NSW", "ui_mode": "chat", "legal_topic": "general"},
    )

    result = _run(run_framework_turn(payload, graph=graph))
    assert "Demo provider escalation path triggered" in result.response
    assert result.safety_result == "escalate"


def _run(awaitable):
    import asyncio

    return asyncio.run(awaitable)
