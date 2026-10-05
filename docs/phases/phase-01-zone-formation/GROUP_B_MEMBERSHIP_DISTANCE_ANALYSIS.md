# Group B Membership Distance / Reference Rule Analysis

## Status

- Group B: NOT FROZEN
- research-only analysis
- no production implementation
- no executable tests changed
- no production behavior change
- no new tolerance formula introduced
- no new zone geometry introduced
- no new Group B freeze created
- Phase 2: NOT STARTED

## 1. Objective

This analysis addresses the remaining unresolved Group B root question:

> How should a newly confirmed eligible swing be evaluated against an existing zone to determine whether it belongs to that zone?

The repository evidence already freezes the following:

- Group A swing semantics
- 15-minute operational bar contract
- canonical replay and eligibility ordering
- same-direction handling
- prior-only, no-look-ahead causal evaluation
- W = 5 prior legal same-direction gaps
- minimum history = 1 prior legal same-direction gap
- tolerance = median of the selected legal prior same-direction gaps

What it does not freeze is the actual zone membership reference rule. The repository contains no authoritative zone geometry, zone center contract, zone interval definition, or final member-to-zone distance function. This analysis therefore stays explicitly in the research-only layer and does not upgrade any candidate into a specification.

## 2. Authoritative inputs

### 2.1 Governing project docs

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)

### 2.2 Relevant Group B research docs reviewed

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

## 3. Frozen inputs used by the analysis

The following are already frozen and govern every comparison in this analysis:

- Group A swing definition remains frozen.
- The 15-minute UTC bar contract remains frozen.
- Only confirmed eligible swings may enter downstream Group B logic.
- HIGH and LOW are separate streams.
- Only prior legal same-direction swings may be used.
- The current swing does not contribute to the tolerance used to evaluate itself.
- Prior observations use canonical replay / eligibility order.
- W = 5 prior legal same-direction gaps.
- minimum history = 1 prior legal same-direction gap.
- If 0 prior legal gaps exist: no tolerance is available.
- If 1–4 prior legal gaps exist: use all available.
- If 5+ prior legal gaps exist: use the five most recent.
- Tolerance = median of the selected prior legal gaps.

These are not broader Group B freezes. They are the exact frozen tolerance-history contract now approved for this research.

## 4. Existing repository evidence

The repository evidence establishes the following without creating a final zone-membership rule:

- The same-direction sequence is legitimate and structurally meaningful.
- High and low sequences must remain separate.
- Mixed high+low and mixed-direction calibration is not valid evidence for same-direction membership.
- The same-direction gap distributions are heavy-tailed and direction-dependent.
- The tolerance architecture is a rolling prior-gap median, but it is not yet a frozen zone-membership policy.
- The repo does not define a zone center, a zone interval, a zone member set, a zone update lifecycle, or a deterministic overlap policy.
- The repo does not define a candidate-to-zone distance metric in an authoritative way.

This means the evidence supports the tolerance history but not the membership geometry itself.

## 5. Missing definitions

The following definitions are missing from the authoritative repository evidence and therefore remain unresolved:

- What is the exact zone object?
- Is a zone represented by a center, an interval, a member list, or all three?
- What is the zone center statistic?
- Is the interval defined by min/max of members, center ± tolerance, both, or something else?
- What is the exact distance metric from a candidate swing to the zone?
- What is the exact rule for multiple candidate zones?
- What is the exact rule for overlap, merge, or join?
- What is the exact zone creation trigger?
- What is the exact historical mutation rule?
- What is the deterministic tie-break for equal-distance cases?

The repository provides no authoritative answer to these questions. Any attempt to fill them by assumption would invent a new rule and violate the governance requirement.

## 6. Candidate membership references

The research evaluates four candidate reference models only as research hypotheses. They are not approved rules.

### Candidate A — distance from the new swing price to the zone center

Hypothetical form:

- center = some defined zone center statistic
- membership if |P_new - center| <= T

Status:
- can be evaluated only if the repo first defines the center statistic and the zone state
- not freeze-ready
- not currently authoritative

### Candidate B — distance from the new swing price to the nearest point of the zone interval

Hypothetical form:

- interval = [lower, upper]
- nearest distance = 0 if lower <= P_new <= upper, else min(|P_new - lower|, |P_new - upper|)
- membership if nearest_distance <= T

Status:
- requires a zone interval definition such as min/max of member prices or center ± tolerance
- the repo does not provide this definition
- therefore not authoritative

### Candidate C — distance from the new swing price to the nearest existing zone member

Hypothetical form:

- member distance = min(|P_new - P_member_j|)
- membership if member_distance <= T

Status:
- can be evaluated as a hypothetical when a member list exists
- does not require a formal zone interval, but it does require a zone member set and a deterministic state model
- the repo does not define the zone member set formally

### Candidate D — whether the new swing lies inside an explicitly defined zone interval

