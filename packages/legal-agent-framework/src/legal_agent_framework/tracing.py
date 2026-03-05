"""Structured tracing utilities for framework runtime events."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Mapping

logger = logging.getLogger(__name__)

# Canonical state keys for framework tracing.
TRACE_ID_KEY = "framework_trace_id"
TRACE_SEQ_KEY = "framework_trace_seq"
TRACE_EVENTS_KEY = "framework_trace_events"

# Keep state size bounded when traces flow through checkpointer-backed graphs.
DEFAULT_MAX_TRACE_EVENTS = 500


@dataclass
class TraceEvent:
    """Single structured trace event."""

    trace_id: str
    seq: int
    stage: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_trace_event(
    trace_id: str,
    seq: int,
    stage: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a structured trace event as a JSON-serializable dict."""
    event = TraceEvent(
        trace_id=trace_id,
        seq=seq,
        stage=stage,
        event_type=event_type,
        payload=payload or {},
    )
    return event.to_dict()


def log_trace_event(event: dict[str, Any]) -> None:
    """Emit a structured trace event as JSON in logs."""
    try:
        logger.info("framework_trace %s", json.dumps(event, sort_keys=True))
    except Exception:
        # Logging should never break execution.
        logger.info("framework_trace %s", event)


def replay_trace_events(events: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return events sorted by sequence for deterministic replay."""
    if not events:
        return []
    return sorted(
        [event for event in events if isinstance(event, dict)],
        key=_event_seq,
    )


def extract_trace_state(
    state: Mapping[str, Any] | None,
) -> tuple[str | None, int, list[dict[str, Any]]]:
    """Extract trace ID/sequence/events from state."""
    if not isinstance(state, Mapping):
        return None, 0, []

    raw_trace_id = state.get(TRACE_ID_KEY)
    trace_id = str(raw_trace_id) if raw_trace_id is not None else None

    raw_seq = state.get(TRACE_SEQ_KEY, 0)
    try:
        seq = max(0, int(raw_seq))
    except (TypeError, ValueError):
        seq = 0

    raw_events = state.get(TRACE_EVENTS_KEY)
    events = replay_trace_events(raw_events if isinstance(raw_events, list) else [])

    if events:
        max_seq = max(_event_seq(event) for event in events)
        if max_seq > seq:
            seq = max_seq

    return trace_id, seq, events


def compact_trace_events(
    events: list[dict[str, Any]],
    max_events: int = DEFAULT_MAX_TRACE_EVENTS,
) -> list[dict[str, Any]]:
    """Bound trace history size while preserving order."""
    if max_events <= 0:
        return []
    if len(events) <= max_events:
        return events
    return events[-max_events:]


def _event_seq(event: Mapping[str, Any]) -> int:
    raw = event.get("seq", 0)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0
