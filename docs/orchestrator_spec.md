
# Orchestrator — Specification (V2)

Purpose
-------
Orchestrator is the authoritative coordinator and task-state manager for the agent organization. In V2 it is explicitly NOT a code-authoring or repository-god component: it routes, validates, and enforces policies, then invokes stateless agent workers. Developers remain responsible for producing commits and pushing branches from their private worktrees.

Core Responsibilities (V2)
-------------------------
- Task-store and state machine enforcement (append-only, auditable). Orchestrator is the single source of truth for task routing and status.
- Deterministic policy evaluation (Policy Engine): run deterministic rules defined in `.agent/policies/` before LLM-based safety reasoning.
- Spawn or enqueue stateless agent workers with a specific read-only repo snapshot and task context.
- Validate machine-readable artifacts and checksums produced by agents and store artifacts references in the task-store.
- Enforce timeouts, retries, and escalation rules; prevent duplicate execution via locks.
- Notify humans/approvers when human sign-off is required.

### Agent Runtime Architecture (STEP 3A)

An Agent Runtime is a provider-agnostic execution layer the Orchestrator uses to run role-specific agents (Architect, Developer, QA, Safety). The runtime responsibilities are intentionally limited to execution lifecycle, isolation, artifact management, and observability. Orchestrator retains policy, workflow, and retry decisions.

Key constraints:
- No agent may receive live trading credentials, withdrawal keys, or automatic merge/deploy authority.
- Developers get an isolated writable `worktree_ref`; only Operator/Orchestrator can apply patches to protected branches.
- All runs must record the exact `repository_revision` (commit SHA) used.

See `docs/agent_runtime_design.md` for the full STEP 3A design.

What Orchestrator MUST NOT do in V1
----------------------------------
- Perform arbitrary repository modifications on behalf of agents (no direct code edits). 
- Merge into protected branches or enable live trading.
- Hold production credentials or perform risk-affecting actions autonomously.

Worker Model
------------
- Orchestrator provides a versioned read-only snapshot (commit SHA) and spawns a stateless worker for the role (Architect/Developer/QA/Safety). Workers run with ephemeral local working directories for the provided snapshot.
- Developer worker receives, in addition, a private writable worktree isolated for the task. This is the only workspace where code changes are made prior to push/PR.

Policy Engine
-------------
- Deterministic rules live under `.agent/policies/` and are evaluated first. Examples:
	- Any diff touching `execution_engine.py` requires Safety run.
	- Any addition of network credential patterns triggers immediate BLOCK.
- The Policy Engine is part of Orchestrator (deterministic component), not an LLM agent.

Branch / Worktree Guidelines
---------------------------
- Branch naming: `agent/dev/{task_id}/{short}` for Developer branches. Branches are created by Developer tooling; Orchestrator may record branch metadata and validate it.
- Worktree lifecycle: created for the task, ephemeral, and tagged with task_id and run_id. Push/pr creation is an explicit Developer action; Orchestrator records the PR metadata but must not inject commits.

Artifacts & Storage
-------------------
- Small, policy and contract artifacts live in repo under `.agent/` (contracts, policies, ADRs). Large binary logs live in external artifact store and are referenced by checksum.

Minimal CLI / API (V2)
----------------------
- `create_task(spec) -> task_id` (creates task record)
- `enqueue_role(task_id, role)` (Orchestrator enqueues worker)
- `validate_artifact(task_id, artifact_id)` (checksum + schema validation)
- `require_human_approval(task_id, reason)` (notifies humans)

Human approval and merge
------------------------
- Orchestrator records approvals and blocks transitions until required explicit human approval is present. Merge to protected branches remains a human action.

Next Steps (V2 focus)
---------------------
- Author `.agent/contracts/` (artifact schemas) and `.agent/policies/` (deterministic rules) and lock them before agents run.
- Implement minimal Orchestrator task-store and Policy Engine that enforces schema and deterministic rules (no branch writes yet).

Implementation notes (STEP 2)
----------------------------
- Runtime-only task state is stored in `.orchestrator/` (JSONL). This directory MUST be gitignored.
- The deterministic Policy Evaluator reads `.agent/policies/policies.json` and currently implements path-based and operation-based detectors. Conceptual conditions return `UNKNOWN` and must be handled conservatively by workflow logic.
- The Workflow Engine loads `.agent/workflows/workflow.json` and enforces only allowed transitions; invalid transitions raise errors.
- The Orchestrator foundation includes a filesystem-based lock at `.orchestrator/locks/` to avoid concurrent mutations. This is a single-machine protection and not distributed.

