Architect ↔ Orchestrator Integration Design (STEP 4C)
====================================================

Status: DESIGN ONLY — do NOT implement in this step.

Summary
-------
This document defines the minimal integration contract and lifecycle for invoking the Architect Agent via the existing AgentRuntime and for Orchestrator consumption of the produced Architecture Result. The design reuses existing abstractions (TaskStore, PolicyEvaluator, WorkflowEngine, AgentRuntime) and maps Architect outputs into artifacts the Orchestrator can validate and act on.

1) Current-state assessment
---------------------------
- Workflow states already include: BACKLOG → TRIAGE → ARCHITECTURE → READY → DEVELOPMENT etc. (`.agent/workflows/workflow.json`).
- Policies include `architecture_changes_require_adr` and `safety_review_for_risk_execution_accounting` which expect an Architect step and safety gating (`.agent/policies/policies.json`).
- The Orchestrator contract explicitly forbids repository writes and requires artifact validation (`.agent/contracts/orchestrator.contract.json`).
- `AgentRuntime` provides `InvocationRequest` and `AgentResult` shapes and idempotency semantics (run_id caching). `ArchitectExecutor` implementation emits an `architecture_result` artifact with structured content.
- The Workflow transition from `ARCHITECTURE` -> `READY` already lists `required_artifacts: ["adr_proposal"]` and `post_condition: adr_validated`, so Orchestrator must validate ADRs and Architect artifacts before allowing READY.

Findings (gaps vs. needs)
- Orchestrator currently has generic `AgentRunner` stub; integration needs a deterministic invocation pattern and validation code to be added in Orchestrator (design only).
- No additional workflow states are required; `PENDING_SAFETY_REVIEW` or `PENDING_HUMAN_APPROVAL` are already represented by `PENDING_SAFETY_REVIEW` behavior in policy evaluation (Orchestrator transitions to `PENDING_SAFETY_REVIEW` in code). Workflow.json includes `SAFETY` and `HUMAN_APPROVAL` states for later steps.

2) Target architecture
----------------------
- Orchestrator remains the coordinator. It will prepare an `InvocationRequest` for AgentRuntime, submit it, and validate the returned `AgentResult` (architecture_result artifact). No Architect-specific in-process logic will be embedded in AgentRuntime or Architect executor; Orchestrator performs orchestration-specific validation.
- Key responsibilities:
  - Create and persist invocation metadata in TaskStore (task_id, run_id, attempt).
  - Submit `InvocationRequest` to AgentRuntime with properly populated fields.
  - Wait for/collect AgentResult and validate payload per Architect contract.
  - Append artifact(s) to TaskStore and update task history and status or escalate/block per policies.

3) Invocation contract (exact fields)
-------------------------------------
Orchestrator must construct the AgentRuntime `InvocationRequest` with these fields mapped as follows.

Required (MUST):
- `task_id` (string): TaskStore task_id (same as task being transitioned to ARCHITECTURE).
- `run_id` (string): UUID for this Architect invocation (Orchestrator generated). If retrying same run, reuse same run_id to leverage AgentRuntime idempotency.
- `agent_role` (string): "ARCHITECT".
- `repository_revision` (string): exact commit SHA from task record.
- `task_spec` (object): canonical task_spec from TaskStore augmented with `repository_context` (see Repository Context section).
- `repository_context` inside `task_spec`: object with `file_list`, `tests_map` (optional), `notable_paths` (optional), `owners` (if available).
- `policy_context` (object): policy evaluation hints (from PolicyEvaluator) including triggered policies that apply (only deterministic triggers) — may be empty object.
- `timeout_seconds` (int): configured invocation timeout (e.g., from policy or default runtime config).
- `attempt` (int): current attempt count from TaskStore.

Optional (MAY):
- `input_artifacts` (list): prior artifacts (e.g., triage_notes, design briefs). Include artifact ids and small payloads.
- `architecture_references` (list[string]): explicit doc/ADR paths from task metadata.
- `prior_adrs` (list[string]): paths/ids of previously relevant ADRs.
- `constraints` (object): any non-functional or safety constraints (read-only note; Architect must not break them).
- `correlation_id` (string): if Orchestrator uses it for grouping related runs.

