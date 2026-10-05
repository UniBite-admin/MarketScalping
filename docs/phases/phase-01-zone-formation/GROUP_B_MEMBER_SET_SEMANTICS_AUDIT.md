# Group B Member-Set Semantics Audit

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

> Once a candidate becomes a valid Zone, which observations belong to the Zone's member set, and how is that member set updated when subsequent eligible same-direction swings arrive?

The objective is to determine what the repository evidence actually supports, not to invent the cleanest implementation or silently convert a proposal into a rule.

This audit keeps the prior proposal explicit:

**PROPOSAL ONLY — NOT FROZEN**

- first eligible same-direction swing → candidate/seed
- next qualifying same-direction observation → valid Zone

This does not become a freeze.

## 2. Evidence reviewed

The following evidence was inspected before completing this audit:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md](GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_CREATION_FIRST_MEMBER_DECISION_AUDIT_V2.md](GROUP_B_ZONE_CREATION_FIRST_MEMBER_DECISION_AUDIT_V2.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

This audit also used the existing canonical reconstructed 15-minute data pipeline already present in the repository.

## 3. Frozen decisions preserved exactly

The following remain the authoritative frozen decisions for this audit:

### 3.1 Group A swing definition

FROZEN

- Swing High: High[i] > High[i - 1] and High[i] > High[i + 1]
- Swing Low: Low[i] < Low[i - 1] and Low[i] < Low[i + 1]
- strict comparisons only
- complete required neighborhood
- confirmation precedes downstream eligibility
- no lookahead

### 3.2 15-minute UTC bar contract

FROZEN

- 15-minute UTC bucket
- interval: [bar_start, bar_end)
- event at bar_end belongs to next bar
- closed bars are immutable
- trailing/incomplete bars excluded
- final partial bar at dataset end is discarded

### 3.3 Tolerance history contract

FROZEN

- HIGH and LOW remain separate
- only prior legal same-direction gaps may enter tolerance history
- current swing excluded from its own tolerance history
- W = 5
- minimum history = 1
- 0 prior legal same-direction gaps => no tolerance available
- 1–4 prior legal gaps => use all available prior legal gaps
- 5+ prior legal gaps => use the five most recent
- tolerance = median(selected prior legal same-direction gaps)

### 3.4 Zone center statistic

FROZEN

- center = median(member prices)

This does not freeze member-set semantics or the lifecycle of that center.

## 4. Repository facts

### 4.1 REPOSITORY FACT

The current research implementation reconstructs canonical 15-minute bars and identifies same-direction swing highs and swing lows in canonical order. It does not implement a true Zone member-set state machine, a stored zone ledger, or a live membership engine.

Evidence:

- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### 4.2 REPOSITORY FACT

The repository’s canonical research pipeline reproduces:

- reconstructed bars: 1146
- eligible HIGH swings: 78
- eligible LOW swings: 68

Verified command:

- .\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"

Observed output:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

### 4.3 REPOSITORY FACT

The repository evidence repeatedly distinguishes between:

- swing existence
- candidate/seed existence
- valid Zone existence
- tolerance availability
- membership of later swings

This distinction is not optional. It is a causal requirement derived from the earlier audits and the project’s no-assumptions rule.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_CREATION_FIRST_MEMBER_DECISION_AUDIT_V2.md](GROUP_B_ZONE_CREATION_FIRST_MEMBER_DECISION_AUDIT_V2.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)

### 4.4 REPOSITORY FACT

The repo does not contain an authoritative rule for member-set mutation, fixed creation membership, or dynamic zone membership updates.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md)

## 5. Candidate member-set semantics

### Candidate 1 — append-only membership

Definition:

- once a swing becomes a Zone member, it remains a member permanently
- new qualifying members are appended
- old members are never removed

#### 5.1 Evidence assessment

This is the smallest and most conservative evolution model consistent with deterministic replay and append-only historical state.

The repo provides evidence that historical state should remain append-only and ordered by canonical eligibility time, and the prior minimum viable spec explicitly calls for append-only history as the governing invariant.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)

#### 5.2 Why it is attractive

- it is causally simple
- it is deterministic
- it preserves historical replay integrity
- it avoids hidden “reclassification” of earlier swings
- it matches the repo’s overall patience with append-only state

#### 5.3 Why it is not yet a frozen rule

The repo does not freeze whether append-only membership is the final desired policy, and it does not define whether the Zone can later be redefined by a different center or geometry rule.

Classification: PROPOSAL ONLY

#### 5.4 Conclusion

Append-only membership is the cleanest candidate consistent with the repo evidence, but it remains a proposal until the wider zone state is frozen.

## 6. Candidate 2 — recomputed membership

Definition:

- the Zone's member set is recalculated whenever a new swing arrives

#### 6.1 What would be required?

