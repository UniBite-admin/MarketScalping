# Group B Single Active Zone Lifecycle Analysis

## 1. Objective

This analysis investigates the unresolved semantics required if the project adopts the research baseline:

> Single Active Zone per direction

This is a research-only assumption and must not be treated as a frozen decision.

The question is:

> What must happen when a direction already has one valid Zone and a new eligible same-direction swing arrives?

This research is intentionally constrained to the evidence currently present in the repository. It does not propose a new frozen rule, does not implement production logic, does not modify tests, and does not start Phase 2.

## 2. Frozen inputs

The following remain the authoritative frozen inputs for this analysis:

- Group A swing definition: FROZEN — HUMAN APPROVED
- 15-minute UTC bar contract: FROZEN — HUMAN APPROVED
- canonical replay ordering: FROZEN — HUMAN APPROVED
- no lookahead / causal eligibility: FROZEN — HUMAN APPROVED
- HIGH and LOW streams remain separate: FROZEN — HUMAN APPROVED
- W = 5 prior same-direction legal gaps: FROZEN — HUMAN APPROVED
- minimum tolerance history = 1: FROZEN — HUMAN APPROVED
- tolerance = median of selected legal prior same-direction absolute gaps: FROZEN — HUMAN APPROVED
- center = median(member prices): FROZEN — HUMAN APPROVED
- membership rule for a valid Zone:
  `abs(incoming_swing_price - current_zone_center) <= current_tolerance`
  FROZEN — narrow rule
- Zone creation rule:
  - first eligible same-direction swing = seed/candidate
  - valid Zone is created when a later same-direction swing qualifies as a member
  FROZEN — narrow rule

Important boundary:

- Group B as a whole remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- production behavior remains unchanged.

## 3. Repository evidence

The following repository evidence is directly relevant.

- [docs/ROADMAP.md](../../ROADMAP.md) clearly states that the current Phase 1 work is specification and governance work and that Phase 2 must not start while the current phase is still unresolved.
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md) records the narrow human-approved membership rule and the narrow Zone creation rule.
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md) repeats the same boundary explicitly: these rules are narrow and do not freeze zone identity, zone lifecycle, overlap, merge, or multiple-zone behavior.
- [docs/phases/phase-01-zone-formation/GROUP_B_ACTIVE_ZONE_IDENTITY_ANALYSIS.md](GROUP_B_ACTIVE_ZONE_IDENTITY_ANALYSIS.md) concludes that the repo does not provide authoritative evidence for a multi-zone identity / selection model.
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_EVIDENCE_AUDIT.md](GROUP_B_ZONE_STATE_CONTRACT_EVIDENCE_AUDIT.md) states that the repo provides evidence for candidate/seed state and valid Zone state, but does not provide a final Zone lifecycle or invalidation contract.
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md) warns against silently importing lifecycle rules, replacement semantics, or a closed member-set concept when the repo has not frozen them.
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) implements descriptive research logic; it is not a stateful production Zone engine.

Repository evidence summary:

- EVIDENCE-SUPPORTED: candidate and valid Zone are distinct states.
- EVIDENCE-SUPPORTED: the member set is a historical concept that must be computable from observed member prices.
- EVIDENCE-SUPPORTED: no-lookahead and causal ordering are required.
- UNRESOLVED: Zone lifecycle semantics beyond creation.
- UNRESOLVED: replacement, invalidation, retirement, and stale Zone handling.
- UNRESOLVED: active-zone selection when more than one same-direction Zone might coexist.

## 4. Existing-Zone member update evidence

### 4.1 Frozen facts

The following are FROZEN and directly constrain the lifecycle question:

- current_zone_center = median(member prices): FROZEN
- current_tolerance is derived from prior legal same-direction gaps: FROZEN
- an incoming same-direction swing is a member when:
  `abs(incoming_swing_price - current_zone_center) <= current_tolerance`
  FROZEN — narrow rule
- the first eligible swing becomes a candidate/seed and does not itself create a valid Zone: FROZEN — narrow rule
- a valid Zone is created when a second same-direction swing qualifies as a member: FROZEN — narrow rule

### 4.2 Evidence on adding a member

The repository evidence does not provide a direct frozen rule for the update operation after a valid Zone already exists.

Evidence status:

- EVIDENCE-SUPPORTED: the repo distinguishes candidate/seed state from valid Zone state.
- EVIDENCE-SUPPORTED: center is derived from member prices.
- EVIDENCE-SUPPORTED: the current tolerance comes from prior legal same-direction gaps, not from current-zone membership.
- UNRESOLVED: whether the member set is append-only after a valid Zone exists.
- UNRESOLVED: whether the center is recomputed when a new member is admitted.
- UNRESOLVED: whether the tolerance history is updated immediately after a new member is admitted or only when the next swing is evaluated.

The project explicitly warns that these are not frozen by the current human-approved rule set. This is documented in:

- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md)

### 4.3 Center update timing

Repository evidence does not freeze center update timing.

Status labels:

- FROZEN: center statistic is median(member prices).
- UNRESOLVED: when that statistic is recomputed after a new member is admitted.
- UNRESOLVED: whether the center is a historical snapshot or a live derived field.
- ASSUMPTION: many designs assume the center is re-derived after each member addition; this is not proven repository evidence.

This matters because the frozen membership rule depends on `current_zone_center`, but the repository does not define the mutation timing of that derived value after validation.

### 4.4 Tolerance-history update timing

Repository evidence is also silent on when the tolerance history must be updated once a valid Zone has accepted a new member.

Status labels:

- FROZEN: tolerance history uses prior legal same-direction gaps, not the current swing and not a future lookahead.
- FROZEN: current swing is excluded from its own tolerance history.
- UNRESOLVED: whether the newly admitted member contributes to future tolerance history immediately, after a later confirmation, or never.
- ASSUMPTION: any rule that updates tolerance history based on Zone membership is an assumption, not a frozen fact.

### 4.5 Conclusion on member update evidence

The repo gives a narrow and precise answer for creation, but not for the later mutation law of an existing Zone.

Therefore:

- FROZEN: membership test for a single valid Zone
- FROZEN: creation boundary for a valid Zone
- UNRESOLVED: member-set mutation law after Zone creation
- UNRESOLVED: center update timing
- UNRESOLVED: tolerance-history update timing

## 5. Non-member swing candidate semantics

Assume a direction already contains one valid Zone and a new eligible same-direction swing arrives. The repo does not freeze the semantics of the non-member case. The available choices must be treated as candidate research behaviors only.

### A. Retain existing Zone and discard/ignore the swing for Zone formation

Status: RESEARCH CANDIDATE

Reasoning:

- This is the least disruptive behavior under a single-active-zone model.
- It preserves the existing Zone as the active reference and avoids premature creation/refinement of a new state.
- It is consistent with the idea that a valid Zone is a stable reference until a human-approved lifecycle rule says otherwise.

Why it is not frozen:

- no authoritative doc specifies that a non-member swing is silently discarded without a candidate or seed state.
- no lifecycle rule says a valid Zone is indefinitely authoritative without being replaced or invalidated.

### B. Retain existing Zone and start a new candidate/seed

Status: RESEARCH CANDIDATE

Reasoning:

- This fits the already-frozen concept that the first eligible swing becomes a seed/candidate.
- It preserves the current valid Zone and creates a new candidate to track later opportunities.
- It is structurally simple if the project is exploring a single-active-zone baseline.

Why it is not frozen:

- the repo does not specify whether a non-member swing can be converted into a pending candidate while a valid Zone remains active.
- the repo does not define the coexistence rules between candidate state and valid Zone state.

### C. Close/invalidate existing Zone and make the new swing a seed

Status: RESEARCH CANDIDATE

Reasoning:

- This is a plausible single-zone baseline if the system treats the old Zone as stale or ended.
- It has a natural lifecycle interpretation.

Why it is not frozen:

- the repo contains no evidence for expiration, invalidation, stale-zone handling, or retirement semantics.
- any such rule would silently import a lifecycle contract the repo has explicitly not frozen.

### D. Replace the existing Zone

Status: UNRESOLVED / ASSUMPTION

Reasoning:

- This is a direct lifecycle + identity decision, not a frozen rule.
- It requires explicit decisions about whether a valid Zone can be retired, superseded, or replaced by a newer seed or newer member set.

Why it is not supported by evidence:

- no authoritative docs define replacement semantics.
- no code path implements replacement logic.
- no tests establish replacement timing or order.

### E. Another evidence-supported behavior

Status: UNRESOLVED

Reasoning:

- The repository does not provide an authoritative alternative behavior beyond the frozen membership and creation rules.
- Any additional behavior is necessarily a design assumption until a human-approved lifecycle rule is documented.

## 6. Candidate/seed coexistence evidence

This section separates facts from design assumptions.

### 6.1 Repository fact

The frozen creation rule already defines two states:

- seed/candidate = first eligible same-direction swing
- valid Zone = second qualifying same-direction member creates validity

This is explicitly documented in:

- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_EVIDENCE_AUDIT.md](GROUP_B_ZONE_STATE_CONTRACT_EVIDENCE_AUDIT.md)

### 6.2 What the repo does not justify

The repo does not establish any of the following:

- one valid Zone plus one pending seed: RESEARCH CANDIDATE, not frozen
- one valid Zone plus multiple pending seeds: RESEARCH CANDIDATE, not frozen
- no pending seed while a valid Zone exists: RESEARCH CANDIDATE, not frozen
- candidate/valid coexistence semantics under a single-active-zone baseline: UNRESOLVED

The critical distinction is:

- the repo supports a two-state creation boundary,
- it does not support a full lifecycle contract for simultaneous states.

### 6.3 Evidence-supported conclusion

The repository evidence supports:

- candidate and valid Zone are distinct states,
- candidate creation is causal and sequential,
- a valid Zone emerges after the second qualifying member.

The repository does not support any final rule for:

- whether a new candidate may coexist with an already valid Zone,
- whether only one candidate may exist,
- whether multiple candidates may exist,
- whether a valid Zone must be closed before a new candidate begins.

## 7. Replacement / invalidation evidence

The project explicitly distinguishes the minimal Zone-state concept from a full lifecycle model.

The following search of the authoritative design documents yields no evidence for the following lifecycle concepts:

- expiration
- invalidation
- replacement
- retirement
- stale Zone
- lifecycle termination

The repository language is explicit that these remain unresolved Group B questions. Evidence appears in:

- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_SEMANTICS_AUDIT.md](GROUP_B_ZONE_GEOMETRY_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_EVIDENCE_AUDIT.md](GROUP_B_ZONE_STATE_CONTRACT_EVIDENCE_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md)

Status labels:

- FROZEN: none of the lifecycle policies above are frozen
- EVIDENCE-SUPPORTED: a Zone may exist as a valid same-direction object once the second member qualifies
- UNRESOLVED: whether that Zone is later expired, invalidated, replaced, merged, or retired
- ASSUMPTION: any lifecycle rule imported from general trading intuition is not repository evidence

## 8. Temporal / no-lookahead implications

### 8.1 Earliest legal transition moment

The earliest legal replay timestamp at which a transition could occur is the moment a new eligible same-direction swing becomes observable and is processed in causal ordering.

This means:

- the candidate/seed status is determined only after the current observation is confirmed and eligible.
- no future data can influence the decision.
- the candidate must not be evaluated with information that is not yet visible in causal replay order.

This is consistent with the frozen no-lookahead rule and with the exact wording in the authoritative governance files.

### 8.2 What is not yet justified

The repo does not justify any of the following as legally supported transitions:

- invalidation of an existing valid Zone before the new swing is processed
- replacement at the same timestamp as a non-member swing
- seed creation while a valid Zone remains active without explicit governance
- stale-zone retirement without a rule that defines stale

Therefore:

- EVIDENCE-SUPPORTED: causal ordering and eligibility timing are defined
- UNRESOLVED: when a valid Zone may be invalidated or replaced
- UNRESOLVED: whether a seed may coexist with an existing valid Zone
- ASSUMPTION: any immediate transition triggered by a non-member swing is not evidence-supported until a lifecycle rule is approved

## 9. Minimal evidence-supported state machine

The smallest state machine justified by repository evidence is narrow and intentionally minimal.

### 9.1 State machine supported by evidence

For one direction-specific stream, the repo supports the following minimal model:

1. NO_ACTIVE_ZONE
   - no current valid Zone exists
   - an eligible swing may become a seed/candidate

2. CANDIDATE / SEED
   - the first eligible same-direction swing exists in candidate state
   - it is not yet a valid Zone

3. VALID_ZONE
   - the second same-direction swing qualifies as a member
   - the Zone becomes valid under the approved creation rule

### 9.2 What is blocked

