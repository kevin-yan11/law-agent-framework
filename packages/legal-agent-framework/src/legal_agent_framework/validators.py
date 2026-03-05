"""Warn-first output validators for legal-agent responses."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from legal_agent_framework.contracts import LawContext


ValidationSeverity = Literal["low", "medium", "high", "critical"]


@dataclass
class ValidationIssue:
    """Single validator issue."""

    validator_id: str
    stage: str
    severity: ValidationSeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ValidatorEngine:
    """Stage output validation in warn-only mode by default."""

    def __init__(self, enforce: bool = False, enforced_validators: set[str] | None = None):
        self.enforce = enforce
        self.enforced_validators = {
            validator_id.upper()
            for validator_id in (enforced_validators or set())
        }

    def validate_stage_result(
        self,
        stage: str,
        stage_output: dict[str, Any] | None,
        context: LawContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_v001_structure(stage, stage_output))
        issues.extend(self._validate_v003_deadline_signals(stage, stage_output, context))
        issues.extend(self._validate_v005_uncertainty_language(stage, stage_output))
        return issues

    def is_enforced_issue(self, issue: ValidationIssue) -> bool:
        """Check whether a validator issue should actively enforce behavior."""
        if self.enforce:
            return True
        return issue.validator_id.upper() in self.enforced_validators

    def _validate_v001_structure(
        self,
        stage: str,
        stage_output: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """V-001: Required output structure per stage."""
        if stage_output is None:
            return [
                ValidationIssue(
                    validator_id="V-001",
                    stage=stage,
                    severity="high",
                    message="Stage returned no output payload.",
                )
            ]
        if not isinstance(stage_output, dict):
            return [
                ValidationIssue(
                    validator_id="V-001",
                    stage=stage,
                    severity="high",
                    message="Stage output is not a dict update payload.",
                    details={"type": type(stage_output).__name__},
                )
            ]
        if stage in {"chat_response", "escalation_response", "brief_ask_questions", "brief_generate"}:
            if "messages" not in stage_output:
                return [
                    ValidationIssue(
                        validator_id="V-001",
                        stage=stage,
                        severity="medium",
                        message="Message-emitting stage did not include a messages field.",
                    )
                ]
        return []

    def _validate_v003_deadline_signals(
        self,
        stage: str,
        stage_output: dict[str, Any] | None,
        context: LawContext,
    ) -> list[ValidationIssue]:
        """V-003: Deadline scenarios should surface timeline/deadline guidance."""
        if stage != "chat_response":
            return []
        if not isinstance(stage_output, dict):
            return []

        query = context.user_query.lower()
        deadline_terms = ["deadline", "tomorrow", "urgent", "hearing", "tribunal", "court"]
        if not any(term in query for term in deadline_terms):
            return []

        text = _extract_message_text(stage_output).lower()
        output_terms = ["deadline", "date", "time", "urgent", "as soon as"]
        if any(term in text for term in output_terms):
            return []

        return [
            ValidationIssue(
                validator_id="V-003",
                stage=stage,
                severity="medium",
                message="Potential deadline-related query without explicit timing guidance.",
            )
        ]

    def _validate_v005_uncertainty_language(
        self,
        stage: str,
        stage_output: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """V-005: Avoid guaranteed-outcome wording."""
        if stage not in {"chat_response", "brief_generate"}:
            return []
        if not isinstance(stage_output, dict):
            return []

        text = _extract_message_text(stage_output).lower()
        banned_terms = [
            "guaranteed outcome",
            "will definitely win",
            "100% sure",
            "certainly win",
        ]
        for term in banned_terms:
            if term in text:
                return [
                    ValidationIssue(
                        validator_id="V-005",
                        stage=stage,
                        severity="high",
                        message="Detected guaranteed-outcome language.",
                        details={"term": term},
                    )
                ]
        return []


def _extract_message_text(stage_output: dict[str, Any]) -> str:
    """Extract best-effort textual content from stage output."""
    messages = stage_output.get("messages")
    if not isinstance(messages, list) or not messages:
        return ""

    last_message = messages[-1]
    content = getattr(last_message, "content", None)
    if isinstance(content, str):
        return content
    if content is not None:
        return str(content)
    return str(last_message)
