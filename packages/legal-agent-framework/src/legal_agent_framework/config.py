"""Framework-level feature flag configuration."""

import os


def _parse_csv_env(name: str) -> set[str]:
    """Parse a comma-separated env var into an uppercase set."""
    value = os.environ.get(name, "")
    if not value:
        return set()
    return {
        item.strip().upper()
        for item in value.split(",")
        if item.strip()
    }


def _parse_bool_env(name: str, default: bool = False) -> bool:
    """Parse common boolean env strings."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_optional_string_env(name: str) -> str | None:
    """Parse optional string env var (empty -> None)."""
    value = os.environ.get(name, "")
    cleaned = value.strip()
    return cleaned if cleaned else None


# Policy enforcement flags (Phase 2 switchboard)
LAW_FRAMEWORK_ENFORCE_ALL_POLICIES = _parse_bool_env(
    "LAW_FRAMEWORK_ENFORCE_ALL_POLICIES",
    default=False,
)
LAW_FRAMEWORK_POLICY_ENFORCE_RULES = _parse_csv_env(
    "LAW_FRAMEWORK_POLICY_ENFORCE_RULES",
)


# Validator enforcement flags (kept off for now, ready for later phases)
LAW_FRAMEWORK_ENFORCE_ALL_VALIDATORS = _parse_bool_env(
    "LAW_FRAMEWORK_ENFORCE_ALL_VALIDATORS",
    default=False,
)
LAW_FRAMEWORK_VALIDATOR_ENFORCE_IDS = _parse_csv_env(
    "LAW_FRAMEWORK_VALIDATOR_ENFORCE_IDS",
)


def get_configured_stage_provider_name() -> str | None:
    """Read preferred stage provider name from env at runtime."""
    return _parse_optional_string_env("LAW_FRAMEWORK_STAGE_PROVIDER")


def get_configured_tool_provider_name() -> str | None:
    """Read preferred tool provider name from env at runtime."""
    return _parse_optional_string_env("LAW_FRAMEWORK_TOOL_PROVIDER")
