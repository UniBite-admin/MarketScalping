# Agentic Development Architecture — Design (V2)

Summary
-------
This V2 design refines the previous proposal to enforce strict separation of responsibilities, reduce Orchestrator power, require explicit human gates for high-risk actions, and establish machine-readable agent contracts as the first implementation artifact. It is design-only: no code changes are made here.

Key V1 Corrections (enforced for V2)
------------------------------------
- Orchestrator is a coordinator (coordination, state, routing). It MUST NOT perform arbitrary repository modifications or act as a "god component." Developer produces code; Architect produces ADRs; QA and Safety validate.
- Developers receive a read-only snapshot plus a private writable worktree (isolated branch/worktree). Branch pushes are Developer actions mediated by Orchestrator, not performed by Orchestrator itself in V1.
- Architect produces ADR proposals; ADRs become binding only after QA/Safety review and Orchestrator validation (not by Architect alone).
- Safety Agent can block changes; it cannot unilaterally declare a change safe for live trading without explicit human approval.
- Deterministic policy rules (Policy Engine) may block or require review automatically; these are deterministic and do not rely on LLM judgment.
- Agents are stateless workers in V1; Orchestrator stores task state and artifacts. Repository is the canonical memory.

Locked Decisions (V1)
---------------------
- 5 agents: Orchestrator, Architect, Developer, QA, Safety (locked).
- Repository = shared project knowledge (locked).
- Orchestrator = coordinator, not developer (locked).
- Architect = independent agent (locked).
- Developer = production-code writer (locked).
- QA = independent verifier (locked).
- Safety = independent safety verifier/blocker (locked).
- No agent may merge protected branches (locked).
- No development agent has live trading credentials (locked).
- Deterministic policies can block workflows independent of LLM outputs (locked).
- Human only enters high-risk approval gates (locked).
- Financial-state ownership is NOT decided yet (deferred).

High-level Principles
---------------------
- Least privilege: only Developer agents hold write-capable worktrees; Orchestrator coordinates and validates.
- Deterministic policy layer: policy rules live in `.agent/policies/` and run before or alongside Safety reasoning.
- Machine-readable contracts: agent contracts and artifact schemas live in `.agent/contracts/` and are the canonical API between agents.
- Stateless workers: Architect/Developer/QA/Safety are stateless per-run workers; Orchestrator holds global state.

Agent Roles & Contracts (concise)
--------------------------------
Each agent has a precise contract (input artifacts, output artifacts, forbidden actions). Contracts are machine-readable JSON schemas under `.agent/contracts/` (see Implementation plan). Key points:
- Architect: input: task, repo_snapshot, ADR history; output: ADR proposal JSON + human summary; forbidden: direct code changes.
- Developer: input: approved ADR + acceptance criteria; output: implementation artifact (branch name, commit SHA, files_changed metadata) and tests; may create branch in private worktree and push via developer tooling; Orchestrator mediates PR metadata but does not itself modify code.
- QA: input: implementation artifact + ADR; output: reproducible test artifact, defects with repro steps.
- Safety: input: implementation + tests + ADR; output: safety report (pass/block, required changes). Safety can block progression but cannot merge or enable live trading.
- Orchestrator: input/output: task-store, routing, policies, artifact validation. Orchestrator triggers agents and enforces state machine and policies.

Policy Engine
-------------
- Deterministic policy rules are first-class. Examples:
  - Any change touching `execution_engine.py` triggers mandatory Safety review.
  - Adding `withdraw` or credentials triggers immediate BLOCK.
- Policies are encoded in `.agent/policies/` and evaluated by Orchestrator before LLM-based Safety reasoning.

Repository / Workspace Model
--------------------------
- Read-only snapshot: for every task Orchestrator records a `repo_revision` (commit SHA) and provides that snapshot to agents.
- Developer private writable workspace: Developer agent receives an isolated worktree (e.g., via `git worktree` or local clone) for the assigned `task_id`. The branch naming convention: `agent/dev/{task_id}/{short}`.
- Worktrees are ephemeral and associated with the task; pushing or PR creation is a Developer action; Orchestrator only records metadata and validates artifacts and signatures.
- No agent writes directly to protected branches; merges are human-operated.

