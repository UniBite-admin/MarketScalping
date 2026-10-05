# Group B Membership Semantics Audit

## Status

RESEARCH ONLY

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- No production code was changed.
- No executable tests were changed.
- No dataset was modified.
- No new technical rule was frozen.
- Human-approved/frozen decisions remain unchanged.

## 1. Known and Frozen

The following decisions are already human-approved and remain authoritative for this audit:

1. Group A swing definitions are frozen and human approved.
2. The 15-minute UTC OHLC/bar contract is frozen and human approved.
3. Group B tolerance-history contract is frozen and human approved:
   - HIGH and LOW remain separate.
   - Only prior legal same-direction gaps are eligible.
   - The current swing is excluded from its own tolerance history.
   - W = 5 prior legal same-direction gaps.
   - Minimum history = 1.
   - 0 prior legal gaps => no tolerance is available.
   - 1–4 prior legal gaps => use all available.
   - 5+ prior legal gaps => use the five most recent.
   - Tolerance = median(selected prior legal absolute gaps).
4. Candidate A center statistic is frozen and human approved:
   - center = median(member prices)

The following remain explicitly NOT FROZEN:

- membership rule
- zone creation
- zone lifecycle
- zone identity
- multiple simultaneous zones
- overlap/merge behavior
- zone width/geometry beyond the frozen center statistic
- historical mutation/snapshot semantics
- any broader Group B architecture

## 2. What the Existing Experiment Actually Measures

### 2.1 Repository evidence examined

The audit used the authoritative project sources and the relevant Group B research documents, including:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ARCHITECT_PROPOSAL.md](GROUP_B_ARCHITECT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL_AUDIT.md](GROUP_B_PROPOSAL_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md](GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_COMPARISON.md](GROUP_B_ZONE_GEOMETRY_COMPARISON.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### 2.2 What the research code actually implemented

The code in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) does not implement a persistent Zone object, zone registry, or stateful membership engine.

It does the following:

- reconstructs 15-minute canonical bars from canonical event data
- identifies swing highs and swing lows based on local extrema in the reconstructed bar series
- separates HIGH and LOW streams
- computes tolerance families such as fixed absolute, fixed relative, mixed absolute+relative, and ATR-based heuristics
- groups values using a simple contiguous-cluster algorithm:
  - for a candidate list of swings, it walks in order
  - compares the next swing price to the last price in the current cluster
  - if abs(next - last) <= tolerance, it stays in the cluster
  - otherwise it starts a new cluster
- reports summary counts and cluster size distributions

This is a descriptive clustering experiment. It does not create:

- a Zone class
- a Zone object
- a zone center state
- an active zone registry
- a historical membership ledger
- a multi-zone assignment engine
- overlap/merge resolution
- branch/merge lifecycle semantics
- historical snapshot mutation semantics

The code is therefore evidence-generating research, not a runtime membership specification.

### 2.3 What is and is not represented

A. Behavior actually implemented by the research code

- canonical order of bars and swings
- HIGH and LOW separation
- prior-gap-based tolerance families in a descriptive sense
- simple cluster grouping by adjacent absolute price distance under a chosen tolerance value
- descriptive summary of cluster size and spread

B. Behavior described in documents but not implemented

- real zone object
- zone center lifecycle
- zone creation timing
- zone identity
- zone overlap semantics
- zone merge semantics
- multiple-active-zone assignment logic
- historical mutation/snapshot policy
- official membership reference metric as a frozen rule

C. Behavior neither specified nor implemented

- final member-to-zone distance function
- final interval geometry
- final overlap resolution
- final multi-zone assignment semantics
- final historical immutability policy for zone state

## 3. Candidate Membership Rules

The research docs compare four candidate membership-reference models only as research hypotheses. They are not approved rules.

### Candidate A — CENTER DISTANCE

Form:

- abs(current_price - zone_center) <= tolerance

This requires a zone center and a zone state. The repository does not define the final zone state or what an actual zone center means in a live, sequential model.

### Candidate B — NEAREST MEMBER

Form:

- min(abs(current_price - member_price)) <= tolerance

This requires a real member set and a persistent zone object. The code does not implement such a zone member-state model.

### Candidate C — MEMBER ENVELOPE / INTERVAL

Form:

- distance from current_price to [min(member_prices), max(member_prices)] <= tolerance

This requires a formal interval definition and a member set. The current repo does not define these semantics explicitly.

### Candidate D — CENTER ± TOLERANCE

Form:

- current_price inside [center - tolerance, center + tolerance]

This is equivalent to the center-distance form when the membership rule is defined by a symmetric interval around a single center:

- abs(current_price - center) <= tolerance
- current_price in [center - tolerance, center + tolerance]

These are mathematically identical for a scalar center and symmetric tolerance.

### Important governance note

The project may compare these candidates as descriptive geometric ideas, but it may not convert them into a frozen membership rule without:

- a zone object definition
- explicit zone center semantics
- explicit interval/membership state
- explicit multiple-zone handling
- explicit historical mutation semantics

## 4. Mathematical Equivalences

### 4.1 A and D

Under the tested geometry, Candidate A and Candidate D are mathematically equivalent.

If the zone center is c and the tolerance is T, then:

- abs(P - c) <= T

is the same as:

- P in [c - T, c + T]

