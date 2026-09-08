# QA ↔ Orchestrator Integration Design (STEP 5C.2)

Status: DESIGN ONLY — no runtime, workflow, policy, or test changes in this step.

## 1. Purpose

This design defines the smallest correct integration path between the existing QA Agent and the Orchestrator while preserving the authority model already defined by the contracts and workflow:

- QA owns verification, evidence classification, defect identification, and the final QA decision.
- Orchestrator owns workflow state, retries, escalation, routing, artifact validation, and persistence.
- Developer owns implementation.
- Architect owns architecture decisions and ADR authority.
- Safety owns safety review and safety blocking decisions.
- Human owns approval gates.

The design reuses the existing `AgentRuntime`, `InvocationRequest`, `AgentResult`, `TaskStore`, `WorkflowEngine`, and policy evaluation flow. It does not create a new state store, provider integration, or alternative schema.

## 2. Current architecture

The active contracts and workflow already establish the intended boundaries:

- `.agent/contracts/qa.contract.json` defines the canonical QA input set, output expectations, allowed decisions, defect model, evidence model, and `qa_result_shape`.
- `.agent/contracts/orchestrator.contract.json` defines Orchestrator as the workflow authority with read-only repo access and artifact validation responsibilities.
- `.agent/workflows/workflow.json` defines the live transition chain: `DEVELOPMENT -> CI -> QA -> SAFETY ...`.
- `.agent/guidelines.md` states the precedence order and requires canonical vocabulary, no silent bypass, and auditability.
- `.agent/agents/qa.md` and `.agent/agents/orchestrator.md` confirm the same separation of duties.
- `tools/agent_runtime.py` already provides `InvocationRequest`, `AgentResult`, and `run_id`-based idempotency.
- `tools/orchestrator_core.py` already implements the existing Architect and Developer integration pattern via `AgentRuntime.invoke()` and artifact validation.

The QA integration should therefore mirror the Architect and Developer patterns rather than inventing a separate orchestration mechanism.

## 3. Integration sequence

The integration sequence is intentionally minimal:

1. Orchestrator advances task to `QA` using the existing workflow engine.
2. Orchestrator validates the prerequisite task state and required artifact bundle.
3. Orchestrator prepares an `InvocationRequest` for the QA agent, using the canonical QA input set.
4. Orchestrator assigns a `run_id` and persists an `invocation_record` in the task store.
5. Orchestrator calls `AgentRuntime.invoke(req)` with `agent_role = "QA"` and the existing runtime executor `QAExecutor`.
6. `AgentRuntime` returns an `AgentResult`.
7. Orchestrator validates the result envelope and extracts the canonical `qa_result` artifact.
8. Orchestrator validates the `qa_result` decision, required fields, and evidence/defect model.
9. Orchestrator updates workflow state only according to the QA decision and existing policy rules.
10. If the decision is a blocking or non-passing state, the task remains in a non-advancing state and follows standard retry/escalation policy.
11. If the decision is `PASS`, Orchestrator continues to the next workflow gate, which is the existing `QA -> SAFETY` transition required by the workflow.

## 4. Input contract

The canonical QA input set is already defined by `.agent/contracts/qa.contract.json` and should be treated as the only accepted payload.

Required inputs to QA:

- `task_record`
- `architecture_result`
- `repository_context`
- `repository_revision`
- `implementation_artifact`
- `test_manifest`
- `run_id`

Required semantics:

- `task_record`: must be a dict and must match the task under orchestration.
- `task_record.task_id`: must equal the orchestrator task ID.
- `task_record.authorized`: must be true; otherwise QA returns a blocked result instead of guessing.
- `architecture_result`: must be a dict; this is the architecture contract artifact used to check compliance.
- `repository_context`: must be a dict; it must carry the repository snapshot metadata needed for verification.
- `repository_revision`: must be non-empty and must match the orchestrator-provided revision exactly.
- `implementation_artifact`: must be a dict; it should carry the developer output and changed files.
- `test_manifest`: must be a dict and must include structured verification evidence, not only a summary string.
- `run_id`: must be non-empty; this is the idempotency key used by the runtime.