This requires a reference definition that is not currently frozen, for example:

- a fixed interval reference
- a center-based reference
- a rolling member window
- a geometric reference set
- a re-anchoring rule for the Zone as new members arrive

The repo has not frozen any of these.

#### 6.2 Why this is blocked

The repo has frozen only the center statistic and the tolerance-history math. It has not frozen the following required elements:

- zone geometry
- interval definition
- member-set reference rule
- update timing for center or member-set recomputation
- re-anchoring semantics
- tie-break or replacement semantics

This means the membership set cannot be safely recomputed without inventing the reference state that would determine inclusion or exclusion.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

#### 6.3 Conclusion

Recomputed membership is not defensible as a current repo-supported rule because the reference and update semantics are unresolved.

## 7. Candidate 3 — fixed creation members

Definition:

- the members that establish the Zone remain the permanent member set
- later qualifying swings may influence other Zone properties, but do not become members

#### 7.1 Evidence assessment

This is a possible conceptual boundary, but the repo does not support it with evidence. There is no explicit freeze that says the original two-member founding set is immutable or that later swings may not join the Zone.

#### 7.2 Why it is not supported by repo evidence

The repo repeatedly says that a valid Zone and membership semantics are unresolved, and it explicitly excludes broader lifecycle behavior from current Phase 1 analysis. A fixed-creation-members rule would silently import a life-cycle-like decision before the repo has defined the Zone candidate state.

Classification: UNRESOLVED

#### 7.3 Conclusion

Fixed-creation membership is not supported by the repository as a current evidence-based rule.

## 8. Candidate 4 — dynamic membership

Definition:

- members can be added and/or removed as the Zone evolves

#### 8.1 Evidence assessment

The repo contains no evidence that removal or replacement is required at Phase 1. It does not define a removal rule, replacement rule, invalidation rule, or zone lifecycle. Those are later-phase concerns and must not be imported into Phase 1.

#### 8.2 Why this is blocked

Dynamic membership is a lifecycle question that crosses into the same unresolved territory as:

- invalidation
- expiry
- retirement
- overlap resolution
- merge behavior
- history mutation

Those are explicitly outside the current membership gate and outside this phase unless a roadmap change is approved.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

#### 8.3 Conclusion

Dynamic membership is not supportable by current repository evidence as a Phase 1 rule.

## 9. Critical distinction: membership vs center vs tolerance vs geometry vs lifecycle

This audit treats the following as distinct concepts and does not merge them:

1. Zone membership
2. Zone center
3. Zone tolerance
4. Zone geometry
5. Zone lifecycle

### 9.1 Membership is not implied by the center

The repo freezes the center statistic but does not freeze a rule that the center determines the member set automatically.

- The center can be median(member prices) once the member set exists.
- The member set is not defined by the center alone.

### 9.2 Membership is not implied by recomputed tolerance

The frozen tolerance history is a prior-gap-derived value. It does not automatically define the Zone member set. The same repo docs explicitly warn against equating tolerance availability with zone validity or membership creation.

### 9.3 Geometry is unresolved

The repo does not freeze the geometry that would determine whether a new swing belongs to a Zone by a distance metric, interval contract, or envelope rule.

### 9.4 Lifecycle is outside scope

The repo evidence repeatedly says that lifecycle, expiry, merge, overlap, and invalidation behavior are not Phase 1 questions unless explicitly reopened by roadmap governance.

Classification: REPOSITORY FACT

## 10. Causal sequential experiment boundary

A minimal causal sequential experiment is possible only if the following are already defined:

- eligible same-direction swings in chronological order
- candidate/seed state after first eligible swing
- valid Zone status after the creation baseline
- member set state for the Zone
- frozen causal tolerance history
- frozen median center
- incoming swing
- membership decision
- resulting member set update

### 10.1 What the repo supports

The repo supports the following causal boundary:

- canonical ordering
- same-direction sequences
- tolerance derived from prior legal same-direction gaps
- current swing excluded from its own tolerance history
- median center only after member set is known

### 10.2 What blocks a real experiment

The missing item is not parameter tuning; it is the state definition itself. The repo does not yet freeze:

- what a valid Zone object contains
- what the member set is once Zone validity begins
- whether the member set is append-only or recalculated
- whether the center is fixed or updated after each addition

Without this, the actual-data experiment can only be descriptive clustering, not a true sequential Zone member-set model.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 11. Actual-data analysis

### 11.1 Canonical data counts

Verified counts from the existing canonical pipeline:

- reconstructed bars: 1146
- eligible HIGH swings: 78
- eligible LOW swings: 68

These are factual historical counts and are valid for this analysis.

### 11.2 Potential Zone formations

The repo supports descriptive historical potential, but not an actual sequential Zone formation engine. There are therefore no frozen counts of valid Zone formations under a full member-set semantics contract.

