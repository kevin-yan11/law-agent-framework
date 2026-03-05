"""Observe-first policy engine for legal-agent control rails."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from legal_agent_framework.contracts import LawContext


PolicySeverity = Literal["low", "medium", "high", "critical"]
PolicyAction = Literal["observe", "continue", "ask_user", "escalate", "block", "retry"]


@dataclass
class PolicyHit:
    """Single policy rule match."""

    rule_id: str
    stage: str
    severity: PolicySeverity
    action: PolicyAction
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PolicyEngine:
    """Evaluates policy hooks in observe mode by default."""

    def __init__(self, enforce: bool = False, enforced_rules: set[str] | None = None):
        self.enforce = enforce
        self.enforced_rules = {rule.upper() for rule in (enforced_rules or set())}

    def before_stage(self, stage: str, context: LawContext) -> list[PolicyHit]:
        """Evaluate rules before stage execution."""
        return self._evaluate(stage=stage, context=context, hook="before_stage")

    def before_output(
        self,
        stage: str,
        context: LawContext,
        stage_output: dict[str, Any] | None,
    ) -> list[PolicyHit]:
        """Evaluate rules before output is emitted to user."""
        return self._evaluate(
            stage=stage,
            context=context,
            hook="before_output",
            stage_output=stage_output,
        )

    def _evaluate(
        self,
        stage: str,
        context: LawContext,
        hook: str,
        stage_output: dict[str, Any] | None = None,
    ) -> list[PolicyHit]:
        hits: list[PolicyHit] = []
        hits.extend(self._rule_p001_state_required(stage, context, hook))
        hits.extend(self._rule_p002_high_risk_escalation(stage, context, hook))
        hits.extend(self._rule_p003_citations_required(stage, context, hook, stage_output))
        return hits

    def is_enforced_hit(self, hit: PolicyHit) -> bool:
        """Check whether a policy hit should actively enforce behavior."""
        if self.enforce:
            return True
        return hit.rule_id.upper() in self.enforced_rules

    def _rule_p001_state_required(
        self,
        stage: str,
        context: LawContext,
        hook: str,
    ) -> list[PolicyHit]:
        """P-001: State/jurisdiction should be set before legal conclusions."""
        if hook != "before_stage":
            return []
        if stage not in {"chat_response", "brief_generate"}:
            return []
        if context.user_state:
            return []
        return [
            PolicyHit(
                rule_id="P-001",
                stage=stage,
                severity="high",
                action="ask_user",
                message="User state/territory is missing for jurisdiction-specific response.",
            )
        ]

    def _rule_p002_high_risk_escalation(
        self,
        stage: str,
        context: LawContext,
        hook: str,
    ) -> list[PolicyHit]:
        """P-002: High-risk content must route to escalation."""
        if hook != "before_stage":
            return []
        if stage != "chat_response":
            return []
        if not context.escalation_required:
            return []
        return [
            PolicyHit(
                rule_id="P-002",
                stage=stage,
                severity="critical",
                action="escalate",
                message="High-risk context detected; escalation should occur before chat response.",
                details={"risk_flags": context.risk_flags},
            )
        ]

    def _rule_p003_citations_required(
        self,
        stage: str,
        context: LawContext,
        hook: str,
        stage_output: dict[str, Any] | None,
    ) -> list[PolicyHit]:
        """P-003: Legal conclusions should include citations where expected."""
        if hook != "before_output":
            return []
        if stage not in {"chat_response", "brief_generate"}:
            return []
        if not context.metadata.get("expects_citations"):
            return []

        # Phase 1 is observe-only. We treat explicit citation arrays as source of truth.
        has_citations = bool(context.citations)
        if not has_citations and isinstance(stage_output, dict):
            has_citations = bool(stage_output.get("citations"))
        if has_citations:
            return []
        return [
            PolicyHit(
                rule_id="P-003",
                stage=stage,
                severity="high",
                action="block",
                message="Potential legal conclusion without explicit citation payload.",
            )
        ]