Missing input handling:

- Missing required inputs are not silently retried by QA.
- QA must return a `BLOCKED` result or an equivalent runtime failure record that Orchestrator interprets as a workflow block.
- Orchestrator must not advance the task state when required QA inputs are absent.

Additional inputs allowed by the contract but not required:

- `acceptance_criteria`
- `policy_context`
- `defect_history`
- `previous_qa_result`

Forbidden inputs:

- live exchange credentials
- production secrets
- withdrawal permissions
- live trading enablement
- risk-limit overrides
- direct workflow transition requests

These are not passed to QA; if they appear in the input envelope, QA must reject the payload as unsafe.

## 5. Invocation lifecycle

### 5.1 Orchestrator invocation creation

When the task reaches `QA`, Orchestrator must:

- read the task from `TaskStore`
- validate the current workflow state is compatible with `QA`
- ensure the task has the required artifacts created by prior stages (`implementation_artifact`, `test_manifest`, `architecture_result`, and the task record)
- confirm a valid `repository_revision` exists
- generate a fresh `run_id` if no prior QA run exists for this task/attempt
- reuse the same `run_id` only when the prior invocation is the same logical QA run

### 5.2 `run_id` generation

The design reuses the existing runtime semantics:

- `run_id` is generated by Orchestrator at invocation time with the same semantics already used elsewhere in the project.
- It is persisted in both the `invocation_record` and the `qa_result` artifact.
- A duplicate invocation for the same logical QA request must reuse that same `run_id` to leverage `AgentRuntime` caching and preserve deterministic behavior.

### 5.3 `AgentRuntime.invoke()` path

Orchestrator creates an `InvocationRequest` with the canonical fields already used by the runtime:

- `task_id`
- `agent_role` = `"QA"`
- `repository_revision`
- `worktree` = `None` for this design, unless future implementation adds separate worktree semantics
- `task_spec` = the canonical QA task payload containing the required fields above
- `input_artifacts` = existing artifact refs and task artifacts needed for context
- `policy_context` = deterministic policy results from `PolicyEvaluator` or equivalent policy context
- `timeout_seconds`
- `attempt`
- `run_id`
- `correlation_id` if needed for grouping but not required by the current runtime

Then Orchestrator calls:

- `self.runtime.executor = QAExecutor()`
- `result = self.runtime.invoke(inv_req)`

### 5.4 Result retrieval and validation

Orchestrator retrieves the result via:

- `runtime.get_result(run_id)` when reusing a prior invocation
- otherwise the return value of `runtime.invoke(req)`

The `AgentResult` is not treated as the QA decision itself; it is the execution envelope. Orchestrator then validates the output artifacts inside it and extracts the canonical `qa_result` and `defect_report` payloads.

### 5.5 Failure behavior

If the executor raises an exception or the runtime returns a failed result:

- `FAILED` is treated as an execution failure and is not silently reinterpreted as PASS
- `TIMED_OUT` is treated as a timeout failure and follows the same retry policy already used elsewhere in Orchestrator
- the task remains non-advancing until policy and workflow handling determine retry or escalation

### 5.6 Timeout behavior

Timeout handling remains policy-driven and follows the existing orchestrator retry limits. The design does not add a new timeout behavior or new retry policy. Orchestrator uses the same retry_limit logic already present in `Orchestrator.transition_task()`.

### 5.7 Duplicate invocation behavior

If the same logical request is repeated under the same `run_id`:

- `AgentRuntime` returns the cached `AgentResult`
- Orchestrator must not invoke QA a second time under the same `run_id` with different payloads
- a second attempt with a different `run_id` may be allowed only if the task requires a new inspection cycle, in line with existing retry semantics

## 6. Artifact flow

### 6.1 Canonical artifact representation

The integration must use the canonical QA contract and the existing AgentRuntime envelope, not an alternative schema.

