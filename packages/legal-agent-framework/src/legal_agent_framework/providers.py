"""Provider registries for stages and tools.

Framework core consumes these registries without importing app-specific
implementations. Apps register concrete providers at startup/import time.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Protocol


NodeHandler = Callable[..., Any]
RouteHandler = Callable[..., Any]
logger = logging.getLogger(__name__)


class StageProvider(Protocol):
    """Stage provider contract."""

    def get_stage_nodes(self) -> dict[str, NodeHandler]:
        """Return stage node handlers keyed by stage name."""

    def get_route_handlers(self) -> dict[str, RouteHandler]:
        """Return optional route handlers keyed by route name."""


class ToolProvider(Protocol):
    """Tool provider contract."""

    def get_tools(self, context: dict[str, Any] | None = None) -> list[Any]:
        """Return tool objects for the active context."""


class StageProviderRegistry:
    """Registry for named stage providers."""

    def __init__(self):
        self._providers: dict[str, StageProvider] = {}
        self._default_name: str | None = None

    def register(self, name: str, provider: StageProvider, *, is_default: bool = False) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("Stage provider name cannot be empty.")
        self._providers[key] = provider
        if is_default or self._default_name is None:
            self._default_name = key

    def get(self, name: str | None = None) -> StageProvider:
        key = (name or self._default_name or "").strip().lower()
        if not key or key not in self._providers:
            available = ", ".join(sorted(self._providers.keys())) or "<none>"
            raise KeyError(f"Stage provider '{name}' is not registered. Available: {available}")
        return self._providers[key]

    def has(self, name: str) -> bool:
        return name.strip().lower() in self._providers

    def list_names(self) -> list[str]:
        return sorted(self._providers.keys())


class ToolProviderRegistry:
    """Registry for named tool providers."""

    def __init__(self):
        self._providers: dict[str, ToolProvider] = {}
        self._default_name: str | None = None

    def register(self, name: str, provider: ToolProvider, *, is_default: bool = False) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("Tool provider name cannot be empty.")
        self._providers[key] = provider
        if is_default or self._default_name is None:
            self._default_name = key

    def get(self, name: str | None = None) -> ToolProvider:
        key = (name or self._default_name or "").strip().lower()
        if not key or key not in self._providers:
            available = ", ".join(sorted(self._providers.keys())) or "<none>"
            raise KeyError(f"Tool provider '{name}' is not registered. Available: {available}")
        return self._providers[key]

    def has(self, name: str) -> bool:
        return name.strip().lower() in self._providers

    def list_names(self) -> list[str]:
        return sorted(self._providers.keys())


_stage_registry = StageProviderRegistry()
_tool_registry = ToolProviderRegistry()


def register_stage_provider(name: str, provider: StageProvider, *, is_default: bool = False) -> None:
    _stage_registry.register(name, provider, is_default=is_default)


def get_stage_provider(name: str | None = None) -> StageProvider:
    return _stage_registry.get(name)


def has_stage_provider(name: str) -> bool:
    return _stage_registry.has(name)


def resolve_stage_provider(preferred_name: str | None = None) -> StageProvider:
    """Resolve stage provider with fallback to registry default.

    If `preferred_name` is unknown, this logs a warning and falls back
    to the default provider.
    """
    if preferred_name:
        try:
            return _stage_registry.get(preferred_name)
        except KeyError:
            logger.warning(
                "Unknown stage provider '%s'. Falling back to default. Available: %s",
                preferred_name,
                ", ".join(_stage_registry.list_names()) or "<none>",
            )
    return _stage_registry.get(None)


def register_tool_provider(name: str, provider: ToolProvider, *, is_default: bool = False) -> None:
    _tool_registry.register(name, provider, is_default=is_default)


def get_tool_provider(name: str | None = None) -> ToolProvider:
    return _tool_registry.get(name)


def has_tool_provider(name: str) -> bool:
    return _tool_registry.has(name)


def resolve_tool_provider(preferred_name: str | None = None) -> ToolProvider:
    """Resolve tool provider with fallback to registry default.

    If `preferred_name` is unknown, this logs a warning and falls back
    to the default provider.
    """
    if preferred_name:
        try:
            return _tool_registry.get(preferred_name)
        except KeyError:
            logger.warning(
                "Unknown tool provider '%s'. Falling back to default. Available: %s",
                preferred_name,
                ", ".join(_tool_registry.list_names()) or "<none>",
            )
    return _tool_registry.get(None)