Derived (Orchestrator sets):
- `repository_context.file_list` derived by scanning repo at `repository_revision` (list of relevant filenames). Prefer lightweight lists (no full file contents unless necessary).
- `policy_context` derived by running `PolicyEvaluator.evaluate(task)` before invocation; include only deterministic `triggered` results.

Forbidden (MUST NOT be sent):
- Any credentials, secrets, or keys.
- Any write-authority tokens (git push/merge credentials).
- Any fields that would grant live trading authority.

Invocation metadata recorded in TaskStore
- Orchestrator must append an `invocation_record` artifact in the TaskStore: {run_id, agent_role, repository_revision, timeout_seconds, attempt, submitted_at} for auditability.

4) Repository context model
---------------------------
Orchestrator supplies a read-only repository snapshot reference and minimal metadata. The model contains four parts:

1) `repository_revision` (commit SHA) — authoritative single-point reference (MUST be included in InvocationRequest top-level and inside task_spec.repository_context.repository_revision).
2) `repository_metadata` (derived):
   - `file_list`: list of path strings (top-level and src files). Limit to relevant files to keep payload small.
   - `tests_map`: optional mapping of module -> tests touching it (if available from CI or precomputed index).
   - `notable_paths`: list of config/docs/ADRs (e.g., .agent/ADRs, .agent/policies/)
3) `relevant_source_references`: explicit file paths the task claims to change (target_paths) — included in task_spec.target_paths when provided by user/triage.
4) `previous_artifacts`: references to prior artifacts (triage_notes, operator reports) included in `task_spec.previous_agent_artifacts`.

Notes:
- Orchestrator does NOT create a new repository abstraction — it provides commit SHA and lists. Worktrees remain runtime responsibility for Developer only.
- Architect must treat the `file_list` read-only and must not expect file contents unless the task requests them (and Orchestrator includes small file excerpts in `input_artifacts`).

5) Result contract (Architect → Orchestrator)
-------------------------------------------
Architect returns an `AgentResult` containing `output_artifacts`. The Orchestrator must validate an artifact of `artifact_type == "architecture_result"` whose `content` matches the Architect contract schema (`.agent/contracts/architect.contract.json`). The minimal required keys in `content` are:

- `task_id` (string) — MUST match original task_id.
- `run_id` (string) — MUST match invocation run_id.
- `repository_revision` (string) — SHOULD match invocation revision (if mismatch, treat as error).
- `architecture_assessment` (object)
- `affected_components` (array)
- `proposed_changes` (array)
- `acceptance_criteria` (array)
- `developer_specification` (object)
- `adr_required` (boolean)
- `safety_implications` (array)
- `assumptions` (array)
- `open_questions` (array)
- `escalation` (object|null)
- `status` (string) — PROPOSAL (Architect must not mark as APPROVED).

6) Result validation rules (Orchestrator must enforce)
-----------------------------------------------------
Orchestrator must apply deterministic checks before advancing state:

- Schema validation: `content` must conform to `architect.contract.json` required keys.
- `task_id` equality: artifact.content.task_id == task_id.
- `run_id` equality: artifact.content.run_id == submitted run_id.
- `repository_revision` equality: artifact.content.repository_revision == invocation revision (mismatch -> reject).
- `status`: MUST be one of allowed statuses; if `status` != "PROPOSAL" or "PROPOSED", treat as suspicious and fail validation.
- `affected_components`: must be non-empty if task_spec indicated `target_paths` OR task asked for scope; empty is allowed for exploratory tasks but require `open_questions` to justify.
- `acceptance_criteria`: each criterion must be a short testable sentence; Orchestrator performs light syntactic verification (non-empty strings) and records them for QA.
- `developer_specification`: must include `files` list (file paths) and at least one change description per file.
- `adr_required`: if true, require an `adr_reference` or produce `BLOCKED`/`PENDING_ADR` state (see ADR flow).
- `safety_implications`: if non-empty and touched sensitive files, escalate to Safety review (transition to `PENDING_SAFETY_REVIEW` or append policy result requiring safety).

