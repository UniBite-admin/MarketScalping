# Safety ↔ Orchestrator Integration Design (STEP 5D)

Status: DESIGN ONLY — no runtime, workflow, policy, test, or trading code changes in this step.

## 1. Objective

This design defines the smallest correct integration between the existing orchestrator workflow and the Safety agent while preserving the authority model already defined by the active contracts, workflow, and policy layer.

The design is intentionally minimal and conservative:

- Orchestrator owns workflow state, lifecycle, retries, escalation, persistence, and transition enforcement.
- Safety owns independent safety verification, safety findings, evidence, and a safety recommendation.
- Safety may block or require human approval; it does not mutate workflow state directly.
- The Orchestrator consumes the Safety result and applies the workflow consequence according to the existing state machine.
- The design reuses the existing `AgentRuntime`, `InvocationRequest`, `AgentResult`, `TaskStore`, policy evaluation, and canonical artifact flow. No new cache, no new state store, no new service layer, no provider integration.

The integration must remain strictly safer than QA: Safety must be able to stop progression even when QA passes.

## 2. Current Architecture

The active architecture already establishes the intended boundaries:

- `.agent/contracts/safety.contract.json` defines the Safety mission, required inputs, output expectations, forbidden actions, and escalation conditions.
- `.agent/contracts/orchestrator.contract.json` defines Orchestrator as the workflow authority with read-only repository access and artifact validation responsibilities.
- `.agent/workflows/workflow.json` defines the live transition chain: `DEVELOPMENT -> CI -> QA -> SAFETY ...`.
- `.agent/policies/policies.json` contains deterministic safety and approval policies, including direct blocks for live trading, withdrawals, and protected-branch merge behavior.
- `.agent/guidelines.md` reinforces the precedence order and the authority model: Safety first, then correctness, then verification, then speed.
- `docs/agentic_architecture_design.md` confirms the partitioning between Orchestrator, Developer, Architect, QA, and Safety.
- `docs/qa_orchestrator_integration_design.md` establishes the design pattern for AgentRuntime-based agent integration with Orchestrator-managed lifecycle and artifact validation.
- `tools/agent_runtime.py` already provides the execution envelope (`InvocationRequest`, `AgentResult`, `run_id` cache semantics).
- `tools/orchestrator_core.py` already has the architectural pattern for orchestrating deterministic runtime invocations, artifact validation, and state transitions.
- `tools/qa_agent.py` shows the precedent for an independent verification executor producing canonical artifacts and leaving workflow state decisions to Orchestrator.

This Safety integration should therefore mirror the QA integration pattern rather than invent a different lifecycle or authority model.

## 3. Authority Boundaries

### 3.1 Orchestrator owns

- workflow state
- routing and lifecycle management
- retries and escalation policy
- artifact validation
- persistence in `TaskStore`
- transition decisions
- human approval state transitions
- policy evaluation and enforcement of allowed transitions

### 3.2 Safety owns

- safety verification
- safety findings and blockers
- safety evidence classification
- safety decision
- severity and blocking assessment
- recommendation of mitigations or required human approval

### 3.3 Safety does not own

- workflow transitions
- direct merge authority
- direct deployment authority
- live trading enablement
- credential provisioning
- risk-limit mutation
- withdrawal permission grant
- production approval by itself

### 3.4 Orchestrator must not reinterpret the technical safety assessment

The Orchestrator must consume Safety's output as a technical decision and apply the workflow consequence. The Orchestrator must not silently reinterpret:

- `FAIL` as `PASS`
- `BLOCKED` as allowed progression
- `INCONCLUSIVE` as safe to proceed
- `REQUIRE_HUMAN_APPROVAL` as autonomous approval

This is a required boundary: Safety decides safety; Orchestrator decides workflow progression.

## 4. Safety Inputs

The canonical Safety input set should be minimal, explicit, and contract-aligned. The current Safety contract is narrower than QA and does not require the entire QA bundle. The minimal design is:

Required canonical inputs:

- `task_record`
- `implementation_artifact`
- `repository_context`
- `repository_revision`
- `qa_result`
- `test_manifest`
- `run_id`

Optional but acceptable when relevant:

- `adr`
- `architecture_result`
- `policy_context`
- `safety_history`

Safety should not require or consume unrelated runtime metadata. The Safety agent should verify the actual safety-relevant facts needed for a safety assessment and reject missing, malformed, or untrusted evidence.

### 4.1 Why these inputs

- `task_record`: identifies the task and task ownership/auth status at the workflow boundary.
- `implementation_artifact`: provides the implementation summary, changed files, and any known limitations/blockers.
- `repository_context`: provides repository state and file scope relevant to risk review.
- `repository_revision`: protects identity and allows the Safety gate to verify the correct code snapshot.
- `qa_result`: gives the current verification status and any QA defect evidence relevant to safety.
- `test_manifest`: captures actual test evidence that may bear on safety-sensitive areas.
- `run_id`: preserves idempotency semantics for runtime reuse.

### 4.2 Input boundaries

Safety should not require:

- live exchange credentials
- production secrets
- live trading activation flags
- risk-limit override settings
- direct workflow transition requests

If such values appear, Safety should reject the request as a safety-unsafe payload rather than attempting to interpret it.

## 5. Safety Outputs

The canonical Safety output should prefer the existing contract vocabulary and avoid redundant artifacts.

### 5.1 Canonical required output

A single canonical `safety_report` artifact is sufficient for the minimal design. This aligns with the existing contract, which defines the expected outputs as `safety_report` and `blocking_reasons_if_any` and allows `safety_report` and `risk_assessment` artifact types.

The `safety_report` content should include:

- `task_id`
- `run_id`
- `repository_revision`
- `decision`
- `severity`
- `evidence`
- `findings`
- `blocking_status`
- `limitations`
- `recommended_mitigations`
- `requires_human_approval` (boolean)

This is the authoritative Safety decision envelope. It must not be duplicated into a second `validation_result` artifact.

### 5.2 Supporting evidence

If a separate `risk_assessment` artifact is desirable for richer risk context, it should remain optional and supporting-only. It must not become a second authoritative decision artifact. The minimal correct design keeps one authoritative Safety decision artifact: `safety_report`.

## 6. Decision Model

The Safety decision model should be stricter than QA and should include explicit approval states.

Recommended decisions:

- `PASS`: no safety blockers; no unresolved safety concerns; execution may proceed if the workflow allows it.
- `FAIL`: safety-critical issue identified; non-advancing state required.
- `BLOCKED`: required evidence, task state, or safety evidence is missing or invalid; non-advancing state required.
- `INCONCLUSIVE`: evidence is insufficient to conclude safety; non-advancing state required pending more evidence.
- `REQUIRE_HUMAN_APPROVAL`: technically reviewable but requires explicit human decision before enabling risky states or actions.

### 6.1 Why `REQUIRE_HUMAN_APPROVAL` is required

Safety must distinguish between:

- technically safe → `PASS`
- unsafe / forbidden → `FAIL`
- insufficient evidence → `INCONCLUSIVE`
- action is acceptable only with human decision → `REQUIRE_HUMAN_APPROVAL`

This is necessary because some changes are not inherently forbidden but still require explicit human approval, such as:

- paper-to-live transition
- changing risk limits
- changing daily loss limits
- changing maximum position size
- API permission changes
- deployment
- major safety architecture changes

### 6.2 Safety decisions are still advisory in one sense, but workflow-authoritative in another

Safety determines the safety assessment and technical blockers. Orchestrator retains the workflow authority: it applies the state transition based on the decision and the current workflow state. Safety must not directly mutate workflow state or bypass an approval gate.

## 7. Workflow Integration

The active workflow remains the canonical state machine:

```
DEVELOPMENT
    ↓
CI
    ↓
QA
    ↓
SAFETY
    ↓
HUMAN_APPROVAL / MERGE / next controlled state
```

This design does not modify the workflow. Instead, it defines the expected minimal integration semantics:

