# Agent Runtime Design (STEP 3A) — V1

Status: DESIGN ONLY — do NOT implement or invoke any model/provider.

## Overview

This document defines a provider-agnostic Agent Runtime abstraction that the Orchestrator will use to execute role-specific agents: Architect, Developer, QA, Safety. The runtime provides execution lifecycle, repository isolation, artifact handling, observability, and failure mechanics. The Orchestrator retains policy, workflow, and retry decisions; the runtime only executes and records runs.

## Core Concepts

- `AgentInvocation` (request): structured request the Orchestrator sends to Agent Runtime.
- `AgentResult` (response): structured result produced by the Agent Runtime and returned to Orchestrator.
- `RepositorySnapshot`: read-only snapshot reference (commit SHA + path) presented to agents.
- `Worktree`: writable private worktree provided to Developer instances only.
- `ProviderAdapter`: pluggable adapter to connect to different LLM/backends (design only).
- `AgentExecutor`: concrete execution unit that orchestrates a single invocation run.

## Structured Request (AgentInvocation)

Minimum fields (JSON-like):
- `task_id`: string (Orchestrator task id)
- `agent_role`: enum {ARCHITECT, DEVELOPER, QA, SAFETY}
- `repository_revision`: commit SHA (the exact commit to base work on)
- `worktree_ref`: optional path or worktree identifier (for Developer writable worktree)
- `working_dir`: path inside snapshot the agent should operate in (read-only unless writable worktree)
- `task_spec`: machine-readable task specification (string or structured object)
- `input_artifacts`: list of artifact references (small JSON, patch refs, file refs)
- `policy_context`: list or object with relevant deterministic policy flags/results
- `timeout_seconds`: integer
- `attempt`: integer (which attempt number, for observability)
- `correlation_id`: UUID (unique per orchestration run)

## Structured Result (AgentResult)

Minimum fields returned by runtime:
- `task_id`
- `agent_role`
- `run_id` (UUID)
- `status`: enum {CREATED, STARTING, RUNNING, SUCCEEDED, FAILED, TIMED_OUT, CANCELLED}
- `start_time`, `end_time` (ISO timestamps)
- `execution_meta`: {provider_profile, container_image, cpu, mem}
- `exit_code` (optional)
- `errors`: structured list (type, message, stack?)
- `output_artifacts`: list (artifact descriptors)
- `changed_files`: list (file paths + patch/diff reference)
- `proposed_next_state`: optional (e.g., `MERGE_PROPOSED`, `HUMAN_APPROVAL`)
- `metrics`: execution metrics (duration, provider-specific metrics — optional)

## Repository Isolation Model

- The runtime records and enforces the exact `repository_revision` (commit SHA) used. This SHA is stored in the AgentResult.
- All agents except Developer receive a read-only repository snapshot (could be a bind-mounted read-only path, container image, or temporary checkout).
- Developer receives a private writable worktree tied to a unique `worktree_ref`. The runtime must ensure this worktree is isolated and does not have push/merge authority onto protected branches.
- QA and Safety operate on the same read-only snapshot by default; they may be given a Developer's `worktree_ref` to inspect developer changes when required.
- The runtime must enforce that no agent has direct credentials to push/merge or to access live trading secrets. Any proposed patch is returned as an artifact (patch/diff reference), never auto-applied.

## Worktree / Patch Handling

- Developer changes are captured as version-controlled patch artifacts (diff/patch files) and recorded as `output_artifacts` with metadata: `{path, diff_ref, size_bytes, sha_patch}`.
- Patches are stored in runtime-managed storage (e.g., `.orchestrator/artifacts/{run_id}/`) and referenced in the AgentResult. Orchestrator decides whether to apply.
- Small artifacts (text ADRs, JSON reports, small patches) are version-controllable and can be checked into a review branch by operator action.
- Large artifacts (test binaries, coverage traces) are runtime-only and referenced by URI in the result; they are not stored in git.

## Agent Lifecycle States

Canonical states:
- CREATED: request accepted and persisted.
- STARTING: resources provisioned (container/worktree snapshot ready).
- RUNNING: agent execution in progress.
- SUCCEEDED: finished successfully and produced outputs.
- FAILED: execution ended with error.
- TIMED_OUT: runtime enforced timeout hit.
- CANCELLED: externally cancelled by Orchestrator or human.

Rationale: these states cleanly separate setup from execution and match failure handling needs. They map directly to `AgentResult.status` and to observability signals.

## Failure Handling (runtime responsibilities)

