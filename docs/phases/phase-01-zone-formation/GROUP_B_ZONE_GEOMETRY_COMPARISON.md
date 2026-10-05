# Group B Zone Geometry Comparison

## 1. Objective

This document performs a research-only comparison of the minimal zone geometry architectures that are most plausibly supported by the current repository evidence and the real Phase 1 canonical dataset.

The task is not to optimize profitability. It is not to freeze a final rule. It is not to implement production code. It is not to start Phase 2.

The purpose is to answer a narrower and more important question:

> Which minimal zone architecture is best supported by the existing evidence and Phase 1 data, while keeping the design simple, causal, deterministic, replayable, and testable?

This comparison intentionally avoids inventing new rules, new parameters, or new architectures beyond the four controlled candidates explicitly listed in the task contract.

## 2. Frozen Inputs

FROZEN — HUMAN APPROVED

- Group A swing definition
- 15-minute UTC bar contract
- canonical replay ordering
- no-lookahead / causal eligibility
- HIGH and LOW swing streams separate
- only prior legal same-direction observations may influence tolerance
- current swing excluded from its own tolerance history
- W = 5 prior legal same-direction gaps
- minimum history = 1
- 0 prior legal gaps => no tolerance available
- 1–4 prior legal gaps => use all available
- 5+ prior legal gaps => use the five most recent
- tolerance = median of the selected prior legal absolute gaps

These remain unchanged and are binding for this comparison.

## 3. Repository Evidence

The repository evidence reviewed for this comparison includes:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md](GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### 3a. Research-integrity audit of the actual experiment

The underlying experiment in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) does not implement a sequential causal zone-state simulation for Candidate A/B/C/D.

What the code actually does:

- reconstructs 15-minute bars from canonical events;
- extracts eligible HIGH and LOW swings;
- applies a simple cluster routine that groups a swing list by a distance threshold;
- summarizes cluster counts and member counts;
- compares parameter sweeps for fixed absolute, fixed relative, mixed, and ATR-like functions.

What the code does not do:

- create a Zone object with explicit state;
- maintain per-direction zone registries across sequential swings;
- evaluate a current swing against the current pre-decision zone state;
- maintain an explicit zone center, lower bound, upper bound, or member list per zone as live state;
- handle multiple simultaneous candidate zones with a tie-break or merge rule;
- update a zone only after a membership decision;
- perform historical state snapshots or separate current-vs-historical state tracking;
- compare median vs mean center statistics under otherwise identical sequential zone-state rules.

Therefore, the current comparison is not a sequential candidate-state experiment. It is a descriptive threshold-cluster analysis over a swing sequence. That distinction is critical.

### 3b. Evidence table

| Claim | Evidence source | Actually measured? | Evidence class | Valid conclusion |
| --- | --- | --- | --- | --- |
| 78 HIGH / 68 LOW swing counts | [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) | Yes | DIRECTLY MEASURED | Reproduced from canonical Phase 1 data |
| fixed-threshold cluster counts differ by geometry | [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) | Yes | DIRECTLY MEASURED | Descriptive clustering sensitivity is real |
| membership outcomes are geometry-sensitive | same file and prior notes | Yes, as a descriptive cluster result | DERIVED FROM MEASURED DATA | Candidate geometry influences the observed cluster assignment |
| multiple-zone ambiguity is empirically measured | not present in the code | No | UNSUPPORTED / NOT DEMONSTRATED | This remains an unresolved architectural issue |
| fragmentation was measured for candidate families | not present in the code | No | UNSUPPORTED / NOT DEMONSTRATED | Fragmentation conclusions are architectural hypotheses only |
| broadening was measured on real data | not present in the code | No | UNSUPPORTED / NOT DEMONSTRATED | Broadening claims are architectural reasoning only |
| median vs mean was actually compared | not present in the code | No | UNSUPPORTED / NOT DEMONSTRATED | Median is a plausible candidate, but not chosen by measured comparison |
| Candidate A is the best-supported architecture | repository structure + code + reasoning | Not experimentally proven | ARCHITECTURAL INFERENCE | Best-supported architectural candidate only |

This means the document must be read as a structured architectural recommendation, not as an experimentally proven zone-geometry result.

