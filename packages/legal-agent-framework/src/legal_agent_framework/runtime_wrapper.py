"""Runtime wrapper that applies policy hooks, validators, and telemetry."""

import inspect
import logging
import time
import uuid
from dataclasses import asdict
from typing import Any, Awaitable, Callable

from langchain_core.messages import AIMessage

from legal_agent_framework.contracts import LawContext
from legal_agent_framework.policy_engine import PolicyEngine, PolicyHit
from legal_agent_framework.tracing import (
    TRACE_EVENTS_KEY,
    TRACE_ID_KEY,
    TRACE_SEQ_KEY,
    compact_trace_events,
    create_trace_event,
    extract_trace_state,
    log_trace_event,
)
from legal_agent_framework.validators import ValidationIssue, ValidatorEngine


NodeHandler = Callable[..., Any]
logger = logging.getLogger(__name__)


class StageRuntimeWrapper:
    """Wraps existing graph nodes without changing functional behavior."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        validator_engine: ValidatorEngine,
    ):
        self.policy_engine = policy_engine
        self.validator_engine = validator_engine

    def wrap_node(self, stage: str, handler: NodeHandler) -> Callable[..., Awaitable[Any]]:
        """Return an async node wrapper compatible with LangGraph nodes."""

        async def wrapped(state: dict, config: dict | None = None) -> Any:
            started = time.perf_counter()
            trace_id, trace_seq, trace_events = extract_trace_state(state)
            trace_id = trace_id or str(uuid.uuid4())
            trace_seq, trace_events = self._append_trace_event(
                trace_id=trace_id,
                seq=trace_seq,
                events=trace_events,
                stage=stage,
                event_type="stage_start",
                payload={"handler": getattr(handler, "__name__", "<anonymous>")},
            )

            context_before = LawContext.from_state(state)

            before_hits = self.policy_engine.before_stage(stage, context_before)
            self._log_policy_hits("before_stage", before_hits)
            trace_seq, trace_events = self._record_policy_trace_events(
                trace_id=trace_id,
                seq=trace_seq,
                events=trace_events,
                stage=stage,
                hook="before_stage",
                hits=before_hits,
            )
            enforced_before_hits = [
                hit for hit in before_hits
                if self.policy_engine.is_enforced_hit(hit)
            ]
            override = self._build_policy_override(stage, enforced_before_hits, state)
            if override is not None:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                trace_seq, trace_events = self._append_trace_event(
                    trace_id=trace_id,
                    seq=trace_seq,
                    events=trace_events,
                    stage=stage,
                    event_type="policy_override_before_stage",
                    payload={
                        "duration_ms": elapsed_ms,
                        "enforced_rules": [hit.rule_id for hit in enforced_before_hits],
                    },
                )
                trace_seq, trace_events = self._append_trace_event(
                    trace_id=trace_id,
                    seq=trace_seq,
                    events=trace_events,
                    stage=stage,
                    event_type="stage_complete",
                    payload={
                        "result": "policy_override",
                        "duration_ms": elapsed_ms,
                    },
                )
                logger.warning(
                    "framework runtime: enforced policy override before stage=%s duration_ms=%s hits=%s",
                    stage,
                    elapsed_ms,
                    len(enforced_before_hits),
                )
                return self._attach_trace_metadata(
                    override,
                    trace_id=trace_id,
                    seq=trace_seq,
                    events=trace_events,
                )

            try:
                result = await self._invoke_handler(handler, state, config)
            except Exception as e:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                trace_seq, trace_events = self._append_trace_event(
                    trace_id=trace_id,
                    seq=trace_seq,
                    events=trace_events,
                    stage=stage,
                    event_type="stage_error",
                    payload={
                        "duration_ms": elapsed_ms,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                )
                trace_seq, trace_events = self._append_trace_event(
                    trace_id=trace_id,
                    seq=trace_seq,
                    events=trace_events,
                    stage=stage,
                    event_type="stage_complete",
                    payload={
                        "result": "error",
                        "duration_ms": elapsed_ms,
                    },
                )
                raise

            merged_state = _merge_state(state, result)
            context_after = LawContext.from_state(merged_state)

            output_hits = self.policy_engine.before_output(stage, context_after, _as_dict(result))
            self._log_policy_hits("before_output", output_hits)
            trace_seq, trace_events = self._record_policy_trace_events(
                trace_id=trace_id,
                seq=trace_seq,
                events=trace_events,
                stage=stage,
                hook="before_output",
                hits=output_hits,
            )
            enforced_output_hits = [
                hit for hit in output_hits
                if self.policy_engine.is_enforced_hit(hit)
            ]
            output_override = self._build_policy_override(stage, enforced_output_hits, merged_state)
            if output_override is not None:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                trace_seq, trace_events = self._append_trace_event(
                    trace_id=trace_id,
                    seq=trace_seq,
                    events=trace_events,
                    stage=stage,
                    event_type="policy_override_before_output",
                    payload={
                        "duration_ms": elapsed_ms,
                        "enforced_rules": [hit.rule_id for hit in enforced_output_hits],
                    },
                )
                trace_seq, trace_events = self._append_trace_event(
                    trace_id=trace_id,
                    seq=trace_seq,
                    events=trace_events,
                    stage=stage,
                    event_type="stage_complete",
                    payload={
                        "result": "policy_override",
                        "duration_ms": elapsed_ms,
                    },
                )
                logger.warning(
                    "framework runtime: enforced policy override before output stage=%s duration_ms=%s hits=%s",
                    stage,
                    elapsed_ms,
                    len(enforced_output_hits),
                )
                return self._attach_trace_metadata(
                    output_override,
                    trace_id=trace_id,
                    seq=trace_seq,
                    events=trace_events,
                )

            validation_issues = self.validator_engine.validate_stage_result(
                stage=stage,
                stage_output=_as_dict(result),
                context=context_after,
            )
            self._log_validation_issues(validation_issues)
            trace_seq, trace_events = self._record_validation_trace_events(
                trace_id=trace_id,
                seq=trace_seq,
                events=trace_events,
                stage=stage,
                issues=validation_issues,
            )

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            trace_seq, trace_events = self._append_trace_event(
                trace_id=trace_id,
                seq=trace_seq,
                events=trace_events,
                stage=stage,
                event_type="stage_complete",
                payload={
                    "result": "success",
                    "duration_ms": elapsed_ms,
                    "policy_hit_count": len(before_hits) + len(output_hits),
                    "validation_issue_count": len(validation_issues),
                },
            )
            logger.info(
                "framework runtime: stage=%s duration_ms=%s policy_hits=%s validation_issues=%s",
                stage,
                elapsed_ms,
                len(before_hits) + len(output_hits),
                len(validation_issues),
            )

            return self._attach_trace_metadata(
                result,
                trace_id=trace_id,
                seq=trace_seq,
                events=trace_events,
            )

        return wrapped

    @staticmethod
    def _build_policy_override(
        stage: str,
        hits: list[PolicyHit],
        state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Create an enforced response payload for supported policy actions."""
        if not hits:
            return None

        # Only message-producing stages can be safely overridden.
        if stage not in {"chat_response", "brief_generate"}:
            return None

        action_priority = {"escalate": 3, "block": 2, "ask_user": 1}
        selected = max(
            hits,
            key=lambda hit: action_priority.get(hit.action, 0),
        )

        if selected.action == "ask_user":
            message = (
                "Before I continue, please select your state or territory so I can provide "
                "jurisdiction-specific legal information."
            )
            return {
                "messages": [AIMessage(content=message)],
                "quick_replies": ["I selected my state", "Continue with general info"],
            }

        if selected.action == "escalate":
            resources_text = _format_crisis_resources(state)
            message = (
                "I can’t continue with normal legal guidance because this may involve an urgent "
                "safety situation.\n\n"
                f"{resources_text}"
            )
            return {
                "messages": [AIMessage(content=message)],
                "safety_result": "escalate",
                "suggest_brief": False,
            }

        if selected.action == "block":
            message = (
                "I’m not ready to provide a legal conclusion yet because required compliance "
                "checks were not satisfied. I can continue once we gather the missing details or sources."
            )
            return {
                "messages": [AIMessage(content=message)],
                "quick_replies": ["Show sources", "Rephrase my question"],
            }

        return None

    async def _invoke_handler(
        self,
        handler: NodeHandler,
        state: dict,
        config: dict | None,
    ) -> Any:
        """Invoke async/sync node handlers while preserving existing signatures."""
        signature = inspect.signature(handler)
        expects_config = "config" in signature.parameters

        if inspect.iscoroutinefunction(handler):
            if expects_config:
                return await handler(state, config)
            return await handler(state)

        if expects_config:
            return handler(state, config)
        return handler(state)

    @staticmethod
    def _log_policy_hits(hook: str, hits: list[PolicyHit]) -> None:
        for hit in hits:
            logger.warning(
                "framework policy (%s): rule=%s stage=%s severity=%s action=%s msg=%s",
                hook,
                hit.rule_id,
                hit.stage,
                hit.severity,
                hit.action,
                hit.message,
            )

    @staticmethod
    def _log_validation_issues(issues: list[ValidationIssue]) -> None:
        for issue in issues:
            logger.warning(
                "framework validator: id=%s stage=%s severity=%s msg=%s",
                issue.validator_id,
                issue.stage,
                issue.severity,
                issue.message,
            )

    @staticmethod
    def _record_policy_trace_events(
        trace_id: str,
        seq: int,
        events: list[dict[str, Any]],
        stage: str,
        hook: str,
        hits: list[PolicyHit],
    ) -> tuple[int, list[dict[str, Any]]]:
        for hit in hits:
            seq, events = StageRuntimeWrapper._append_trace_event(
                trace_id=trace_id,
                seq=seq,
                events=events,
                stage=stage,
                event_type=f"policy_hit_{hook}",
                payload={
                    "rule_id": hit.rule_id,
                    "severity": hit.severity,
                    "action": hit.action,
                    "message": hit.message,
                    "details": hit.details,
                },
            )
        return seq, events

    @staticmethod
    def _record_validation_trace_events(
        trace_id: str,
        seq: int,
        events: list[dict[str, Any]],
        stage: str,
        issues: list[ValidationIssue],
    ) -> tuple[int, list[dict[str, Any]]]:
        for issue in issues:
            seq, events = StageRuntimeWrapper._append_trace_event(
                trace_id=trace_id,
                seq=seq,
                events=events,
                stage=stage,
                event_type="validation_issue",
                payload={
                    "validator_id": issue.validator_id,
                    "severity": issue.severity,
                    "message": issue.message,
                    "details": issue.details,
                },
            )
        return seq, events

    @staticmethod
    def _append_trace_event(
        trace_id: str,
        seq: int,
        events: list[dict[str, Any]],
        stage: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        next_seq = seq + 1
        event = create_trace_event(
            trace_id=trace_id,
            seq=next_seq,
            stage=stage,
            event_type=event_type,
            payload=payload,
        )
        log_trace_event(event)
        return next_seq, compact_trace_events([*events, event])

    @staticmethod
    def _attach_trace_metadata(
        result: Any,
        trace_id: str,
        seq: int,
        events: list[dict[str, Any]],
    ) -> Any:
        if not isinstance(result, dict):
            return result

        enriched = dict(result)
        enriched[TRACE_ID_KEY] = trace_id
        enriched[TRACE_SEQ_KEY] = seq
        enriched[TRACE_EVENTS_KEY] = compact_trace_events(events)
        return enriched


def build_default_runtime() -> StageRuntimeWrapper:
    """Factory for the Phase 1 default runtime (observe/warn mode)."""
    from legal_agent_framework.config import (
        LAW_FRAMEWORK_ENFORCE_ALL_POLICIES,
        LAW_FRAMEWORK_POLICY_ENFORCE_RULES,
        LAW_FRAMEWORK_ENFORCE_ALL_VALIDATORS,
        LAW_FRAMEWORK_VALIDATOR_ENFORCE_IDS,
    )

    return StageRuntimeWrapper(
        policy_engine=PolicyEngine(
            enforce=LAW_FRAMEWORK_ENFORCE_ALL_POLICIES,
            enforced_rules=LAW_FRAMEWORK_POLICY_ENFORCE_RULES,
        ),
        validator_engine=ValidatorEngine(
            enforce=LAW_FRAMEWORK_ENFORCE_ALL_VALIDATORS,
            enforced_validators=LAW_FRAMEWORK_VALIDATOR_ENFORCE_IDS,
        ),
    )


def _merge_state(state: dict, result: Any) -> dict:
    if not isinstance(state, dict):
        return {}
    if isinstance(result, dict):
        merged = dict(state)
        merged.update(result)
        return merged
    return dict(state)


def _as_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    try:
        return asdict(value)
    except Exception:
        return None


def _format_crisis_resources(state: dict[str, Any] | None) -> str:
    """Format crisis resources from state, if available."""
    if not isinstance(state, dict):
        return (
            "If you are in immediate danger, contact emergency services now. "
            "If you'd like, I can also help find relevant crisis support numbers."
        )

    resources = state.get("crisis_resources")
    if not isinstance(resources, list) or not resources:
        return (
            "If you are in immediate danger, contact emergency services now. "
            "If you'd like, I can also help find relevant crisis support numbers."
        )

    lines: list[str] = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        name = resource.get("name", "Support service")
        phone = resource.get("phone")
        url = resource.get("url")
        line = f"- {name}"
        if phone:
            line += f": {phone}"
        if url:
            line += f" ({url})"
        lines.append(line)

    if not lines:
        return (
            "If you are in immediate danger, contact emergency services now. "
            "If you'd like, I can also help find relevant crisis support numbers."
        )

    return "Please use one of these support options:\n" + "\n".join(lines)
