# Group B Zone-State Contract Evidence Audit

## Status

RESEARCH / PROPOSAL ONLY

- Group A: FROZEN / HUMAN APPROVED
- 15-minute bar contract: FROZEN / HUMAN APPROVED
- W = 5: FROZEN / HUMAN APPROVED
- minimum history = 1: FROZEN / HUMAN APPROVED
- center = median(member prices): FROZEN / HUMAN APPROVED
- Group B: NOT FROZEN
- Phase 2: NOT STARTED
- production behavior: unchanged

## 1. Purpose

This audit exists to determine what the repository evidence can and cannot support for a minimum sequential Zone-State Contract.

The objective is not to implement a Zone engine, not to freeze a Zone contract, and not to silently invent missing semantics. It is to identify the smallest Zone-state representation that is justified by existing evidence, and to separate that from the many technical rules that remain unresolved.

The core constraint is:

- the repository contains frozen Phase 1 inputs,
- it does not contain an authoritative runtime Zone-state implementation,
- therefore the minimum state contract must be derived from the frozen evidence and constrained by explicit uncertainty.

## 2. Evidence hierarchy

The evidence hierarchy used in this audit is:

1. Frozen human decisions
   - Group A swing definition
   - 15-minute UTC bar contract
   - W = 5
   - minimum history = 1
   - separate HIGH/LOW streams
   - current swing excluded from its own tolerance history
   - tolerance = median of selected legal prior same-direction absolute gaps
   - center = median(member prices)

