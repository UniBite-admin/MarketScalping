# Full Agentic End-to-End Integration Design (STEP 5E)

Status: DESIGN ONLY

This document defines the smallest correct end-to-end workflow using the repository’s existing architecture, contracts, policies, workflow, runtime, and integration patterns. It does not implement any runtime or workflow changes, does not modify any production code, and does not add any new dependency, state store, or duplicate artifact model.

The design must remain faithful to the current repository evidence:

- `.agent/contracts/*` define the authoritative agent contracts and canonical artifact vocabulary.
- `.agent/policies/policies.json` defines deterministic guards and approval conditions.
- `.agent/workflows/workflow.json` defines the live transition model.
- `.agent/guidelines.md` defines the operational precedence and authority model.
- `tools/agent_runtime.py` defines the runtime facade and `run_id` idempotency model.
- `tools/orchestrator_core.py` defines the workflow authority, task persistence, retries, and artifact validation logic.
- the existing Architect/Developer/QA/Safety implementations define the actual accepted local execution pattern.

---

## 1. End-to-End Flow

The end-to-end flow is the existing minimal workflow, preserved without redesign:

TASK
→ ORCHESTRATOR
→ ARCHITECT
→ READY
→ DEVELOPER
→ CI
→ QA
→ SAFETY
→ HUMAN APPROVAL
→ MERGE GATE

This is the smallest correct integration because it matches the repository’s active workflow contract and the existing implementation pattern already validated for each component pair.

### 1.1 Ownership by stage

- Orchestrator owns:
  - task lifecycle and state transitions
  - policy evaluation
  - artifact validation and persistence
  - run_id assignment and semantic fingerprint validation
  - retry and escalation logic
  - human approval enforcement
  - workflow routing between stages

- Architect owns:
  - architecture assessment and technical proposal
  - affected components, risks, safety implications, acceptance criteria
  - ADR proposal or ADR reference when required
  - developer-ready specification
  - no code implementation and no workflow ownership

- Developer owns:
  - implementation within authorized scope
  - generated `implementation_artifact`
  - generated `test_manifest`
  - no autonomous state transitions or approval authority

- CI owns:
  - execution of the developer’s validation commands
  - evidence generation for actual command results
  - not the same as a QA or Safety decision

- QA owns:
  - independent verification
  - `qa_result`
  - `defect_report`
  - evidence-based correctness decision
  - no workflow ownership

- Safety owns:
  - independent safety verification
  - `safety_result`
  - safety findings, blockers, severity, and required human approval conditions
  - no workflow ownership and no approval bypass

- Human owns:
  - explicit approval before high-risk and protected transitions
  - final authority for protected merge and release decisions

### 1.2 Required artifact sequence

The canonical E2E artifact chain is:

- `task_record`
- `architecture_result`
- `adr` / `adr_proposal` / `adr_reference` when required
- `implementation_artifact`
- `test_manifest`
- `ci_results` (evidence only, not a replacement for QA/Safety)
- `qa_result`
- `defect_report`
- `safety_result`
- `human_approval_record` when required
- `merge_record` when the workflow reaches merge

The repository already defines the required canonical vocabulary. The design must not introduce aliases such as `validation_result`, duplicate QA artifact copies, duplicate safety artifact copies, or a parallel task store.

### 1.3 Where retries happen

Retries happen only in Orchestrator under the existing retry-limit policy (`agent_retry_limits` in `.agent/policies/policies.json`). The design keeps the current pattern:

- runtime execution failure -> Orchestrator increments attempt and blocks or retries
- malformed artifact -> Orchestrator blocks the task and increments failure count
- stale fingerprint / same `run_id` with different logical input -> Orchestrator blocks and does not call the agent again
- retry exhaustion -> Orchestrator escalates to `ESCALATED`

### 1.4 Where escalation happens

Escalation is deterministic and occurs in Orchestrator only:

- retry threshold exceeded
- invalid workflow transition
- policy block without remediation
- persistent malformed/missing artifact
- stale logical identity mismatch
- non-recoverable execution failure
- safety retry limit exceeded

No agent is allowed to escalate itself into a workflow state change.

### 1.5 Where human approval happens

