# legal-agent-framework

Reusable orchestration primitives for legal AI agents.

## Scope

- Core contracts (`LawContext`, `StageResult`)
- Policy engine and validators
- Runtime wrapper with structured tracing
- Transport-neutral runner models + execution helper
- Stage/tool provider registries

## Notes

- This package is extracted from the app-local `app.framework` module.
- `run_framework_turn(...)` requires an explicit compiled graph argument.
  The package does not import app-specific graph implementations.
