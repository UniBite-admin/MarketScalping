# Group B Zone Geometry Semantics Audit

## Status

RESEARCH ONLY

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- This document is an audit only.
- No production code was modified.
- No production tests were modified.
- No canonical data was modified.
- No frozen decision was changed.

## 1. Objective

This audit addresses the unresolved Group B root decision:

> What is the actual geometric extent of a Zone, once a valid Zone exists?

The repository currently supports:

- member prices
- a median center
- a causal tolerance derived from prior legal same-direction historical gaps

What is not established is that:

- Zone = center ± tolerance
- Zone = member envelope ± tolerance
- Zone = nearest-member coverage
- Zone = member-bound interval without further expansion

This audit evaluates only geometry models that can be defined from the current evidence. It does not invent new parameters or freeze any rule.

## 2. Frozen decisions preserved exactly

The following decisions remain authoritative and are not reinterpreted in this document:

### 2.1 Phase 1 Group A swing definition

FROZEN

- Swing High: High[i] > High[i - 1] and High[i] > High[i + 1]
- Swing Low: Low[i] < Low[i - 1] and Low[i] < Low[i + 1]
- strict comparisons only
- complete required neighborhood
- confirmation before downstream eligibility
- no lookahead

### 2.2 15-minute UTC bar contract

FROZEN

- 15-minute UTC bucket
- interval: [bar_start, bar_end)
- event at bar_end belongs to next bar
- closed bars are immutable
- trailing/incomplete bars excluded
- final partial bar at dataset end is discarded

### 2.3 Same-direction separation and tolerance history

FROZEN

- HIGH and LOW streams remain separate
- W = 5
- minimum tolerance history = 1
- tolerance = median of selected legal prior same-direction gaps
- current swing excluded from its own tolerance history
- 0 prior legal same-direction gaps => no tolerance available
- 1–4 prior legal gaps => use all available prior legal gaps
- 5+ prior legal gaps => use the five most recent

### 2.4 Center rule

FROZEN

- center = median(member prices)

This does not imply a frozen Zone geometry.

## 3. Existing proposals preserved as proposal only

The following prior proposals remain proposal-only and are not frozen:

- first eligible same-direction swing → candidate/seed
- second qualifying same-direction observation → valid Zone
- append-only member set after Zone creation

These are treated as:

PROPOSAL ONLY — NOT FROZEN

## 4. Repository evidence reviewed

This audit was grounded in the existing repository evidence and current process documents, including:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md](GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_COMPARISON.md](GROUP_B_ZONE_GEOMETRY_COMPARISON.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

The repository current evidence is descriptive research and state documentation, not a persistent Zone implementation.

## 5. Critical distinction: the root issue

The repo supports the distinction between:

1. center
2. tolerance
3. membership criterion
4. Zone geometry
5. Zone lifecycle

These are not equivalent or derivable from one another without additional frozen rules.

### 5.1 REPOSITORY FACT

The repo does not freeze a Zone geometry rule; it only freezes the center statistic and tolerance history.

This means:

- frozen center ≠ frozen geometry
- frozen tolerance ≠ frozen geometry
- membership rule ≠ geometry rule
- geometry ≠ lifecycle

### 5.2 REPOSITORY FACT

The project repeatedly treats geometry, overlap, merge, and lifecycle behavior as unresolved Group B questions.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md](GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_COMPARISON.md](GROUP_B_ZONE_GEOMETRY_COMPARISON.md)

## 6. Actual-data evidence from the existing canonical pipeline

The canonical research pipeline already reconstructs the 15-minute stream and enumerates same-direction eligible swings.

### 6.1 Verified canonical counts

Command used:

```powershell
.\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"
```

Output observed:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

### 6.2 Interpretation

These are factual historical counts for eligible swings in the canonical stream.

They do not constitute a frozen Zone geometry or a final Zone count because the repository does not currently define a valid Zone-state engine or geometry contract.

Classification: REPOSITORY FACT

## 7. Candidate geometry models

### Candidate A — symmetric center interval

Zone:

`[center - tolerance, center + tolerance]`

#### 7.1 What the repository actually supports

This is a mathematically natural interpretation of the current frozen state because:

- center is frozen as median(member prices)
- tolerance is frozen as median of prior same-direction gaps
- the interval is a symmetric scalar expansion around a single center

However, the repo does not define a governing rule that says:

- the Zone extent must be this interval
- the Zone is defined only by this interval
- the interval is the primary Zone geometry rather than just a convenience for evaluating membership

#### 7.2 Why it is not yet a frozen rule

The repo does not freeze the mapping from the center/tolerance pair to Zone geometry.

This is an architectural gap:

- the center statistic is frozen
- the tolerance history is frozen
- the geometry interpretation is not frozen

#### 7.3 Evidence assessment

Candidate A is a coherent descriptive model, but it remains a convenience interpretation, not evidence-backed geometry.

