"""Core framework primitives for legal-agent orchestration.

This package intentionally exposes lazy imports so lightweight submodules
(`legal_agent_framework.tracing`, contracts, registries) can be imported
without booting app-specific runtime dependencies.
"""

from __future__ import annotations

import importlib
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    # contracts
    "Decision": ("legal_agent_framework.contracts", "Decision"),
    "LawContext": ("legal_agent_framework.contracts", "LawContext"),
    "StageResult": ("legal_agent_framework.contracts", "StageResult"),
    # policy/validation
    "PolicyEngine": ("legal_agent_framework.policy_engine", "PolicyEngine"),
    "PolicyHit": ("legal_agent_framework.policy_engine", "PolicyHit"),
    "ValidationIssue": ("legal_agent_framework.validators", "ValidationIssue"),
    "ValidatorEngine": ("legal_agent_framework.validators", "ValidatorEngine"),
    # runtime
    "StageRuntimeWrapper": ("legal_agent_framework.runtime_wrapper", "StageRuntimeWrapper"),
    "build_default_runtime": ("legal_agent_framework.runtime_wrapper", "build_default_runtime"),
    # runner
    "FrameworkMessage": ("legal_agent_framework.runner", "FrameworkMessage"),
    "FrameworkRunRequest": ("legal_agent_framework.runner", "FrameworkRunRequest"),
    "FrameworkRunResponse": ("legal_agent_framework.runner", "FrameworkRunResponse"),
    "run_framework_turn": ("legal_agent_framework.runner", "run_framework_turn"),
    # tracing
    "TRACE_ID_KEY": ("legal_agent_framework.tracing", "TRACE_ID_KEY"),
    "TRACE_SEQ_KEY": ("legal_agent_framework.tracing", "TRACE_SEQ_KEY"),
    "TRACE_EVENTS_KEY": ("legal_agent_framework.tracing", "TRACE_EVENTS_KEY"),
    "TraceEvent": ("legal_agent_framework.tracing", "TraceEvent"),
    "create_trace_event": ("legal_agent_framework.tracing", "create_trace_event"),
    "log_trace_event": ("legal_agent_framework.tracing", "log_trace_event"),
    "replay_trace_events": ("legal_agent_framework.tracing", "replay_trace_events"),
    "extract_trace_state": ("legal_agent_framework.tracing", "extract_trace_state"),
    # providers
    "StageProvider": ("legal_agent_framework.providers", "StageProvider"),
    "ToolProvider": ("legal_agent_framework.providers", "ToolProvider"),
    "register_stage_provider": ("legal_agent_framework.providers", "register_stage_provider"),
    "get_stage_provider": ("legal_agent_framework.providers", "get_stage_provider"),
    "has_stage_provider": ("legal_agent_framework.providers", "has_stage_provider"),
    "resolve_stage_provider": ("legal_agent_framework.providers", "resolve_stage_provider"),
    "register_tool_provider": ("legal_agent_framework.providers", "register_tool_provider"),
    "get_tool_provider": ("legal_agent_framework.providers", "get_tool_provider"),
    "has_tool_provider": ("legal_agent_framework.providers", "has_tool_provider"),
    "resolve_tool_provider": ("legal_agent_framework.providers", "resolve_tool_provider"),
}

__all__ = sorted(_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module_name, attr_name = _EXPORTS[name]
    module = importlib.import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