Human approval is distinct and explicit. It occurs only when the workflow requires it, usually after Safety emits `REQUIRE_HUMAN_APPROVAL` or policy requires explicit approval for a high-risk action. The Orchestrator enforces the state transition to `HUMAN_APPROVAL` and awaits the human decision, while preventing any silent bypass.

---

## 2. Authority Model

The current repository already establishes the correct model and this E2E design preserves it.

### 2.1 Orchestrator

Orchestrator is the workflow authority and is responsible for:

- workflow state transitions
- routing to Architect, Developer, QA, and Safety
- persistence of tasks and artifacts in `TaskStore`
- `run_id` and semantic fingerprint enforcement
- retry policy and deterministic escalation
- policy evaluation and guard enforcement
- human approval gate enforcement
- no direct production code modification

### 2.2 Architect

Architect is a read-only analysis and design authority for:

- feasibility and architecture assessment
- affected components and interfaces
- risks and safety implications
- acceptance criteria and developer specification
- ADR generation when required

Architect does not own workflow progression and does not implement code.

### 2.3 Developer

Developer is the implementation authority for approved work only:

- implementation within the authorized scope
- generation of `implementation_artifact` and `test_manifest`
- private isolated worktree/branch semantics according to policy
- no merge or deployment authority
- no autonomous workflow advancement

### 2.4 QA

QA is the independent verification authority for correctness, evidence, and defect identification:

- verifies task requirements and acceptance criteria
- validates architecture alignment and scope
- inspects evidence and tests
- generates `qa_result` and `defect_report`
- `PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE` only

QA does not own workflow state, cannot approve releases, and cannot bypass Safety.

### 2.5 Safety

Safety is the independent safety verification authority for:

- safety-sensitive change detection
- risk review based on repository and QA evidence
- safety blocking and severity classification
- explicit `REQUIRE_HUMAN_APPROVAL` decision when required
- canonical `safety_result`

Safety does not own workflow state transitions, merge authority, deployment authority, or human approval bypass.

### 2.6 Human

Human is the final authority only for high-risk or protected actions such as:

- explicit human approval before any live or release-sensitive action
- merge gate approvals and protected branch execution
- policy-defined high-risk decisions

The human approval record must be explicit and persisted as a workflow artifact or state, not assumed or implied by agent output.

### 2.7 Non-negotiable rule

No agent may become workflow owner. The workflow owner remains Orchestrator, and the human remains the final approval authority for high-risk actions.

---

## 3. Artifact Flow

The canonical artifact chain is not a second data model. It is the existing artifact vocabulary already defined in the contracts and implemented by the local executors.

### 3.1 Canonical artifacts and role ownership

- `task_record`: produced and persisted by Orchestrator; identifies the work record, status, owner, and canonical task identity.
- `architecture_result`: produced by Architect; validates architecture, scope, and operational constraints.
- `adr` / `adr_proposal` / `adr_reference`: produced by Architect when required by architecture or policy; the design does not introduce a second housing system.
- `implementation_artifact`: produced by Developer; declares changed files, implementation status, assumptions, and blockers.
- `test_manifest`: produced by Developer; records executed verification commands and their results.
- `ci_results`: produced by CI; evidence of command execution and pass/fail state, not an independent final approval.
- `qa_result`: produced by QA; independent correctness decision and evidence summary.
- `defect_report`: produced by QA; structured defect list and evidence.
- `safety_result`: produced by Safety; safety decision, severity, evidence, and blocking/approval status.
- `human_approval_record`: produced/accepted by the human approval process; required for high-risk transitions.
- `merge_record`: produced when the human-approved merge action is recorded.

### 3.2 Artifact validity rules

At each transition, the required artifact or artifact bundle is mandatory. The Orchestrator validates the artifact envelope and content before moving the task forward.

The E2E design preserves the repository’s existing validation pattern:

- required envelope fields must be present
- task_id must match the current task
- run_id must match the current invocation identity
- `repository_revision` must match the orchestrator-provided revision
- decision values must be from the canonical vocabulary
- malformed or missing artifacts block progression

### 3.3 Forbidden duplicates

The design explicitly prohibits:

- `validation_result` as a parallel artifact
- duplicate `qa_result` variants
- duplicate `safety_result` variants
- second state store or second workflow ledger
- alternative artifact chain with hidden authoritative copies

