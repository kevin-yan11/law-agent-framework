"""Conversational mode graph for natural legal chat.

This is a simpler, faster alternative to the adaptive graph.
Focuses on natural conversation with tools, not multi-stage pipelines.

Flow (chat and analysis modes):
    initialize -> safety_check -> chat_response -> END
                      |
                      v (if crisis)
              escalation_response -> END

    In analysis mode, the agent naturally guides users through a consultation
    (understand situation → explain law → offer options) via its system prompt.
    No automatic analysis triggers - conversation flows naturally.

Flow (brief mode - triggered by user button):
    initialize -> brief_check_info -> [brief_ask_questions | brief_generate] -> END
"""

import uuid
from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.conversational_state import ConversationalState, ConversationalOutput
from app.agents.providers import ensure_builtin_stage_providers_registered
from app.context import resolve_request_context
from legal_agent_framework import build_default_runtime, resolve_stage_provider
from legal_agent_framework.config import get_configured_stage_provider_name
from app.config import logger


# Brief generation trigger marker (sent from frontend)
BRIEF_TRIGGER = "[GENERATE_BRIEF]"

# Early generation trigger (user wants to generate with available info)
GENERATE_NOW_TRIGGER = "[GENERATE_NOW]"

# Phase 1 framework runtime (observe/warn mode, no behavior changes)
_framework_runtime = build_default_runtime()


# ============================================
# Graph Nodes
# ============================================

async def initialize_node(state: ConversationalState) -> dict:
    """
    Initialize state with session ID, extract query and CopilotKit context.

    This is lightweight - just extracts what we need for conversation.
    Also detects brief generation trigger from frontend.
    """
    messages = state.get("messages", [])
    current_query = ""

    # Extract the latest human message as the current query
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            current_query = msg.content
            break

    session_id = state.get("session_id") or str(uuid.uuid4())

    # Extract normalized request context via transport-agnostic resolver
    request_context = resolve_request_context(state)
    user_state = request_context.user_state
    uploaded_document_url = request_context.uploaded_document_url
    ui_mode = request_context.ui_mode  # "chat" or "analysis"
    legal_topic = request_context.legal_topic  # "general", "parking_ticket", etc.

    # Check if this is the first message (new session)
    is_first_message = len(messages) <= 1

    # Check for brief generation trigger
    is_brief_mode = BRIEF_TRIGGER in current_query
    if is_brief_mode:
        # Clean the trigger from the query
        current_query = current_query.replace(BRIEF_TRIGGER, "").strip()

    logger.info(
        f"Conversational init: session={session_id[:8]}, "
        f"query_length={len(current_query)}, user_state={user_state}, "
        f"has_document={bool(uploaded_document_url)}, first_msg={is_first_message}, "
        f"brief_mode={is_brief_mode}, ui_mode={ui_mode}, legal_topic={legal_topic}"
    )

    return {
        "session_id": session_id,
        "current_query": current_query,
        "user_state": user_state,
        "uploaded_document_url": uploaded_document_url,
        "is_first_message": is_first_message,
        "mode": "brief" if is_brief_mode else "chat",
        "ui_mode": ui_mode,
        "legal_topic": legal_topic,
    }


def route_after_initialize(state: ConversationalState) -> Literal["brief", "check", "skip"]:
    """
    Route based on mode after initialization.

    - brief: User triggered brief generation
    - check: Run safety check (first message or risky content)
    - skip: Skip safety, go directly to chat
    """
    # Brief mode bypasses normal flow
    if state.get("mode") == "brief":
        return "brief"

    # Always check on first message
    if state.get("is_first_message", True):
        return "check"

    # Quick heuristic: check if query is short follow-up
    query = state.get("current_query", "")
    if len(query) < 30 and not any(
        word in query.lower()
        for word in ["help", "emergency", "scared", "hurt", "kill", "die", "suicide"]
    ):
        return "skip"

    return "check"