Validation outcome mapping:
- If validation passes and `adr_required` is false and `safety_implications` is empty, Orchestrator may move task to `READY` (subject to human approval policy if any).
- If validation passes but `adr_required` is true and `adr_reference` missing, Orchestrator sets task to `BLOCKED` (or a `PENDING_ADR` alias) and records required ADR action.
- If validation passes but `safety_implications` non-empty -> Orchestrator sets `PENDING_SAFETY_REVIEW` (task history) and notifies Safety/human approvers.
- If validation fails (schema mismatch, id mismatches, repository mismatch), Orchestrator marks task `BLOCKED` and records failure reason and increments attempt (policy-driven retry applies).

7) Workflow/state transitions (lifecycle)
---------------------------------------
Canonical happy-path:

BACKLOG -> TRIAGE -> ARCHITECTURE
   Orchestrator creates task and populates triage notes.
ARCHITECTURE (orchestrator triggers Architect invocation)
   - Submit InvocationRequest to AgentRuntime (run_id generated), record invocation artifact in TaskStore.
   - Wait for AgentResult (synchronous or async poll).
   - Validate AgentResult (see Result validation).
   - If validation passes and no ADR required and no safety flags -> append artifact and transition to READY.

Failure / retry path:
- If AgentResult.status == "TIMED_OUT" or AgentRuntime returns status FAILED:
  - Treat as retryable failure if PolicyEvaluator `agent_retry_limits` not exceeded.
  - Increment task.attempt. If attempt <= retry_limit -> schedule retry by enqueuing Architect again.
  - If attempt > retry_limit -> set task to ESCALATED and append policy/escalation note.
- If AgentResult returns malformed artifact -> set task to BLOCKED, append validation_failure artifact, increment attempt, allow retry per policy.

Safety-sensitive path:
- If validation indicates `safety_implications` non-empty or `affected_components` intersects policy-sensitive list (risk/execution/accounting/position):
  - Orchestrator appends policy_result requiring Safety review and transitions task to `PENDING_SAFETY_REVIEW` or `BLOCKED` depending on immediate policy decision.
  - A human/Safety review must supply a `safety_report` artifact before READY.

State machine mapping notes:
- Workflow.json already defines ARCHITECTURE -> READY with `required_artifacts: ["adr_proposal"]` and `post_condition: adr_validated`. Orchestrator must implement `adr_validated` check as part of validation.

8) ADR flow
-----------
Three cases:

Case A — ADR not required:
- Architect returns `adr_required:false` and validation passes -> Orchestrator transitions to READY.

Case B — ADR required but Architect attaches ADR reference:
- Architect sets `adr_required:true` and provides `adr_reference` (path or artifact id).
- Orchestrator validates ADR presence (checks `.agent/adr/` or artifact payload) and marks `adr_validated` true once ADR schema is acceptable. Then proceed to READY (subject to safety/human approval policies).

Case C — ADR required but missing:
- Architect returns `adr_required:true` without `adr_reference` -> Orchestrator must not transition to READY. Instead:
  - Mark task `BLOCKED` (or append a `PENDING_ADR` marker in history). Record required ADR action.
  - Notify operator/human for ADR creation or ask Architect to re-run with ADR (re-invoke Architect after ADR is added to artifacts).

Note: This design does not create new workflow states; it uses existing `BLOCKED`/`ESCALATED` and the ARCHITECTURE->READY guard `post_condition: adr_validated` to enforce ADR presence.