Only the canonical artifact names already accepted by the contracts and tested in the local integration flow are valid.

### 3.4 Mandatory artifact set by stage

- ARCHITECTURE stage: `architecture_result` required; `adr` only if required.
- DEVELOPMENT stage: `implementation_artifact` and `test_manifest` required.
- CI stage: `ci_results` as evidence; not a substitute for QA/Safety.
- QA stage: `qa_result` and `defect_report` required.
- SAFETY stage: `safety_result` required.
- HUMAN_APPROVAL stage: explicit approval artifact or approval record required.
- MERGE stage: merge record required if the workflow continues.

---

## 4. State Transitions

The active workflow remains authoritative:

BACKLOG → TRIAGE → ARCHITECTURE → READY → DEVELOPMENT → CI → QA → SAFETY → HUMAN_APPROVAL → MERGE → DEPLOY → MONITOR

The transition path must not be redesigned unless the existing workflow clearly cannot express the needed behavior. The repository’s current workflow and agent contracts already support the required E2E logic without a new state model.

### 4.1 Successful progression

Normal success path:

- Orchestrator creates task
- task advances to `ARCHITECTURE`
- Architect produces `architecture_result`
- Orchestrator transitions to `READY`
- Developer produces `implementation_artifact` and `test_manifest`
- Orchestrator transitions to `CI`
- CI runs and records evidence
- Orchestrator transitions to `QA`
- QA produces `qa_result` and `defect_report`, decision `PASS`
- Orchestrator transitions to `SAFETY`
- Safety produces `safety_result`, decision `PASS`
- If no approval gate is required, Orchestrator continues through the existing merge path or next allowed state

### 4.2 Malformed artifact

Malformed artifact behavior is strict and non-advancing:

- missing required envelope keys -> `BLOCKED`
- wrong artifact type -> `BLOCKED`
- task_id mismatch -> `BLOCKED`
- run_id mismatch -> `BLOCKED`
- repository revision mismatch -> `BLOCKED`
- invalid decision -> `BLOCKED`

The task cannot advance until the artifact is corrected or a new valid invocation is created with a fresh logical fingerprint.

### 4.3 Missing artifact

Missing required artifact handling follows the same rule:

- no `architecture_result` -> block at Architecture/Ready gate
- no `implementation_artifact` -> block at development/CI gate
- no `test_manifest` -> block at CI/QA gate
- no `qa_result` -> block at QA/Safety gate
- no `safety_result` -> block at Safety gate

### 4.4 Agent failure

If an agent execution fails:

- `FAILED`, `TIMED_OUT`, `CANCELLED`, or execution-blocked runtime result is treated as a failed invocation
- Orchestrator increments the attempt counter
- Orchestrator follows retry policy
- after retry limit, Orchestrator transitions to `ESCALATED`

### 4.5 CI failure

CI does not implicitly mean a final pass. The design requires a clear distinction between:

- Developer claim: “I implemented and ran tests.”
- CI evidence: actual command result and exit status.
- QA verification: independent evidence check using canonical artifacts.
- Safety verification: independent risk check and blockers.

If CI fails, the task remains blocked and does not move to QA/Safety approval.

### 4.6 QA FAIL / BLOCKED / INCONCLUSIVE

QA decisions map directly to non-advancing workflow behavior:

- `FAIL`: task blocked; defect documented; retry or escalation depending on policy
- `BLOCKED`: task blocked because required conditions or inputs are missing/invalid
- `INCONCLUSIVE`: task held pending more evidence or escalation

No QA decision may silently bypass Safety or human approval.

### 4.7 Safety FAIL / BLOCKED / INCONCLUSIVE / REQUIRE_HUMAN_APPROVAL

Safety decisions map directly to the workflow authority:

- `FAIL`: block the task from advancing; must not be reinterpreted as safe
- `BLOCKED`: required evidence or task state invalid; hold task
- `INCONCLUSIVE`: hold pending more evidence or escalation
- `REQUIRE_HUMAN_APPROVAL`: route to `HUMAN_APPROVAL` and prevent direct progression

The Safety gate is stricter than QA and is intentionally allowed to stop the workflow even when QA passed.

