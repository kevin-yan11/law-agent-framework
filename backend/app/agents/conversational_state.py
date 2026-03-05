"""Simplified state for conversational mode.

This replaces the complex AdaptiveAgentState with a simpler structure
focused on natural conversation rather than multi-stage analysis pipelines.
"""

from typing import Optional, Literal, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
import operator


class ConversationalState(TypedDict):
    """Simple state for conversational legal assistant.

    Focuses on:
    - Fast, natural conversation
    - Tool usage (RAG, lawyer finder) as needed
    - Quick replies for smooth UX
    - Brief generation only on explicit request
    """

    # ---- Session & Context ----
    session_id: str
    user_state: Optional[str]  # Australian state/territory (NSW, VIC, etc.)
    uploaded_document_url: Optional[str]

    # ---- Conversation ----
    messages: Annotated[list[BaseMessage], operator.add]
    current_query: str

    # ---- Mode Control ----
    mode: Literal["chat", "brief"]  # Current operation mode
    ui_mode: Literal["chat", "analysis"]  # UI mode: casual chat vs guided analysis
    legal_topic: str  # Legal topic/domain: "general", "parking_ticket", etc.
    is_first_message: bool  # First message in session (run safety check)

    # ---- Chat Response Metadata ----
    quick_replies: Optional[list[str]]  # Suggested response options
    suggest_brief: bool  # Whether to highlight brief generation option

    # ---- Safety ----
    safety_result: Literal["safe", "escalate", "unknown"]
    crisis_resources: Optional[list[dict]]  # If escalation needed

    # ---- Brief Generation (only used in brief mode) ----
    brief_facts_collected: Optional[dict]
    brief_missing_info: Optional[list[str]]
    brief_unknown_info: Optional[list[str]]  # Info user explicitly doesn't know
    brief_info_complete: bool
    brief_questions_asked: int
    brief_needs_full_intake: bool  # True if conversation was too short when brief triggered
    brief_pending_questions: Optional[list[str]]  # Questions waiting to be asked (one at a time)
    brief_current_question_index: int  # Which question we're on (0-indexed)
    brief_total_questions: int  # Total number of questions in current round

    # ---- CopilotKit Integration ----
    copilotkit: Optional[dict]

    # ---- Transport-Agnostic Context ----
    # Preferred integration contract for reusable framework consumers.
    request_context: Optional[dict]

    # ---- Framework Trace Metadata ----
    # Structured trace stream propagated by StageRuntimeWrapper.
    framework_trace_id: Optional[str]
    framework_trace_seq: Optional[int]
    framework_trace_events: Optional[list[dict]]

    # ---- Error Handling ----
    error: Optional[str]


class ConversationalOutput(TypedDict):
    """Output schema - these fields are streamed to UI via AG-UI protocol.

    The frontend accesses these via useCoAgent hook.
    Note: The quick reply LLM call uses get_internal_llm_config to suppress
    streaming, preventing raw JSON from appearing in the chat.

    IMPORTANT: Messages are NOT included here to prevent duplicates.
    Messages are streamed separately via AG-UI protocol events (emit-messages).
    Including messages here causes the full accumulated history to be re-sent
    each turn, resulting in duplicate messages in CopilotChat.
    """

    quick_replies: Optional[list[str]]
    suggest_brief: bool
