"""Tests for framework runtime enforcement behavior."""

from langchain_core.messages import AIMessage

from legal_agent_framework.policy_engine import PolicyEngine
from legal_agent_framework.runtime_wrapper import StageRuntimeWrapper
from legal_agent_framework.tracing import TRACE_EVENTS_KEY, TRACE_ID_KEY, TRACE_SEQ_KEY
from legal_agent_framework.validators import ValidatorEngine


def _build_wrapper(enforced_rules: set[str] | None = None) -> StageRuntimeWrapper:
    return StageRuntimeWrapper(
        policy_engine=PolicyEngine(
            enforce=False,
            enforced_rules=enforced_rules or set(),
        ),
        validator_engine=ValidatorEngine(enforce=False),
    )


async def _ok_handler(_state):
    return {"messages": [AIMessage(content="ok")]}


def test_observe_mode_does_not_override_when_rule_hits():
    wrapper = _build_wrapper()
    wrapped = wrapper.wrap_node("chat_response", _ok_handler)
    state = {
        "current_query": "What law applies here?",
        "user_state": None,  # triggers P-001 in observe mode only
        "mode": "chat",
    }

    result = _run(wrapped(state))
    assert "messages" in result
    assert result["messages"][-1].content == "ok"


def test_enforced_p001_returns_ask_user_override():
    wrapper = _build_wrapper({"P-001"})
    wrapped = wrapper.wrap_node("chat_response", _ok_handler)
    state = {
        "current_query": "What law applies here?",
        "user_state": None,  # triggers P-001 and is enforced
        "mode": "chat",
    }

    result = _run(wrapped(state))
    text = result["messages"][-1].content.lower()
    assert "select your state" in text
    assert "quick_replies" in result


def test_enforced_p003_blocks_output_without_citations():
    wrapper = _build_wrapper({"P-003"})
    wrapped = wrapper.wrap_node("chat_response", _ok_handler)
    state = {
        "current_query": "Explain the law about tenant rights",
        "user_state": "NSW",  # avoids P-001
        "mode": "chat",
    }

    result = _run(wrapped(state))
    text = result["messages"][-1].content.lower()
    assert "not ready to provide a legal conclusion" in text


def test_enforced_p002_escalates_before_chat_stage():
    wrapper = _build_wrapper({"P-002"})
    wrapped = wrapper.wrap_node("chat_response", _ok_handler)
    state = {
        "current_query": "just continue",
        "user_state": "NSW",
        "mode": "chat",
        "safety_result": "escalate",  # triggers P-002
    }

    result = _run(wrapped(state))
    text = result["messages"][-1].content.lower()
    assert "urgent safety situation" in text
    assert result.get("safety_result") == "escalate"


def test_runtime_attaches_trace_metadata_and_ordered_events():
    wrapper = _build_wrapper()
    wrapped = wrapper.wrap_node("initialize", _ok_handler)

    result = _run(wrapped({"messages": []}))

    assert isinstance(result.get(TRACE_ID_KEY), str)
    assert isinstance(result.get(TRACE_SEQ_KEY), int)
    events = result.get(TRACE_EVENTS_KEY)
    assert isinstance(events, list)
    assert events

    seq_values = [event.get("seq") for event in events if isinstance(event, dict)]
    assert seq_values == sorted(seq_values)
    assert result[TRACE_SEQ_KEY] == seq_values[-1]

    event_types = [event.get("event_type") for event in events]
    assert "stage_start" in event_types
    assert "stage_complete" in event_types


def _run(awaitable):
    import asyncio

    return asyncio.run(awaitable)