### 4.8 Human approval granted / rejected

- granted: Orchestrator allows the workflow to continue to the next authorized gate or merge step
- rejected: task remains in `HUMAN_APPROVAL` or returns to a non-advancing state; no automatic retry unless policy explicitly permits a new valid submission

Human approval is a control gate, not a silent pass-through.

### 4.9 Retry exhausted and escalation

When the task hits the configured retry limit:

- Orchestrator records the failure reason and transition to `ESCALATED`
- no further automatic advancement occurs
- investigation or operator action is required

### 4.10 No invented states

The current workflow already expresses the required states. No new states are introduced for this design. If a flow requires more granularity later, it should be added only in a separate, explicit workflow update and only if the current model cannot express the required behavior.

---

## 5. Failure Containment

The E2E design enforces containment at the workflow and artifact boundary so that no agent can silently bypass policy.

### 5.1 Developer cannot bypass QA

Developer produces implementation and test evidence, but the workflow forces the task through QA before later gates. The Orchestrator enforces that `DEVELOPMENT -> CI -> QA` is the required path. There is no direct developer-to-merge path, and no direct developer-to-Safety path unless the task is already in the accepted workflow.

### 5.2 QA cannot bypass Safety

The current workflow requires `QA -> SAFETY` for the risk-sensitive path. There is no valid direct `QA -> MERGE` transition for tasks in the workflow’s safety-sensitive path. The Orchestrator rejects such transitions.

### 5.3 Safety cannot bypass human approval

If Safety returns `REQUIRE_HUMAN_APPROVAL`, Orchestrator must route to `HUMAN_APPROVAL`. Safety cannot convert that condition into release or merge authority. That is explicitly disallowed by the safety contract and policy layer.

### 5.4 Failed artifacts cannot advance workflow

The Orchestrator validates every artifact before it advances the workflow. Any missing, malformed, mismatched, or invalid artifact keeps the task blocked. There is no implicit conversion from a failed artifact to a success state.

### 5.5 Retry loops terminate

The repository already includes retry limits and loop protection. The Orchestrator must enforce a maximum retry count and escalate if it is exceeded. This prevents infinite loops and repeated attempts on a fundamentally invalid artifact or failed gate.

### 5.6 Escalation is deterministic

Escalation is not ad hoc. It is a direct consequence of policy and workflow logic already implemented in `Orchestrator.transition_task()`: retry limit exceeded, loop detection, explicit policy block, invalid state transition, stale fingerprint mismatch. This is deterministic and auditable.

### 5.7 No silent success

No agent can silently cause a successful state transition. The workflow requires artifact validation, policy evaluation, and the appropriate gate to confirm progress. A runtime success result without a valid artifact envelope or contract-compliant decision is not enough to proceed.

---

## 6. Idempotency

The E2E design reuses the repository’s existing semantic invocation identity model without creating a second idempotency system.

### 6.1 Existing model

The runtime model in `tools/agent_runtime.py` already provides:

- `InvocationRequest.run_id`
- `AgentResult.run_id`
- in-memory `AgentRuntime._runs` registry
- idempotent reuse when the same `run_id` is invoked again

The orchestrator adds a semantic fingerprint layer for logically equivalent invocations so that stale or mismatched runs do not silently reuse a result for materially different inputs.

### 6.2 `run_id`

`run_id` is the stable invocation identity. It must remain stable for the same logical action so that a repeated invocation reuses the same result rather than rerunning work.

### 6.3 Semantic fingerprint

The Orchestrator computes a logical fingerprint from the canonical, material inputs and stores it with the invocation record. The fingerprint protects against stale `run_id` reuse when the underlying logical inputs differ materially.

### 6.4 Incidental metadata exclusion

The fingerprint excludes runtime incidental metadata such as timestamps, non-semantic or transient runtime fields, and non-authoritative metadata. Only material logical inputs are included. This is required to avoid unnecessary re-invocation while still detecting stale reuse.

### 6.5 Stale run_id protection

If the same `run_id` is reused with materially different inputs, Orchestrator must block the task rather than reusing stale output. This is a high-severity correctness and idempotency defect in the repository’s own design, and it is explicitly prevented by the orchestrator logic.