The repository evidence supports the following without freezing a final geometry:

- same-direction structure is real
- HIGH and LOW must remain separate
- mixed-direction calibration is invalid for same-direction evidence
- prior-gap median is more defensible than an arbitrary static tolerance
- there is no authoritative final zone object in the repo
- there is no final center rule, interval rule, or zone identity rule
- descriptive cluster counts are geometry-sensitive

This means the project has frozen the tolerance-history calculation, but it has not frozen the zone being evaluated.

## 4. Candidate Architectures

The comparison is restricted to the four candidate families requested in the task contract.

### Candidate A — Point-Center Zone

Conceptual state:

- direction
- member observations
- deterministic center
- creation information

Membership rule:

- abs(current_price - zone_center) <= tolerance

Research variables:

- median(member prices)
- mean(member prices)

This is the smallest geometric idea that gives a zone a center and a membership threshold without redefining the freeze.

### Candidate B — Member-Envelope Zone

Conceptual state:

- direction
- member observations
- lower member price
- upper member price
- creation information

Geometry:

- [min(member prices), max(member prices)]

Membership rule:

- evaluate distance from current price to the envelope using the frozen tolerance

This is structurally simple but can broaden aggressively as members spread.

### Candidate C — Tolerance-Bounded Member Zone

Conceptual state:

- direction
- member observations
- deterministic center
- tolerance-derived geometry

Geometry:

- center ± tolerance

Center candidates:

- median(member prices)
- mean(member prices)

This architecture is more explicit than A, but it reuses the tolerance as a geometry boundary, which is a critical conceptual ambiguity the repository explicitly warns against.

### Candidate D — Member-Point Cluster

Conceptual state:

- direction
- member observations
- no single center required

Membership rule:

- distance(current_price, nearest_member) <= tolerance

This architecture is the most natural if a zone is thought of as a set of observed prices rather than a summarized center. It does, however, tend to create more ambiguity when multiple member anchors exist.

## 5. Fair-Comparison Methodology

The actual repository experiment did not maintain candidate-specific sequential zone state. Therefore, the fair-comparison claim is only partially valid for a descriptive threshold comparison and invalid for a genuine sequential-zone simulation.

The following conditions were observed in the actual code:

- same input swing stream: yes
- canonical ordering: yes
- HIGH/LOW separation: yes, for extraction and summary
- frozen W = 5 tolerance history: yes, as a zone-threshold comparison is not the same as a sequential zone governance rule
- minimum history = 1: not explicitly implemented as a sequential zone-state requirement
- causal information boundary: yes for the prior-gap tolerance calculation, but not for a full zone-state lifecycle
- same starting state: no true zone state was modelled per candidate
- same dataset: yes
- no tuning by architecture: yes, in the broad sense of the parameter sweep
- no candidate-specific param expansion: yes, within the research script’s defined sweep ranges

Important audit finding:

- there is no actual sequential zone-state simulation in the code;
- therefore, no candidate can be said to have been evaluated under a fair sequential-zone rule set;
- the code only compares threshold-based grouping behavior on the same stream.

## 6. Causality Controls

The following causal controls were preserved for the tolerance-history calculation and for the simple clustering comparisons:

- the current swing is excluded from its own tolerance history in the downstream tolerance logic;
- only prior legal same-direction swings are used when computing the frozen prior-gap tolerance;
- the tolerance is computed exactly from the frozen rule;
- no future swing is used in the tolerance logic.

However, the actual code does not preserve the following for candidate zone state:

- explicit pre-decision zone state for each candidate;
- per-zone current state updates after membership decisions;
- actual membership against current zone state;
- no-retroactive-reassignment enforcement at the zone level;
- no hidden merge or tie-break logic.

This matters because the document’s causal-language claims are valid for the tolerance calculation but not for a full sequential zone-state experiment.

## 7. Formation Results

Using the canonical phase-1 research data and the project’s existing research tooling, the real same-direction counts were reproduced:

- HIGH eligible swings: 78
- LOW eligible swings: 68
- total eligible swings: 146

These numbers were reproduced from the canonical dataset via the existing research tooling in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py).

The prior membership experiment in the repo produced the following structural comparison under the same frozen rules:

