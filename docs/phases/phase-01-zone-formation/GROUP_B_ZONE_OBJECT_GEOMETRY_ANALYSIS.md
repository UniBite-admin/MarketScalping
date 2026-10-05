# Group B Zone Object & Geometry Analysis

## 1. Objective

This document addresses the root question that follows from the prior membership-distance audit:

> Before a membership rule can be defined, the repository must define what a zone actually is.

The current frozen contract does not include a final zone object or a final zone geometry. The repository supports a frozen tolerance-history rule, but it does not yet define:

- what constitutes a zone
- whether a zone requires a center
- whether it requires lower/upper bounds
- whether zone membership is based on a distance metric, an interval, or a member set
- whether the zone state is mutable or snapshot-based
- whether zone identity must be deterministic and stable
- how multiple candidate zones are resolved

This is a research-only audit. It does not create a production rule, does not modify executable tests, does not alter the frozen contract, and does not start Phase 2.

## 2. Authoritative Inputs

Authoritative project sources read for this audit:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)

Relevant Group B research documents reviewed:

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
- [docs/phases/phase-01-zone-formation/GROUP_B_HUMAN_DECISION_REQUEST.md](GROUP_B_HUMAN_DECISION_REQUEST.md)

Repository search was also performed for the relevant terms:

- zone
- cluster
- member
- center
- boundary
- upper
- lower
- interval
- geometry
- tolerance
- membership
- join
- merge
- overlap
- identity
- immutable
- snapshot
- lifecycle

## 3. Frozen Inputs

FROZEN — HUMAN APPROVED

The following are already frozen and may not be changed in this task:

- Group A swing definition
- 15-minute UTC bar contract
- canonical replay ordering
- no-lookahead / causal eligibility
- HIGH and LOW swing streams remain separate
- only prior legal same-direction observations may influence tolerance
- current swing is excluded from its own tolerance history
- W = 5 prior legal same-direction gaps
- minimum history = 1
- 0 prior legal gaps => no tolerance available
- 1–4 prior legal gaps => use all available
- 5+ prior legal gaps => use the five most recent
- tolerance = median of the selected prior legal absolute gaps

Group B as a whole remains NOT FROZEN.

## 4. Repository Evidence

### 4.1 Explicit evidence hierarchy used in this audit

The repository evidence must be classified according to the following hierarchy:

1. Explicit human decision
2. Frozen specification / ADR
3. Authoritative source code
4. Tests
5. Reproducible experiment
6. Documented data
7. External documentation
8. Agent reasoning

Lower-level reasoning is not authoritative and is treated as research only.

### 4.2 What the repo does support

RESEARCH EVIDENCE

The repo consistently supports the following:

- same-direction high and low sequences are distinct
- mixed high+low or mixed-direction calibration is invalid for same-direction tolerance evidence
- the same-direction gap process shows real structure
- the prior-gap median is a stronger tolerance candidate than a naïve mean under skewed same-direction distributions
- a causal rolling-history design is more defensible than a static pair of arbitrary tuning constants
- the repository contains no final zone object definition

### 4.3 What the repo does not support

AUTHORITATIVE EVIDENCE MISSING

The current repository does not provide:

- an authoritative zone object type
- authoritative zone fields
- authoritative member-set semantics
- authoritative center formula
- authoritative lower/upper bounds
- authoritative overlap resolution
- authoritative zone lifecycle semantics
- authoritative zone identity scheme
- authoritative historical snapshot semantics

Therefore, no implementation can claim a final zone geometry from repository evidence alone.

## 5. Existing Zone Definitions

### 5.1 Minimum known findings

The repo contains no authoritative implementation of a zone object. There is no production class, dataclass, schema, or state model in the Python codebase that defines a zone as a persistent object.

This is a direct finding from repository inspection:

- no authoritative Python Zone class exists in the codebase
- no production zone object schema exists in the current project code
- no final zone geometry contract exists in the repo
- no zone identity contract exists in the repo

### 5.2 What the docs do say

RESEARCH EVIDENCE

The research docs repeatedly mention zone-related concepts but consistently treat them as proposed, not frozen:

- zone center is proposed but not frozen
- zone geometry is proposed but not frozen
- nearest-center assignment is proposed but not frozen
- minimum cluster size is proposed but not frozen
- overlap resolution is unresolved
- historical mutation is discussed as a design issue, not a frozen standard

The architecture proposal documents refer to a zone as a cluster, center, or member-span representation, but they do so as modeling proposals rather than as authoritative definitions.

### 5.3 Conclusion on the minimum zone object

No authoritative zone object exists in the repository.

