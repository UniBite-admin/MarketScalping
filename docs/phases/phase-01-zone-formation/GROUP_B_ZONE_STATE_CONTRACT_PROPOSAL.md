# Group B Zone-State Contract Proposal

## Status

PROPOSAL ONLY

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- This document is architecture research only.
- No production implementation was changed.
- No executable tests were changed.
- No canonical data was changed.
- No new technical rule was frozen.
- Human-approved/frozen decisions remain unchanged.

## 1. Objective

The objective of this document is to determine whether the repository evidence is sufficient to support a minimal, causal, deterministic, auditable Zone-State Contract proposal without inventing unsupported strategy behavior.

This is not an implementation proposal. It is a research-only design check.

The central question is:

> Can a minimal Zone-State Contract be formulated that is compatible with the frozen Phase 1 decisions and is precise enough to make membership semantics meaningful, without silently inventing unapproved strategy rules?

The answer supported by the repository evidence is:

- a minimal conceptual proposal is supportable as a design baseline,
- but a final, complete, implementation-ready Zone-State Contract is not supportable from the repo evidence alone without additional human approval.

## 2. Authoritative Inputs

The following repository documents were reviewed as the governing evidence:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
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
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md](GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_COMPARISON.md](GROUP_B_ZONE_GEOMETRY_COMPARISON.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_CENTER_CALIBRATION_ANALYSIS.md](GROUP_B_CENTER_CALIBRATION_ANALYSIS.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

Additional repository search was used to check for any authoritative concepts related to:

- zone
- level
- support/resistance
- cluster
- swing state
- identity
- lifecycle
- interval
- membership
- state transition
- replay
- immutable historical state

No authoritative Zone production object or zone-state machine was found in the current repo implementation.

## 3. Frozen Decisions Used

The following are definitively frozen and remain binding for this audit:

A. Group A swing definitions

- Swing High: High[i] > High[i-1] AND High[i] > High[i+1]
- Swing Low: Low[i] < Low[i-1] AND Low[i] < Low[i+1]
- strict inequalities
- complete required neighborhood
- confirmation precedes downstream eligibility
- no lookahead

B. 15-minute bar contract

- UTC aligned
- half-open [bar_start, bar_end)
- event at bar_end belongs to the next bar
- closed bars are immutable
- incomplete final/trailing bar excluded
- Group A operates only on closed bars

C. Group B tolerance history

- HIGH and LOW streams are separate
- only prior legal same-direction gaps are eligible
- current swing is excluded from its own tolerance history
- W = 5
- minimum history = 1
- 0 prior legal gaps => no tolerance available
- 1–4 => use all available
- 5+ => use latest 5
- tolerance = median(selected prior legal absolute gaps)

D. Candidate A center statistic

- center = median(member prices)
- human approved and frozen

## 4. Repository Facts

### A. REPOSITORY FACT

The project contains a deterministic replay and canonical ordering path, and the historical research code uses a descriptive clustering model rather than a live Zone state machine.

Evidence:

- [replay_runner.py](../../replay_runner.py)
- [feature_signal_engine.py](../../feature_signal_engine.py)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### B. REPOSITORY FACT

The repo supports the separation of HIGH and LOW sequences as distinct same-direction streams.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### C. REPOSITORY FACT

The descriptive research code reproduces the same-direction structure, including the actual counts:

- HIGH = 78
- LOW = 68

This is supported by the canonical reconstruction used in the research tooling and by the documented same-direction analysis.

### D. REPOSITORY FACT

The repo does not currently contain a final, authoritative Zone object, Zone history ledger, or runtime state machine that defines:

- zone identity
- zone lifecycle
- overlap semantics
- merge semantics
- historical mutation semantics
- zone creation trigger in deterministic state terms

This is evidenced by the absence of a final Zone class, schema, or authoritative runtime object in the project codebase.

## 5. Existing Zone-State Gaps

The current evidence leaves the following unresolved:

- Zone object/state contract
- Zone creation semantics
- First member semantics
- Membership semantics
- Zone member-set mutation
- Center update timing
- Tolerance update timing relative to membership
- Multiple simultaneous zones
- Multiple-zone membership ambiguity
- Zone identity
- Overlap handling
- Merge behavior
- Lifecycle
- Historical snapshot/immutability semantics
- Exact replay/state transition semantics
- Any broader Group B architecture

These are not implementation details to be invented by assumption; they are root decisions that remain open.

## 6. Root Decisions

The following root decisions remain unresolved under the current repository evidence:

1. Zone creation trigger
   - first eligible swing
   - first swing with valid tolerance history
   - first qualifying multi-member cluster
   - no evidence currently justifies one choice over another

2. First-member semantics
   - is a single member sufficient?
   - does the frozen minimum-history = 1 tolerance rule imply anything about minimum zone evidence?
   - no, it does not imply a zone-creation rule by itself

3. Zone member-set contract
   - what minimum state is required?
   - direction, member observations, eligibility timestamps, price values, creation timestamp, identity are all plausible options
   - no final minimum state is frozen

4. Membership evaluation order
   - current swing → compute tolerance from prior legal history → evaluate membership → mutate zone → append current swing to future tolerance history
   - this ordering is intuitively causal but not yet formally frozen

5. Center update timing
   - median(member prices) is frozen as the center statistic
   - whether the center is recomputed on every member addition, only at evaluation time, or is immutable after creation is unresolved

6. Tolerance update timing
   - current swing is excluded from its own tolerance history
   - but whether adding the current swing affects only future decisions, or also current evaluation, depends on implementation order and has not been frozen

7. Membership reference rule
   - A. distance to center
   - B. nearest member
   - C. member envelope / interval
   - D. center ± tolerance
   - A and D are mathematically equivalent under a symmetric point-center interpretation
   - B and C require a defined member set and geometry
   - no candidate has been proven as a true sequential rule in the repo

8. Multiple-zone ambiguity
   - whether multiple zones may coexist
   - whether one swing may join multiple zones
   - how a swing chooses among multiple candidate zones
   - no authoritative rule exists

9. Overlap / merge
   - no authoritative overlap or merge semantics
   - not currently definable from repository evidence

10. Zone identity
    - deterministic identity remains unresolved
    - possible conceptual candidates include creation event, first member, or stable sequence number

11. Historical immutability
    - true replay-safe historical state requires a clear statement of what is immutable versus mutable
    - current evidence does not supply this contract

12. Lifecycle semantics
    - active / inactive
    - expiry
    - invalidation
    - retirement
    - these belong to later-phase lifecycle questions unless the roadmap requires otherwise

## 7. Minimal Zone-State Contract — PROPOSAL ONLY

The smallest supportable conceptual contract is a minimal state model for future specification work, not a final freeze.

### 7.1 Zone definition

PROPOSAL ONLY: A Zone is a same-direction historical object that contains a deterministic historical member set of eligible confirmed swings and a canonical creation reference.

This is intentionally minimal. It avoids inventing lifecycle behavior, merge rules, and phase-4 semantics.

### 7.2 Required minimal fields

PROPOSAL ONLY: The minimum state needed to avoid immediate ambiguity is:

- direction
- member observations
- eligibility timestamps for the members
- member price values
- creation timestamp
- deterministic identity reference

This is a minimal state, not a complete architecture.

### 7.3 Center rule

PROPOSAL ONLY: For the minimal state, center is defined as the median of member prices, consistent with the frozen Candidate A center statistic.

This is a proposal about center calculation, not a proposal that the whole zone geometry is frozen.

### 7.4 Zone creation trigger

PROPOSAL ONLY: A Zone may be created only after at least two eligible same-direction observations are present and the candidate zone has a valid causal history under the frozen rules.

This is intentionally cautious and avoids the unsupported claim that a single member is sufficient.

### 7.5 Membership evaluation order

PROPOSAL ONLY: The causal order for a new swing is:

1. the swing is confirmed and becomes eligible
2. the tolerance is computed from prior legal same-direction observations only
3. the current swing is excluded from the tolerance history used for its own evaluation
4. existing same-direction zones are evaluated under the chosen membership reference
5. if the candidate does not match any qualifying zone, the creation logic may consider a new zone only under a separate, explicit creation rule
6. the current swing is appended to future same-direction history only after its own evaluation is complete

This is a proposal and not a frozen sequence.

### 7.6 Zone membership reference

PROPOSAL ONLY: A future sequential rule may use one of the following reference models, but none is final under current evidence:

- A. distance to center
- B. nearest member
- C. member envelope / interval
- D. center ± tolerance

The repo evidence supports that A and D are equivalent under a symmetric point-center definition, while B and C require a concrete member-set geometry that the repository does not yet define.

### 7.7 Multiple-zone handling

PROPOSAL ONLY: Multiple simultaneous zones are a later design problem and should not be treated as a solved part of the minimal contract.

This document explicitly does not define:

- nearest zone rule
- candidate tie-break rule
- overlap resolution
- merge policy

### 7.8 Historical immutability

PROPOSAL ONLY: Zone history should be append-only at the historical level and should not silently reinterpret earlier members once a historical observation becomes eligible.

This is a design principle, not a final historical-state implementation contract.

## 8. Membership Semantics Dependencies

The membership rule cannot be defined without the following upstream decisions:

- same-direction observation set
- legal gap definition
- current swing exclusion from own tolerance history
- tolerance family and formula
- tolerance window semantics
- candidate-to-zone distance function
- zone center semantics
- zone member-set state
- explicit zone creation trigger
- deterministic ordering for equal-distance or equal-time cases

The repo supports the upstream items only partially. Therefore the membership semantics are not yet final.

## 9. Multiple-Zone Dependencies

Multiple-zone semantics are not supportable from the repo under current evidence because the following are unresolved:

- whether multiple same-direction zones may coexist
- whether a swing can join more than one zone
- how two candidate zones are ranked if both qualify
- what overlap means
- whether an overlap triggers merge, rejection, or coexistence
- what zone identity is used to distinguish one zone from another

These are root blockers, not minor details.

## 10. Lifecycle / Phase Boundary

The roadmap establishes a clear boundary:

- Phase 1 — Zone Formation
- Phase 4 — Zone Lifecycle

This means the following are not to be silently imported into Phase 1:

- active/inactive lifecycle states
- expiry or invalidation semantics
- retirement rules
- merge behavior
- zone splitting semantics
- full lifecycle state machine

PROPOSAL ONLY: Phase 1 may define a minimal historical Zone object that is stable enough to allow sequential evaluation, but it should not define the Phase 4 lifecycle model.

This keeps the design within the Phase 1 scope while preserving the later lifecycle work.

## 11. Determinism and Causality

The following are required and already supported by the frozen architecture:

- canonical replay ordering
- no lookahead
- current swing excluded from own tolerance history
- same-direction historical sequences only
- closed-bar rule before downstream use
- deterministic tie-break from canonical replay ordering when timestamps are equal

PROPOSAL ONLY: the minimal Zone-State Contract should preserve these invariants and should not introduce any state transition that depends on future information.

## 12. Open Questions

The following remain open and require explicit human approval or later technical specification before a final contract can be frozen:

- exact zone creation trigger
- minimum evidence required before a zone exists
- exact minimum member count for a valid zone
- exact zone object fields required for deterministic membership evaluation
- exact membership reference rule
- exact handling of multiple simultaneous zones
- exact overlap and merge semantics
- exact historical mutation policy
- exact stable zone identity scheme
- exact lifecycle semantics
- whether Phase 4 lifecycle behavior should be anticipated in Phase 1

## 13. Human Approval Gates

The following items require explicit human approval before a final Zone-State Contract can be considered valid:

- any final zone creation rule
- any final membership rule
- any final multiple-zone rule
- any overlap/merge policy
- any final historical mutation policy
- any final identity scheme
- any final lifecycle semantics
- any final freeze of Group B architecture

No item in this document is frozen. All proposed elements are explicitly labeled PROPOSAL ONLY.

## 14. Governance Status

Status: PROPOSAL ONLY / RESEARCH ONLY

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- Human-approved frozen decisions remain unchanged.
- No production or executable test files were modified.
- No Phase 4 lifecycle semantics were imported into Phase 1.
- This is sufficiently minimal to support future design work, but not sufficient to freeze the final Zone-State Contract.

## Final Conclusion

A minimal Zone-State Contract is supportable only as a design baseline, not as a final implementation contract.

The repository evidence supports the following:

- same-direction-only historical sequence is valid
- current swing exclusion from its own tolerance history is valid
- center = median(member prices) is frozen as the center statistic
- a minimal Zone object can be conceptually proposed without inventing later lifecycle behavior

The repository evidence does not support the following as final, frozen facts:

- a final zone creation rule
- a final membership rule
- a final multiple-zone rule
- a final overlap or merge rule
- a final historical mutation contract
- a final lifecycle state machine
- a final Group B freeze

Therefore the correct design posture is:

- a minimal Zone-State Contract proposal is supportable as PROPOSAL ONLY,
- but a final Zone-State Contract remains blocked by unresolved root decisions and requires explicit human approval.