9) Safety flow (detailed)
-------------------------
- Detection: Orchestrator runs PolicyEvaluator before invocation and again after Architect result validation to ensure deterministic policy triggers are recorded.
- If Architect flags `safety_implications` or touches policy-sensitive files, Orchestrator appends a policy_result (require_safety_review) and transitions to `PENDING_SAFETY_REVIEW`.
- Task remains in safety review until a `safety_report` artifact (provided by Safety human/operator or Safety agent in future) is attached and passes validation. Only then can Orchestrator proceed to `HUMAN_APPROVAL` or `READY` depending on policy.

10) Developer handoff
---------------------
READY -> DEVELOPMENT pre-conditions (Orchestrator must ensure):
- Architect artifact present and validated.
- Acceptance criteria present and syntactically testable.
- Developer specification lists `files` and change descriptions and `tests_to_add` (or mapping to test cases).
- ADR either not required or validated.
- Safety requirements satisfied or explicit exception documented by Safety/human.

Developer handoff artifact bundle (Orchestrator must attach to task record):
- `architecture_proposal` artifact (architect output)
- `acceptance_criteria` array
- `developer_specification` object
- `artifact_index` entries referencing artifacts

Developer must not be invoked until all pre-conditions satisfied. Orchestrator must enforce this by its workflow engine.

11) Idempotency and runtime semantics
------------------------------------
- Use AgentRuntime semantics: reuse `run_id` to get cached result if the same invocation is repeated. Orchestrator should:
  - Generate a fresh `run_id` for the first Architect invocation for a task/attempt.
  - On retry, either reuse the previous `run_id` (to check cached result) or generate a new `run_id` to force a fresh execution depending on policy. Prefer reuse for crash recovery.
- If Orchestrator crashes after invocation but before recording artifact, on recovery it should query AgentRuntime by `run_id` (TaskStore recorded invocation artifact) and fetch the result. If found and valid, continue validation.

12) Retry / failure / escalation rules
-------------------------------------
- Retryable failures: AgentResult.status in {TIMED_OUT, FAILED} when PolicyEvaluator `agent_retry_limits` not exceeded.
- Non-retryable failures: malformed artifact (schema mismatch), identity mismatch (task_id/run_id/revision mismatch) — must be BLOCKED and human-reviewed.
- Timeout: treated as retryable until retry_limit reached.
- Executor failure: treat as FAILED.
- Repeated identical failure: if retry_count > retry_limit (policy), set ESCALATED and notify humans.
- Loop prevention: rely on existing loop threshold policy `infinite_loop_prevention` and `prevent_infinite_retries` guard.

13) Auditability
---------------
Record these items in TaskStore/task history and policy_results:
- `invocation_record` (run_id, start_time, agent_role, repository_revision, attempt)
- `artifact_index` for each returned artifact (artifact_id, artifact_type, checksum)
- Policy evaluation details before and after Architect invocation (include triggered deterministic policies)
- Validation_result artifact (success/failure reasons)
- State transitions and responsible actor
- Escalation reasons and human notifications

14) Security boundaries
-----------------------
- Orchestrator MUST NOT include credentials in invocation. Architect execution environment must be read-only for repository snapshot.
- Architect artifact must never include secrets.
- Orchestrator must preserve `allowed_repository_access.write == false` and forbid automatic merges or deploys.

15) Sequence (textual)
----------------------
1. Operator creates task in BACKLOG.
2. Orchestrator TRIAGEs task, sets `task_spec` and `repository_revision`.
3. Orchestrator runs deterministic PolicyEvaluator(task) and records results.
4. Orchestrator transitions task to ARCHITECTURE and generates `run_id`.
5. Orchestrator constructs InvocationRequest (see section 3) and appends `invocation_record` to TaskStore.
6. AgentRuntime executes ArchitectExecutor and returns AgentResult.
7. Orchestrator validates AgentResult artifact (apply rules in section 6).
8a. If validation passes and no ADR/safety required -> Orchestrator appends artifacts and transitions to READY.
8b. If ADR required but missing -> Orchestrator BLOCKS and notifies humans.
8c. If safety flags present -> Orchestrator transitions to PENDING_SAFETY_REVIEW and records policy_result.
9. When READY, Orchestrator may later enqueue Developer (DEVELOPMENT) after human approvals.