This is a critical result: the project has frozen the tolerance history and causal observation semantics, but it has not yet frozen the object being evaluated.

## 6. Missing Zone Definitions

The following are missing from the current repo evidence:

- exact zone type
- exact member list semantics
- exact center requirement
- exact lower/upper boundary definition
- exact geometry model
- exact creation timestamp semantics
- exact membership update timing
- exact identity semantics
- exact historical snapshot rules
- exact multiple-zone tie-break semantics

This gap is not filled by the current tolerance history decision. The tolerance history is a rule for a prior-gap median, not a zone object definition.

## 7. Minimum Zone Object Requirements

This section evaluates what would be required if a zone object were to be formalized in a future specification.

### A. Direction

REQUIRED BY FROZEN EVIDENCE

- Zone membership must remain same-direction-only.
- HIGH and LOW must remain separate.

### B. Members

SUPPORTED BY RESEARCH EVIDENCE

- a zone logically contains member swings of the same direction
- a member list is a natural representation
- but the repo does not freeze whether all members or only a recent subset must be retained

### C. Center

SUPPORTED BY RESEARCH EVIDENCE, BUT NOT FROZEN

- a center is a plausible component of a zone
- median member price is a commonly discussed center candidate
- but median is not the same thing as a frozen zone-center rule

### D. Lower boundary

UNRESOLVED

- no authoritative lower bound is defined
- no final lower-bound rule is supported by repo evidence

### E. Upper boundary

UNRESOLVED

- no authoritative upper bound is defined
- no final upper-bound rule is supported by repo evidence

### F. Tolerance

FROZEN — HUMAN APPROVED for historical tolerance calculation only

The project has frozen the tolerance history rule as:

- W = 5 prior legal same-direction gaps
- minimum history = 1
- median of the selected past legal absolute gaps

This is a tolerance used to evaluate a current swing against prior history. It is not necessarily the same thing as zone width, zone boundary, or zone geometry.

This distinction is critical and remains unresolved.

### G. Creation timestamp

SUPPORTED BY RESEARCH EVIDENCE

- a zone has a causal creation time in principle
- but the repo does not freeze the exact creation rule or state machine

### H. Member timestamps

PROPOSED ONLY

- a robust zone may retain member timestamps
- this is recommended for replay and auditability
- but it is not frozen by repo evidence

### I. Identity

PROPOSED ONLY

- deterministic identity may be required for zone selection and tie-breaks
- no authoritative identity format exists

### J. Historical snapshot

SUPPORTED BY RESEARCH EVIDENCE

- historical zone state should be snapshot-like and append-only for replay determinism
- no final policy is frozen

## 8. Center Candidates

This section distinguishes center ideas that have been discussed in the repo from a frozen center rule.

### Candidate 1 — median of member prices

RESEARCH EVIDENCE

- this is repeatedly discussed as a plausible center estimate
- it is easy to compute deterministically
- it is less sensitive to a single outlier than the mean

BUT:

- it is a candidate, not a frozen decision
- it does not automatically become the zone center merely because median is a good tolerance statistic

### Candidate 2 — mean of member prices

PROPOSED ONLY

- mathematically valid as a center definition
- more sensitive to outliers
- not justified by the repo as a frozen center rule

### Candidate 3 — first member

PROPOSED ONLY

- a possible anchor if zones are treated as a time-ordered chain
- not supported by repo evidence as a final zone object rule

### Candidate 4 — latest member

PROPOSED ONLY

- plausible if the current member is treated as the zone focal point
- not supported by repo evidence as a final rule

### Candidate 5 — tolerance-derived center

PROPOSED ONLY

- a zone center could be defined relative to the prior tolerance history
- but this is not frozen and requires a separate specification

### Candidate 6 — no explicit center

RESEARCH EVIDENCE

- a zone could be defined as a member set with a distance metric instead of a center
- this is a legitimate geometric alternative only if the repo later chooses it

### Conclusion on center

The repository supports center-as-a-possible-concept, but it does not establish a final center rule.

A center is not justified merely because the tolerance statistic is median.

## 9. Geometry Candidates

These are research-only geometry models and must not be treated as approved rules.

### Model A — center ± tolerance

HYPOTHETICAL / RESEARCH-ONLY

Definition:

- zone interval = [center - tolerance, center + tolerance]

Interpretation:

- a candidate zone is represented by a symmetric band around a center

Problem:

- this requires both a center and a tolerance-to-geometry mapping
- the repo has not froze either one

### Model B — min(member prices) to max(member prices)

HYPOTHETICAL / RESEARCH-ONLY

Definition:

- zone interval = [min(member prices), max(member prices)]

Interpretation:

- the zone is the historical span of its members

Problem:

- this requires a member-set history and a planned durability policy
- it does not tell us how new members are evaluated against the old span

### Model C — member points with tolerance around each member

HYPOTHETICAL / RESEARCH-ONLY

Definition:

- each member contributes a local tolerance band or point neighborhood

Problem:

- this is structurally more complex than current repo evidence supports
- it requires a clear membership model and update semantics

### Model D — no explicit interval; membership defined only by a distance metric

HYPOTHETICAL / RESEARCH-ONLY

Definition:

- zone is a member set plus a distance function
- no explicit lower/upper boundary is required

Problem:

- this can be valid as a design, but the repo does not choose it
- without a defined distance metric, it is not a working rule

### Conclusion on geometry

The repository supports several plausible geometric representations as research constructs, but none is frozen.

## 10. Tolerance vs Geometry Analysis

This is the key distinction that must be preserved.

### 10.1 Frozen tolerance history

FROZEN — HUMAN APPROVED

The repo has a frozen tolerance history rule:

- W = 5 prior legal same-direction gaps
- minimum history = 1
- use all available prior gaps if 1–4
- use the five most recent prior gaps if 5+
- tolerance = median of selected prior legal absolute gaps

### 10.2 Not frozen: zone width

UNRESOLVED

The repo does not establish that:

- the historical tolerance equals the zone width
- the historical tolerance equals a zone boundary
- the historical tolerance is the distance metric for zone membership
- the historical tolerance is the same concept as a zone interval

The tolerance history is about the same-direction gap history used to estimate scale. It is not automatically the actual member-to-zone distance rule or the zone boundary.

### 10.3 Implication

Tolerances and geometry are separate layers. At the current repo state, the former is frozen; the latter is unresolved.

## 11. Causal Construction Analysis

Any future zone model must remain causal.

The frozen causal requirements are:

- use only information available at eligibility time
- no future swings
- no future bar information beyond canonical replay order
- current swing is excluded from its own tolerance history
- historical state must be append-only for replay stability

### Research-only requirement

For any hypothetical zone construction, the following must be maintained:

1. pre-decision state
2. candidate evaluation under prior state only
3. post-decision state update
4. no retroactive movement of earlier zone members
5. no future-informed zone mutation

If a candidate geometry requires retroactive mutation after later swings appear, that is a design problem and must be labelled as such.

## 12. Mutability / Historical Snapshot Analysis

### Immutable historical zone snapshots

RESEARCH EVIDENCE

This is the cleanest replay-safe direction conceptually:

- once a decision is made for a swing at time t, the state used for that decision is preserved as a historical snapshot
- later swings may create new state, but they do not silently rewrite earlier decisions

### Mutable current zone state

PROPOSED ONLY

This is also possible but less conservative:

- the current zone object may evolve as new members arrive
- but then the historical meaning of earlier membership decisions becomes less clear

### Current repo evidence

The existing repo explicitly supports the principle that earlier historical decisions must remain replay-stable and not be silently retroactively rewritten. This is consistent with the canonical replay and deterministic-ordering evidence.

But the exact lifecycle of zone objects is not frozen.

## 13. Zone Identity Analysis

### Necessity of identity

RESEARCH EVIDENCE

A deterministic identity is likely useful for:

- multiple-zone comparison
- equal-distance ambiguities
- zone selection
- auditability
- replay traceability

### Existing repo evidence

There is no authoritative zone identity scheme in the repo.

### What the project can say today

- identity may be required for determinism
- the exact identity format remains unresolved
- no formal identity schema is frozen

## 14. Multiple-Zone Analysis

This is a major unresolved root question.

### Structural issue

Under different hypothetical geometric models, the same swing may plausibly belong to:

- zero zones
- one zone
- multiple zones

This is not merely a theoretical point: the prior membership-distance audit showed materially different join counts under different reference models.

### Real-data structural findings

Using the project’s real historical swing stream:

- HIGH: 78 swings
- LOW: 68 swings
- different hypothetical geometries produce materially different membership counts

The large disagreement counts imply that a final zone geometry is not a harmless implementation detail. It affects whether the same swing would be treated as an existing-zone member or a new-zone candidate.

### Critical result

The multiple-zone ambiguity issue is real, but the repo does not define a deterministic tie-break or a stable zone identity. This means the problem is acknowledged, but not resolved.

## 15. Real-Data Structural Results

The repository’s canonical Phase 1 data supports the following descriptive results:

- HIGH same-direction swings: 78
- LOW same-direction swings: 68
- total same-direction swings evaluated: 146