Classification: PROPOSAL ONLY

#### 7.4 Conclusion

Center ± tolerance is supported only as a plausible geometric representation. It is not yet a repository-supported Zone definition.

## 8. Candidate B — member-envelope expansion

Zone geometry is based on the minimum and maximum member prices, with tolerance applied to the envelope.

#### 8.1 What the repository supports

The repo supports the idea that members have prices and a current median center, and it supports tolerance as a scalar based on prior legal gaps.

It does not define:

- whether the envelope uses min/max as the base
- whether tolerance is applied symmetrically to both sides
- whether tolerance is applied once to the whole envelope or per boundary
- whether the envelope is recalculated or fixed after creation
- whether a member set can expand or contract under the chosen geometry

#### 8.2 Why this candidate is not well-specified enough to test as a rule

This candidate requires a new, explicit envelope contract that the repository does not define.

There is no frozen formula for:

- lower bound
- upper bound
- growth rule
- expansion direction
- tolerance application timing

Without these, the candidate cannot be treated as a valid sequential geometry test.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

#### 8.3 Conclusion

Member-envelope geometry cannot be defined without inventing an unrecorded expansion rule. It is not testable as a final rule today.

## 9. Candidate C — nearest-member coverage

The Zone covers price regions around individual member prices rather than around the median center.

#### 9.1 What the repository supports

The repo supports the existence of a member set and a frozen tolerance value. It does not freeze a nearest-member rule, a radius, or a coverage function.

This means the candidate is not meaningfully defined unless the repository also specifies:

- what constitutes a member neighborhood
- whether the reference is nearest member price or nearest member distance
- whether a single member acts as a local center
- whether coverage is symmetric or directional
- how a later swing is judged against multiple nearby members

#### 9.2 Why this candidate is not frozen

Nearest-member coverage implicitly requires a member-reference geometry that the repo has not frozen.

This is not just a formula detail; it is a state definition problem.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

#### 9.3 Conclusion

Nearest-member geometry cannot be defined from the frozen rules alone. It remains an unapproved research concept.

## 10. Candidate D — direct member-derived interval without additional expansion

The Zone is bounded directly by member prices.

#### 10.1 What the repository supports

This is compatible with the concept of a member set and the existence of member prices.

It is, however, not compatible with the frozen tolerance contract unless the tolerance is explicitly used as the direct boundary or as a secondary consistency rule.

If the Zone is bounded only by the member prices themselves, then the tolerance rule is effectively unused in the geometry itself.

#### 10.2 Why this is a problem

The project has explicitly frozen a causal tolerance derived from prior same-direction gaps. If the Zone geometry is only the direct min/max of current members, then:

- tolerance is not part of the Zone extent
- member-set geometry is no longer tied to the tolerance rule
- the repo is silently redefining the meaning of the approved tolerance

This is not evidence-supported under the current Phase 1 contract.

Classification: UNRESOLVED

#### 10.3 Conclusion

Direct member-envelope geometry is conceptually meaningful as a set description, but it is not compatible with the repo’s current tolerance semantics unless a stronger rule is later approved.

## 11. Sequential causal analysis

The minimum research-only state that could be constructed from the current evidence is:

- direction
- seed/member observations
- member prices
- current median center
- current causal tolerance
- candidate geometry

### 11.1 What the repo can support

A minimal causal history can be constructed in canonical order using:

- same-direction eligible swings
- valid Zone candidate/seed semantics as proposal only
- median center from current member prices
- tolerance from prior legal same-direction gap history

This yields a deterministic historical state without implementing a production Zone engine.

Classification: REPOSITORY FACT / PROPOSAL ONLY

### 11.2 What the repo cannot support without assumptions

The repo cannot support a final geometry test without first freezing:

- Zone member-set semantics
- exact Zone state object
- exact update semantics for members
- exact interpretation of which swings belong to a Zone
- whether geometry is fixed or recomputed
- how multiple candidate geometries are compared in sequential time

If those are missing, all geometry candidates are only descriptive comparisons, not operationally valid Zone rules.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 12. Actual-data comparison of geometry candidates

### 12.1 Candidate testability today

The following are testable in a research-only, non-production sense:

- center ± tolerance as a mathematical comparison object
- direct member-bound interval as a descriptive shape
- nearest-member neighborhood as a descriptive measure on an already-defined member set

The following are not testable as final rules today:

- member-envelope expansion because the expansion formula is not frozen
- nearest-member coverage because no member-reference semantics are frozen
- dynamic geometry because lifecycle and update semantics are unresolved

### 12.2 Material differences on actual data

The repo’s existing descriptive analyses show that different geometric interpretations can produce materially different membership or cluster outcomes when applied to the same historical stream.

However, those differences are not proof of a final Zone geometry. They are evidence that geometry matters to the observed shape, not that one geometry is the correct final Zone contract.