16) Interface definitions (summary)
---------------------------------
- InvocationRequest (Orchestrator → AgentRuntime): fields as section 3.
- AgentResult (AgentRuntime → Orchestrator): existing AgentResult with `output_artifacts` containing at least one `architecture_result` artifact whose `content` conforms to Architect contract.
- TaskStore artifacts: store `artifact_index`, `invocation_record`, `validation_result`, `policy_result`.

17) Acceptance criteria for the design
-------------------------------------
- Orchestrator can invoke Architect via AgentRuntime using only the fields in section 3.
- Architect results validated deterministically without manual inspection for schema correctness and identity matching.
- Tasks touching sensitive components are routed to Safety review; no task automatically proceeds to READY without safety clearance if policies require it.
- ADR-required cases block progression until ADR is present and validated.

18) Open questions
------------------
- Should Orchestrator prefer reuse of `run_id` on retry for crash-recovery, or should each retry create a new `run_id`? (Design recommends reuse for crash recovery.)
- Is there a preferred ADR artifact format or filename convention beyond `.agent/adr/*.md`? (Currently free-form.)
- Do we want a lightweight schema-checker library in Orchestrator for artifact validation (future implementation)?

19) Explicit non-goals
---------------------
- No implementation of Safety/Developer/QA Agents.
- No runtime sandboxing changes.
- No provider/LLM integration.
- No changes to AgentRuntime or WorkflowEngine code.

Validation vs. existing contracts
--------------------------------
- This design respects `architect.contract.json`, `orchestrator.contract.json`, `policies.json`, and `workflow.json`. It requires Orchestrator to perform additional validation and recording of invocation_record and validation_result but does not change existing contracts or workflow states.

Conclusion
----------
This integration reuses existing workflow states and AgentRuntime semantics. No new workflow states or ADRs are required. Orchestrator must implement deterministic validation, recording of invocation artifacts, and enforce policy-driven safety and ADR checks before transitioning to READY.

Contract consistency remediation (design-only)
--------------------------------------------
The following remediation sections resolve the CONTRACT CONSISTENCY issues found during STEP 4C design review. This is design-only; no code, contract, or workflow files are modified here. The decisions below define a single canonical vocabulary and the expected validation/ownership responsibilities for the upcoming implementation phase.

Problem 1 — Artifact type (canonical selection)
------------------------------------------------
Current: The implemented `ArchitectExecutor` emits artifacts with `artifact_type: "architecture_result"`. Existing contracts and workflow reference `architecture_proposal`, `adr_proposal`, `adr`, and `adr_reference` in different places.

Canonical: `architecture_result` is the canonical artifact_type for the Architect's primary output. It represents the complete structured Architect payload (see Architecture Result schema below). ADRs are separate artifacts and use `artifact_type: "adr"` (or `adr_proposal` when a human-readable proposal variant is produced). The Orchestrator must treat `architecture_result` as the authoritative single payload that may reference zero-or-more ADR artifacts.

Reason: The Architect produces a structured, machine-readable result that aggregates assessment, proposals, acceptance criteria, developer specification, and ADR necessity flags. Naming it `architecture_result` avoids ambiguity between a short `architecture_assessment` and a full proposal, and keeps ADRs explicitly separate objects that can be validated and signed independently.

Problem 2 — Artifact envelope vs Architecture Result payload
-----------------------------------------------------------
Canonical envelope shape (artifact):
- Required fields (Orchestrator-level validation MUST enforce):
  - `artifact_id` (string, UUID)
  - `artifact_type` (string) — e.g., `architecture_result`, `adr`, `acceptance_criteria`, `developer_task`
  - `task_id` (string) — the task this artifact belongs to
  - `run_id` (string) — agent runtime run id for audit/idempotency
  - `repository_revision` (string) — commit SHA referenced by this artifact
  - `producer` (string) — producing agent id (e.g., `architect`)
  - `created_at` (ISO timestamp)
  - `content` (object) — the payload, whose schema depends on `artifact_type`