The prior research found these descriptive gap statistics:

- HIGH median same-direction gap ≈ 33.78
- LOW median same-direction gap ≈ 35.85
- HIGH p90 same-direction gap ≈ 541.49
- LOW p90 same-direction gap ≈ 545.20
- HIGH p95 same-direction gap ≈ 1439.30
- LOW p95 same-direction gap ≈ 1335.56

The earlier membership-distance experiment also found that membership outcomes differ materially under alternative geometry assumptions:

| Candidate | HIGH joins | LOW joins |
| --- | ---: | ---: |
| center-distance | 22 | 14 |
| nearest interval point | 64 | 54 |
| nearest member | 51 | 41 |
| center ± tolerance | 22 | 14 |

These are descriptive results only. They are not a selection of a winning geometry.

## 16. HIGH vs LOW Differences

RESEARCH EVIDENCE

The same structural pattern appears in both directions, but not in the same intensity:

- HIGH is more permissive under interval-based reference logic than LOW
- center-based rules are stricter in both directions
- the absolute counts differ materially while the direction separation remains required

This supports the repo’s earlier finding that the high and low streams must remain separate and cannot be merged into a single zone geometry calibration stream.

## 17. Limitations

This analysis is intentionally limited by the project’s current frozen state.

- The repo does not contain a final zone object definition.
- The repo does not contain a final zone geometry definition.
- The repo does not contain a final center rule.
- The repo does not contain a final interval rule.
- The repo does not contain a final member-to-zone distance rule.
- The repo does not contain a final multiple-zone state machine.
- The repo does not contain a final historical snapshot lifecycle for zone state.

The purpose of this audit is therefore to establish the missing definitions clearly, not to fill them silently.

## 18. Evidence Classification

### FROZEN — HUMAN APPROVED

- Group A swing definition
- 15-minute UTC bar contract
- canonical replay ordering
- no-lookahead / causal eligibility
- HIGH and LOW swing streams remain separate
- only prior legal same-direction observations may influence tolerance
- current swing excluded from its own tolerance history
- W = 5 prior legal same-direction gaps
- minimum history = 1
- tolerance = median of selected prior legal absolute gaps

### RESEARCH EVIDENCE

- same-direction gap structure is real
- high and low streams differ materially
- a rolling prior-gap tolerance is more defensible than a static family
- the candidate geometry models materially change membership counts
- a final zone object cannot be inferred from the current repo evidence alone

### ARCHITECTURAL RECOMMENDATION

- keep the tolerance-history rule separate from any future zone-geometry rule
- keep center, interval, and membership as distinct root decisions
- treat any geometry model as research-only until a human-approved spec exists

### HUMAN DECISION REQUIRED

- exact zone object definition
- exact center requirement and calculation
- exact interval or boundary model
- exact member-to-zone distance rule
- exact zone lifecycle and snapshot semantics
- exact identity semantics
- exact multiple-zone tie-break semantics
- exact overlap, merge, or join policy

## 19. Architectural Recommendation

The strongest repo-grounded recommendation is procedural rather than mathematical:

- do not treat the historical tolerance rule as identical to zone width or zone boundary
- do not treat center-based distance and interval-based membership as interchangeable
- do not freeze any geometry model until the actual zone object is defined
- preserve member history and snapshot semantics for auditability
- distinguish tolerance, geometry, and membership as separate root decisions

This recommendation is intentionally conservative and respects the current repository evidence.

## 20. Unresolved Root Decisions

The next root decision should not be a membership rule alone. The next root decision is:

> What exactly is a zone?

Until that question is answered, the following remain unresolved:

1. zone object definition
2. center requirement and formula
3. interval definition
4. membership distance metric
5. multiple-zone resolution
6. overlap / merge / join policy
7. identity semantics
8. historical snapshot or mutation policy
9. replay-safe zone update sequence

## 21. Governance Status

- no production code changed
- no executable tests changed
- canonical dataset unchanged
- frozen Group A unchanged
- frozen 15-minute bar contract unchanged
- frozen W=5 unchanged
- frozen minimum-history=1 unchanged
- Group B remains NOT FROZEN
- Phase 2 remains NOT STARTED

## Final conclusion

The repository clearly supports a frozen tolerance-history rule, but it does not define a zone object or a zone geometry. The membership-distance audit showed that different geometry assumptions materially change the membership outcome, which means the geometry is a real root decision and not a downstream implementation detail.

The correct repository-grounded position is therefore:

> A zone object and geometry remain unresolved. The project has frozen tolerance history, but it has not frozen the object being evaluated.