### 6.6 Same logical invocation reuse

If the same logical task, same repository revision, same canonical inputs, and same `run_id` are reused, the runtime may return the stored result without re-execution. This is the intended idempotent behavior.

### 6.7 Materially changed inputs require fresh logical invocation

If the underlying inputs change materially (e.g., different architecture_result, test_manifest, repository_revision, or task identity), the orchestrator must detect the fingerprint mismatch and reject or re-invoke appropriately. It must not silently reuse a stale result.

---

## 7. CI Integration

The E2E flow must preserve the distinction between Developer claims, CI evidence, QA verification, and Safety verification.

### 7.1 CI placement in the workflow

The workflow requires CI between Developer and QA:

DEVELOPMENT → CI → QA → SAFETY

CI is not a final approval gate. It is the evidence collection stage that produces actual command results, logs, and test outcomes.

### 7.2 What CI must provide

Before QA can proceed, the Orchestrator should require:

- `implementation_artifact`
- `test_manifest`
- repository revision
- current task context and task record
- CI execution evidence showing whether commands passed or failed

This evidence is necessary for QA to decide whether the code is actually verified or whether the evidence is insufficient.

### 7.3 Why CI is not enough

A Developer claim of success, even if recorded in a test manifest, is not equivalent to independent QA verification. The E2E design requires a strict separation:

- Developer claim = implementation assertion
- CI evidence = actual command results
- QA verification = independent correctness assessment
- Safety verification = independent safety assessment

QA and Safety must use the same canonical input and must not accept a mere developer summary as proof. The repository’s existing QA and Safety executors explicitly treat developer output as evidence but not truth.

### 7.4 Decision gate

The orchestrator should move from CI to QA only when the evidence is present and the task is still in a valid stage. If CI fails, the task remains blocked. If CI succeeds but the evidence is incomplete or contradictory, QA may still return `INCONCLUSIVE` or `FAIL`.

---

## 8. Human Approval

The human approval boundary is explicit and must remain mandatory where the active policies require it.

### 8.1 Required approval conditions

Human approval remains mandatory for:

- paper-to-live transitions
- risk limit and capital-limit changes
- API permission escalations
- production deployment
- merge into protected branches
- safety-sensitive or major safety architecture changes
- any explicit `REQUIRE_HUMAN_APPROVAL` conditions from Safety or policy evaluation

### 8.2 Approval behavior

The correct pattern is:

Safety or policy -> Orchestrator routes to `HUMAN_APPROVAL` -> Human approves or rejects -> Orchestrator continues or blocks

No agent may:

- self-approve
- simulate approval as real approval
- bypass `HUMAN_APPROVAL`
- enable live trading
- change risk limits
- enable withdrawals
- deploy production
- merge protected changes

The approval boundary is deliberate and must remain explicit in the workflow and docs.

### 8.3 Approval persistence

When the human grants or rejects approval, the workflow persists that approval decision in the task and/or task artifacts so the decision is auditable. The design does not create a second state store or a hidden approval object.

---

## 9. Security Boundary

The E2E system remains development-only and must not cross into live trading or production operations.

The design explicitly forbids:

- exchange API access
- live credentials or credential provisioning to agents
- live withdrawal capability
- live order placement
- live trading activation
- automatic production deployment
- protected branch merge authority
- autonomous risk-limit mutation

The E2E system only validates local logic, contract compliance, tests, risk-sensitive architecture review, and workflow gates. The repository’s local safety and QA executors already enforce this boundary by rejecting unsafe payloads and by ensuring the workflow remains development-only.

### 9.1 E2E proof requirement

The E2E design does not merely assume the boundary. It requires the test strategy to assert these guarantees explicitly by checking:

- no token or code path enabling live trading
- no live credential exposure
- no withdrawal capability
- no trade or market activation logic
- no merge or deploy authority in agent contracts or runtime assumptions

---

## 10. Test Strategy

The E2E design must be validated with a minimal but complete matrix covering both successful and failed workflow paths. This matrix is design-level and should map directly to the current repository tests and the orchestrator’s guard logic.

### 10.1 Matrix format

For each scenario, the expected outcome includes:

- input
- expected agent invoked
- expected artifact
- expected state
- expected persistence
- expected retry/escalation
- expected terminal outcome

### 10.2 Scenario matrix

A. Happy path
- Input: valid `task_record`, `architecture_result`, `implementation_artifact`, `test_manifest`, `qa_result` pass, `safety_result` pass
- Agent invoked: Architect → Developer → CI → QA → Safety
- Artifact: `architecture_result`, `implementation_artifact`, `test_manifest`, `qa_result`, `defect_report`, `safety_result`
- State: progresses through workflow, eventually reaches the next allowed state or merge gate
- Persistence: artifacts persisted in `TaskStore`
- Retry/escalation: none
- Terminal: success

B. Architect failure
- Input: missing or malformed `architecture_result` or invalid repository context
- Agent invoked: Architect
- Artifact: no valid `architecture_result`
- State: blocked before `READY`
- Persistence: invocation record + agent result captured; no state progression
- Retry/escalation: retry if within limits; escalation after threshold
- Terminal: blocked or escalated

C. Developer failure
- Input: invalid developer auth or invalid implementation artifact/test manifest
- Agent invoked: Developer
- Artifact: missing `implementation_artifact` or `test_manifest`
- State: blocked or returned before CI/QA
- Persistence: invocation record and runtime result persisted
- Retry/escalation: yes, bounded
- Terminal: blocked or escalated

D. CI failure
- Input: failing CI evidence or missing CI evidence
- Agent invoked: CI runner, then Orchestrator blocks transition
- Artifact: `ci_results` indicates failure
- State: remains before QA/Safety advancement
- Persistence: CI evidence recorded
- Retry/escalation: bounded retry if workflow policy allows
- Terminal: blocked

E. QA FAIL
- Input: `qa_result` decision = `FAIL`
- Agent invoked: QA
- Artifact: `qa_result`, `defect_report`
- State: non-advancing state; task remains blocked
- Persistence: defect report and audit history persist
- Retry/escalation: retry then escalate if limit exceeded
- Terminal: blocked or escalated

F. QA BLOCKED
- Input: malformed or missing artifacts at QA gate
- Agent invoked: QA
- Artifact: `qa_result` with `BLOCKED` or runtime failure
- State: blocked before `SAFETY`
- Persistence: invocation + output persisted
- Retry/escalation: bounded retry, then escalate
- Terminal: blocked or escalated

G. QA INCONCLUSIVE
- Input: insufficient evidence or contradictory results
- Agent invoked: QA
- Artifact: `qa_result` with `INCONCLUSIVE`
- State: held, not advanced
- Persistence: evidence and limitations persist
- Retry/escalation: retry or escalation per policy
- Terminal: blocked or escalated

H. Safety FAIL
- Input: `safety_result` decision = `FAIL`
- Agent invoked: Safety
- Artifact: `safety_result`
- State: blocked; may become `ESCALATED` after retry limits
- Persistence: safety findings persist
- Retry/escalation: bounded retry then escalate
- Terminal: blocked or escalated

I. Safety BLOCKED
- Input: missing or malformed Safety evidence bundle
- Agent invoked: Safety
- Artifact: `safety_result` or runtime-blocked result
- State: blocked; no progression
- Persistence: invocation + artifact debug data persist
- Retry/escalation: bounded retry then escalate
- Terminal: blocked or escalated

J. Safety INCONCLUSIVE
- Input: insufficient safety evidence
- Agent invoked: Safety
- Artifact: `safety_result` with `INCONCLUSIVE`
- State: blocked or held
- Persistence: safety evidence and limitations persist
- Retry/escalation: bounded retry or escalation
- Terminal: blocked or escalated

K. Safety REQUIRE_HUMAN_APPROVAL
- Input: risk-sensitive change requiring approval
- Agent invoked: Safety
- Artifact: `safety_result` with `REQUIRE_HUMAN_APPROVAL`
- State: `HUMAN_APPROVAL`
- Persistence: safety result persists; approval decision persists
- Retry/escalation: no silent bypass; retry is not a substitute for human approval
- Terminal: approval granted continues, approval rejected blocks

