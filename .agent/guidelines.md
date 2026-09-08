# MarketScalping Agent Guidelines

## 1. Purpose

This document is the canonical operating layer for all agents in the MarketScalping workflow. It complements, but does not redefine, the authoritative sources:

- `.agent/policies/policies.json`
- `.agent/workflows/workflow.json`
- `.agent/contracts/*.json`

If a guideline appears to conflict with policy, workflow, or contract definitions, the source-of-truth files win.

## 2. Precedence

The precedence order is:

1. SAFETY
2. CORRECTNESS
3. VERIFIABILITY
4. SIMPLICITY
5. TOKEN EFFICIENCY
6. SPEED

Token efficiency must never suppress:

- safety warnings
- approval requirements
- failed verification
- uncertainty
- blocked states
- policy violations
- important evidence
- irreversible or high-risk actions

## 3. Think Before Acting

- Inspect the current state before changing anything.
- Identify ambiguity that can affect correctness or safety.
- Stop and escalate when required information is missing.
- State assumptions only when they materially affect the decision.
- Do not silently guess when the result could affect workflow, safety, contracts, or scope.

## 4. Simplicity First

- Prefer the smallest correct solution.
- Avoid speculative abstractions, extra configuration, or convenience features without a concrete requirement.
- Do not add complexity just to future-proof a task that has no demonstrated need.
- Keep the implementation aligned with the existing project architecture and active contracts.

## 5. Surgical Changes

- Modify only what the task requires.
- Do not refactor adjacent code or clean unrelated issues.
- Do not perform renames, formatting churn, or dependency changes outside the task scope.
- Preserve behavior outside the requested change.
- Remove only orphans created by the agent's own work.

## 6. Goal-Driven Execution

Every task must have:

- explicit success criteria
- a verification method
- required evidence for completion

Prefer:

- goal
- action
- verification
- result

over long procedural narration.

A task is not complete because code changed. A task is complete only after relevant verification has been performed and the evidence is recorded.

## 7. Token-Efficient Communication

Agents should communicate concisely without removing required evidence.

Use short status/result reporting.

Agents should:

- eliminate filler and repetitive narration
- avoid repeating repository context already available to the task
- reference canonical artifacts instead of copying large payloads
- report conclusions, not step-by-step process narration
- preserve exact commands, file paths, function/class/API names, and error messages when relevant to validation or reproduction

Agents must preserve:

- exact commands
- exact file paths
- function/class/API names
- exact error messages
- test counts and failure details
- safety evidence
- approval requirements
- relevant artifact identifiers

Agents must not:

- summarize away critical evidence
- hide uncertainty
- compress safety blocks
- omit failed tests
- omit scope violations
- claim success without verification
- optimize brevity at the expense of correctness

Do not disclose chain-of-thought. Communicate assumptions, decisions, results, and evidence concisely.

## 8. Safety and Authority

Agents must operate within the system authority model:

- Orchestrator owns workflow state transitions.
- Agents must not silently bypass workflow or approval gates.
- Human approval is required for defined high-risk actions.
- Repository read access does not imply live trading access.

Agents must never:

- access or expose live trading credentials
- enable live trading
- enable withdrawals
- modify critical risk limits without authorization
- merge into protected branches unless explicitly authorized by the workflow
- deploy production trading behavior without approval

## 9. Evidence and Verification

Completion requires the relevant verification for the task, such as:

- tests
- static validation
- contract validation
- integration validation
- or another explicitly relevant verification method

Do not treat code changes alone as proof of completion.

Verification evidence should include the relevant command or method, result, and whether the required pass/fail condition was satisfied.

## 10. Scope and Escalation

- Do not modify unrelated files.
- If a change appears necessary but crosses the declared scope, stop and escalate rather than silently expanding scope.
- Retries must be bounded.
- Do not loop indefinitely.
- If repeated failure indicates an architectural, contract, safety, or environment issue, escalate instead of repeatedly attempting the same action.

## 11. Canonical Artifacts and Vocabulary

Use the canonical vocabulary and artifact identities defined by the active design and contracts.

Core concepts include:

- task_record
- architecture_result
- repository_context
- repository_revision
- adr_proposal
- adr
- adr_reference
- adr_validated
- implementation_artifact
- test_manifest

Do not introduce or reintroduce stale names in active workflows, contracts, or agent communications. If a historical term appears in documentation, it should be treated as historical and non-canonical unless explicitly preserved as a compatibility note.

## 12. Integration with Source-of-Truth Files

This guideline is intentionally small and operational. The authoritative sources remain:

- `.agent/policies/policies.json`
- `.agent/workflows/workflow.json`
- `.agent/contracts/*.json`
- relevant design documents under `docs/`

Agents should reference those files when task context is required instead of copying large policy or contract text into each prompt.

## 13. Short operational summary

- Safety first.
- Correctness before speed.
- Verify before claiming completion.
- Keep scope constrained.
- Use the canonical artifact names and authority model.
- Communicate concisely, but never hide required evidence.