- Optional envelope fields (may be present):
  - `checksum` (string) — artifact content sha256
  - `visibility` (string) — `orchestrator|runtime|public`
  - `metadata` (object) — small indexable metadata (e.g., `files_touched`)

ArchitectureResult payload (inside `content` for `artifact_type == "architecture_result"`):
- Required payload keys (Architect contract mapping MUST include):
  - `task_id` (string)
  - `run_id` (string)
  - `repository_revision` (string)
  - `architecture_assessment` (object)
  - `affected_components` (array[string])
  - `proposed_changes` (array[object])
  - `acceptance_criteria` (array[string])
  - `developer_specification` (object)
  - `adr_required` (boolean)
  - `status` (string) — e.g., `PROPOSAL` or `INCOMPLETE`

- Optional payload keys:
  - `adr_reference` (string|null) — artifact_id or repo-path of ADR artifact when produced
  - `safety_implications` (array[object])
  - `testing_strategy` (object)
  - `open_questions` (array[string])
  - `escalation` (object|null)

Ownership and validation responsibility:
- Artifact envelope creation/initial write: produced by the AgentRuntime/Architect executor and recorded in runtime storage. The `producer` field is set by the runtime/agent.
- Envelope integrity and schema validation: Orchestrator is responsible for validating the envelope (presence and types of required envelope fields) and then validating `content` against the Architect contract schema before accepting the artifact into the TaskStore. The Architect (executor) is responsible for producing `content` that attempts to conform to the Architect contract.
- The Orchestrator MUST reject artifacts with missing required envelope fields or with `content` that fails schema validation. Rejected artifacts must not be used for state transitions and must be recorded with validation failure reasons.

Problem 3 — Orchestrator allowed artifact types (minimal set)
-----------------------------------------------------------
Current: `.agent/contracts/orchestrator.contract.json` lists a narrow `allowed_artifact_types` set that omits architecture artifacts.

Canonical minimal set (Orchestrator must accept and index these types for Architect workflow):
- `architecture_result` — canonical architect payload (primary output)
- `adr` — ADR document artifact (machine-readable + human text)
- `adr_proposal` — optional alias for ADR drafts (human-readable proposal)
- `acceptance_criteria` — (if produced as independent artifact)
- `developer_task` — optional developer-ready task artifact

Reason: Keep the orchestrator's allowed types minimal yet sufficient for the Architect→READY lifecycle. The Orchestrator should validate these explicitly; do not accept arbitrary strings. Future artifact types must be added deliberately and documented.

Problem 4 — Workflow semantics and authority
-------------------------------------------
Clarification:
- What proves architecture analysis completed: an accepted `architecture_result` artifact with required payload keys and `status == "PROPOSAL"` and with `content.acceptance_criteria` and `content.developer_specification` present. If `content.adr_required == true`, an ADR artifact must also be present and validated.
- What proves ADR validation: a validated `adr` artifact (envelope present + content schema checked). Orchestrator applies an `adr_validated` predicate that returns true only after ADR artifact content passes validation.
- Actor responsibility and state transition authority: The Architect (agent) is the proposal author and producer of `architecture_result` and any `adr` artifacts. The Orchestrator is the sole authority to perform workflow state transitions. The transition `ARCHITECTURE -> READY` must be executed by the Orchestrator after it validates required artifacts and policies. The workflow `responsible` field in `.agent/workflows/workflow.json` currently lists `architect` for this transition; this should be considered an attribution of who must produce the artifacts, not who may perform the state change. Recommended corrective documentation (design-only): change the `responsible` value to `orchestrator` for the `ARCHITECTURE -> READY` transition in the authoritative workflow or document that `responsible: architect` means `artifact production responsibility` while `state transition authority` remains with `orchestrator`.