1. Task reaches `QA` and receives a valid QA decision.
2. Orchestrator validates the QA result, required artifacts, and repository revision.
3. Orchestrator advances the task to `SAFETY` only when the task is in the valid workflow state and the required artifacts are present.
4. Orchestrator creates an `InvocationRequest` with `agent_role = "SAFETY"` and the canonical Safety input bundle.
5. Orchestrator calls `AgentRuntime.invoke(req)` using a `SafetyExecutor` implementation.
6. `AgentRuntime` returns an `AgentResult`.
7. Orchestrator validates the returned Safety artifact(s) and extracts the canonical `safety_report`.
8. Orchestrator applies the decision to workflow state:
   - `PASS`: continue to the next eligible workflow gate, subject to workflow rules and policy checks.
   - `FAIL`: block progression into a non-advancing state.
   - `BLOCKED`: block progression.
   - `INCONCLUSIVE`: hold and require additional evidence or escalation.
   - `REQUIRE_HUMAN_APPROVAL`: route to `HUMAN_APPROVAL`, not silent progression.

### 7.1 Future workflow change if needed

If a future implementation requires a stricter workflow for Safety-specific gating, the design should be updated in a dedicated workflow change document. This step does not change the current workflow; it documents the required future change only if necessary.

## 8. Human Approval Gates

Safety may identify conditions that must never be autonomously approved. The design must preserve the human approval boundary:

- enabling live trading
- changing risk limits
- changing maximum position size
- changing daily loss limits
- changing API permissions
- enabling withdrawal capability
- production deployment
- changing paper/live split behavior
- kill-switch or emergency-stop behavior changes
- major safety architecture changes

The correct pattern is:

```
Safety recommendation
    ↓
Orchestrator
    ↓
Human approval gate
```

This preserves the authority rule: Safety can recommend and block; Human approves high-risk changes; Orchestrator enforces the gate.

Safety must never bypass human approval by transforming a `REQUIRE_HUMAN_APPROVAL` result into direct progression.

## 9. Failure / Recovery

The design reuses the existing AgentRuntime and Orchestrator retry/escalation model.

### 9.1 Failure modes

- SafetyExecutor failure → treated as a runtime failure; Orchestrator blocks progression and follows existing retry/escalation policy.
- timeout → retry/escalation according to the current orchestrator policy limits; no new timeout engine.
- malformed safety artifact → blocked as malformed; no progression.
- missing required evidence → blocked.
- `FAIL` → no progression.
- `BLOCKED` → no progression.
- `INCONCLUSIVE` → no silent progression; hold or retry/escalate according to policy.
- `REQUIRE_HUMAN_APPROVAL` → route to `HUMAN_APPROVAL` only.
- duplicate invocation → same `run_id` + same logical inputs may reuse cached result under the same semantics.
- same `run_id` + changed inputs → block before runtime cache reuse.

### 9.2 Recovery model

The design does not invent a second recovery system. It reuses:

- `AgentRuntime` result caching semantics
- `TaskStore` artifact persistence
- orchestrator retry limits
- workflow transition blocking
- escalation behavior already present in `Orchestrator.transition_task()`

## 10. Idempotency

This Safety design reuses the same semantic principle already established for QA:

```
same run_id + same logical Safety inputs
    → idempotent reuse

same run_id + materially different Safety inputs
    → BLOCK before runtime cache reuse

new run_id
    → fresh invocation
```

### 10.1 Semantic fingerprinting requirement

If Safety requires a semantic fingerprint, it should follow the same design pattern already established for QA:

- canonical projection of materially relevant Safety inputs
- include only fields that materially affect safety assessment
- exclude incidental metadata such as artifact IDs, timestamps, producer metadata, and runtime execution metadata
- hash the canonical representation deterministically with `json.dumps(..., sort_keys=True, separators=(",", ":"))` plus SHA-256
- never include `run_id` in the semantic fingerprint

### 10.2 Why the pattern is required

This small design ensures Safety does not accidentally reuse a stale safety verdict when the underlying implementation or repository state changed under the same `run_id`.

