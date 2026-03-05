"""Tests for extracted framework package imports."""

from legal_agent_framework import PolicyEngine, FrameworkRunRequest
from legal_agent_framework.runtime_wrapper import StageRuntimeWrapper
from legal_agent_framework.tracing import TRACE_ID_KEY


def test_framework_package_imports_are_available():
    assert PolicyEngine.__module__.startswith("legal_agent_framework.")
    assert FrameworkRunRequest.__module__.startswith("legal_agent_framework.")
    assert StageRuntimeWrapper.__module__.startswith("legal_agent_framework.")
    assert TRACE_ID_KEY == "framework_trace_id"
