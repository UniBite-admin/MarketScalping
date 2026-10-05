# Group B Zone Geometry Final Audit

## 1. Scope

This document is a governance/research audit only.

It addresses the unresolved Group B root decision:

> What is the simplest defensible geometry for a Zone after membership is evaluated?

This audit does not:

- freeze any geometry rule
- modify production code
- modify tests
- modify datasets
- start Phase 2
- perform arbitrary parameter optimization
- invent an envelope-expansion formula
- silently change any frozen decision

The purpose is to separate three distinct ideas that the repository has already made clear are not equivalent:

1. membership rule
2. center statistic
3. Zone geometry

This separation is required because the repository has frozen membership under the current center and tolerance semantics, but it has not frozen any final Zone geometry.

Classification: REPOSITORY FACT / RESEARCH ONLY / NOT FROZEN

## 2. Frozen inputs

The following inputs remain authoritative and are preserved exactly for this audit:

- 15-minute UTC bar contract
- separate HIGH and LOW streams
- W = 5 prior legal same-direction gaps
- minimum tolerance history = 1
- causal prior same-direction absolute-gap tolerance
- current swing excluded from its own tolerance history
- zone center = median(member prices)
- membership = abs(incoming_price - current_zone_center) <= current_tolerance
- same-direction ordering remains causal and replay-safe
- no lookahead

This is a list of frozen constraints. It is not a frozen Zone object or Zone geometry contract.

Classification: FROZEN

## 3. Geometry candidates

### A. Symmetric center geometry

Lower = center - tolerance
Upper = center + tolerance

Interpretation: a Zone is represented as a symmetric interval around the current center.

### B. Member-envelope geometry

Lower = min(member prices)
Upper = max(member prices)

Interpretation: a Zone is represented by the span of the observed member prices.

### C. Nearest-member / member-derived geometry

Geometry is derived from the proximity of the incoming price to a nearest existing member rather than to the zone center.

Interpretation: the Zone is effectively member-centered rather than center-centered.

### D. Other geometry already documented in the repository

The repository documents several descriptive proposals and state contracts, but not a final frozen geometry. No authoritative lower/upper boundary rule is frozen beyond the member list and the causal center/tolerance semantics already approved.

The repo does not define a final Zone object, explicit lower/upper bound semantics, overlap semantics, merge semantics, or lifecycle semantics.

Classification: PROPOSAL ONLY / UNRESOLVED / BLOCKED BY UNRESOLVED ROOT DECISION

## 4. Causal computability

### Candidate A — center ± tolerance

1. Is it causally computable?
   - Yes, if the current zone center and current tolerance are already known.

2. Does it use only frozen state?
   - It uses the frozen center statistic and the frozen tolerance history.
   - However, it adds a new geometry interpretation to already-frozen state.

3. Does it remain consistent with frozen median center semantics?
   - Yes, when the center is still median(member prices).
   - But the center median does not prove that the Zone boundaries are center ± tolerance.

4. Does it require an additional expansion/update rule?
   - Not necessarily for membership evaluation.
   - But it does require a new rule to say that the Zone boundary is the center interval itself, rather than merely a convenient membership test.

5. Does it introduce hidden state?
   - Not if it is only treated as a descriptive interval computed from current state.
   - It does introduce a hidden semantic decision: that a Zone boundary equals the center-based interval, not just a membership radius.

6. Is it supported by repository evidence?
   - Partially, as a natural interpretation of the frozen center/tolerance pair.
   - Not as a frozen rule.

7. Is it merely a proposal?
   - Yes, as a geometry definition.

Classification: PROPOSAL ONLY

### Candidate B — member-envelope geometry

1. Is it causally computable?
   - Yes, once the member set exists.

2. Does it use only frozen state?
   - It uses the member list and the current member prices.
   - It does not require a new tolerance formula, but it does require a new choice: whether the envelope is a final Zone boundary or only a descriptive summary.

3. Does it remain consistent with frozen median center semantics?
   - It can be consistent as long as the center remains median(member prices).
   - But it is a different geometric object from the center-based interval.

4. Does it require an additional expansion/update rule?
   - It requires an explicit decision that min/max of member prices is the Zone geometry definition.
   - Without that rule, it remains a descriptive summary rather than a final Zone boundary.

5. Does it introduce hidden state?
   - It introduces no extra hidden state by itself, but it depends on the existence and semantics of the member set.

6. Is it supported by repository evidence?
   - It is directly derivable from the member set and the repository’s repeated discussions of member observations.
   - But the repo does not freeze it as the authoritative Zone geometry.

7. Is it merely a proposal?
   - Yes, as a final geometry rule.

Classification: PROPOSAL ONLY

### Candidate C — nearest-member / member-derived geometry

1. Is it causally computable?
   - Yes, in a research-only sequential model, if the member set is already defined.

2. Does it use only frozen state?
   - It requires a current member set and a nearest-member proximity interpretation.
   - The repo does not freeze those semantics as final state.

3. Does it remain consistent with frozen median center semantics?
   - It can be inconsistent with the center semantics, because nearest-member distance is a different geometric anchor from center-distance.

4. Does it require an additional expansion/update rule?
   - Yes. It inherently depends on nearest-member selection semantics and member-set update behavior.

5. Does it introduce hidden state?
   - Yes, because the rule depends on which member is considered nearest and how the member set is maintained and updated.

6. Is it supported by repository evidence?
   - Not as an authoritative final rule.
   - The repository evidence explicitly distinguishes center-based membership from nearest-member membership, and it does not freeze the latter.

7. Is it merely a proposal?
   - Yes.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION / PROPOSAL ONLY

### Candidate D — other documented geometry