The `AgentResult` from `AgentRuntime` is an execution envelope and contains:

- `task_id`
- `agent_role`
- `run_id`
- `status`
- `started_at`
- `completed_at`
- `output_artifacts`
- `error`
- `execution_metadata`

Inside `output_artifacts`, Orchestrator expects the canonical QA artifacts:

- `artifact_type == "qa_result"`
- `artifact_type == "defect_report"`

The artifact payloads must remain strictly compliant with `.agent/contracts/qa.contract.json`.

### 6.2 `qa_result` envelope

The `content` of the `qa_result` artifact must be a dict matching the canonical shape:

- `task_id`
- `run_id`
- `repository_revision`
- `decision`
- `verification_summary`
- `evidence_references`
- `defects`
- `limitations`
- `safety_relevant_findings`

The decision must be one of:

- `PASS`
- `FAIL`
- `BLOCKED`
- `INCONCLUSIVE`

### 6.3 `defect_report` envelope

The `defect_report` artifact should represent the same structural defect data required by the QA contract. The defect objects must include the canonical fields required by the defect model:

- `defect_id`
- `severity`
- `category`
- `description`
- `affected_area`
- `evidence`
- `expected_behavior`
- `observed_behavior`
- `verification_info`
- `blocking_status`

The design does not invent a second defect schema. Orchestrator validates the defect report only for canonical field presence and allowed values, not for a new abstraction.

## 7. Decision → workflow mapping

The QA decision mapping is strict and must not be reinterpreted by Orchestrator.

### QA `PASS`

- Workflow may proceed to the next eligible gate.
- For the current workflow, the immediate next gate is the existing `QA -> SAFETY` transition required by `workflow.json`.
- Orchestrator is still responsible for validating any policy-driven safety gate or human approval conditions.

### QA `FAIL`

- Task must not advance.
- Task transitions to a non-advancing state according to existing policy and retry semantics.
- Orchestrator records the defect and keeps the task in `BLOCKED`/`ESCALATED` as appropriate.

### QA `BLOCKED`

- Task must not advance.
- This indicates missing inputs, invalid state, or an authority prerequisite issue.
- Orchestrator must not silently reinterpret `BLOCKED` as `PASS`.

### QA `INCONCLUSIVE`

- Task must not silently advance.
- Orchestrator must either requeue for additional evidence, escalate, or hold the task based on the current retry and escalation policy.

The key rule: QA decides verification state; Orchestrator decides workflow state transitions and escalation.

## 8. Workflow compatibility

The existing workflow includes:

- `DEVELOPMENT -> CI -> QA -> SAFETY`

The currently defined responsibility is:

- Orchestrator invokes QA after CI and before Safety.
- QA produces `qa_result` and defect evidence.
- Safety remains separate and receives the artifacts needed for safety review.

The integration should not alter the state machine. The `QA -> SAFETY` transition remains the exact workflow gap that is satisfied by the QA artifact bundle: `qa_result` and `test_manifest` are the structured evidence the Safety agent can review. Orchestrator is still the workflow authority that determines whether the task may move to `SAFETY`.

This preserves:

- Orchestrator as the transition owner
- QA as artifact producer
- Safety as independent reviewer

## 9. Failure handling

The design reuses the current failure-handling model instead of creating new semantics.

### QAExecutor failure

- If the QA executor raises an exception, the runtime returns a failed `AgentResult`.
- Orchestrator records the failure and handles it through the existing policy/retry flow.

### AgentRuntime failure

- Runtime-level failure is not treated as a QA decision.
- It is treated as an execution failure requiring workflow blocking or retry according to existing `retry_limit` logic.

### Timeout

- Timeout is handled as a runtime failure and follows the same retry and escalation semantics already used by Orchestrator.

### Malformed `qa_result`

- Orchestrator must mark the task as blocked or escalated and record the invalid envelope.
- It must not advance to the next workflow step.

### Missing `qa_result`

- If no valid `qa_result` artifact exists in `output_artifacts`, the task is blocked.
- This is an orchestration validation failure, not a QA PASS.

