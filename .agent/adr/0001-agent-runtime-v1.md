# ADR 0001: Agent Runtime V1 (Design only)

Status: Proposed (STEP 3A)

Context
-------
The Orchestrator needs a provider-agnostic runtime to execute role-based agents (Architect, Developer, QA, Safety) while keeping workflow, policy, and retry decisions in the Orchestrator. The runtime must provide isolation, reproducibility, and artifact handling without granting agents live trading authority or secrets.

Decision
--------
Design the Agent Runtime with the following responsibilities:
- Accept structured AgentInvocation requests from Orchestrator.
- Provision read-only repository snapshots and isolated writable Developer worktrees.
- Execute role-specific agents via pluggable ProviderAdapters.
- Persist structured AgentResult artifacts and execution logs.
- Enforce timeouts and record failure metadata.
- Never provide secrets or push/merge authority; only return patches as artifacts for Orchestrator/operator review.

Consequences
------------
- Runtime acts purely as an execution layer; Orchestrator retains policy and state decisions.
- Implementation choices (containers, artifact store) deferred to STEP 3B.