Classification: REPOSITORY FACT / EXPERIMENTAL EVIDENCE

### 11.3 Member counts under candidate semantics

The repo does not provide a final member-set state definition, so the following cannot be measured as a final rule:

- fixed creation members count
- append-only member counts over time
- recomputed member-set counts
- dynamic member-set counts
- example disagreements between candidate semantics

These candidate semantics are conceptual alternatives only. The repo has not defined a candidate state machine to evaluate them sequentially.

Classification: UNRESOLVED

### 11.4 What can be said from the evidence

The only defensible data-level statement is:

- the same-direction stream is real and dense enough to support distinct historical sequences
- the descriptive clustering literature suggests that different geometric interpretations materially change how member-like behavior appears in the historical stream
- the repo does not yet provide a formal member-set state that makes those geometry differences operationally meaningful

Classification: EXPERIMENTAL EVIDENCE

## 12. Conclusion by question

### 1. Is append-only membership defensible?

Yes, as a proposal only.

Classification: PROPOSAL ONLY

### 2. Is recomputed membership defensible?

No, not under current repo evidence.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 3. Is fixed-creation membership defensible?

No evidence supports it.

Classification: UNRESOLVED

### 4. Is dynamic membership supported by any repository evidence?

No.

Classification: UNRESOLVED / BLOCKED BY UNRESOLVED ROOT DECISION

### 5. Which candidates are actually distinguishable with the current evidence?

Only the abstract conceptual options are distinguishable. The repo does not yet define a sequential Zone state that makes them operationally distinguishable.

Classification: EXPERIMENTAL EVIDENCE / UNRESOLVED

### 6. Does the proposed 2-member Zone creation baseline allow a causal member-set experiment?

Only in a limited research sense.

It allows a conceptual experiment by treating the first two same-direction observations as the initial member set, but only as a proposal. The repo still does not freeze the exact Zone object or member-update semantics.

Classification: PROPOSAL ONLY

### 7. Does membership still depend on an unresolved geometry definition?

Yes.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 8. Does membership still depend on unresolved multiple-Zone/overlap semantics?

Yes, if multiple Zone candidates are allowed. The repo has not frozen that rule.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 9. What is the smallest remaining ROOT decision blocking a membership freeze?

The smallest remaining root decision is:

> Define the exact Zone candidate state and the exact member-set update semantics once a valid Zone exists.

This includes deciding whether the member set is append-only, fixed, recomputed, or dynamic — but the repo evidence currently supports only append-only as a proposal, not as a freeze.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 10. If one candidate is clearly the simplest defensible approach, identify it only as PROPOSAL ONLY — NOT FROZEN

The simplest defensible approach currently supported by the repo evidence is:

**PROPOSAL ONLY — NOT FROZEN**

- first eligible same-direction swing → candidate/seed
- second qualifying same-direction observation → valid Zone
- once valid, member set is append-only
- later members are appended in canonical same-direction order
- no membership removal is assumed at this phase

This is a proposal only. It is not a freeze.

## 13. Final classification summary

- FROZEN: Phase 1 swing definition, bar contract, tolerance-history contract, center statistic
- REPOSITORY FACT: canonical same-direction historical stream exists; research code is descriptive only; no runtime Zone-state engine exists
- EXPERIMENTAL EVIDENCE: descriptive clustering behavior differs by geometry, but does not prove a final member-set rule
- PROPOSAL ONLY: append-only member set after a valid Zone, as a minimal causal model; first eligible swing as a candidate/seed before valid Zone; valid Zone after second same-direction observation
- UNRESOLVED: fixed-creation membership, dynamic membership, zone geometry definition, zone lifecycle semantics
- BLOCKED BY UNRESOLVED ROOT DECISION: recomputed membership, multiple-zone / overlap semantics, member-set freeze gate

## 14. Governance verification

This audit was written as a documentation-only research task and did not modify:

- production code
- production tests
- canonical data
- frozen decisions

### Exact command used for data verification

- .\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"

Observed output:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

### Exact repo integrity check used

- git diff --check; Write-Host '---'; git status --short --untracked-files=all

Observed result:

- git diff --check produced no errors
- the workspace contains unrelated existing modifications, but this audit task did not modify production code, production tests, or canonical data

## Final conclusion

The repository evidence does not yet support freezing the member-set semantics. It does support a minimal proposal:

- valid Zone begins after the next qualifying same-direction observation
- member set is append-only in the first minimal model
- no dynamic removal or recomputation is evidence-supported at this phase

This is the simplest defensible causal approach, but it remains:

**PROPOSAL ONLY — NOT FROZEN**

The member-set semantics are still blocked by the unresolved Zone candidate state and geometry contract, and the repo evidence does not yet justify a formal freeze gate.