def route_brief_info(state: ConversationalState) -> Literal["generate", "ask"]:
    """
    Route based on whether we have enough info for the brief.

    - generate: We have enough info, generate the brief
    - ask: Need more info, ask follow-up questions

    No arbitrary question limit - keep asking until:
    - brief_info_complete is True (all critical info gathered)
    - User explicitly requests early generation via GENERATE_NOW_TRIGGER
    - No more missing info remains (including items marked as unknown)
    """
    # If info is complete, generate brief
    if state.get("brief_info_complete", False):
        return "generate"

    # Check if user requested early generation
    current_query = state.get("current_query", "")
    if GENERATE_NOW_TRIGGER in current_query:
        return "generate"

    # Check if no more missing info (all either answered or marked unknown)
    missing_info = state.get("brief_missing_info", [])
    if not missing_info:
        return "generate"

    # Otherwise, ask more questions
    return "ask"


# ============================================
# Graph Definition
# ============================================

def build_conversational_graph():
    """
    Build the conversational legal assistant graph.

    Chat/Analysis flow:
    - Initialize (extract context)
    - Safety check (lightweight, skippable for follow-ups)
    - Chat response (natural conversation with tools)
    - END

    In analysis mode, the agent uses a different system prompt that guides
    it to behave like a lawyer consultation (understand → explain law → options).
    No automatic analysis triggers - conversation flows naturally.

    Brief flow (user-triggered):
    - Initialize (detect brief trigger)
    - Brief check info (extract facts, find gaps)
    - Brief ask questions (if info missing) or Brief generate (if ready)
    """
    ensure_builtin_stage_providers_registered()
    stage_provider = resolve_stage_provider(get_configured_stage_provider_name())
    stage_nodes = stage_provider.get_stage_nodes()
    route_handlers = stage_provider.get_route_handlers()

    # Output schema limits what gets streamed to UI
    workflow = StateGraph(ConversationalState, output=ConversationalOutput)

    # Add chat/analysis mode nodes
    workflow.add_node(
        "initialize",
        _framework_runtime.wrap_node("initialize", initialize_node),
    )
    workflow.add_node(
        "safety_check",
        _framework_runtime.wrap_node("safety_check", stage_nodes["safety_check"]),
    )
    workflow.add_node(
        "escalation_response",
        _framework_runtime.wrap_node("escalation_response", stage_nodes["escalation_response"]),
    )
    workflow.add_node(
        "chat_response",
        _framework_runtime.wrap_node("chat_response", stage_nodes["chat_response"]),
    )

    # Add brief mode nodes
    workflow.add_node(
        "brief_check_info",
        _framework_runtime.wrap_node("brief_check_info", stage_nodes["brief_check_info"]),
    )
    workflow.add_node(
        "brief_ask_questions",
        _framework_runtime.wrap_node("brief_ask_questions", stage_nodes["brief_ask_questions"]),
    )
    workflow.add_node(
        "brief_generate",
        _framework_runtime.wrap_node("brief_generate", stage_nodes["brief_generate"]),
    )

    # Entry point
    workflow.set_entry_point("initialize")

    # After initialize, route based on mode
    workflow.add_conditional_edges(
        "initialize",
        route_after_initialize,
        {
            "brief": "brief_check_info",
            "check": "safety_check",
            "skip": "chat_response",
        }
    )

    # After safety check, route based on result
    workflow.add_conditional_edges(
        "safety_check",
        route_handlers["route_after_safety"],
        {
            "escalate": "escalation_response",
            "continue": "chat_response",
        }
    )

    # After chat response, always end (no auto-analysis trigger)
    workflow.add_edge("chat_response", END)

    # Brief mode routing
    workflow.add_conditional_edges(
        "brief_check_info",
        route_brief_info,
        {
            "generate": "brief_generate",
            "ask": "brief_ask_questions",
        }
    )

    # Terminal nodes
    workflow.add_edge("escalation_response", END)
    workflow.add_edge("brief_ask_questions", END)  # Wait for user response
    workflow.add_edge("brief_generate", END)

    return workflow


def create_conversational_agent():
    """Create the compiled conversational agent graph with memory."""
    workflow = build_conversational_graph()
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Singleton compiled graph
_conversational_graph = None


def get_conversational_graph():
    """Get or create the singleton conversational graph."""
    global _conversational_graph
    if _conversational_graph is None:
        _conversational_graph = create_conversational_agent()
    return _conversational_graph