Classification: EXPERIMENTAL EVIDENCE

### 12.3 Concrete disagreement examples

The existing geometry and membership research already identifies the core issue: a single center and tolerance can be used to generate a symmetric interval, but a member-based or nearest-member-based geometry yields a different set of covered observations once the member list and membership state are defined.

The repo does not yet freeze the member list, geometry, or update semantics needed to give those differences an authoritative operational meaning.

Classification: EXPERIMENTAL EVIDENCE / BLOCKED BY UNRESOLVED ROOT DECISION

## 13. Required conclusions

### 1. Is center ± tolerance supported by evidence or only a proposal?

Answer: only a proposal.

Classification: PROPOSAL ONLY

### 2. Can member-envelope geometry be defined without inventing a new parameter?

Answer: not from the current repo evidence.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 3. Can nearest-member geometry be defined from the frozen rules?

Answer: no.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 4. Is direct member-envelope geometry meaningful despite the tolerance rule?

Answer: only as a conceptual description, not as a frozen Zone rule.

Classification: UNRESOLVED

### 5. Which geometry candidates are actually testable today?

Answer: only descriptive, research-only comparisons; not a final Zone geometry contract.

Classification: EXPERIMENTAL EVIDENCE

### 6. Which candidates produce materially different behavior on the actual data?

Answer: the descriptive analyses show that geometry matters materially, but the repo does not yet define which geometry is the formal Zone geometry.

Classification: EXPERIMENTAL EVIDENCE

### 7. Does geometry require member-set semantics to be frozen first?

Answer: yes.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 8. Does geometry require multiple-zone/overlap semantics?

Answer: only if multiple-zone coexistence is allowed. The repository has not frozen that rule.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 9. What is the smallest remaining ROOT decision blocking a geometry freeze?

Answer: the minimum missing root decision is:

> Define the exact Zone object, its member-set state, and the exact causal update semantics that determine which observations are inside the Zone geometry.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 10. If one geometry is clearly the simplest defensible approach, identify it only as:

PROPOSAL ONLY — NOT FROZEN

The simplest defensible approach under the current evidence is:

- define the Zone by a symmetric center-based interval using the frozen center and the frozen causal tolerance
- keep this interpretation as a convenience for evaluating membership only
- do not treat it as the final Zone geometry contract until member-set, creation, and update semantics are frozen

This is a proposal only.

## 14. Evidence classification summary

- FROZEN: swing definition; 15-minute UTC bar contract; same-direction stream separation; W=5; minimum tolerance history=1; tolerance median rule; current swing excluded from its own history; center = median(member prices)
- REPOSITORY FACT: canonical historical stream exists; there are 78 eligible HIGH swings and 68 eligible LOW swings; the repo does not implement a runtime Zone geometry engine
- EXPERIMENTAL EVIDENCE: geometry choice changes descriptive results materially; the same data can be viewed differently under different geometric interpretations
- PROPOSAL ONLY: center ± tolerance as a Zone geometry interpretation; append-only Zone candidate semantics; the simplest symmetric interval proposal
- UNRESOLVED: direct member-derived interval without additional expansion; what exactly counts as the Zone boundary under a member set
- BLOCKED BY UNRESOLVED ROOT DECISION: member-envelope expansion; nearest-member coverage; any final geometry freeze without member-set and update-state definitions

## 15. Governance verification

### 15.1 Production code unchanged

No production code files were modified in this audit.

### 15.2 Production tests unchanged

No production tests were modified in this audit.

### 15.3 Canonical data unchanged

No canonical data files were modified in this audit.

### 15.4 Frozen decisions unchanged

The frozen decisions were preserved exactly as stated in the project record.

### 15.5 Group B remains not frozen

This audit does not freeze any Group B decision.

### 15.6 Phase 2 remains not started

This audit does not start Phase 2.

### 15.7 Exact verification commands

```powershell
.\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"
```

```powershell
git diff --check; Write-Host '---'; git status --short --untracked-files=all
```

### 15.8 Evidence counts and result

Observed output from the canonical pipeline:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

Observed repository integrity result:

- git diff --check produced no errors
- the workspace contains unrelated existing modifications, but this audit did not modify production code, tests, or canonical data

## Final conclusion

The repository does not yet support a final Zone geometry freeze.

The current evidence supports a minimal, research-only interpretation of Zone extent as a symmetric center-based interval using the frozen center and the frozen tolerance, but that is only a proposal and not a repository-approved geometry contract.

The repository does not currently justify any stronger claim, because the geometry definition still depends on earlier unresolved decisions about the Zone object, its member set, and its update semantics.

The correct final status is therefore:

PROPOSAL ONLY — NOT FROZEN

and the smallest remaining root blocker is still the same:

> the Zone object, member-set semantics, and causal update semantics must be defined before a geometry freeze can be justified.