## 11. Persistence

Persistence remains in the existing TaskStore and artifact model.

Required persisted elements:

- task record and current state
- invocation_record for the Safety agent
- `safety_report` artifact
- supporting evidence or `risk_assessment` artifact if used
- workflow history entries
- retry and escalation metadata

No new database, no new state store, no new cache, no new artifact system.

## 12. Security Boundary

This integration does not grant Safety any live trading or production control capability.

Specifically, Safety remains isolated from:

- live exchange access
- live credentials
- withdrawal capability
- order placement
- risk mutation
- live-mode activation
- production deployment
- merge authority

Repository read access remains separate from live-money operation capability. Access to repository state does not imply access to live secrets, live exchange, or live trading operations.

## 13. Independence

Safety must remain independent from Developer and QA.

Safety must not simply accept:

```
Developer says safe
QA says PASS
therefore Safety says PASS
```

That pattern is not a valid safety assessment.

Safety must perform its own evidence-based safety evaluation using the input artifacts and repository state, with explicit findings and blockers. Developer claims and QA status are inputs, not final authority.

## 14. Simplicity

The minimal architecture should look like this:

```
Orchestrator
    → AgentRuntime
    → SafetyExecutor
    → safety_report artifact
    → TaskStore persistence
    → workflow decision
```

This design intentionally avoids:

- new messaging infrastructure
- event buses
- service mesh
- additional persistence layers
- extra orchestration frameworks
- provider or model integration
- LLM-driven decision logic embedded in the workflow

This is the smallest architecture satisfying the required safety gate semantics and authority model.

## 15. Implementation Plan

This is a design-only step; no implementation is performed here. The intended implementation sequence, if executed later, is:

1. Align the Safety input bundle to the minimal canonical set already described above.
2. Define the canonical `safety_report` artifact shape compatible with `.agent/contracts/safety.contract.json`.
3. Implement a `SafetyExecutor` that follows the same `AgentRuntime` contract pattern used by Architect, Developer, and QA.
4. Orchestrator creates the `InvocationRequest`, persists the `invocation_record`, and validates the returned Safety output envelope.
5. Orchestrator then evaluates the safety decision and applies the corresponding state transition or approval gate.
6. Add only the minimal idempotency guard for stale `run_id` reuse, following the same pattern already established for QA.
7. Verify via focused tests and contract validation, without broadening scope or introducing new capabilities.

## 16. Open Questions

The current design is sufficient for the minimal Safety gate, but the following questions remain for future implementation and future review:

- Should `risk_assessment` remain an optional supporting artifact or be folded into `safety_report` only?
- Should `REQUIRE_HUMAN_APPROVAL` be represented as a separate workflow state or as a safety decision state held by Orchestrator?
- How much of the repository state is required for a minimal Safety evidence bundle in the first implementation?
- What is the exact evidence threshold for `INCONCLUSIVE` in a real workflow?
- Should human approval be a distinct workflow gate that is separate from `HUMAN_APPROVAL` in the existing state machine, or should the current state remain the canonical gate?

## 17. Explicit Non-Goals

This design explicitly does not do any of the following:

- introduce a new database or cache
- implement live trading support
- provide exchange connectivity
- grant withdrawal or credentials access
- allow direct merge or deployment
- implement provider/model integration
- add workflow mutations or bypasses
- create a second safety state machine
- add a new artifact system beyond the existing TaskStore and canonical agent output artifacts
- modify trading, execution, risk, or accounting code
- implement Safety in runtime code during this design phase

## 18. Required Design Conclusion

The correct minimum pattern is:

```
Orchestrator
    ↓
AgentRuntime
    ↓
SafetyExecutor
    ↓
canonical safety_report artifact
    ↓
Orchestrator workflow evaluation
    ↓
human approval or block when required
```

Safety remains a verification and blocker gate, not a workflow-authority bypass. The Orchestrator remains the workflow authority and the sole actor allowed to move state, enforce retries, and apply human approval gates.