Problem 5 — ADR naming and relationships
----------------------------------------
Canonical vocabulary:
- `adr_required` (boolean) — in `architecture_result.content`, signals whether an ADR is required for the proposed change.
- `adr` (artifact_type) — an ADR artifact (machine JSON + human text). This is the authoritative ADR document when present.
- `adr_proposal` (artifact_type) — optional alias for ADR drafts (human-readable proposal). When present, Orchestrator treats it as an ADR artifact for validation but may require a final `adr` artifact for `adr_validated`.
- `adr_reference` (payload string) — inside `architecture_result.content` points to `artifact_id` of the ADR artifact or a repository path where the ADR resides.
- `adr_validated` (predicate/post_condition) — true when the Orchestrator has validated the ADR artifact content (schema, signatures, or minimal required keys) and recorded a validation_result artifact.

Relationship:
- `architecture_result.content.adr_required == true` implies the Orchestrator must find a referenced ADR (`adr_reference`) or a separate `adr` artifact attached to the task. If none present, Orchestrator must block the transition to READY and request ADR production.

Problem 6 — Runtime recovery API (minimum interface)
---------------------------------------------------
Required API (design-only):
- `get_result(run_id: str) -> AgentResult | None`

Behavior specification:
- If `run_id` exists and finished (status in {SUCCEEDED, FAILED, TIMED_OUT, CANCELLED}), return the stored `AgentResult` object immediately (without re-execution). The returned object must be the same canonical shape produced by `invoke` and include `status`, `started_at`, `completed_at`, `output_artifacts`, and `error` if any.
- If `run_id` exists and is still running (status == RUNNING or STARTING), return a representation reflecting the current status (ideally `{status: RUNNING, started_at: ..., run_id: ...}`) so the Orchestrator can poll or wait. This call must not block indefinitely.
- If `run_id` does not exist, return `None` or raise a `RunNotFound` error (documented). Preferred: return `None` to make existence check idempotent and simple.
- If the runtime previously returned a result for `run_id` and the Orchestrator re-requests, `get_result` must return the same result (preserve idempotency). The runtime must not re-execute the original invocation when `get_result` is called; it only returns stored outcomes.

Rationale: This single `get_result` API is sufficient for Orchestrator crash/recovery semantics and preserves the existing AgentRuntime idempotency model (single authoritative run per `run_id`). It avoids inventing a second idempotency mechanism in the Orchestrator.

Problem 7 — Responsibility model (explicit)
-----------------------------------------
Architect (producer role):
- Produces `architecture_result` and zero-or-more `adr` artifacts.
- Must NOT perform state transitions, authorizations, merges, deploys, or safety approvals.
- Must mark its result `status` as `PROPOSAL` (or `INCOMPLETE`/`FAILED`), never `APPROVED`.

Orchestrator (controller role):
- Invokes Architect via AgentRuntime.
- Validates envelope and payload against the Architect contract/schema.
- Records artifacts in TaskStore with full audit metadata.
- Determines and executes workflow transitions (e.g., `ARCHITECTURE -> READY`) after policy checks and validation.
- Issues retries and escalations per policy; routes to Safety/Human/Developer as required.

Architect MUST NOT:
- Transition workflow state independently.
- Authorize its own architecture for READY/DEVELOPMENT.
- Invoke Developer, QA, or Safety agents directly.

CONTRACT CONSISTENCY DECISIONS
------------------------------
For each affected concept provide: Current / Canonical / Reason

- architecture artifact type
  - Current: `architecture_result` (implementation) and `architecture_proposal`/`architecture_assessment` (contracts)
  - Canonical: `architecture_result`
  - Reason: Single authoritative, structured payload representing all architect outputs; disambiguates assessment vs ADR.

- ADR proposal artifact
  - Current: `adr` / `adr_proposal` referenced in workflow and contracts
  - Canonical: `adr` (artifact_type) for authoritative ADR documents; `adr_proposal` may be used as an alias for human-draft ADRs but is optional.
  - Reason: ADRs are separate documents; keeping `adr` as the canonical artifact avoids conflation with `architecture_result`.

