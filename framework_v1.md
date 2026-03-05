# law_framework v0.1 Design Document

## 1. Document Info
- Version: v0.1
- Status: Active implementation draft
- Author: Kevin
- Created: 2026-02-27
- Last Updated: 2026-02-27
- Related Repository: `law-agent-framework`
- Related Branch: `main`

## 2. Background
- Current project: `law_agent` (Australian legal assistant app using FastAPI + LangGraph + CopilotKit).
- Current pain points:
  - Business policy and runtime concerns were mixed into app-specific stage code.
  - Transport coupling (CopilotKit context assumptions) limited reuse.
  - Provider switching and framework extraction paths were unclear.
- Why abstract a framework layer now:
  - Reuse the same orchestration rails in this app first.
  - Then extract to a standalone package without rewriting stage logic.
- Expected business value:
  - Faster bootstrapping of new legal agent variants.
  - Better policy/validation consistency and traceability.
  - Lower integration cost for non-CopilotKit frontends.

## 3. Goals and Non-Goals

### 3.1 Goals
1. Define a reusable orchestration abstraction for legal workflows.
2. Keep the execution model as “controlled outer rails + autonomous inner loop”.
3. Migrate incrementally without breaking current behavior.
4. Provide auditable, replayable, testable execution traces.

### 3.2 Non-Goals
1. Rewriting the underlying LLM/graph engine.
2. Covering every legal sub-domain in v0.1.
3. Building full multi-tenant platform capabilities in v0.1.

## 4. Design Principles
1. Compliance first: safety routing, human escalation, and disclaimers are non-bypassable.
2. Control first: critical workflow decisions are explicit in policy.
3. Incremental migration: wrap existing flows before replacing internals.
4. Observability first: every step has trace data and decision rationale.
5. Low coupling: business rules are decoupled from the underlying framework/runtime.

## 5. Current System Baseline (As-Is)
- Entry flow:
  - Chat/analysis: `initialize -> safety_check -> chat_response -> END` (or `escalation_response -> END`).
  - Brief: `initialize -> brief_check_info -> brief_ask_questions|brief_generate -> END`.
  - Shared runtime wrapper is now applied to all stage nodes.
- Key nodes:
  - `initialize`, `safety_check`, `escalation_response`, `chat_response`,
    `brief_check_info`, `brief_ask_questions`, `brief_generate`.
  - Stage nodes are resolved through a stage provider registry, not hardcoded imports.
- Key tools:
  - Tool access is resolved via tool provider registry (default + demo providers available).
  - Default app tools still include legal lookup, case-law search, lawyer finder, and document analysis.
- Existing safety mechanisms:
  - Stage-level safety routing via `safety_check`.
  - Framework policy hooks (`before_stage`, `before_output`) with rules P-001/P-002/P-003 implemented.
  - Enforce switches exist via env flags; default behavior remains observe/warn aligned.
  - Structured trace events are emitted with `trace_id` + ordered sequence.
- Known issues:
  - Standalone package is extracted in-repo, but not yet published/versioned as an external dependency.
  - Package dependency is local editable path today; release/version strategy for external consumers is not finalized.
  - Some app modules still directly depend on app config/runtime concerns.
  - Policy catalog includes planned rules (P-004/P-005) not fully enforced in current runtime behavior.

## 6. Target Architecture (To-Be)

### 6.1 Modules
- `contracts`: context, stage result, decision types.
- `policy_engine`: hard-rule checks and blocking.
- `validators`: output structure and compliance validation.
- `runtime_wrapper`: unified invoke/stream/retry/checkpoint entry point.
- `stages/*`: business-stage implementations (intake/research/synthesis/etc).

### 6.2 Execution Model
1. Hard outer track: `intake -> safety -> fact-gap -> research -> synthesis -> validate -> deliver`.
2. Autonomous inner loop: allow agent-driven tool sequencing inside `research`.
3. Stage-to-stage state transfer through a unified `LawContext`.

## 7. Core Contracts

### 7.1 LawContext (Suggested Fields)
- session_id
- user_query
- user_state
- facts
- citations
- deadlines
- risk_flags
- escalation_required
- metadata

### 7.2 StageResult (Suggested Fields)
- updates
- decision (`continue` / `ask_user` / `escalate` / `block` / `end`)
- reason
- telemetry

### 7.3 PolicyHook (Suggested Hooks)
- before_stage
- before_tool
- after_tool
- before_output

## 8. Policy Rule Catalog (v0.1)

| Rule ID | Rule | Trigger | Action | Severity |
|---|---|---|---|---|
| P-001 | State/jurisdiction must be selected before legal conclusions | `user_state` is empty | `ask_user` | high |
| P-002 | High-risk content must escalate | safety high-risk matched | `escalate` | critical |
| P-003 | No conclusion without citations | citations empty | `block/retry` | high |
| P-004 | Deadline-related scenarios must include deadlines | deadline scenario detected | `block/retry` | high |
| P-005 | Required disclaimer must be present | disclaimer missing | `block/retry` | medium |