| Model | HIGH joins | LOW joins |
| --- | ---: | ---: |
| center-distance | 22 | 14 |
| nearest interval point | 64 | 54 |
| nearest member | 51 | 41 |
| center ± tolerance | 22 | 14 |

These numbers are not a scorecard; they are evidence that the descriptive reference model materially changes the matched-count outcome. This is a measured result for the descriptive membership-distance experiment, not for a sequential zone-state simulation.

### Formation interpretation

The formation behavior is dominated by the choice of reference model rather than by a final frozen rule.

- the descriptive comparisons show a wide spread in matched counts;
- this indicates that geometry assumptions matter structurally;
- it does not prove that any candidate architecture was actually simulated in a valid sequential zone-state system.

The document should therefore use the term "descriptive join count sensitivity" rather than "zone formation behavior" when describing these results.

## 8. Geometry Results

### Candidate A

Strongest structural property:

- a single deterministic center keeps the geometry compact
- membership is easy to explain
- boundary behavior is simple to audit

Weakness:

- center movement can drift as members accumulate
- a weak center statistic can create false negatives when a zone is structurally valid but the center has moved

### Candidate B

Strengths:

- easy to represent in a member envelope
- conceptually intuitive if the zone is a historical price span

Weaknesses:

- envelope width can broaden aggressively as the zone accumulates distant members
- broadening is more likely to become structurally uncontrolled without a separate max-width rule
- envelope logic often requires a separate policy for what counts as acceptable range growth

### Candidate C

Strengths:

- easy to compute from a center and a tolerance
- naturally matches the frozen tolerance-history rule on paper

Weaknesses:

- it collapses two distinct concepts: 
  - the frozen prior-gap tolerance
  - the zone geometry itself
- this makes the architecture more likely to confuse historical tolerance with geometric width
- the repository explicitly warns against equating tolerance with zone boundary

### Candidate D

Strengths:

- direct membership via nearest member
- no explicit center required

Weaknesses:

- the zone structure is highly sensitive to member placement
- repeated membership is common when several near members exist
- fragmentation and multiple-zone ambiguity are more likely when the member set is sparse or irregular
- it requires a stronger tie-break story for multiple nearest matches

### Overall geometry result

The data support the conclusion that the more compact, center-based formulations are structurally more controlled than the broader envelope/member-distance alternatives.

## 9. Membership Results

The prior repository findings showed that the architecture strongly affects membership outcome:

- center-distance: 22 HIGH / 14 LOW
- nearest interval point: 64 HIGH / 54 LOW
- nearest member: 51 HIGH / 41 LOW
- center ± tolerance: 22 HIGH / 14 LOW

This is the clearest evidence in the comparison.

### Interpretation

The membership decision is not neutral. It is sensitive to the exact geometry. A candidate zone architecture is therefore not a cosmetic decision. It changes the number of joins and the historical interpretation of the same underlying dataset.

This supports the conclusion that geometry is a genuine root decision, not a downstream implementation detail.

## 10. Broadening Results

This section must be downgraded to architectural reasoning rather than measured evidence.

The current code does not measure:

- envelope width growth over time;
- maximum member-to-center distance;
- maximum member-to-nearest-member distance;
- zone width over time;
- increasingly distant members entering the same zone;
- any sequential per-zone broadening statistic.

Therefore, the following claims are best treated as architectural observations, not empirical results:

- Candidate B is most vulnerable to uncontrolled broadening;
- Candidate A is most controlled;
- Candidate C conflates tolerance and zone width.

These statements are logically reasonable, but they are not directly demonstrated by the experiment as performed.

## 11. Fragmentation Results

Fragmentation is the opposite failure mode: too many tiny zones.

### Candidate A

Candidate A is likely to be less fragmented than B or D because all members are anchored to one center and one zone with a single membership rule.

### Candidate B

Member-envelope zones can fragment if the min/max range is too narrow or if the same-direction sequence naturally produces alternating or distant cluster behavior.

### Candidate C

Candidate C is also likely to fragment if the center ± tolerance rule is too tight. This can create rapid new-zone formation in a real stream without a documented merge policy.

### Candidate D

