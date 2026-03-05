"""Tests for transport-neutral framework runner."""

from langchain_core.messages import AIMessage

from legal_agent_framework import FrameworkMessage, FrameworkRunRequest, run_framework_turn
from legal_agent_framework.tracing import TRACE_EVENTS_KEY, TRACE_ID_KEY, TRACE_SEQ_KEY


class _FakeGraph:
    async def astream(self, state_input, config=None, stream_mode=None):
        assert stream_mode == "updates"
        assert isinstance(state_input.get("messages"), list)
        assert state_input.get("request_context", {}).get("user_state") == "NSW"
        assert config and config.get("configurable", {}).get("thread_id")
        assert state_input.get(TRACE_ID_KEY) == "trace-123"
        assert state_input.get(TRACE_SEQ_KEY) == 2
        assert [event.get("seq") for event in state_input.get(TRACE_EVENTS_KEY, [])] == [1, 2]

        yield {
            "initialize": {
                "mode": "analysis",
                "safety_result": "safe",
                TRACE_ID_KEY: "trace-123",
                TRACE_SEQ_KEY: 3,
                TRACE_EVENTS_KEY: [
                    {"seq": 1, "event_type": "seed"},
                    {"seq": 2, "event_type": "seed"},
                    {"seq": 3, "event_type": "stage_start"},
                ],
            }
        }
        yield {
            "chat_response": {
                "messages": [AIMessage(content="Here is your response.")],
                "quick_replies": ["Tell me more", "What are my options?"],
                "suggest_brief": True,
                TRACE_ID_KEY: "trace-123",
                TRACE_SEQ_KEY: 4,
                TRACE_EVENTS_KEY: [
                    {"seq": 1, "event_type": "seed"},
                    {"seq": 2, "event_type": "seed"},
                    {"seq": 3, "event_type": "stage_start"},
                    {"seq": 4, "event_type": "stage_complete"},
                ],
            }
        }


def test_runner_returns_response_from_updates_stream():
    payload = FrameworkRunRequest(
        messages=[FrameworkMessage(role="user", content="Help me with tenancy law")],
        request_context={"user_state": "NSW", "ui_mode": "analysis", "legal_topic": "general"},
        trace_id="trace-123",
        trace_events=[
            {"seq": 2, "event_type": "seed"},
            {"seq": 1, "event_type": "seed"},
        ],
    )
    result = _run(run_framework_turn(payload, graph=_FakeGraph()))

    assert result.response == "Here is your response."
    assert result.mode == "analysis"
    assert result.safety_result == "safe"
    assert result.quick_replies == ["Tell me more", "What are my options?"]
    assert result.suggest_brief is True
    assert result.session_id
    assert result.thread_id
    assert result.trace_id == "trace-123"
    assert [event.get("seq") for event in result.trace_events] == [1, 2, 3, 4]


def test_runner_validates_user_message_presence():
    payload = FrameworkRunRequest(
        messages=[FrameworkMessage(role="assistant", content="Hello from assistant")],
        request_context={"user_state": "NSW"},
    )

    try:
        _run(run_framework_turn(payload, graph=_FakeGraph()))
    except ValueError as e:
        assert "user message" in str(e).lower()
    else:
        raise AssertionError("Expected ValueError for missing user message")


def test_runner_requires_explicit_graph():
    payload = FrameworkRunRequest(
        messages=[FrameworkMessage(role="user", content="Hello")],
        request_context={"user_state": "NSW"},
    )

    try:
        _run(run_framework_turn(payload))
    except ValueError as e:
        assert "graph must be provided" in str(e).lower()
    else:
        raise AssertionError("Expected ValueError when graph is not provided")


def _run(awaitable):
    import asyncio

    return asyncio.run(awaitable)