L. Human approval granted
- Input: explicit approval record
- Agent invoked: none additional; human decision at gate
- Artifact: `human_approval_record`
- State: continues to next authorized state or merge gate
- Persistence: approval recorded
- Retry/escalation: no automated override
- Terminal: approved continuation

M. Human approval rejected
- Input: explicit rejection or missing approval
- Agent invoked: none additional
- Artifact: rejection recorded or no approval record
- State: remains blocked / returns to prior state
- Persistence: rejection persists
- Retry/escalation: depends on policy, but no silent continuation
- Terminal: blocked

N. malformed artifact
- Input: missing required keys, wrong type, bad decision, invalid envelope
- Agent invoked: relevant producer agent
- Artifact: invalid artifact
- State: blocked immediately before workflow progression
- Persistence: invalid artifact and audit log remain recorded
- Retry/escalation: bounded retry or escalation
- Terminal: blocked or escalated

O. missing artifact
- Input: required artifact absent from task bundle
- Agent invoked: previous or current agent depending on stage
- Artifact: none or incomplete artifact
- State: blocked at the gate
- Persistence: task history and failure reason persist
- Retry/escalation: yes, bounded
- Terminal: blocked or escalated

P. stale run_id
- Input: same `run_id` used with materially different logical input
- Agent invoked: orchestrator validation first, then agent is not re-executed
- Artifact: existing invocation record and fingerprint mismatch
- State: blocked
- Persistence: previous invocation record and current mismatch recorded
- Retry/escalation: blocked; may escalate after retry counts
- Terminal: blocked or escalated

Q. same run_id + same logical inputs
- Input: duplicate invocation with same canonical payload and same `run_id`
- Agent invoked: reused runtime result; no second execution
- Artifact: same result reused
- State: no duplicate state change
- Persistence: one invocation record and one result set
- Retry/escalation: none
- Terminal: idempotent success or status reuse

R. same run_id + changed logical inputs
- Input: identical `run_id`, different logical payload
- Agent invoked: orchestrator rejects or blocks the re-use path
- Artifact: mismatch reported
- State: blocked
- Persistence: mismatch recorded
- Retry/escalation: deterministic block and retry/escalation if allowed
- Terminal: blocked or escalated

S. retry exhaustion
- Input: repeated failed invocation or malformed artifact cycle
- Agent invoked: same failing stage
- Artifact: repeated failure evidence
- State: `ESCALATED`
- Persistence: full failure history persists
- Retry/escalation: yes, the final result is escalation
- Terminal: escalated

T. escalation
- Input: any policy-triggered or retry-triggered escalation condition
- Agent invoked: previous agent or workflow state; no workflow bypass
- Artifact: transition log and escalation reason persist
- State: `ESCALATED`
- Persistence: retry and escalation history persist
- Retry/escalation: no automatic continuation
- Terminal: escalated

U. regression of existing integrations
- Input: previously validated Architect/Developer/QA/Safety flows
- Agent invoked: the same existing integration pattern
- Artifact: no new artifact or schema changes
- State: existing validated transitions continue to pass
- Persistence: no duplicate artifact records created
- Retry/escalation: same as current logic
- Terminal: confirm no regression in the current architecture

---

## 11. Scope

This is design only. The design includes only the creation of this file and does not change any code, policy, workflow, contract, test, runtime, or trading logic.

Only the design document being created here is in scope:

- `docs/full_agentic_e2e_design.md`

All other files remain untouched.

---

## 12. Acceptance Criteria

The design is acceptable only if all statements below are satisfied:

- it reuses the existing workflow
- it reuses the existing `AgentRuntime`
- it reuses the existing `TaskStore`
- it reuses the existing semantic fingerprint/idempotency model
- it preserves all authority boundaries
- it introduces no duplicate artifacts
- it introduces no second state store
- it clearly defines CI evidence
- it clearly defines human approval
- it covers failure/retry/escalation
- it covers stale `run_id`
- it covers malformed and missing artifacts
- it preserves development-only safety boundaries
- it does not redesign trading architecture
- it does not introduce speculative complexity

---

## 13. Final Design Status

This design is the minimum correct end-to-end workflow using the current repository architecture. It preserves the current contracts, workflow, runtime, and authority boundaries, and it explicitly avoids speculative redesign. It is therefore the correct E2E design for the current repository state.