The following transitions remain blocked by the evidence:

- VALID_ZONE -> INVALIDATED
- VALID_ZONE -> REPLACED
- VALID_ZONE -> RETIRED
- VALID_ZONE + CANDIDATE coexistence semantics
- CANDIDATE -> VALID_ZONE while another valid Zone remains active, without explicit human decision
- multiple active Zones in the same direction
- merge / overlap / stale-zone resolution

### 9.3 Minimal conclusion

The evidence supports only a creation-state machine, not a full lifecycle state machine.

So the minimal justified state machine is:

- seed/candidate exists if there is no valid Zone yet
- a valid Zone is created only after the second qualifying same-direction member is admitted
- once a valid Zone exists, the repo does not define what may happen next without an unapproved lifecycle rule

Any larger state machine is therefore:

- RESEARCH CANDIDATE
- ASSUMPTION
- not repository evidence

## 10. Unresolved root decisions

The following root decisions remain unresolved and must be treated as open research topics, not frozen decisions:

1. Existing Zone membership update semantics after a valid Zone exists
2. Whether the center is recomputed on every member admission
3. Whether the tolerance history is recomputed after member admission or only on future evaluations
4. Whether a new non-member swing is discarded, seeds a candidate, closes the current Zone, or triggers replacement
5. Whether a valid Zone and a candidate can coexist in the same direction
6. Whether multiple valid Zones may coexist in the same direction
7. Whether a valid Zone can be invalidated, replaced, or retired
8. Whether overlap is allowed or disallowed
9. Whether merge semantics exist
10. Whether Zone identity is persistent or ephemeral
11. Whether stale Zones are legal or invalid
12. Whether any later lifecycle rules must be frozen before implementation

## 11. Recommended next research gate

The next required decision gate is not an implementation gate. It is a human-governance gate for the single-active-zone baseline.

The smallest meaningful question is:

> When a valid Zone already exists and a new same-direction eligible swing does not satisfy the frozen membership rule, what state transition is allowed?

This question is the true blocker before any candidate lifecycle logic can be designed.

Recommended research gate:

- choose whether a single-active-zone baseline must be treated as:
  - valid Zone persists and non-member swing is ignored or seeded,
  - valid Zone is invalidated and new seed replaces it,
  - or another explicit model after human approval
- do not implement any of these behaviors before the question is explicitly decided

This remains a research gate, not a frozen rule.

## 12. Governance status

- Group A swing definition: FROZEN — HUMAN APPROVED
- 15-minute UTC bar contract: FROZEN — HUMAN APPROVED
- W = 5 prior same-direction legal gaps: FROZEN — HUMAN APPROVED
- minimum tolerance history = 1: FROZEN — HUMAN APPROVED
- tolerance = median of selected legal prior same-direction absolute gaps: FROZEN — HUMAN APPROVED
- center = median(member prices): FROZEN — HUMAN APPROVED
- membership rule for a valid Zone: FROZEN — narrow rule
- Zone creation rule: FROZEN — narrow rule
- Group B as a whole: NOT FROZEN
- single-active-zone baseline: RESEARCH CANDIDATE ONLY
- any replacement / invalidation / lifecycle rule: UNRESOLVED
- Phase 2: NOT STARTED
- production behavior: unchanged

## 13. Final conclusion

The repository evidence supports a narrow and important conclusion:

- the first eligible same-direction swing becomes a candidate/seed,
- a valid Zone is created only when a later same-direction swing qualifies as a member,
- the frozen membership rule is evaluated using the current center and tolerance under causal order,
- no complete lifecycle state machine is justified by the repo.

However, the repository does not justify any frozen answer for the event in which a valid Zone already exists and a new same-direction swing arrives but does not satisfy the membership rule.

Therefore:

- A behavior like "keep the current Zone and ignore the non-member swing" is a RESEARCH CANDIDATE.
- A behavior like "start a new candidate/seed" is a RESEARCH CANDIDATE.
- A behavior like "invalidate or replace the current Zone" is UNRESOLVED and should be treated as an assumption, not evidence.
- The repo does not support a frozen single-active-zone lifecycle rule.

The strongest evidence-based conclusion is:

- no complete lifecycle state machine is justified,
- no replacement / invalidation / stale-zone rule is frozen,
- any single-active-zone lifecycle must remain explicitly non-frozen until human governance resolves it.