2. Phase 1 specification and audit documents
   - [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
   - [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
   - [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
   - [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
   - [docs/phases/phase-01-zone-formation/BAR_CONTRACT_DECISION.md](BAR_CONTRACT_DECISION.md)

3. Source code and repository implementation
   - [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
   - [replay_runner.py](../../replay_runner.py)
   - [feature_signal_engine.py](../../feature_signal_engine.py)

4. Group B research and proposal documents
   - [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_ARCHITECT_PROPOSAL.md](GROUP_B_ARCHITECT_PROPOSAL.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL_AUDIT.md](GROUP_B_PROPOSAL_AUDIT.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_SECOND_ROOT_DECISION_BATCH_ANALYSIS.md](GROUP_B_SECOND_ROOT_DECISION_BATCH_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_TOLERANCE_ARCHITECTURE_COMPARISON.md](GROUP_B_TOLERANCE_ARCHITECTURE_COMPARISON.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_TOLERANCE_FORMULA_ANALYSIS.md](GROUP_B_TOLERANCE_FORMULA_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_HISTORY_WINDOW_ANALYSIS.md](GROUP_B_HISTORY_WINDOW_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_WINDOW_CALIBRATION_ANALYSIS.md](GROUP_B_WINDOW_CALIBRATION_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_W_MINIMUM_HISTORY_FINAL_ANALYSIS.md](GROUP_B_W_MINIMUM_HISTORY_FINAL_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md](GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_COMPARISON.md](GROUP_B_ZONE_GEOMETRY_COMPARISON.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_CENTER_CALIBRATION_ANALYSIS.md](GROUP_B_CENTER_CALIBRATION_ANALYSIS.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_CENTER_HUMAN_DECISION.md](GROUP_B_CENTER_HUMAN_DECISION.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md)
   - [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md)

5. Reproducible research
   - bounded exploratory simulation under a single-active-seed analysis model
   - documented in [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md)

6. Reasoning / proposal
   - all remaining contract ideas below are proposal only and must not be frozen

## 3. Frozen inputs

The following are already frozen and treated as fixed inputs for this audit:

- Group A swing definition
- 15-minute UTC bar contract
- W = 5
- minimum history = 1
- HIGH and LOW remain separate
- current swing excluded from its own tolerance history
- tolerance = median of selected legal prior same-direction absolute gaps
- Zone center = median(member prices)

These remain the only authoritative inputs for the minimum Zone-state research.

## 4. Existing repository evidence

### 4.1 What exists

The repository contains:

- a canonical replay and historical reconstruction path in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
- time-order validation in [replay_runner.py](../../replay_runner.py)
- deterministic canonical event ordering and validation in [feature_signal_engine.py](../../feature_signal_engine.py)
- multiple research and governance documents analyzing the root decisions for Zone creation, membership, geometry, and member-set update semantics

### 4.2 What does not exist

The repository does not contain an authoritative production Zone-state engine, runtime Zone object, or final sequential state machine that defines:

- Zone identity
- multi-Zone active selection
- overlap semantics
- merge semantics
- lifecycle transitions
- snapshot semantics
- persistent Zone state serialization
- final member-set mutation law

No production code in the current repo was identified as the authoritative Zone-state implementation. The existing code is research and orchestration oriented, not a final Zone runtime contract.

## 5. Minimum state analysis

| State element | Evidence | Classification | Why |
|---|---|---|---|
| direction | frozen HIGH/LOW separation; same-direction tolerance history | Required by frozen evidence | Zone logic is defined within same-direction streams. Without direction, the tolerance and membership rules cannot be applied coherently. |
| member observations | median(member prices) requires actual member set; creation and membership analysis refer to member observations | Required by frozen evidence | The center statistic is impossible without a member set. The repo repeatedly distinguishes member observations and candidate/valid Zone states. |
| candidate / seed state | creation rule says first eligible same-direction swing is seed/candidate and does not create a valid Zone | Required by frozen evidence | This is the explicit causal state boundary already approved. |
| valid Zone state | creation rule says valid Zone emerges on second qualifying same-direction swing | Required by frozen evidence | This is the required state transition boundary already documented. |
| center value | center = median(member prices) | Required by frozen evidence | It is an explicitly frozen derived value and necessary for membership evaluation. |
| tolerance value used for evaluation | W=5 history, minimum history=1, causal same-direction gap history | Required by frozen evidence | This is a required input to membership evaluation under the approved rule. |
| eligibility / causal timestamp reference | causal ordering and no-lookahead requirement | Required for deterministic implementation but unresolved | The repo requires causal ordering, but the exact Zone-object timestamp fields are not yet frozen as a complete schema. |
| zone width / lower-upper bounds | no frozen geometry or width rule | Not currently justified | No final width, envelope, or bounds semantic exists in the current evidence. |
| overlap state | no frozen overlap semantics | Not currently justified | Overlap and conflict resolution are unresolved root decisions. |
| merge state | no frozen merge semantics | Not currently justified | Merge is listed as unresolved and is not in the present frozen contract. |
| lifecycle state | no frozen lifecycle semantics | Not currently justified | Zone validity, invalidation, expiry, and continuity are not frozen. |
| mutable vs immutable center | median center is frozen as a statistic, but update timing is unresolved | Required for deterministic implementation but unresolved | The statistic is frozen, but whether the center is recomputed at each admitted member is not. |
| historical snapshots | no frozen snapshot rule | Optional / derived | Might be useful for replay determinism, but no snapshot contract is currently specified. |
| zone identity | no frozen identity semantics | Not currently justified | The repo does not define persistent Zone identity, ownership, or selection semantics. |
| multiple simultaneous zones | no frozen multi-zone semantics | Required for deterministic implementation but unresolved | The repository does not provide enough evidence to declare whether there may be more than one active Zone in one direction. |

## 6. Sequential event analysis

| Question | Evidence | Status | Blocking impact |
|---|---|---|---|
| What existing Zones are eligible to be considered? | No frozen multi-zone or lifecycle rule exists. | Unresolved / human decision required | Blocks any active Zone selection rule. |
| In what order are they evaluated? | Only causal ordering is frozen; no Zone queue or evaluation order is defined. | Unresolved / human decision required | A sequential state machine cannot define a valid update order without this. |
| What exactly constitutes membership? | Narrow membership rule exists for a valid Zone: abs(incoming_price - current_zone_center) <= current_tolerance | Established by evidence | This constrains membership evaluation, but only for the current narrow rule. |
| If membership succeeds, does the swing become a new member? | The repo distinguishes member observations and candidate/valid Zone states, but does not freeze update semantics. | Candidate design | Blocks member-set mutation law. |
| If membership succeeds, does the center change? | center = median(member prices), but update timing is not frozen | Strongly implied | Does not yet define whether center is recomputed after every admission. |
| If membership fails, is a new Zone created? | creation rule says valid Zone requires second qualifying same-direction member | Established by evidence | This is a frozen creation boundary but not a full lifecycle rule. |
| Can more than one Zone exist simultaneously? | no frozen rule | Unresolved / human decision required | Major state-machine blocker. |
| If multiple Zones qualify, what is the tie-break? | no frozen rule | Unresolved / human decision required | Blocks deterministic multi-zone behavior. |
| Can Zones overlap? | no frozen rule | Unresolved / human decision required | Blocks geometry and active-state semantics. |
| Can Zones merge? | no frozen rule | Unresolved / human decision required | Blocks state transitions and membership conflict resolution. |
| Can a Zone ever disappear? | no frozen lifecycle semantics | Unresolved / human decision required | Blocks lifecycle contract. |
| Can historical membership change? | no frozen update law | Unresolved / human decision required | Blocks result mutation semantics. |
| Is Zone identity persistent? | no frozen identity semantics | Unresolved / human decision required | Blocks stable Zone tracking across events. |
| What information must be snapshotted for replay determinism? | canonical ordering and frozen inputs exist; exact Zone snapshot fields are not defined | Required for deterministic implementation but unresolved | Blocks reproducible state tracing. |

## 7. Candidate minimal contract

The following is the smallest contract that is defensible from current evidence. It is proposal only and must not be frozen.

### Candidate minimal Zone record (proposal only)

```text
ZoneRecord {
  direction: HIGH | LOW,
  state: CANDIDATE | VALID,
  creation_reference: {seed_index, trigger_index, time},
  member_refs: [member observation references],
  member_prices: [prices],
  center: median(member_prices),
  tolerance_used_for_membership: float | null,
  creation_tolerance_history: [prior legal same-direction gaps],
  causal_order: canonical replay order / eligibility time
}
```

### Why this is the minimum defensible proposal

- direction is required by frozen same-direction separation
- state is required because the repo explicitly distinguishes seed/candidate from valid Zone
- member references + prices are required to compute the frozen center statistic
- center is required because membership evaluation uses current_zone_center
- tolerance history is required because membership is evaluated using current_tolerance derived from prior legal same-direction gaps
- causal order is required because the repo is explicit about causal ordering and no lookahead

### What remains proposal-only

The following are not established by evidence and should remain clearly marked as proposal-only:

- whether the Zone object is mutable after creation
- whether member sets are append-only, fixed, or recomputed
- whether Zones have identity over time
- whether there can be multiple active Zones in one direction
- whether a Zone can expire, merge, or be invalidated
- whether overlap is legal or invalid
- whether lower/upper bounds or widths are part of the contract

## 8. Unresolved root decisions

### 8.1 Root decisions that remain unresolved

1. Active-zone selection
   - one active Zone per direction or many active Zones?
   - no evidence yet justifies a single answer.

2. Zone identity
   - does a Zone persist by identity across later observations?
   - no evidence yet defines this.

3. Membership update semantics
   - append-only, fixed creation membership, recompute, or dynamic add/remove remain unresolved.
   - the bounded exploratory simulation is not a full proof for any of them.

4. Geometry and width semantics
   - no frozen width, envelope, or interval rule exists.

5. Overlap and merge semantics
   - unresolved and not currently justified by evidence.

6. Lifecycle semantics
   - no frozen issue of invalidation, expiry, replacement, or closure exists.

### 8.2 Derived decisions

These are downstream from the root decisions above and should not be treated as primary decisions:

- whether the center is recomputed after each admission
- whether the member list is append-only or fixed
- whether a new member changes the active Zone identity
- whether historical membership can be altered after acceptance
- whether future events can join or split an existing Zone

## 9. Governance status

- Group A: FROZEN / HUMAN APPROVED
- 15-minute bar contract: FROZEN / HUMAN APPROVED
- W = 5: FROZEN / HUMAN APPROVED
- minimum history = 1: FROZEN / HUMAN APPROVED
- center = median(member prices): FROZEN / HUMAN APPROVED
- Group B: NOT FROZEN
- Phase 2: NOT STARTED
- production behavior: unchanged

## 10. Recommendation for the next decision gate

The smallest next technical decision that must be resolved before a Zone-State implementation can be specified is:

- the active Zone identity and selection model

This is the most direct blocker because the repository has frozen the creation boundary and the membership metric, but it has not frozen:

- whether one or many Zones can exist in the same direction
- how Zone identity is retained across later observations
- how multiple candidate Zones are evaluated deterministically
- whether overlap or merge is allowed

Without this decision, any Zone-state contract remains under-specified and cannot be implemented as a final, reproducible state machine without inventing unsupported behavior.

## 11. Final conclusion

The repository evidence supports a minimal conceptual Zone state, but only as a constrained proposal. The minimum defensible state center is:

- direction,
- candidate-valid state,
- member references and member prices,
- center,
- tolerance context,
- canonical ordering / causal reference.

This is not a frozen Zone-State Contract.

The repository does not currently contain authoritative production Zone-state behavior. The current evidence supports a narrow research baseline only, not implementation or freeze.
