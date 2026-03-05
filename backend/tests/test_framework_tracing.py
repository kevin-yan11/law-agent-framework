"""Tests for framework trace utility helpers."""

from legal_agent_framework.tracing import (
    TRACE_EVENTS_KEY,
    TRACE_ID_KEY,
    TRACE_SEQ_KEY,
    extract_trace_state,
    replay_trace_events,
)


def test_replay_trace_events_sorts_and_tolerates_non_numeric_seq():
    events = [
        {"seq": "bad", "event_type": "x"},
        {"seq": 3, "event_type": "c"},
        {"seq": 1, "event_type": "a"},
        {"seq": 2, "event_type": "b"},
    ]

    replayed = replay_trace_events(events)
    assert [event.get("seq") for event in replayed] == ["bad", 1, 2, 3]


def test_extract_trace_state_prefers_highest_sequence_from_events():
    state = {
        TRACE_ID_KEY: "trace-abc",
        TRACE_SEQ_KEY: 2,
        TRACE_EVENTS_KEY: [
            {"seq": 5, "event_type": "stage_complete"},
            {"seq": 4, "event_type": "stage_start"},
        ],
    }

    trace_id, seq, events = extract_trace_state(state)
    assert trace_id == "trace-abc"
    assert seq == 5
    assert [event.get("seq") for event in events] == [4, 5]
