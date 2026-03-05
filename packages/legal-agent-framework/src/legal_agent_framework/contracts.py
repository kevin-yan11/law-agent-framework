"""Framework contracts shared across runtime, policy, and validation layers."""

from dataclasses import dataclass, field
from typing import Any, Literal


Decision = Literal["continue", "ask_user", "escalate", "block", "end"]


@dataclass
class LawContext:
    """Framework-level context passed across policy/validation hooks."""

    session_id: str | None = None
    user_query: str = ""
    user_state: str | None = None
    facts: dict[str, Any] = field(default_factory=dict)
    citations: list[dict[str, Any]] = field(default_factory=list)
    deadlines: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    escalation_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_state(cls, state: dict[str, Any] | None) -> "LawContext":
        """Best-effort conversion from graph state to framework context."""
        if not isinstance(state, dict):
            return cls()

        safety_result = state.get("safety_result")
        risk_flags: list[str] = []
        if safety_result == "escalate":
            risk_flags.append("high_risk")

        current_query = state.get("current_query") or ""
        citations = state.get("citations") or []
        deadlines = state.get("deadlines") or []

        metadata = {
            "mode": state.get("mode"),
            "ui_mode": state.get("ui_mode"),
            "legal_topic": state.get("legal_topic"),
            "safety_result": safety_result,
            "has_document": bool(state.get("uploaded_document_url")),
            # Heuristic marker used by observe-only policy rule P-003.
            "expects_citations": any(
                token in current_query.lower()
                for token in ["law", "act", "section", "rights", "legal"]
            ),
        }

        return cls(
            session_id=state.get("session_id"),
            user_query=current_query,
            user_state=state.get("user_state"),
            facts=state.get("brief_facts_collected") or {},
            citations=citations if isinstance(citations, list) else [],
            deadlines=deadlines if isinstance(deadlines, list) else [],
            risk_flags=risk_flags,
            escalation_required=safety_result == "escalate",
            metadata=metadata,
        )


@dataclass
class StageResult:
    """Normalized stage output container for framework adapters."""

    updates: dict[str, Any] = field(default_factory=dict)
    decision: Decision = "continue"
    reason: str = ""
    telemetry: dict[str, Any] = field(default_factory=dict)
