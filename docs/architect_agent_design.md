Architect / Technical Lead Agent — Design (V1)
===========================================

Purpose
-------
This document defines the V1 contract and operational design for the Architect / Technical Lead Agent. This is a design-only specification; the Architect Agent is NOT implemented here.

Design goals
------------
- Produce machine- and human-readable architecture outputs that enable safe, testable development.
- Keep the agent read-only and non-actionable: it must never change production code or authorize runtime effects.
- Ensure the Architect's outputs are auditable and traceable to repository facts.

Input contract (schema summary)
--------------------------------
- `task_id`: string — Orchestrator provided task identifier
- `run_id`: string — Orchestrator-provided run id for idempotency
- `repository_revision`: string — commit SHA
- `task_spec`: object — full task spec describing requested change
- `repository_context`: object — minimal snapshot: list of files, test map, entry modules
- `architecture_references`: array — docs and ADRs to consult
- `prior_adrs`: array — previous ADR ids or paths
- `policy_context`: object — governance/policy hints
- `constraints`: object — safety and non-functional constraints
- `previous_agent_artifacts`: array — earlier artifacts if any

Output contract (schema summary)
---------------------------------
- `architecture_assessment`: concise assessment with references
- `affected_components`: list of component identifiers and files
- `proposed_changes`: enumerated proposals (high-level; no code)
- `interfaces_contracts`: interface definitions and examples
- `data_flow_impact`: before/after dataflow sketches
- `state_ownership_impact`: mapping of authoritative owners per state
- `risks`: enumerated risks with severity and mitigation
- `safety_implications`: stepwise checklist for Safety
- `testing_strategy`: test types, targets, and quick commands
- `acceptance_criteria`: testable pass/fail items
- `developer_specification`: file-by-file tasks, sample diffs, unit/integration tests
- `adr_required`: boolean
- `adr_reference`: path or null

ADR rules (deterministic)
--------------------------
Architect MUST produce an ADR when any of the following apply:

- Architectural boundary changes: adding/removing subsystems, introducing new persistent services, or splitting service responsibilities.
- State ownership changes: moving authoritative data or responsibilities between modules (e.g., accounting becomes authoritative for ledger).
- Security boundary changes: any change that expands credentials, privileges, network access, or secret handling surface.
- Workflow/policy changes: changes that affect orchestrator gates, safety approvals, or authorization models.
- New persistent subsystem: databases, schema changes, migration plans.
- Major interface changes: breaking API changes exposed to other components or external consumers.

Architect NOT required to generate ADR for:

- Purely cosmetic refactors, non-functional improvements (performance tuning), or tests-only additions that do not change ownership or interfaces.

Handoff conditions
------------------
ARCHITECTURE → READY when:

- `architecture_proposal` artifact exists and is attached to the task.
- `acceptance_criteria` array is present and each item is testable (references tests or commands).
- `developer_specification` enumerates files and includes at least one example change and corresponding unit/integration test suggestions.
- If `adr_required` is true, an `adr_reference` must be provided.
- `risks` and `safety_implications` enumerated and an `owner` suggested.

READY → DEVELOPMENT (Orchestrator responsibility) — additional gating before Developer may be invoked:

- Human approvals and Safety sign-off recorded in the workflow metadata.
- QA acknowledges testing strategy and has a plan to validate acceptance criteria.

Developer handoff contents
-------------------------
The Developer receives an artifact bundle that minimally contains:

- Exact scope and file/line ranges to change.
- Interfaces to implement or modify with example signatures and input/output schemas.
- Acceptance criteria mapped to tests and commands to run.
- Suggested unit and integration tests, plus mock data examples.
- Any ADRs that must be respected or updated.
- Safety checklist and any additional approvals required.

Interaction with QA and Safety
----------------------------
Architect must provide:

- A compact `safety_implications` checklist with: what to verify, thresholds, failure modes, and rollback suggestions.
- `testing_strategy` with steps QA can run locally (commands) and what exact assertions must pass.

Failure and escalation policy
----------------------------
- If `repository_context` lacks required files or the Architect cannot answer a required question, mark result `INCOMPLETE` with explicit `missing` items.
- If the Architect detects safety-violating changes, produce `safety_block` artifact and escalate to human Safety review. The Orchestrator must not proceed to Development until Safety clears the block.

Quality checklist (Architect output validation)
--------------------------------------------
- All repository claims reference file paths and line ranges or clearly-stated assumptions.
- Acceptance criteria map to automated tests where possible.
- Developer tasks are actionable and contain all required inputs.
- ADRs include: context, decision, consequences, and alternatives considered.

Open design decisions (for future iterations)
--------------------------------------------
- Formal schema versioning for outputs (v1 chosen here; consider schema evolution policy).
- Artifact storage format and canonical URIs for `artifact_refs` (deferred to runtime/infra design).
