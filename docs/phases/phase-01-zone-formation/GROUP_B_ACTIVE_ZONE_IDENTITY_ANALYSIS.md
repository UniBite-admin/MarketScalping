# Group B Active Zone Identity Analysis

## 1. Objective

This analysis addresses the next unresolved Phase 1 Group B root decision:

> Active Zone Identity and Selection Model

The current frozen rules define:

1. a valid same-direction swing may be evaluated as a member of an existing Zone when it satisfies
   `abs(incoming_swing_price - current_zone_center) <= current_tolerance`
2. the first eligible same-direction swing is a seed/candidate
3. a valid Zone is created only after a second same-direction swing qualifies as a member

Those decisions establish a membership test and a creation boundary. They do not determine:

- which existing Zone(s) are eligible to receive a new swing,
- whether one or many valid Zones may coexist,
- how identity is tracked across time,
- how multiple qualifying Zones are selected,
- whether overlap or merge is allowed,
- whether a Zone can expire or be replaced.

This is a research-only analysis. It does not implement production code, it does not modify executable tests, it does not freeze a model, and it does not advance the project to Phase 2.

## 2. Frozen inputs

The following remain the authoritative frozen inputs for this analysis:

- Group A swing definition is frozen and human approved
- 15-minute UTC bar contract is frozen and human approved
- canonical replay ordering is frozen and human approved
- no lookahead / causal eligibility is frozen and human approved
- HIGH and LOW streams remain separate
- W = 5 prior legal same-direction gaps is frozen and human approved
- minimum tolerance history = 1 is frozen and human approved
- the current swing is excluded from its own tolerance history
- tolerance = median of selected legal prior same-direction absolute gaps is frozen and human approved
- center = median(member prices) is frozen and human approved
- membership rule for a valid Zone is frozen as a narrow rule:
  `abs(incoming_swing_price - current_zone_center) <= current_tolerance`
- Zone creation rule is frozen as a narrow rule:
  first eligible same-direction swing = seed/candidate;
  valid Zone is created at the second same-direction swing that qualifies as a member

Important boundary:

- these are narrow frozen decisions,
- Group B as a whole remains NOT FROZEN,
- Phase 2 remains NOT STARTED,
- production behavior remains unchanged.

## 3. Existing repository evidence

The authoritative roadmap and governance documents are explicit that the project is still in a research / specification stage for Group B, not an implementation stage:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)

The project also contains research evidence that makes the distinction very clear:

- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_EVIDENCE_AUDIT.md](GROUP_B_ZONE_STATE_CONTRACT_EVIDENCE_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMAL_ZONE_STATE_CONTRACT_AUDIT.md](GROUP_B_MINIMAL_ZONE_STATE_CONTRACT_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_UPDATE_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md](GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_COMPARISON.md](GROUP_B_ZONE_GEOMETRY_COMPARISON.md)

Relevant repository fact from code inspection:

- The Python code and tests do not define an authoritative Zone class, active-zone registry, zone lookup, zone identity field, overlap policy, merge policy, lifecycle state, or multi-zone selection rule.
- The descriptive research script in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) is a historical clustering/summary tool; it is not a production Zone runtime or a final state machine.

This means the current evidence supports a frozen membership test, a frozen creation trigger, and a frozen center/tolerance rule, but it does not support a frozen active-zone selection model.

## 4. Root decision definition

The frozen creation rule gives the following sequential state:

1. eligible same-direction swing becomes a seed/candidate
2. a later same-direction swing may qualify
3. a valid Zone is created when the second qualifying same-direction member is accepted

The unresolved problem begins when there may be more than one existing valid Zone in the same direction.

The actual root decision is:

> Given a new eligible same-direction swing and a set of existing valid Zones, which Zone(s) are candidates for membership evaluation?

This is not the same question as whether the swing qualifies against a given Zone. The frozen rule only answers the second question. It does not resolve the first. This distinction is repeatedly emphasized in the research documents and in the governance language.

## 5. Candidate models

### Model A — Single Active Zone

Description:

- only one valid Zone per direction may exist at a time
- a new eligible swing is evaluated only against that one active Zone
- if a new Zone would otherwise be created, the implementation must define how the active Zone is replaced, merged, or retained

Evidence support:

- minimal assumption
- requires the fewest unresolved state transitions
- fits the idea of a narrow, sequential state machine
- not frozen

Assumptions required:

- a single active Zone per direction must be chosen by governance
- replacement / merge / discard semantics are not yet defined by repo evidence

### Model B — Multiple Persistent Zones

Description:

- multiple valid Zones per direction may coexist
- each Zone has persistent identity
- new swings may be evaluated against one or several Zones
- deterministic selection or fan-out rules are required if multiple Zones qualify

Evidence support:

- conceptually plausible and consistent with a registry model
- not frozen
- requires explicit identity, selection, overlap, and lifecycle decisions that are absent from the repo

Assumptions required:

- persistent identity semantics
- deterministic tie-break or all-qualifying behavior
- overlap and merge resolution

### Model C — Nearest Zone

Description:

- multiple Zones may exist
- when multiple Zones qualify, choose the Zone whose center is nearest to the incoming swing

Evidence support:

- mathematically simple
- plausible as a deterministic selection rule
- not frozen
- not backed by authoritative repo evidence as a final rule

Assumptions required:

- multiple Zones must have been authorized
- a deterministic zone-center selection rule must exist
- tie-breaks are still required when distances are equal

### Model D — Earliest / Oldest Zone

Description:

- multiple Zones may exist
- if more than one qualifies, choose the oldest existing Zone

Evidence support:

- historically legible and easy to audit
- not frozen
- not supported by authoritative repo evidence as a final rule

Assumptions required:

- stable creation time / identity
- deterministic ordering semantics
- lifecycle semantics for abandonment, expiry, or invalidation

### Model E — Most Recent Zone

Description:

- multiple Zones may exist
- if multiple Zones qualify, choose the most recently created one

Evidence support:

- easy to implement
- not frozen
- not supported by authoritative repo evidence as a final rule

Assumptions required:

- stable creation ordering
- no ambiguous overlap or simultaneous completion
- lifecycle semantics for older zones

### Model F — All Qualifying Zones

Description:

- any incoming swing that qualifies against multiple Zones is added to all qualifying Zones

Evidence support:

- conceptually possible
- but leads directly to overlapping identity, duplicate membership, correlated centers, and ambiguous downstream strategy behavior
- not frozen

Assumptions required:

- explicit policy for duplicate membership and center mutation
- overlap semantics
- deterministic replay semantics under repeated additions to multiple Zones

## 6. Evidence comparison

| Model | Evidence support | Assumptions | Determinism | Complexity | Unresolved dependencies |
| --- | --- | --- | --- | --- | --- |
| Model A — Single Active Zone | weak, but minimal and consistent with narrow frozen logic | requires a single active Zone rule and replacement/merge semantics | moderate if deterministic, but still requires unresolved replacement behavior | low to moderate | replacement policy, merge policy, lifecycle, identity |
| Model B — Multiple Persistent Zones | conceptual only; not supported by repo runtime evidence | requires persistent identity, registry, membership fan-out, selection/overlap rules | weak unless a full registry and deterministic tie-break are specified | high | identity, overlap, merge, lifecycle, state transitions |
| Model C — Nearest Zone | descriptive candidate only | requires multiple Zones and center-based selection | moderate if distances are defined and ties are handled | moderate | multiple-zone existence, tie-break, center validity |
| Model D — Earliest / Oldest Zone | descriptive candidate only | requires stable creation ordering and identity | moderate if creation order is deterministic | moderate | identity, lifecycle, stale-zone handling |
| Model E — Most Recent Zone | descriptive candidate only | requires creation ordering and tie-break logic | moderate if creation order is deterministic | moderate | identity, stale-zone handling |
| Model F — All Qualifying Zones | weak; introduces cross-zone duplication and ambiguity | requires full overlap semantics, duplicate-membership policy, and replay-safe state mutation | low unless explicitly constrained | high | overlap, identity, duplicate membership, center mutation |

## 7. Empirical distinguishability

Current data does not distinguish these models in a meaningful, authoritative way.

Why:

- the repository research code does not maintain a real Zone registry or active-zone state
- it performs descriptive clustering over a sequence of swings, not sequential membership against a live set of valid Zones
- there is no authoritative implementation that stores Zone identity, active Zone membership, overlap behavior, or lifecycle transitions
- no code path or test uses multiple simultaneous valid Zones and resolves tie-break behavior in a deterministic way

Therefore, the available data can show that geometry and tolerance sensitivity matter, but it cannot prove which identity/selection model is correct for a live Zone engine.

The evidence supports only this narrow conclusion:

- a zone can exist as a same-direction object with a center and a member set,
- a new swing can be evaluated against a valid Zone by the frozen membership rule,
- but the repo currently provides no authoritative evidence for which Zone(s) are chosen when multiple Zones exist.

## 8. Root decision

The root decision is not whether a swing can qualify against one Zone. That is already frozen.

The actual unresolved root decision is:

> Which existing valid Zone(s) are considered when a new eligible same-direction swing arrives?

This decision is not codeable from the current repo evidence alone. It requires explicit human governance because it sits above the narrow frozen membership rule and affects:

- identity semantics
- allocation semantics
- overlap handling
- member-set update behavior
- lifecycle and invalidation
- deterministic replay under multiple active Zones

The most defensible research recommendation is not to choose a model as final. It is to recommend a minimal baseline for design exploration:

- evaluate the single-active-zone-per-direction model as a low-assumption baseline,
- keep all other models explicitly in research-only status,
- do not freeze any model,
- treat all other models as open design options until human governance resolves the root decision.

This recommendation is practical and conservative, but it is still a recommendation only, not a frozen rule.

## 9. Recommended next gate

The smallest next technical decision required before implementation is:

- active Zone identity and selection model

Specifically, the project must decide one of the following before any implementation logic is considered:

- one active Zone per direction
- multiple persistent Zones with explicit identity and deterministic selection
- or another model, but only after explicit human approval

This is the minimum decision gate because all later issues depend on it: overlap, merge, lifecycle, member-set update, deterministic ordering, and replay safety.

## 10. Governance status

- Group A: FROZEN
- 15m bar contract: FROZEN
- W=5: FROZEN
- minimum history=1: FROZEN
- center=median: FROZEN
- membership rule: FROZEN — narrow
- Zone creation rule: FROZEN — narrow
- Group B: NOT FROZEN
- Phase 2: NOT STARTED
- production behavior: unchanged

## Final conclusion

The repository evidence supports the frozen membership and creation rules, but it does not support a frozen active Zone identity or selection model. The active-zone question remains a true root decision and requires explicit governance before implementation can be attempted.

The simplest research baseline is a single-active-zone-per-direction design for exploratory work only, but it must remain explicitly non-frozen and non-implementation-bound until human approval is recorded.