- ADR reference
  - Current: `adr_reference` sometimes present in payloads
  - Canonical: `adr_reference` (string) inside `architecture_result.content` pointing to `artifact_id` or repo path
  - Reason: Allows `architecture_result` to reference ADR without embedding ADR content, supporting independent validation.

- Architecture Result schema
  - Current: Architect contract describes outputs but implementation returns `architecture_result` wrapped object
  - Canonical: `architecture_result` artifact envelope with `content` whose schema includes required payload keys listed above (task_id, run_id, repository_revision, architecture_assessment, affected_components, proposed_changes, acceptance_criteria, developer_specification, adr_required, status)
  - Reason: Clear separation of envelope vs content simplifies validation and audit.

- artifact envelope
  - Current: Loose; implementation wraps content but orchestrator checks vary
  - Canonical: explicit envelope with required fields (`artifact_id`, `artifact_type`, `task_id`, `run_id`, `repository_revision`, `producer`, `created_at`, `content`) and optional `checksum`, `visibility`, `metadata`.
  - Reason: Standardized envelope enables Orchestrator to validate artifacts deterministically and index metadata for search/audit.

- Orchestrator allowed artifact types
  - Current: narrow set that omits architecture artifacts
  - Canonical: include `architecture_result`, `adr`, `adr_proposal`, `acceptance_criteria` (optional), `developer_task` (optional)
  - Reason: These minimally support the Architect→READY lifecycle; Orchestrator validation will explicitly allow and schema-check these.

- workflow responsibility
  - Current: `ARCHITECTURE -> READY` `responsible: architect` in `workflow.json`
  - Canonical: `responsible: orchestrator` (state transition authority) with `artifact_production_responsibility: architect` documented; Alternately document the current `responsible` as `artifact_production` only. Strong recommendation: update `workflow.json` to set `responsible: orchestrator` for this transition or add a clarifying field.
  - Reason: Avoids mixing artifact production responsibility with authority to change workflow state.

- runtime recovery API
  - Current: AgentRuntime exposes `invoke()` and stores runs internally (`_runs`), but no public `get_result` API
  - Canonical: expose `get_result(run_id)` returning stored `AgentResult | None` and reflecting current run status if running
  - Reason: Orchestrator needs deterministic recovery semantics without re-execution; a single `get_result` API preserves runtime idempotency.

Notes on migration and compatibility
----------------------------------
- Because existing implementations and contracts are not modified here, the implementation phase must update `orchestrator.contract.json`, `architect.contract.json` (if necessary), and `workflow.json` to reflect the canonical vocabulary before deploying the integration.
- Orchestrator validation must accept `architecture_result` artifacts and treat `architecture_proposal` as an alias only if explicitly mapped in the updated contract.

## STEP 4C REMEDIATION REPORT

Artifact vocabulary:
PASS

Architecture Result schema:
PASS

Artifact envelope:
PASS

Orchestrator artifact contract:
PASS

Workflow responsibility:
FAIL

ADR vocabulary:
PASS

Runtime recovery design:
PASS

Architect authority boundary:
PASS

Orchestrator authority boundary:
PASS

Contract consistency:
FAIL

Implementation files modified:
NO

Trading files modified:
NO

Runtime files modified:
NO

Design files modified:
docs/architect_orchestrator_integration_design.md

Critical unresolved issues:
- `workflow.json` currently lists `responsible: architect` for the `ARCHITECTURE -> READY` transition. This conflates artifact production responsibility with state-transition authority. Recommend updating the workflow or adding a clarifying field; until that change is made the Orchestrator must treat `responsible` as `artifact_production_responsibility` only. This is the only remaining critical inconsistency blocking a strictly consistent contract model.
- `orchestrator.contract.json` must be updated before implementation to explicitly include the canonical artifact types listed above (`architecture_result`, `adr`, optional `adr_proposal`). Without that change the Orchestrator's strict allowed_artifact_types will reject architect artifacts.

Overall:
FAIL