- Timeout handling: runtime enforces `timeout_seconds` and transitions to `TIMED_OUT`, captures partial artifacts and logs, returns structured error.
- Crash handling: capture exit code, stderr/stdout, stack traces where available, set status `FAILED`.
- Retry handling: runtime supports idempotent re-execution semantics (see Idempotency) but does NOT implement Orchestrator retry policy.
- Idempotent invocation: runtime must ensure runs with same `correlation_id` + `run_id` are not executed twice; if asked to re-run for the same `run_id`, return cached result unless explicitly forced.
- Duplicate execution protection: unique run identifiers prevent parallel duplicate runs; locks per `task_id` + `run_id` should be usable.
- Correlation IDs: Orchestrator must provide `correlation_id` to group sub-invocations; runtime propagates it to logs and metadata.

## Artifact Model

Artifact descriptor (JSON):
```
{
  "artifact_id": "<uuid>",
  "type": "patch|report|adr|binary|json",
  "path": "relative/path/or/storage-uri",
  "size": 12345,
  "sha256": "...",
  "version_controlled": true,
  "visibility": "orchestrator|runtime|public"
}
```

Classification:
1) Small version-controlled artifacts — text files, ADRs, small patches. Stored and optionally proposed as git changes.
2) Runtime-only artifacts — test logs, coverage, binary outputs; stored in runtime storage and referenced by URI.
3) Large CI artifacts — large traces, container images; stored externally (artifact store) and referenced.

## Security Boundary — MUST NOT provide

- Live exchange credentials or any secret that permits trading operations.
- Withdrawal credentials or keys.
- Production deploy keys or automatic deploy pipelines that can be triggered without explicit human approval.
- Automatic merge or push authority to protected branches.
- Unrestricted outbound network access by default (policy-controlled egress only).

Repository access is NOT equivalent to live trading access.

## Multiple Agent Instances and Provider Profiles

- The runtime design includes the notion of `agent_profile` which maps to provider/model configuration (CPU/GPU, container image, token use, provider adapter).
- Each invocation gets a deterministic `run_id` and is logged; multiple instances are supported by namespacing worktrees/artifact stores by `run_id`.
- Developer/QA parallelism: runtime can provision multiple isolated worktrees (`worktree_ref` per run) so multiple Developers or QA runs do not interfere.

## Provider Adapter (design only)

Abstract interfaces:
- `AgentRuntime` — top-level facade used by Orchestrator to submit invocations and collect results.
- `AgentExecutor` — executes a single `AgentInvocation` and returns `AgentResult`.
- `ProviderAdapter` — pluggable adapter that maps role-specific prompts/invocations to provider mechanics (tokens, API calls, container invocation). No providers implemented in STEP 3A.

## Observability

Minimum logging for every run:
- `task_id`, `run_id`, `agent_role`, `attempt`, `commit_sha`, `start_time`, `end_time`, `status`, `artifact_refs`, `error_information`.
Logs should be structured (JSON) and persisted to runtime logs and optionally to central logging.

## Proposed Interfaces / Classes (design-only)

- `AgentRuntime` (facade): `submit(invocation) -> run_id`; `get_result(run_id) -> AgentResult`; `cancel(run_id)`.
- `AgentExecutor`: `prepare_resources(invocation) -> ExecutionContext`; `execute(ctx) -> AgentResult`.
- `ExecutionContext`: `{worktree_ref, snapshot_path, temp_dir, env_vars, run_id}`.
- `ProviderAdapter` (abstract): `run_task(execution_context, invocation) -> AgentResult`.
- `ArtifactStore`: `store_artifact(bytes|path) -> artifact_ref`; `retrieve(artifact_ref) -> path`.
- `WorktreeManager`: `create_worktree(commit_sha) -> worktree_ref`; `cleanup(worktree_ref)`.
- `RunRegistry`: record run state transitions and prevent duplicate runs.

## Design constraints and guarantees

- The runtime enforces repository read-only snapshots and isolatable writable worktrees for Developer.
- The Orchestrator retains control over retries, escalation, and state transitions; runtime only executes and records.
- Agents never receive secrets or credentials granting access to live trading systems.

## Open design questions (for later STEP 3B)

- Execution sandboxing approach (containers vs lightweight chroot vs host bind-mounts).
- Artifact retention policy and storage backend choices.
- Network egress control model and default allowlists.
- Provider billing/usage telemetry integration.

## Next steps (after design approval — STEP 3B)

- Implement `ProviderAdapter` interface and one local-adapter for testing (no external API keys).
- Implement `AgentRuntime` skeleton with dry-run mode that records runs without contacting providers.

Document revision: 2026-09-07

## Implementation status (V1 - STEP 3B)

- Implemented: minimal `tools/agent_runtime.py` providing `AgentRuntime`, `MockAgentExecutor`, dataclasses for `InvocationRequest` and `AgentResult`.
- Implemented: `tests/test_agent_runtime.py` exercising invocation success, failure, timeout, idempotency, artifact structure, repository_revision recording, and security boundary checks.
- Not implemented: any provider adapters, container sandboxing, or networked model providers.
- Not implemented: artifact store; artifacts are in-memory descriptors only.

This implementation is intentionally minimal and local-only to validate execution flow and integration points. It does not contact external services or modify repository state.