This category remains unapproved because the repository does not freeze a final Zone object or a final lower/upper boundary definition. Any additional geometry beyond A/B/C is either a descriptive representation or an unapproved design hypothesis.

Classification: UNRESOLVED / BLOCKED BY UNRESOLVED ROOT DECISION

## 5. State requirements

The minimal state contract already supported by the repo is narrower than a final Zone geometry definition.

The repo supports the following minimum causal state:

- direction (HIGH or LOW)
- candidate/seed existence
- member observations
- median center from current member prices
- current tolerance from prior same-direction legal gaps
- causal ordering, no lookahead

This is enough to define membership under the frozen rule, but it is not enough to define final Zone geometry without an additional explicit decision.

The currently missing geometry state is:

- whether a Zone has a lower/upper boundary
- whether the boundary is derived from center, members, or another construct
- whether the boundary is descriptive only or operationally authoritative
- whether the boundary is recomputed dynamically or fixed after creation
- how member-set updates affect the geometry
- whether overlap/merge behavior is part of the Zone state

This is a root decision gap, not a parameter issue.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 6. Evidence comparison

### Repository evidence summary

- The repository freezes the tolerance-history rule and the median center statistic.
- The repository freezes membership under the center-distance rule.
- The repository does not freeze a Zone geometry rule.
- The repository does not freeze a final Zone object schema.
- The repository documents multiple descriptive geometry interpretations, but treats them as research proposals, not authorities.
- The descriptive research code reconstructs bars and eligible swings, but it does not implement a final sequential Zone geometry engine.

### Direct evidence that membership does not imply geometry

The critical distinction is explicit and supported by the repo evidence:

- center = median(member prices)
- tolerance = causal prior-gap median
- membership = abs(incoming_price - center) <= tolerance

These facts define a membership test. They do not define the boundary of the Zone itself.

A membership rule can be symmetric about a center without requiring the Zone boundary itself to equal the same symmetric interval. The repo does not authorize that leap.

Therefore:

- Candidate A is a plausible geometric interpretation
- it is not a logically necessary consequence of the frozen membership rule
- it remains a proposal only, not a freeze

### Candidate-by-candidate evidence classification

| Candidate | Causally computable | Uses only frozen state | Consistent with median center | Needs expansion/update rule | Hidden state | Repo support | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. center ± tolerance | Yes | Partially | Yes | Yes, if treated as final geometry | Low | Partial, as interpretation only | PROPOSAL ONLY |
| B. member envelope | Yes | Partially | Yes, but different geometry | Yes, if treated as final boundary | Low | Partial, descriptive support only | PROPOSAL ONLY |
| C. nearest member | Yes | No | Not necessarily | Yes | Yes | Not authoritative | BLOCKED BY UNRESOLVED ROOT DECISION |
| D. other documented geometry | Unclear | No | Unclear | Yes | Yes | Not authoritative | UNRESOLVED |

## 7. Hidden assumptions / unresolved semantics

The major unresolved semantics are the following:

1. Is a Zone defined only by a member set and center, or must it also carry explicit lower and upper bounds?
2. If bounds exist, are they derived from center ± tolerance, min/max(member prices), or another rule?
3. Is Zone geometry computed dynamically after every membership event, or only when the Zone is created or updated?
4. Is a Zone immutable after creation, or is the geometry updated as member prices accumulate?
5. Does a Zone require explicit lifecycle state such as active / closed / merged / retired?
6. Is overlap or merge logic required before boundary geometry can be considered final?
7. Is the zone boundary an operational object or merely a descriptive summary used for membership evaluation?

These are not implementation details. They are root decisions.

Classification: UNRESOLVED / BLOCKED BY UNRESOLVED ROOT DECISION

## 8. Recommended simplest proposal

The simplest defensible research-only recommendation is:

- do not freeze a final Zone geometry yet
- keep membership and center/tolerance as separate concepts
- if a descriptive geometry must be recorded for research only, Candidate B (member-envelope geometry) is the least assumption-laden explicit representation because it is directly derived from the observed member prices and does not require a new center-based expansion rule
- but even that should be labeled PROPOSAL ONLY, not FROZEN

This is the strongest evidence-grounded recommendation because it recognizes the distinction between:

- membership = already frozen
- geometry = still unresolved

The project should not assume that the current frozen membership test automatically implies the Zone boundary. That inference is not supported by the repository evidence.

Classification: PROPOSAL ONLY / RESEARCH ONLY

## 9. Decision readiness

Status: NOT READY TO FREEZE

The repository evidence is insufficient to freeze a final Zone geometry rule because:

- the final Zone object is not defined
- lower/upper bound semantics are unresolved
- update semantics are unresolved
- overlap/merge semantics are unresolved
- the geometry question is not logically derived from the already-frozen membership rule

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 10. Remaining blockers

The remaining blockers are:

- no authoritative Zone object definition
- no final lower/upper bound rule
- no authoritative geometry update rule
- no authoritative lifecycle or overlap semantics
- no evidence that center ± tolerance is the final Zone boundary
- no final human decision resolving whether Zone geometry is descriptive or operational

Any attempt to freeze geometry before these are resolved would silently change the current design boundary.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 11. Required human decision

The required human decision is a single root question:

> Should a Zone have an explicit lower/upper boundary at all, and if so, which boundary definition is authoritative: center ± tolerance, member envelope, nearest-member distance, or some other rule?

Until this question is answered, the repository must treat Zone geometry as:

- UNRESOLVED
- PROPOSAL ONLY
- BLOCKED BY UNRESOLVED ROOT DECISION

The precise policy outcome is:

- Group B remains NOT FROZEN
- Phase 2 remains NOT STARTED

This document is an audit only and does not authorize any implementation, test change, or downstream Phase 2 work.