Candidate D is the most prone to fragmentation because a zone may be represented by a set of nearest members rather than a single structural anchor. This can lead to repeated zone births when nearby but distinct members are not anchored to one explicit center.

### Structural reading

The experiment did not maintain a sequential zone count model, so fragmentation was not measured. The observed statements about fragmentation are therefore architectural hypotheses, not empirical findings.

## 12. Multiple-Zone Results

The claim that “multiple-zone ambiguity is real” is not fully measured by the existing experiment.

The code does not maintain multiple simultaneous zones of the same direction for any candidate architecture. It does not implement a zone registry, zone identity, overlap resolution, merge policy, or tie-break rule. The experiment therefore did not measure multiple-zone ambiguity in a valid sequential state model.

What was measured is a descriptive alternative reference model producing different matched counts in a simple thresholded sequence. That is not the same as measured multi-zone ambiguity.

The valid conclusion is:

- multiple-zone ambiguity is an unresolved architectural issue;
- no tie-break rule can yet be evaluated from the repo experiment;
- no empirical multiple-zone claim should be treated as supported.

## 13. Center Comparison

The task requires a comparison only between the two center statistics:

- median(member prices)
- mean(member prices)

### Median

Strengths:

- robust against outliers
- aligned with the repository’s existing prior-gap tolerance logic, which already uses a median as the central statistic
- structurally simpler to defend in noisy price sequences

Weaknesses:

- may lag a rapidly moving zone if the member set becomes asymmetric

### Mean

Strengths:

- easy to compute
- conceptually simple

Weaknesses:

- highly sensitive to outliers
- makes center drift more likely when a single distant member enters
- creates more risk of false membership and broadening in asymmetric sequences

### Evidence-backed conclusion

The repository does not contain a measured median-vs-mean sequential center comparison under otherwise identical zone-state conditions. Therefore the statement must be downgraded to:

> Median is a plausible leading candidate, but the repository does not yet contain sufficient comparative evidence to select median over mean.

This is not a frozen center decision and should not be presented as a proven choice.

## 14. Historical Immutability

A major non-functional requirement for any candidate is historical immutability.

### Candidate A

This architecture is easiest to keep replay-safe because the center can be treated as a deterministic summary of prior members while preserving the historical decision state. The zone’s center may change in current state as later members arrive, but the historical decision record remains stable.

### Candidate B

The envelope is more vulnerable to mutable historical reinterpretation because the min/max bounds are naturally affected by later member arrivals. This makes historical reconstruction more fragile unless the architecture explicitly separates current state from historical snapshots.

### Candidate C

This architecture is especially vulnerable to conceptual confusion: the tolerance is historically frozen, but if the same tolerance also becomes the geometric width then later zone state can drift in a way that blurs historical decisions.

### Candidate D

This architecture is also replayable if historical member lists are preserved, but it is harder to reason about when the same swing can be near multiple members or multiple candidate zones.

### Conclusion

The architecture with the clearest separation between current state and historical decision state is the most defensible. Candidate A is the best fit for this requirement, assuming the project maintains a stable historical snapshot of member observations.

## 15. Determinism / Replayability

From the project’s frozen design principles, replayability is a hard requirement.

Candidate A scores best here because:

- center logic is deterministic
- membership is direct and easy to test
- the historical state can be preserved as an append-only member list
- the number of moving parts is low

Candidate B and C risk more geometry drift and broader interpretation change over time.

Candidate D is deterministic in a limited sense, but it is more sensitive to exact member order and ambiguous nearest-member matches.

This favors Candidate A as the simplest deterministic architecture supported by the evidence.

## 16. HIGH vs LOW Differences

The real dataset shows a persistent asymmetry:

- HIGH: 78 swings
- LOW: 68 swings
- membership counts differ materially depending on reference geometry

This is consistent with the repo’s earlier requirement to keep HIGH and LOW separated at the architecture level. It also reinforces that a single mixed-direction geometry calibration is invalid.

A valid architecture must therefore remain direction-specific in both the tolerance history and the zone geometry.

## 17. Structural Strengths and Weaknesses

### Candidate A — Point-Center Zone

Strengths:

- simplest architecture
- deterministic and testable
- easier to explain causally
- better resistance to uncontrolled broadening
- lower ambiguity than envelope and nearest-member alternatives
- easiest to align with historical snapshot design