### Malformed `defect_report`

- If the defect report is missing required canonical fields, Orchestrator must reject it and keep the task non-advancing.
- This is a validation problem, not a new integration contract.

### Missing required evidence

- If the QA decision relies on missing or empty evidence, QA should return `BLOCKED` or `INCONCLUSIVE`.
- Orchestrator must not reinterpret this as a pass.

### Duplicate `run_id`

- Duplicate `run_id` must simply return the cached AgentResult from the runtime.
- Orchestrator must not allow different payloads under the same `run_id` to silently change the meaning of the run.

### Repository revision mismatch

- If `qa_result.repository_revision` or the artifact content does not match the task revision, Orchestrator must reject the result and block the task.

### Task mismatch

- If `task_id` inside the QA output does not match the orchestrated task, Orchestrator must reject the result and block the task.

## 10. Idempotency

Idempotency is defined by the existing runtime model.

- `run_id` identifies a single logical QA invocation.
- `task_id` identifies the work item under orchestration.
- `repository_revision` identifies the repo snapshot used for the task.
- Repeated calls with the same `run_id` return the cached `AgentResult` and must not re-execute QA.
- A different `run_id` is treated as a new attempt or a new logical run, subject to Orchestrator retry policy.
- The design does not allow QA to be invoked multiple times under the same `run_id` with different inputs.
- If a result is cached for a given `run_id`, the caller reads the result and validates it without executing again.

## 11. Persistence / auditability

Orchestrator persists artifacts through the existing `TaskStore` and artifact append model. No new state store is introduced.

Persistent artifacts should include:

- `invocation_record`
- `agent_result`
- `qa_result`
- `defect_report`
- task history transitions for `QA`, `BLOCKED`, `ESCALATED`, and any retry or policy decisions

Required audit metadata:

- `task_id`
- `run_id`
- `agent` = `qa`
- `repository_revision`
- `decision`
- `artifact types`
- `failure state`
- `timestamps`

This is the minimum structured audit record needed to explain why a workflow gate passed or failed.

## 12. Security boundary

The integration must explicitly maintain the security model:

- Repository access is not live trading access.
- QA does not receive credentials.
- QA does not receive exchange connectivity or trading authorization.
- QA does not create live execution capability.
- QA does not enable withdrawals, risk-limit changes, merge operations, or deploy actions.
- QA only evaluates artifacts, evidence, and repository context.

No provider or networking integration is required for this design.

## 13. Reuse of existing integration patterns

The existing Architect and Developer integration patterns are directly reusable:

- Orchestrator prepares a runtime `InvocationRequest`
- Orchestrator persists an `invocation_record`
- Orchestrator calls `AgentRuntime.invoke()`
- Orchestrator validates `AgentResult.output_artifacts`
- Orchestrator checks task identity, run identity, repository revision, and schema correctness
- Orchestrator decides state transitions based on the validation result

What is QA-specific:

- The canonical QA contract defines `qa_result` and `defect_report` and the QA decision model
- QA decisions are not simply success/failure of an executor; they express evidence-backed verification opinion
- QA is a verification gate, not an implementation gate
- QA does not own workflow transition authority

This means the reusable infrastructure is the same; only validation logic and the role-specific contract differ.

## 14. Known limitations

- QA evaluates the evidence that is supplied; it does not independently prove repository truth beyond the provided artifacts.
- The QA decision is only as strong as the provided test manifest and implementation metadata.
- The `architecture_result` alignment check is a minimal heuristic unless a richer semantic validation layer is added in the future.
- QA is intentionally not the place for live execution, live trading, or deployment.
- This design preserves the current local, deterministic model and intentionally does not broaden QA into a broader systems-validation layer.

## 15. Open questions

Resolved by closure decision for STEP 5C.2A:

- A separate `validation_result` artifact is not introduced. `qa_result` remains the canonical QA verification result.
- `defect_report` is part of the canonical QA output bundle and is emitted even when no defects exist; the defects collection is empty when no defects are found.
- `evidence_references` is not replaced with a new mechanism. Orchestrator validates the canonical `qa_result` shape but does not reinterpret, rewrite, or transform QA evidence.

## 16. Explicit non-goals

This design deliberately does not do any of the following:

- modify runtime code
- modify QA implementation
- modify Orchestrator implementation
- modify tests
- modify workflow
- modify policies
- implement Safety
- touch trading, exchange, or live-money logic
- add new dependencies
- introduce compatibility aliases
- redesign the existing workflow
- create a second state store or persistence mechanism

## Acceptance criteria check

This design satisfies the required acceptance criteria:

- QA remains independently responsible for verification.
- Orchestrator remains the workflow authority.
- Safety remains independent.
- The canonical QA artifacts are used.
- No new schemas are invented.
- No duplicated state store is introduced.
- No new provider or network dependency is introduced.
- Existing retry and escalation patterns are reused.
- Existing Architect/Developer integration patterns are reused where applicable.
- No trading/live-money capability is granted.
- QA responsibilities remain bounded and non-expanding.

## Closure decisions

### 1. `validation_result`

Not introduced.

Reason: `qa_result` is already the canonical QA verification and decision artifact. Orchestrator owns workflow state and must not create a second verification result or duplicate schema.

### 2. `defect_report`

`defect_report` remains part of the canonical QA output bundle and is always produced as part of the QA invocation, even when there are no defects.

In the no-defect case:

- `defects` is represented as an empty collection according to the existing contract schema
- no alternative `no_defects` structure is introduced

### 3. `evidence_references`

No new evidence-reference mechanism is introduced.

Orchestrator validates the canonical artifact shape and the existing QA contract semantics but does not reinterpret or transform QA evidence. The integration design intentionally preserves the exact representation already defined by `.agent/contracts/qa.contract.json` and `tools/qa_agent.py`.

## Authority

- QA: produces the verification decision and reports defects/evidence classification.
- Orchestrator: consumes the QA decision and applies workflow/policy consequences only; it does not create a second QA decision nor rewrite PASS/FAIL/BLOCKED/INCONCLUSIVE.
- Safety: reviews safety issues independently and applies safety blocking decisions if required.

## Idempotency

A `run_id` identifies one logical QA invocation.

The same `run_id` may be retried or retrieved only with the same logical invocation inputs. If any of the following differ, the invocation must not be reused under the same `run_id`:

- `task_id`
- `repository_revision`
- `implementation_artifact`
- `test_manifest`
- `architecture_result`

If the inputs differ, a new `run_id` is required.

This preserves the existing `AgentRuntime` behavior and avoids redefining idempotency semantics.

## Files changed

- [docs/qa_orchestrator_integration_design.md](qa_orchestrator_integration_design.md)

## Validation

Validation performed against the active source-of-truth design files and runtime shapes:

- `.agent/contracts/qa.contract.json` parsed successfully as JSON.
- `.agent/contracts/orchestrator.contract.json` parsed successfully as JSON.
- `.agent/contracts/developer.contract.json` parsed successfully as JSON.
- `.agent/contracts/safety.contract.json` parsed successfully as JSON.
- `.agent/workflows/workflow.json` parsed successfully as JSON.
- `tools/agent_runtime.py` reviewed for `InvocationRequest`, `AgentResult`, and `run_id` idempotency semantics.
- `tools/orchestrator_core.py` reviewed for the existing Architect and Developer integration pattern.
- No executable Python files were modified.
- No trading/exchange/live-money files were modified.
- No workflow or policy files were modified.
- Existing Architect/Developer integration assumptions remain intact.

Overall: PASS WITH FINDINGS

The only findings are design-level and intentional limitations, not code-level defects:

- QA verification is evidence-based, but it is only as strong as the supplied artifacts.
- The workflow gate is correct, but it does not make QA itself the final safety authority.
- The runtime is deliberately minimal and does not expand QA beyond the current contract model.