Hypothetical form:

- zone interval = [L, U]
- membership if L <= P_new <= U

Status:
- can be calculated only after interval geometry is defined
- not authorized as a rule because the repo does not define L and U

### Evidence-based conclusion on candidate viability

The repository evidence supports evaluating A and C as center-based or member-based research constructions, and B and D only as interval-based hypothetical geometries. But none of the four is frozen because the repository does not define the critical geometry that turns them into a valid zone rule.

## 7. Dataset and methodology

### 7.1 Dataset used

The actual canonical research dataset used was:

- [data/canonical/tardis_btc_eur_20200101](../../data/canonical/tardis_btc_eur_20200101)
- metadata: [data/canonical/tardis_btc_eur_20200101/metadata.json](../../data/canonical/tardis_btc_eur_20200101/metadata.json)

This is the authoritative canonical BTC-EUR research data already used by prior Group B documentation.

### 7.2 Reproduction method

The historical reconstruction was performed using the existing repository research tooling:

- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

The analysis used the repository’s canonical bar reconstruction and the same-direction swing extraction already established in the project evidence.

### 7.3 Research-only experiment definition

Because a real zone geometry is not in the repo, a controlled research experiment was used to compare candidate reference behavior under a minimal hypothetical zone state.

For each same-direction sequence:

- use only prior legal confirmed same-direction swings
- compute the legal prior gap history under the frozen W = 5 / minimum-history = 1 semantics
- compute the tolerance T as the median of the selected prior legal gaps
- define a hypothetical zone around the prior same-direction state using only the historical sequence itself
- compare membership under four reference variants:
  - A: absolute distance to the historical center
  - B: absolute distance to the nearest point of the historical interval
  - C: absolute distance to the nearest historical member
  - D: inside the center-based interval defined as center ± T

This is a structural comparison only; it is not a production rule.

## 8. Causality / no-lookahead controls

All calculations used the causal controls already frozen in the repo:

- canonical replay order
- eligibility ordering
- no future swing access
- no retroactive mutation of earlier evaluations
- current swing excluded from the tolerance history used to evaluate itself
- only prior legal same-direction observations used
- no new timeframe introduced
- no new dataset introduced

This preserves the same causal structure as the approved tolerance-history rule and avoids accidentally turning a hypothetical membership formula into a frozen behavior.

## 9. Quantitative findings

The canonical research data produced the following same-direction swing counts:

- HIGH eligible same-direction swings: 78
- LOW eligible same-direction swings: 68
- total eligible same-direction swings evaluated: 146

The same-direction gap stream had the following descriptive shape:

- HIGH median same-direction gap: approximately 33.78
- LOW median same-direction gap: approximately 35.85
- HIGH p90 same-direction gap: approximately 541.49
- LOW p90 same-direction gap: approximately 545.20
- HIGH p95 same-direction gap: approximately 1439.30
- LOW p95 same-direction gap: approximately 1335.56

Under the minimal research-only comparison, the number of hypothetical memberships was:

| Candidate | HIGH join count | LOW join count |
| --- | ---: | ---: |
| A. center-distance | 22 | 14 |
| B. nearest interval point | 64 | 54 |
| C. nearest member | 51 | 41 |
| D. inside center ± T interval | 22 | 14 |

This shows that the candidate reference model materially changes the membership result even when the tolerance itself is held fixed to the frozen same-direction prior-gap median semantics.

### Disagreement counts

The disagreement percentages are large and directionally consistent:

| Pair | HIGH disagreements | LOW disagreements |
| --- | ---: | ---: |
| A vs B | 42 | 40 |
| A vs C | 29 | 27 |
| A vs D | 0 | 0 |
| B vs C | 13 | 13 |
| B vs D | 42 | 40 |
| C vs D | 29 | 27 |

Important interpretation:

- A and D are effectively equivalent under a center ± tolerance interpretation.
- B is dramatically more permissive than A/C because interval logic treats a point inside the historical range as close even when the center is far away.
- C is intermediate: it avoids the hard center/interval assumptions but still depends on the historical member set.

## 10. HIGH vs LOW findings

The same experiment produced the same general pattern in both directions, but the intensity differs:

- For HIGH, the center-distance rule is strictest (22 joins) while interval logic is much broader (64 joins).
- For LOW, the same pattern repeats, but with fewer total joins overall.
- This means the exact membership reference rule is not merely a mathematical detail; it materially changes whether the current swing is treated as belonging to an existing same-direction zone.

This supports the repo’s earlier finding that high and low spacing are materially different and cannot be merged into a single calibration stream.

## 11. Multiple-candidate-zone findings

A true multiple-candidate-zone evaluation is not possible from the repository evidence because the repo has no authoritative zone creation, zone identity, or zone member-state contract.

The research-only experiment therefore does not represent an actual multi-zone runtime state. Instead, it shows the following:

- the exact membership rule strongly changes how often a candidate would be grouped with a historical same-direction state
- the same current swing may appear to belong under one reference rule and not under another
- multiple plausible zone interpretations are therefore structurally common even before any zone lifecycle is defined
- this is an unresolved root decision,
  not a solved one

The evidence therefore supports the conclusion that the multiple-candidate-zone problem is structurally real but not currently resolvable by the repo because the zone state machine itself is absent.

## 12. Structural interpretation

The evidence supports the following interpretation:

1. The historical same-direction gap process has real structure.
2. The tolerance rule is not the only unresolved factor; the membership reference model is a separate root decision.
3. A center-based rule and an interval-based rule are not interchangeable.
4. A nearest-member rule is materially different from a center-distance rule.
5. The repo does not define which of these is the correct zone reference.
6. Without a frozen zone center and zone interval definition, the membership rule cannot be safely frozen.

The strongest practical conclusion is not that one of A-D is correct, but that the repo evidence already shows the membership rule is a genuine root decision and cannot be silently chosen.

## 13. Limitations

This analysis is intentionally limited by governance and evidence discipline.

- There is no authoritative zone geometry in the repo.
- There is no authoritative zone center contract.
- There is no authoritative member-to-zone distance metric.
- There is no authoritative multi-zone state machine.
- There is no final overlap / merge / join rule.
- The experiments above are hypothetical and comparative only.
- They are used to expose structural sensitivity, not to justify a production rule.

This is the correct research posture under the project’s current frozen state.

## 14. Evidence classification

### FROZEN / HUMAN APPROVED

- Group A swing semantics
- 15-minute operational bar contract
- canonical replay ordering
- same-direction separate sequence requirement
- prior-only legal observation rule
- current swing excluded from its own tolerance history
- W = 5 prior legal same-direction gaps
- minimum history = 1 prior legal same-direction gap
- tolerance = median of the selected prior legal same-direction gaps

### AUTHORITATIVE REPO EVIDENCE

- same-direction high and low sequences are distinct
- mixed-direction / mixed high+low calibration is invalid for same-direction tolerance design
- the repo supports deterministic replay and no-look-ahead causality
- the historical same-direction gap process shows real structure

### RESEARCH EVIDENCE

- center-distance, nearest-member, and interval-based membership are materially different in the actual data
- the interval-based reference is much more permissive than the center-distance rule
- the candidate differences are large enough to change membership decisions materially
- the data does not support a final choice of one reference model

### ARCHITECTURAL RECOMMENDATION

- Do not freeze a zone-membership distance rule yet.
- Treat the current candidate models as comparative research only.
- If a provisional baseline is needed later, a center-based rule is the least arbitrary only when an explicit center statistic is also approved.

### UNRESOLVED / HUMAN DECISION REQUIRED

- exact zone object definition
- zone center statistic
- zone interval semantics
- zone member list semantics
- zone creation trigger
- member-to-zone distance function
- multiple-candidate-zone resolution
- overlap / merge / join rule
- deterministic tie-break for equal-distance or equal-center cases

## 15. Architectural recommendation, if justified

No final membership rule is justified by the current repository evidence.

The research does, however, justify the following cautious recommendation:

- Do not freeze a zone-membership distance function until the zone center and zone geometry are explicitly defined.
- Treat center-distance and nearest-member as more defensible research baselines than interval-based membership only if the project later approves a center or member-list zone representation.
- Treat interval-based membership as a separate architecture requiring its own explicit geometry and tie-break semantics.

This is a recommendation for future root decision work, not a frozen rule.

## 16. Explicit unresolved decisions

The following remain unresolved and must be treated as separate human-approved decisions if the project chooses to move beyond research-only analysis:

1. exact zone object definition
2. exact zone center statistic
3. exact zone interval or boundary definition
4. exact member-to-zone distance metric
5. exact behavior when a new swing could satisfy multiple same-direction zones
6. exact join / merge / overlap semantics
7. exact zone creation trigger and minimum evidence threshold
8. exact tie-break semantics for equal distances or equal center values
9. exact historical snapshot / mutation semantics for prior zone membership

## 17. Governance status

- no production code was changed
- no executable tests were changed
- no strategy behavior was changed
- no Phase 2 work was started
- Group B remains NOT FROZEN
- Phase 2 remains NOT STARTED

## Final conclusion

The repository evidence clearly supports the frozen tolerance history and the causal prior-observation model. It does not support a final zone membership distance rule because the required zone geometry is absent from the repo and from the current evidence hierarchy.

The real research result is therefore not a final answer but a clear root-cause finding:

- the zone-membership reference problem is structurally significant
- the model choice materially changes membership counts in real data
- the repo does not yet define the missing geometry needed to make the choice authoritative
- the content required for a final rule must be added only as a future explicit human-approved specification

At this stage, the correct repository-grounded position is:

> Membership distance is unresolved, not silently chosen.