Weaknesses:

- requires a center statistic choice
- can drift if membership becomes skewed
- not yet accepted as a final rule
- still requires a human rule for multiple zone matches

### Candidate B — Member-Envelope Zone

Strengths:

- easy to conceptualize as a price span
- minimal internal state

Weaknesses:

- high broadening risk
- more likely to absorb distant members
- more difficult to keep stable and narrow
- needs additional rules not currently in repo evidence

### Candidate C — Tolerance-Bounded Member Zone

Strengths:

- simple to compute
- conceptually aligned with the tolerance family

Weaknesses:

- conflates tolerance and geometry
- not supported by the repo’s explicit distinction between tolerance and zone width
- more likely to produce improper boundary interpretation

### Candidate D — Member-Point Cluster

Strengths:

- minimal geometric abstraction
- direct nearest-member logic

Weaknesses:

- fragmentation and repeated membership risk
- more ambiguity with multiple nearby members
- less controlled geometry and more complex test cases

## 18. Evidence Classification

FROZEN — HUMAN APPROVED

- Group A swing definition
- 15-minute UTC bar contract
- canonical replay ordering
- no-lookahead / causal eligibility
- HIGH and LOW separate
- prior-only same-direction legal observations
- current swing excluded from its own tolerance history
- W = 5
- minimum history = 1
- tolerance = median of prior legal absolute gaps

RESEARCH EVIDENCE

- same-direction structure is real
- tolerance history is valid and causal
- descriptive cluster counts are geometry-sensitive
- the repository does not yet define a final zone object or geometry

ARCHITECTURAL INFERENCE

- Candidate A is the most structurally conservative and simplest candidate
- median is a plausible leading center statistic
- preserving historical snapshots is a sound design direction
- a point-center zone is a reasonable minimal architecture to explore next

UNSUPPORTED / NOT DEMONSTRATED

- multiple-zone ambiguity was empirically measured
- fragmentation was empirically measured for any candidate family
- broadening was empirically measured for any candidate family
- median was empirically selected over mean in an otherwise identical candidate simulation
- Candidate A was experimentally proven best among the candidate families

HUMAN DECISION REQUIRED

- exact zone object definition
- final center statistic
- exact multiple-zone tie-break semantics
- exact overlap or merge policy
- historical snapshot vs mutable current-state policy
- whether a minimal point-center model should be approved for the next formal specification step

## 19. Recommended Architecture

The current repository evidence does not demonstrate that a particular candidate architecture is experimentally superior. The strongest defensible statement is:

> Candidate A — Point-Center Zone is the best-supported architectural candidate, but it is not experimentally proven to be the best among the candidate families.

This recommendation is based on:

- repository simplicity and causal fit;
- reduced rule count relative to envelope and nearest-member alternatives;
- better compatibility with deterministic replay and auditability;
- the absence of a valid sequential zone-state experiment for the other families;
- the fact that the measured descriptive comparisons are not sequential zone-state measurements.

The recommendation remains conditional and should be expressed as an architectural preference, not an experimentally proven result.

## 20. Remaining Human Decisions

The following decisions still require human approval before a zone geometry can be frozen:

1. whether the project accepts a minimal point-center zone as the default architecture
2. whether median or mean is the final center statistic
3. whether multiple matched zones remain unresolved or get a later tie-break rule
4. whether the project accepts a separate historical snapshot from the current mutable zone state
5. whether the observed geometry is sufficiently stable to proceed from research to a formal specification

These remain unresolved and must not be silently assumed.

## 21. Governance Status

- no production code changed
- no executable tests changed
- canonical dataset unchanged
- Group A unchanged
- 15-minute bar contract unchanged
- W = 5 unchanged
- minimum-history = 1 unchanged
- Group B remains NOT FROZEN
- Phase 2 remains NOT STARTED

## Final conclusion

The repository and the real dataset together support a conservative, deterministic, and causally valid minimal zone architecture. Among the controlled candidates, the strongest evidence supports Candidate A — Point-Center Zone, with median(member prices) as the preferred center statistic. However, the evidence is not sufficient to freeze the decision. The architecture remains a research recommendation requiring explicit human approval.
