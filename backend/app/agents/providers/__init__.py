"""Default app provider registrations for stages and tools."""


def ensure_default_stage_provider_registered() -> None:
    """Idempotently register app default stage provider."""
    from app.agents.providers.default_stage_provider import register_default_stage_provider

    register_default_stage_provider()


def ensure_default_tool_provider_registered() -> None:
    """Idempotently register app default tool provider."""
    from app.agents.providers.default_tool_provider import register_default_tool_provider

    register_default_tool_provider()


def ensure_builtin_stage_providers_registered() -> None:
    """Register all built-in stage providers (default + demo)."""
    ensure_default_stage_provider_registered()

    from app.agents.providers.demo_stage_provider import register_demo_stage_provider

    register_demo_stage_provider()


def ensure_builtin_tool_providers_registered() -> None:
    """Register all built-in tool providers (default + demo)."""
    ensure_default_tool_provider_registered()

    from app.agents.providers.demo_tool_provider import register_demo_tool_provider

    register_demo_tool_provider()


def ensure_default_providers_registered() -> None:
    """Idempotently register app default providers."""
    ensure_builtin_stage_providers_registered()
    ensure_builtin_tool_providers_registered()


__all__ = [
    "ensure_default_stage_provider_registered",
    "ensure_default_tool_provider_registered",
    "ensure_builtin_stage_providers_registered",
    "ensure_builtin_tool_providers_registered",
    "ensure_default_providers_registered",
]