Agent Runtime & Invocation (V1 simplicity)
-----------------------------------------
- Agents are stateless worker processes spawned or triggered by Orchestrator. Architect need not be persistent. Orchestrator spawns a worker with the provided repo snapshot and task context.
- Invocation: Orchestrator writes a task entry and enqueues the role. A worker picks up the task, fetches the snapshot, runs, and writes artifacts to `reports/{task_id}/` (external artifact store preferred) and updates task-store with checksums.
- Crash/timeouts: Orchestrator enforces timeouts, retries up to configured limits, then escalates.

Communication Model
-------------------
- Primary channels: task-store + artifacts + GitHub issues/PRs + labels + CI checks.
- Handoff artifact (minimal schema) is machine JSON with fields: task_id, agent_id, run_id, repo_revision, branch, files_changed (paths + checksums), output_artifacts (ids), status, next_action.
- Orchestrator validates and indexes artifacts so the next agent can fetch and verify without human copy-paste.

Task State Machine (authoritative, trimmed)
------------------------------------------
States (summary): BACKLOG → TRIAGE → ARCHITECTURE → READY → DEVELOPMENT → CI → QA → SAFETY → HUMAN_APPROVAL → MERGE → DEPLOY → MONITOR → DONE/ESCALATED/FAILED
For each state Orchestrator enforces entry conditions, responsible agent, required artifacts, allowed next states, and retry/escalation rules.

Handoff Protocol (minimal)
--------------------------
- Required fields: task_id, agent_id, run_id, parent_artifact_ids, repo_revision, branch, files_changed[], status, tests (commands), risks, next_action, timestamp, checksum.

Independent Verification
------------------------
- Every agent consumer must verify producer claims by re-fetching and checksum-validation; e.g., QA re-runs tests using exact commands recorded in implementation artifact.

Storage & Artifacts (policy)
----------------------------
- Only stable, long-lived artifacts are stored in the repository (`.agent/contracts/`, `.agent/policies/`, ADRs).
- Large CI, test, and agent logs are stored in an external artifact store (or `reports/` kept outside git) and referenced by checksum in the task-store.

First Implementation Order (V2 recommended)
------------------------------------------
STEP 1: Define and commit `.agent/contracts/` JSON schemas and `.agent/policies/` deterministic rules (LOCK BEFORE AGENTS RUN)
STEP 2: Implement Orchestrator minimal task-store and policy evaluator (no code pushes, no branch creation)
STEP 3: Implement stateless agent worker harnesses (Architect/Developer/QA/Safety) that read contracts and write artifacts (no merging)
STEP 4: Add Developer private worktree flow and branch naming documentation; allow Developer to produce implementation artifacts
STEP 5: Integrate CI/QA/Safety artifact verification and human approval gates
STEP 6: After vetting, carefully enable mediated branch push/PR creation; merging remains human.

Smallest Correct First Implementation
------------------------------------
- Create `.agent/contracts/` and `.agent/policies/` with machine-readable schemas and deterministic rules. This establishes the agent "language" before any agent performs writes.

Risks and Open Questions
------------------------
- Overcentralization risk if Orchestrator later accrues write privileges — policy must prevent this for V1.
- Where to store large artifacts (external vs repo) — decision needed.
- Financial-state authority and commit protocol deferred to Architect investigation task.

Decisions to Lock / Defer
-------------------------
- LOCK: 5 core agents, Orchestrator as coordinator only, no agent merges, deterministic policy layer, human gate for high-risk actions.
- DEFER: exact financial-state ownership, multi-signature human approval requirements, external artifact store selection.

Next Step (recommended)
-----------------------
- Produce the machine-readable JSON schemas for the agent contracts and deterministic policies (STEP 1). This is the correct first implementation artifact.

---
This file replaces the previous V1 baseline and records the V2 corrections requested. It is design-only and contains the locked decisions and the recommended minimal implementation order.
