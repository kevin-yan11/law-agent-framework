"""Transport-neutral framework runner.

This entrypoint runs the conversational graph using a generic request payload
with `messages` + `request_context`, independent of CopilotKit transport.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from legal_agent_framework.tracing import (
    TRACE_EVENTS_KEY,
    TRACE_ID_KEY,
    TRACE_SEQ_KEY,
    replay_trace_events,
)


class FrameworkMessage(BaseModel):
    """Transport-neutral chat message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


logger = logging.getLogger(__name__)


class FrameworkRunRequest(BaseModel):
    """Input payload for framework runner."""

    messages: list[FrameworkMessage] = Field(
        default_factory=list,
        description="Conversation history including the latest user message.",
    )
    request_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Transport-agnostic context (user_state, ui_mode, legal_topic, etc.)",
    )
    session_id: str | None = None
    thread_id: str | None = None
    trace_id: str | None = None
    trace_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Optional prior trace events from earlier turns. "
            "Runner will replay/sort and append new events."
        ),
    )


class FrameworkRunResponse(BaseModel):
    """Output payload from framework runner."""

    session_id: str
    thread_id: str
    response: str
    quick_replies: list[str] = Field(default_factory=list)
    suggest_brief: bool = False
    mode: str | None = None
    safety_result: str | None = None
    trace_id: str
    trace_events: list[dict[str, Any]] = Field(default_factory=list)


async def run_framework_turn(
    payload: FrameworkRunRequest,
    graph: Any | None = None,
) -> FrameworkRunResponse:
    """Run one graph turn using transport-neutral request payload."""
    session_id = payload.session_id or str(uuid.uuid4())
    thread_id = payload.thread_id or session_id
    trace_id = payload.trace_id or str(uuid.uuid4())
    trace_events = replay_trace_events(payload.trace_events)
    trace_seq = _max_trace_seq(trace_events)

    messages = _to_langchain_messages(payload.messages)
    if not messages:
        raise ValueError("At least one message is required.")
    if not any(isinstance(msg, HumanMessage) for msg in messages):
        raise ValueError("At least one user message is required.")

    state_input = {
        "session_id": session_id,
        "messages": messages,
        "request_context": payload.request_context or {},
        TRACE_ID_KEY: trace_id,
        TRACE_SEQ_KEY: trace_seq,
        TRACE_EVENTS_KEY: trace_events,
    }
    config = {"configurable": {"thread_id": thread_id}}

    if graph is None:
        raise ValueError(
            "A compiled graph must be provided. "
            "This package does not import app-specific graph implementations."
        )
    compiled_graph = graph

    latest_response = ""
    quick_replies: list[str] = []
    suggest_brief = False
    mode: str | None = None
    safety_result: str | None = None

    async for event in compiled_graph.astream(
        state_input,
        config=config,
        stream_mode="updates",
    ):
        if not isinstance(event, dict):
            continue
        for update in event.values():
            if not isinstance(update, dict):
                continue

            if "mode" in update:
                mode = _safe_str(update.get("mode"))
            if "safety_result" in update:
                safety_result = _safe_str(update.get("safety_result"))
            if "quick_replies" in update and isinstance(update["quick_replies"], list):
                quick_replies = [str(item) for item in update["quick_replies"] if item is not None]
            if "suggest_brief" in update:
                suggest_brief = bool(update.get("suggest_brief"))
            if TRACE_ID_KEY in update:
                maybe_trace_id = _safe_str(update.get(TRACE_ID_KEY))
                if maybe_trace_id:
                    trace_id = maybe_trace_id
            if TRACE_SEQ_KEY in update:
                try:
                    trace_seq = max(trace_seq, int(update.get(TRACE_SEQ_KEY)))
                except (TypeError, ValueError):
                    pass
            if TRACE_EVENTS_KEY in update and isinstance(update[TRACE_EVENTS_KEY], list):
                trace_events = replay_trace_events(update[TRACE_EVENTS_KEY])

            maybe_response = _extract_latest_ai_text(update.get("messages"))
            if maybe_response:
                latest_response = maybe_response

    trace_events = replay_trace_events(trace_events)
    if trace_events:
        trace_seq = max(trace_seq, _max_trace_seq(trace_events))

    logger.info(
        "framework runner completed: thread_id=%s session_id=%s mode=%s trace_id=%s trace_events=%s",
        thread_id,
        session_id,
        mode or "unknown",
        trace_id,
        len(trace_events),
    )

    return FrameworkRunResponse(
        session_id=session_id,
        thread_id=thread_id,
        response=latest_response,
        quick_replies=quick_replies,
        suggest_brief=suggest_brief,
        mode=mode,
        safety_result=safety_result,
        trace_id=trace_id,
        trace_events=trace_events,
    )


def _to_langchain_messages(messages: list[FrameworkMessage]) -> list[BaseMessage]:
    converted: list[BaseMessage] = []
    for message in messages:
        if message.role == "user":
            converted.append(HumanMessage(content=message.content))
        elif message.role == "assistant":
            converted.append(AIMessage(content=message.content))
    return converted


def _extract_latest_ai_text(messages: Any) -> str:
    if not isinstance(messages, list) or not messages:
        return ""

    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return _content_to_text(message.content)
        message_type = getattr(message, "type", None)
        if message_type == "ai":
            return _content_to_text(getattr(message, "content", ""))

    return ""


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return " ".join(part.strip() for part in parts if part).strip()
    if content is None:
        return ""
    return str(content)


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _max_trace_seq(events: list[dict[str, Any]]) -> int:
    if not events:
        return 0

    max_seq = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        try:
            seq = int(event.get("seq", 0))
        except (TypeError, ValueError):
            continue
        if seq > max_seq:
            max_seq = seq
    return max_seq

