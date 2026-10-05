# Group B Minimal Zone Object / State Contract Audit

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

This audit addresses the root decision that the geometry audit identified as the current blocker:

> the exact Zone object + member-set + update semantics

The objective is not to design the final trading Zone engine.

The objective is to determine the smallest Zone state contract that can represent the Phase 1 concepts already discussed without silently importing lifecycle, overlap, merge, phase-2, or implementation-specific behavior.

The focus is strictly on a minimal representation for:

1. candidate/seed existence
2. Zone creation
3. member observations
4. median center
5. causal tolerance
6. membership evaluation
7. deterministic replay

This audit is intentionally narrow. It does not freeze a final Zone engine.

## 2. Evidence hierarchy used

The following repository evidence was used as the governing source for this audit:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md](GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_CREATION_FIRST_MEMBER_DECISION_AUDIT_V2.md](GROUP_B_ZONE_CREATION_FIRST_MEMBER_DECISION_AUDIT_V2.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_SEMANTICS_AUDIT.md](GROUP_B_ZONE_GEOMETRY_SEMANTICS_AUDIT.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

The repo evidence is descriptive, not production-grade state logic. The current objective is therefore state-boundary analysis, not implementation.

## 3. Frozen decisions preserved exactly

The following remain authoritative and are not reinterpreted in this document:

### 3.1 Phase 1 Group A swing definition

FROZEN

- Swing High: High[i] > High[i - 1] and High[i] > High[i + 1]
- Swing Low: Low[i] < Low[i - 1] and Low[i] < Low[i + 1]
- strict comparisons only
- complete required neighborhood
- confirmation before downstream eligibility
- no lookahead

### 3.2 15-minute UTC bar contract

FROZEN

- 15-minute UTC bucket
- interval: [bar_start, bar_end)
- event at bar_end belongs to next bar
- closed bars are immutable
- trailing/incomplete bars excluded
- final partial bar at dataset end is discarded

### 3.3 Same-direction/tolerance contract

FROZEN

- HIGH and LOW streams remain separate
- W = 5
- minimum tolerance history = 1
- tolerance = median of selected legal prior same-direction gaps
- current swing excluded from its own tolerance history
- 0 prior legal gaps => no tolerance available
- 1–4 prior legal gaps => use all available prior legal gaps
- 5+ prior legal gaps => use the five most recent

### 3.4 Center statistic

FROZEN

- center = median(member prices)

## 4. Existing proposals explicitly preserved as PROPOSAL ONLY

The following remain proposals, not frozen decisions:

- first eligible same-direction swing → candidate/seed
- second qualifying same-direction observation → valid Zone
- append-only member set after Zone creation

These are treated as:

PROPOSAL ONLY — NOT FROZEN

## 5. What the repo actually supports

### 5.1 REPOSITORY FACT

The repository supports a canonical, replayable sequence of eligible same-direction swings in time order, but it does not contain an authoritative runtime Zone state machine or final Zone object schema.

This is explicitly reflected in the earlier Group B research and zone-state docs.

### 5.2 REPOSITORY FACT

The repo can represent a historical sequence of eligible swings and a tolerance history derived from legal prior same-direction gaps. It does not yet define the exact operational Zone object for those swings.

### 5.3 REPOSITORY FACT

The repo distinguishes conceptually between:

- swing candidate
- candidate/seed
- valid Zone
- member observation
- membership decision

This distinction is evidence-supported, but the exact state encoding is not frozen.

## 6. State categories to investigate

### Category 1 — Direction

#### Classification

REQUIRED STATE

#### Why

The frozen architecture explicitly separates HIGH and LOW streams. A Zone must therefore preserve direction as a state variable or otherwise be impossible to meaningfully represent in same-direction logic.

#### Minimality test

If direction is removed, the same-direction tolerance and membership rule cannot be represented without ambiguity.

#### Conclusion

Direction is required for the current Phase 1 contract.

---

### Category 2 — Candidate / seed state

#### Classification

REQUIRED STATE (for minimal causal representation)

#### Why

The evidence supports distinguishing:

- no candidate
- candidate/seed exists
- valid Zone exists

This is expressly called out in the zone-creation and first-member audits.

#### Minimality test

If candidate/seed status is removed, the process cannot distinguish an initial eligible observation from a valid Zone. That collapses the creation boundary and destroys the causal distinction already identified in the research.

#### Conclusion

A minimal state contract must include at least a state enum or equivalent state flag for candidate vs valid Zone.

---

### Category 3 — Member observations

#### Classification

REQUIRED STATE

#### Why

The center statistic is defined as median(member prices), which implies an actual member set. A Zone cannot be meaningfully represented without storing or referencing the member observations that define that set.

The minimal evidence-supported member record should logically include:

- deterministic observation identity or reference
- price
- direction
- eligibility/confirmation timestamp or equivalent canonical ordering reference

The repo evidence does not justify adding arbitrary fields beyond this minimum set.

#### Minimality test

If price is removed, median(member prices) cannot be computed. If observational identity is removed, replay determinism becomes ambiguous. If direction is removed, same-direction membership semantics collapse.

#### Conclusion

Member observations are required state. The exact shape should stay minimal and deterministic.

---

### Category 4 — Center

#### Classification

DERIVED VALUE

#### Why

The repository froze the center statistic as median(member prices), but did not freeze whether the center must be stored as authoritative state at runtime. It may be computed from current member prices whenever needed.

The value is therefore best treated as a derived value rather than a separate authoritative state variable unless an implementation chooses to cache it for convenience.

#### Minimality test

If center is removed from stored state but member prices remain available, the median can still be derived and reconstructed deterministically. Therefore center is not proven as required stored state.

#### Conclusion

Center should be treated as a derived value from member prices, not as a free-standing required Zone state field.

---

### Category 5 — Tolerance

#### Classification

DERIVED VALUE

#### Why

The tolerance formula is frozen as a median of prior legal same-direction gaps. That value is derived from the historical same-direction sequence, not from the Zone object itself.

The repo evidence explicitly separates:

- historical tolerance computation
- Zone member semantics
- Zone geometry

It does not support placing tolerance into the Zone object as a required internal state field without additional rules.

#### Minimality test

If tolerance is removed from Zone state but the historical sequence remains available, the current tolerance rule can still be computed. Therefore tolerance is not a required Zone-state field.

#### Conclusion

Tolerance remains a derived historical value, not primary Zone state.

---

### Category 6 — Geometry

#### Classification

UNRESOLVED

#### Why

The repo evidence never successfully defines a final Zone geometry. It does not freeze:

- center ± tolerance as geometry
- member-envelope geometry
- nearest-member coverage
- direct member-bound interval without expansion

The geometry audits explicitly say the repo does not support a final geometry rule yet.

#### Minimality test

Removing geometry does not break the existence of candidate/seed and valid Zone state, because those concepts are supported by the repo evidence before geometry is frozen.

#### Conclusion

Geometry is not part of the minimal Zone state contract yet. It remains unresolved.

---

### Category 7 — Identity

#### Classification

OPTIONAL / UNRESOLVED

#### Why

The repo does not freeze a deterministic Zone identity scheme. There is no evidence that a UUID, creation event, first member, or sequence number is authoritative.

A minimal contract could represent a Zone by a local in-memory reference or by a derived creation-order index, but that is an implementation detail and not a frozen repo rule.

#### Minimality test

If identity is removed, a minimal state representation can still represent the sequence of events and the current Zone status as a local object in a replay implementation. However, that does not mean identity is unnecessary in a production engine; it means it is not yet frozen by repo evidence.

#### Conclusion

Identity is not yet an evidence-supported required field. It remains optional and unresolved.

---

### Category 8 — Timestamps

#### Classification

REQUIRED ONLY FOR MEMBER OBSERVATIONS; OPTIONAL FOR ZONE STATE

#### Why

The repo evidence supports the existence of determination points like:

- observation time
- confirmation time
- eligibility time
- creation time

But it does not justify a full timestamp schema for a Zone object until Zone creation semantics are frozen.

At the minimum, member observations need an ordering or eligibility reference so that the replay and tolerance logic remain deterministic.

#### Minimality test

If timestamps are removed from individual members, replay determinism and canonical ordering become ambiguous. If creation time is removed from the Zone object, the minimal causal state still exists for research purposes as long as ordering is reconstructable.

#### Conclusion

Timestamps are required as canonical ordering metadata for member observations, but they should not be over-specified as a full Zone contract until the root semantics are frozen.

---

### Category 9 — Lifecycle state

#### Classification

REQUIRED ONLY FOR MINIMAL BOUNDARY: candidate vs valid Zone

#### Why

The repo evidence supports at least two meaningful Phase 1 states:

- no candidate
- candidate/seed exists
- valid Zone exists

It does not support importing one of the following into the minimal contract without evidence:

- active/inactive
- expired
- invalidated
- merged
- retired
- touched
- reacted

Those belong to later lifecycle design and would be a silent import of unresolved behavior.

#### Minimality test

If lifecycle states beyond candidate/valid Zone are removed, the minimal causal flow remains representable and consistent with the current evidence. If those states are added prematurely, the model invents behavior not supported by the repo.

#### Conclusion

Minimal lifecycle state should be limited to candidate vs valid Zone; anything more is not supportable at this phase.

---

### Category 10 — Multiple zones

#### Classification

OPTIONAL / INTENTIONALLY OUT OF SCOPE FOR MINIMAL CONTRACT

#### Why

The repo does not support a final multiple-zone or overlap rule. The minimal Zone state contract should therefore remain intentionally single-zone for research purposes unless a later root decision explicitly requires multiple Zone objects.

#### Minimality test

A single-zone representation remains sufficient to express the current frozen and proposed behavior. It does not require multiple-zone semantics in order to represent candidate/seed or valid Zone.

#### Conclusion

Multiple zones are a blocking dependency, not part of the minimal current contract.

## 7. Minimal state proposal

### 7.1 Proposed minimal representation

PROPOSAL ONLY — NOT FROZEN

The most defensible minimal Zone state boundary supported by the current evidence is:

- direction
- state: { no_candidate, candidate_seed, valid_zone }
- member observations list
  - deterministic observation reference
  - price
  - direction
  - eligibility / canonical ordering reference
- creation reference (only if needed to anchor the candidate/valid-zone transition)

This is intentionally small. It is enough to represent:

- no candidate
- candidate/seed existence
- valid Zone existence
- member list
- canonical replay ordering
- median center as a derived value from member prices
- tolerance as a derived value from the historical causal gap stream

### 7.2 What should not be stored as authoritative state

The following should be treated as derived values, not stored Zone-authoritative state:

- center = median(member prices)
- tolerance = median(selected prior same-direction gaps)
- geometry (since unresolved)
- lifecycle status beyond candidate/valid Zone
- multiple-zone association or overlap resolution

### 7.3 What remains unresolved

The following remain unresolved and must not be silently assumed into the minimal contract:

- exact Zone geometry
- exact member-set update rule
- exact membership criterion
- exact candidate-to-zone distance rule
- multiple-zone semantics
- overlap/merge semantics
- stable zone identity semantics
- exact creation trigger beyond a proposal-only candidate/seed boundary

## 8. Sequential reconstruction test

The minimal proposed model can theoretically represent the causal path below in a research-only sense:

1. no candidate
2. first eligible swing
3. candidate/seed
4. second qualifying same-direction swing
5. valid Zone
6. subsequent eligible swing
7. membership decision
8. member-set update
9. updated center
10. updated derived tolerance

This is supportable only if the following are kept semantically separate:

- observation history
- candidate/seed state
- Zone state
- derived center
- derived tolerance
- unresolved membership and geometry logic

### 8.1 Where the model breaks

The minimal model cannot represent the final membership decision or geometry without an unresolved rule for:

- whether membership is center-based, nearest-member-based, envelope-based, or otherwise defined
- whether the member set is append-only or recomputed
- what Zone geometry means once the set exists
- whether a valid Zone can admit multiple simultaneous zones or overlap

If any of those are missing, the model remains a state container, not a final Zone contract.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 9. Required conclusions

### 1. What is the minimum state contract supported by evidence?

The minimum defensible state contract is a same-direction Zone with:

- direction
- candidate/seed vs valid Zone status
- member observation list
- canonical ordering metadata
- creation reference if needed for deterministic identity

Classification: PROPOSAL ONLY

### 2. Which fields are required vs derived?

Required state:

- direction
- candidate/seed status
- member observation list with deterministic ordering/reference

Derived values:

- center
- tolerance
- geometry

Classification: REQUIRED STATE / DERIVED VALUE

### 3. Can a minimal Zone contract now be drafted?

Only in a narrow, proposal-only way.

Classification: PROPOSAL ONLY

### 4. Does the current frozen evidence support a complete Zone contract?

No.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 5. What is the smallest next root decision after this audit?

The smallest next root decision is:

> Define the exact Zone membership rule and the exact member-set update semantics after a valid Zone exists.

This is the next unresolved root decision beyond the minimal Zone state contract.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 6. Does a minimal Zone object require geometry to be frozen first?

No, but a minimal Zone object cannot be used to freeze geometry. Geometry remains separate and unresolved.

Classification: REPOSITORY FACT

### 7. Does the minimal contract require multiple-zone semantics to be frozen?

No. The minimal state contract can intentionally remain single-zone for research and causal modeling.

Classification: REPOSITORY FACT

### 8. Is lifecycle beyond candidate/valid Zone currently supportable?

No.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 9. Is the minimal contract complete enough to implement a production Zone engine?

No.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 10. Governance classification summary

- FROZEN: Group A swing definition; 15-minute bar contract; same-direction separation; W=5; minimum tolerance history=1; tolerance median rule; center = median(member prices)
- REPOSITORY FACT: canonical historical reconstruction exists; eligible same-direction swings are real; the repo does not currently contain a final runtime Zone state machine
- EXPERIMENTAL EVIDENCE: descriptive historical measures of membership behavior under different geometries are informative but not final evidence of a required Zone contract
- PROPOSAL ONLY: minimal Zone state with direction + state + member list + ordering metadata; candidate/seed → valid Zone progression; append-only member-set model as a minimal research-only state boundary
- UNRESOLVED: exact geometry; exact membership rule; exact member-set update semantics; stable identity; multiple-zone semantics; lifecycle semantics
- BLOCKED BY UNRESOLVED ROOT DECISION: any final Zone contract freeze; any formal zone geometry freeze; any production Zone engine definition

## 11. Verification

### 11.1 Production code unchanged

No production code was modified in this audit.

### 11.2 Production tests unchanged

No production tests were modified in this audit.

### 11.3 Canonical data unchanged

No canonical data files were modified in this audit.

### 11.4 Frozen decisions unchanged

The frozen decisions remain unchanged and were preserved exactly.

### 11.5 Group B remains not frozen

This audit did not freeze Group B.

### 11.6 Phase 2 remains not started

This audit did not start Phase 2.

### 11.7 Exact verification commands

```powershell
.\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"
```

```powershell
git diff --check; Write-Host '---'; git status --short --untracked-files=all
```

### 11.8 Evidence counts and result

Observed output from the canonical pipeline:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

Observed repo integrity result:

- git diff --check produced no errors
- the workspace contains unrelated existing modifications, but this audit did not modify production code, production tests, or canonical data

## Final conclusion

The repository evidence supports a minimal Zone state boundary, but only in a research-only, proposal form.

The smallest defensible state contract is:

- same-direction Zone
- candidate/seed vs valid Zone distinction
- member observations list with deterministic ordering/reference
- creation reference if needed for auditability

All of the following remain outside the current evidence-supported contract and must not be silently frozen:

- exact geometry
- exact membership rule
- exact member-update semantics
- multiple-zone semantics
- overlap/merge semantics
- lifecycle semantics
- stable identity semantics

This means the current repo supports a minimal Zone state model for causal representation, but not a final Zone contract.

The correct final status is therefore:

PROPOSAL ONLY — NOT FROZEN

and the next unresolved root decision is:

> Define the exact Zone membership rule and member-set update semantics after a valid Zone exists.