## 9. Output Validation
- V-001: Structure completeness (all required fields present).
- V-002: Citation validity (source format and traceability).
- V-003: Deadline completeness (date, consequence, recommended action).
- V-004: Compliance wording (disclaimer and non-legal-advice language).
- V-005: Uncertainty expression (no guaranteed-outcome wording).

## 10. Migration Plan

### 10.1 Phase 1 (No Behavior Change)
- Integrate `runtime_wrapper`.
- Integrate `policy_engine` in observe-only mode.
- Integrate `validators` in warn-only mode.
- Status: Completed in current codebase.

### 10.2 Phase 2 (Control Enforcement)
- Enable blocking for P-001/P-002/P-003.
- Apply retry/escalate on high-risk or no-citation outputs.
- Status: Partially implemented.
  - Enforce flags exist and targeted enforcement works.
  - Default production posture remains non-breaking (observe/warn unless enabled).

### 10.3 Phase 3 (Module Replacement)
- Gradually migrate existing analysis path into `stages/*`.
- Keep old-path feature flags for rollback safety.
- Status: In progress.
  - Providers and transport adapters are extracted.
  - Standalone package now exists at `packages/legal-agent-framework/src/legal_agent_framework`.
  - App now imports `legal_agent_framework` directly.
  - Legacy `backend/app/framework` shim layer has been removed.
  - Docker build path for local editable package dependency has been validated.

### 10.4 Phase Alignment Summary
1. Implementation is currently following this phased plan.
2. Sequence being used: Phase 1 done -> Phase 2 controlled rollout -> Phase 3 extraction.
3. Immediate next step: finalize public API/versioning and publish/distribute package beyond local editable dependency.

## 11. Testing and Evaluation

### 11.1 Regression Suite
- Number of scenarios: 81 tests passing in latest local run.
- Scenario categories:
  - Framework runtime and runner contract.
  - Provider registry and provider switching.
  - Request context normalization/adapters.
  - Conversational and brief flow regressions.
- Data source:
  - Repository test fixtures/mocks.
  - Deterministic demo providers for transport/provider contract tests.

### 11.2 Core Metrics
- Escalation precision/recall
- Citation completeness rate
- Critical fact omission rate
- Average response latency
- Replayability coverage for failures

### 11.3 Go/No-Go Criteria
- Metric thresholds:
- Mandatory pass rules:
- Release gates:

## 12. Observability and Audit
- Trace ID conventions:
  - UUID-style `trace_id` propagated per run/turn.
  - Existing trace can be continued via `/framework/run` payload (`trace_id`, `trace_events`).
- Event log schema:
  - Core fields: `trace_id`, `seq`, `stage`, `event_type`, `payload`, `timestamp_utc`.
  - Event ordering is deterministic by `seq`.
- Decision log schema:
  - Policy hits include rule id, severity, action, message, and details.
  - Validator issues include validator id, severity, and details.
- Sensitive data redaction policy:
  - Not finalized yet; currently logs should avoid raw sensitive documents where possible.
- Retention period:
  - TBD; to be aligned with deployment/audit policy before GA.

## 13. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation | Owner |
|---|---|---|---|---|
| Model behavior drift | High | Medium | stronger validators + regression suite | |
| Over-blocking by rules | Medium | Medium | feature flags + human review fallback | |
| Performance regression | Medium | Low | staged load testing + caching | |

## 14. Release Plan
- v0.1-alpha:
  - In-app framework integration complete, tests green.
  - Direct package consumption (`legal_agent_framework`) and Docker build verified.
- v0.1-beta:
  - Standalone package extracted and consumed by this app.
  - Stable public contracts for runtime, providers, and tracing.
- v0.1-ga:
  - Production hardening, docs, and versioned release policy.
- Rollback strategy:
  - Keep app-side default providers and env-based feature flags to revert to safer modes quickly.

## 15. Open-Source Plan (Optional)
- Planned repository name:
- License:
- Public API stability policy:
- Example application(s):
- Documentation site:

## 16. Open Questions
1. What is the minimum public API surface for the standalone package v0.1?
2. Which policy rules (P-004/P-005) should become enforce-on by default at beta?
3. What trace retention/redaction policy is acceptable for production compliance?

## 17. Decision Log (ADR)
- ADR-001: Use incremental wrapper-first migration instead of full graph rewrite.
- ADR-002: Decouple transport with normalized request context and adapters.
- ADR-003: Use provider registries (stage/tool) for app-specific pluggability and extraction readiness.