Therefore, A and D are not independent operational models under a symmetric point-center rule. They are the same membership test expressed in two equivalent forms.

### 4.2 B and C are not equivalent to A/D without extra state

Candidate B and C require a member-based geometry or interval-based geometry that is not actually defined as a persistent zone state in the repo. Without a formal zone object, these remain hypothetical reference constructions, not authoritative membership rules.

### 4.3 The current evidence does not justify treating A/D as fixed final winners

The repo evidence proves only that the choice of reference geometry matters. It does not yet prove that one specific geometry is the final correct rule in a sequential zone lifecycle.

## 5. Evidence That Is Legitimately Comparable

The following evidence is legitimate within the current model:

### DIRECT EVIDENCE

- The current repository evidence supports that HIGH and LOW must be treated separately.
- The canonical research data contains 78 eligible HIGH swings and 68 eligible LOW swings under the current same-direction descriptive reconstruction.
- The same-direction tolerance history is frozen as W = 5 prior legal same-direction gaps with median-of-selected-gap tolerance.
- The center statistic is frozen for Candidate A as median(member prices).

### DESCRIPTIVE EVIDENCE

- The descriptive cluster experiment shows that the way a candidate is referenced materially changes the resulting membership count.
- The candidate A / D group produced 22 HIGH joins and 14 LOW joins in the documented comparison.
- The candidate B interval formulation produced 64 HIGH joins and 54 LOW joins.
- The candidate C nearest-member formulation produced 51 HIGH joins and 41 LOW joins.
- These are comparative behaviors of the descriptive model, not proof of a final runtime rule.

### METHODOLOGICAL EVIDENCE

- The same-direction comparison method is structurally sensitive to how the reference geometry is defined.
- A and D are equivalent under a symmetric point-center interpretation.
- The interval and member-based variants are materially different from the center-distance form.

### ARCHITECTURAL INFERENCE

- A full membership rule cannot be frozen without specifying the zone object and sequential state semantics.
- The repository already establishes that the membership semantics are a genuine root decision and cannot be silently inferred.

### NOT MEASURABLE WITH CURRENT MODEL

The current experiment does not legitimately measure:

- fragmentation in a live sequential zone state
- zone broadening under a real lifecycle
- repeated membership churn
- stability of a real zone center over time
- overlap/merge effects
- multiple-zone ambiguity in a real runtime engine
- historical mutation behavior
- robustness of a zone in a true sequential state model

These are not direct metrics of the current descriptive experiment and should not be presented as if they were.

## 6. Evidence That Is NOT Legitimately Comparable

The following claims are not anchored in the current repository model and therefore cannot be treated as evidence:

- a final zone membership rule is proven
- a final winner between A, B, C, and D is known
- a sequential zone lifecycle has been evaluated
- multiple simultaneous zones have been evaluated in code
- overlap/merge behavior has been evaluated in code
- historical membership immutability has been validated in a runtime system
- zone fragmentation or robustness has been directly measured in a sequential engine

Any claim that one candidate is “better” without a true sequential zone simulation remains an architectural hypothesis, not evidence.

## 7. Missing Root Decisions

The current repository does not yet define the following root decisions:

1. What is the zone object?
2. Does a zone store a center, a member set, a lower/upper range, or all of them?
3. Is the center mutable or immutable after creation?
4. If mutable, when does it update?
5. Is the zone interval defined from members, center ± tolerance, or another formula?
6. How is membership evaluated against multiple active zones?
7. What determines that a zone is active?
8. What happens when two zones overlap or nearly overlap?
9. Does a candidate join the nearest zone, the earliest zone, or the best-fit zone?
10. Can a zone gain or lose members retroactively?
11. Is zone membership permanent or revisable as new data arrives?
12. What is the deterministic tie-break order for equal distances?

These are unresolved root decisions. The project is not currently allowed to invent them in this audit.

## 8. Recommended Next Research Question

The next valid research question is not “Which candidate wins?”

The next valid question is:

> What exact sequential zone-state model is required before the repository can compare A, B, C, and D as real membership rules instead of purely descriptive geometric constructions?

This question is still research-only and does not authorize implementation or a Group B freeze.

## 9. Human Decision Required? — YES / NO

### YES

A human decision is required only at the next level of governance: the zone-state contract itself.

The current evidence does not yet justify a final membership rule, because the project still lacks a specified zone object, sequential lifecycle, and multiple-zone semantics.

This is not a request to choose a winner today. It is a request to decide whether a future sequential zone-state specification should be designed before any membership freeze is attempted.

## 10. Governance Status

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- No production code changed.
- No executable tests changed.
- No dataset modified.
- No new technical rule frozen.
- Only the already approved frozen decisions remain in force.

## Final conclusion

The current repository evidence supports a disciplined conclusion:

- the frozen tolerance-history rule is real and causal
- the descriptive cluster experiment is real and measurable
- the reference geometry materially changes the membership result
- A and D are mathematically equivalent under a symmetric point-center rule
- B and C require an actual zone-member state that the repo does not define
- the repository does not yet have a valid sequential zone-state model for a final membership freeze

Therefore the proper audit conclusion is:

The membership-reference question is a real root decision, but it is not yet comparable as a final zone rule under the repository’s current evidence. The evidence currently supports a comparative structural sensitivity result, not a final membership selection.
