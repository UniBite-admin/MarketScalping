# Group B Member-Set Update Semantics Audit

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

This audit addresses the root decision immediately downstream of a hypothetical membership outcome:

> After an incoming observation has already been treated as a member, what should happen to the existing Zone member set?

This is intentionally narrower than the membership question itself.

The membership question remains unresolved, and this document does not decide it. This audit begins only after the following assumption is made:

- an incoming same-direction observation has already been classified as a member of an existing Zone candidate

The question is then strictly:

> What update behavior is evidence-supported for the resulting member set?

## 2. Frozen decisions preserved exactly

### 2.1 Group A swing definition

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
- event at bar_end belongs to the next bar
- closed bars are immutable
- trailing/incomplete bars excluded
- final partial bar at dataset end is discarded

### 2.3 Tolerance-history contract

FROZEN

- HIGH and LOW streams remain separate
- W = 5
- minimum tolerance history = 1
- tolerance = median of selected legal prior same-direction gaps
- current swing excluded from its own tolerance history
- 0 prior legal same-direction gaps => no tolerance available
- 1–4 prior legal gaps => use all available prior legal gaps
- 5+ prior legal gaps => use the five most recent

### 2.4 Center statistic

FROZEN

- center = median(member prices)

## 3. Proposal-only decisions kept as proposal only

The following remain proposal only and are not frozen:

- first eligible same-direction swing → candidate/seed
- second qualifying same-direction observation → valid Zone
- minimal Zone state contains direction, candidate/valid state, and member observations
- append-only member set

These are treated as:

PROPOSAL ONLY — NOT FROZEN

## 4. Unresolved root decisions preserved

The following remain unresolved and remain outside any freeze:

- exact membership rule
- exact member-set update semantics
- exact geometry
- multiple-zone behavior
- overlap/merge behavior
- lifecycle semantics
- stable identity

## 5. Evidence reviewed

The following evidence was reviewed before completing the audit:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMAL_ZONE_STATE_CONTRACT_AUDIT.md](GROUP_B_MINIMAL_ZONE_STATE_CONTRACT_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_SEMANTICS_AUDIT.md](GROUP_B_ZONE_GEOMETRY_SEMANTICS_AUDIT.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

## 6. Repository facts

### 6.1 REPOSITORY FACT

The canonical research pipeline reconstructs the 15-minute stream and identifies eligible same-direction swings in chronological order. It does not implement a production Zone state machine or a persistent Zone member-set update engine.

Evidence:

- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### 6.2 REPOSITORY FACT

The project has already verified the current canonical counts:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

Command used:

```powershell
.\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"
```

### 6.3 REPOSITORY FACT

The repo distinguishes:

- candidate/seed existence
- valid Zone existence
- historical member observations
- tolerance derivation from prior legal same-direction gaps
- center calculation from member prices

It does not freeze the member-set update law itself.

## 7. Critical distinction

This audit must not decide:

- whether an observation belongs to a Zone
- Zone geometry
- Zone overlap
- multiple Zone selection
- merge behavior
- invalidation
- expiry
- touch/reaction behavior

It only answers:

> After membership has already been established, how may the Zone member set evolve?

## 8. Model A — append-only

Definition:

members_new = members_old + observation

### 8.1 Evidence assessment

This model is the cleanest causal interpretation consistent with the repo-wide pattern of historical append-only state and canonical replay ordering.

The previous audits explicitly state that a minimal Zone state should keep historical member records in canonical order and that append-only historical state is the governing invariant.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBER_SET_SEMANTICS_AUDIT.md](GROUP_B_MEMBER_SET_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMAL_ZONE_STATE_CONTRACT_AUDIT.md](GROUP_B_MINIMAL_ZONE_STATE_CONTRACT_AUDIT.md)

### 8.2 Why it is attractive

- deterministic
- replay-safe
- preserves prior history
- avoids reclassification of earlier members
- matches the repository’s append-only historical design language

### 8.3 Why it is not yet frozen

The repo does not freeze append-only member-set evolution as the final architecture. It remains a proposal-only minimal model.

Classification: PROPOSAL ONLY

### 8.4 Conclusion

Append-only update semantics are the simplest defensible model supported by the repo’s historical-state pattern, but not yet a frozen rule.

## 9. Model B — replace/recompute

Definition:

The member set is recalculated after each new observation.

### 9.1 Evidence assessment

This model is not supportable by current repository evidence because the repo does not define:

- a valid member-set reference rule
- a valid geometry rule
- a valid update rule for recomputation
- a valid replacement or re-anchoring semantics
- a deterministic tie-break for recalculated membership

The repo has frozen tolerance and center, but it has not frozen a rule that says the Zone member set should be recomputed from a new center or a new interval after each observation.

### 9.2 Why it is blocked

Recomputation requires a reference definition, and the repository evidence does not supply one.

The earlier geometry and state audits explicitly identify the missing dependency:

- member-set semantics
- Zone geometry
- center update timing
- membership criterion
- historical mutation semantics

Without those, recalculation invents an unsupported state transition.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 9.3 Conclusion

Replace/recompute is not evidence-supported today.

## 10. Model C — fixed creation set

Definition:

The members that establish the Zone remain the permanent member set. Later qualifying observations do not become members.

### 10.1 Evidence assessment

This is not supported by current repo evidence.

The repo does not define a rule that the initial founder set is permanent and closed, and it does not define any evidence-based reason why later observations should not become members. This would silently import lifecycle semantics and a closed-set concept not present in the Phase 1 rules.

### 10.2 Why it is not justified

A fixed-creation set is effectively a lifecycle rule disguised as state update semantics. The repo explicitly does not support those lifecycle decisions in Phase 1.

Classification: UNRESOLVED

### 10.3 Conclusion

Fixed creation membership is not supported by the repository evidence.

## 11. Model D — add/remove dynamically

Definition:

Members can be added and/or removed over time.

### 11.1 Evidence assessment

This model requires:

- removal semantics
- invalidation semantics
- replacement semantics
- lifecycle semantics
- likely a geometry or overlap rule

The Phase 1 repo evidence does not establish any of these. There is no authoritative requirement that a member must leave the Zone after a later observation arrives.

### 11.2 Why it is blocked

Removal is not justified anywhere in the current evidence. It would require more than a member-set update rule; it would require lifecycle behavior and likely geometry / overlap semantics as well.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 11.3 Conclusion

Dynamic add/remove is not supported by the current Phase 1 evidence.

## 12. Mathematical/state question: center and tolerance constraints

### 12.1 Center = median(member prices)

This is frozen as the center statistic.

The critical point is:

- the center is a function of the current member set
- changing the member set will generally change the center if the new member is not identical to the existing median
- but this does not force a specific update policy for member-set evolution

Therefore:

- frozen center does not imply append-only semantics
- frozen center does not imply recomputation semantics
- frozen center does not imply a fixed creation set
- frozen center does not imply removal behavior

It is a dependent value, not an update law.

Classification: FROZEN / DERIVED VALUE

### 12.2 Tolerance = median(selected prior legal gap history)

This is frozen as a historical derived value from prior same-direction observations.

The tolerance rule does not define member-set update semantics.

The repo evidence does not support any statement that:

- tolerance must be recomputed when the member set changes
- tolerance must be recomputed when an observation is appended
- tolerance must be recomputed at all inside the Zone object

This is a separate historical stream from the Zone member state.

Classification: FROZEN / DERIVED VALUE

### 12.3 Conclusion

The member-set update law is not forced by either the frozen center or the frozen tolerance rule.

That is important. The repo evidence supports the center and tolerance as separate, derived values, but it does not define their causal dependency on the Zone member-set update law.

## 13. Sequential thought experiment

Consider the minimal abstract sequence:

1. seed S1
2. qualifying observation S2
3. Zone becomes valid
4. qualifying member S3
5. qualifying member S4

This can be represented abstractly without choosing a membership rule as:

- members(S1, S2)
- after S3: members(S1, S2, S3)
- after S4: members(S1, S2, S3, S4)

The same symbolic form works under append-only semantics.

Under fixed-creation semantics, the form would instead become:

- members(S1, S2)
- after S3: members(S1, S2)
- after S4: members(S1, S2)

Under recompute semantics, the form would become:

- members(S1, S2)
- after S3: recompute_members(...)
- after S4: recompute_members(...)

The key point is that the repo evidence does not define which of these is the actual Zone-state law.

This is not a hidden implementation detail. It is the missing root rule.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 14. Actual-data evidence

The actual historical data proves the existence of a same-direction canonical stream and its counts:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

These counts are real and deterministic. They do not, however, distinguish the update models because the missing rule is not the count of historical swings; it is the rule that determines what happens to the Zone member set after a hypothetical member is admitted.

### 14.1 What the data can show

The data can show that:

- append-only and fixed-creation semantics would diverge if later same-direction swings are admitted after creation
- append-only and recompute semantics would diverge once a new member changes the center or the underlying set
- add/remove semantics would diverge only if there were a defined removal rule, which does not exist

### 14.2 What the data cannot show

The data cannot distinguish the models without first defining:

- the membership rule itself
- the geometry rule
- the Zone object state law
- the update timing

So the current data is insufficient to freeze member-set update semantics.

Classification: EXPERIMENTAL EVIDENCE / BLOCKED BY UNRESOLVED ROOT DECISION

## 15. Bounded exploratory simulation under a single-active-seed analysis model

This section is intentionally limited to a bounded exploratory analysis model. It is not a full sequential Zone-state specification, not project behavior, and not a frozen decision.

### 15.1 Why this model is explicitly bounded

The project does not yet have a frozen specification for:

- Zone creation semantics beyond the approved seed/candidate + second-member creation rule
- multiple simultaneous Zones
- Zone identity
- overlap handling
- join/merge behavior
- lifecycle/state transitions
- member-set update semantics

Because those items remain unresolved, the simulation below uses a single-active-seed analysis model only. It is an analysis convenience for inspecting the post-creation effect of a member admission under the currently frozen rules, not a claim that the repository has defined a complete Zone-state system.

### 15.2 Exact analysis model used

The model respected the frozen rules already documented in the repo:

- 15-minute UTC closed bars
- HIGH and LOW remain separate
- W = 5
- minimum history = 1
- causal prior same-direction gap history
- current swing excluded from its own tolerance history
- center = median(member prices)
- membership = abs(incoming_price - current_zone_center) <= current_tolerance
- first eligible same-direction swing = seed/candidate
- second qualifying same-direction swing = valid Zone

Within this single-active-seed model, the following bounded post-creation comparisons were performed for each later eligible same-direction observation:

- Candidate A — append-only: admit the observation, append it to the retained member set, recompute the median center
- Candidate B — fixed creation membership: treat the observation as a qualifying member under the frozen geometry, but do not modify the Zone member set or center

This is a bounded exploratory simulation under an explicitly chosen single-active-seed analysis model.

### 15.3 Measured observations within that bounded model

The exact results from the canonical dataset were:

HIGH
- eligible swings: 78
- bounded valid Zone count: 1
- post-creation observations: 75
- post-creation qualifying observations: 2
- actual append events: 2
- center-changed cases: 2
- downstream A-vs-B membership divergence: 0

LOW
- eligible swings: 68
- bounded valid Zone count: 1
- post-creation observations: 65
- post-creation qualifying observations: 1
- actual append events: 1
- center-changed cases: 1
- downstream A-vs-B membership divergence: 0

### 15.4 Correct interpretation of the measured results

Within this bounded exploratory model, no downstream A-vs-B membership divergence was observed.

This does not establish:

- that Candidate A and Candidate B are equivalent under a complete sequential Zone-state model
- that append-only membership is correct
- that fixed-creation membership is correct
- that member-set update semantics are frozen
- that membership semantics are frozen
- that a complete Zone lifecycle has been validated

It only establishes that, in this explicitly bounded single-active-seed analysis model, no downstream membership divergence was observed in the measured canonical suffixes.

### 15.5 Evidence vs interpretation

Evidence:

- the repo contains frozen Group A swing definitions
- the repo contains a frozen 15-minute bar contract
- the repo contains frozen tolerance-history and center rules
- the repo contains a frozen membership rule for a valid Zone under the current narrow semantics
- the canonical dataset yields the measured observations above

Interpretation:

- the observed zero-divergence result is valid only within the bounded exploratory model
- it does not justify a freeze of member-set update semantics
- it does not justify a freeze of broader membership semantics
- it does not justify a Zone lifecycle specification or a full sequential Zone-state contract

## 16. Explicit frozen vs unresolved decision boundary

### Established / frozen

- Group A swing definitions
- 15-minute UTC bar contract
- W = 5
- minimum history = 1
- tolerance = median of selected legal prior same-direction absolute gaps
- HIGH and LOW remain separate
- current swing excluded from its own tolerance history
- Zone center = median(member prices)

### Not frozen

- membership reference / distance semantics beyond the narrow approved rule
- Zone creation / seed semantics beyond the approved creation rule
- member-set update semantics
- Zone identity
- multiple simultaneous Zones
- overlap handling
- join / merge behavior
- Zone geometry / width
- Zone lifecycle / state transitions

Group B remains NOT FROZEN.

Phase 2 remains NOT STARTED.

## 17. Required conclusions

### 1. Does the bounded exploratory simulation justify a freeze recommendation?

Answer: No.

The analysis is valid only as a bounded exploratory simulation under an explicitly chosen single-active-seed model. It does not establish a complete Zone-state law and does not justify freezing either membership or member-set update semantics.

### 2. Does the analysis establish append-only correctness?

Answer: No.

It does not establish append-only correctness as project behavior. It only shows that, within the bounded model, no downstream membership divergence was observed in the measured suffixes.

### 3. Does the analysis establish equivalence between Candidate A and Candidate B?

Answer: No.

It shows zero observed divergence within the bounded exploratory model only. This is not the same as proving equivalence under a complete sequential Zone-state model.

### 4. What does the analysis establish?

Answer: It establishes that, in the bounded single-active-seed model, center changes from append-only admission did not cause a downstream membership decision difference in the observed canonical suffixes.

### 5. What does it not establish?

Answer: It does not establish a complete Zone lifecycle, a complete Zone-state contract, or a valid frozen member-set update rule.

## 18. Final status

RESEARCH ONLY — NOT FROZEN

The bounded exploratory simulation under a single-active-seed analysis model is valid as a measurement exercise only. It is not evidence sufficient to freeze Zone membership semantics, member-set update semantics, or any broader Zone-state contract.

## 19. Verification

### 19.1 Production code unchanged

No production code was modified.

### 19.2 Executable tests unchanged

No executable tests were modified.

### 19.3 Data unchanged

No dataset was modified.

### 19.4 Frozen decisions unchanged

The existing frozen decisions were preserved.

### 19.5 Group B remains not frozen

Confirmed.

### 19.6 Phase 2 remains not started

Confirmed.

### 19.7 Exact verification commands

```powershell
git diff --check
git status --short --untracked-files=all
```

### 19.8 Observed repository integrity result

The repository is clean with respect to the intended audit cleanup:

- no production code changed
- no executable tests changed
- no dataset changed
- no frozen governance decision changed
- Group B remains NOT FROZEN
- Phase 2 remains NOT STARTED
- temporary diagnostic script was removed

## Final conclusion

This cleanup preserves the measured observational results while correcting the interpretation to a clearly bounded exploratory analysis under a single-active-seed model only. The audit does not freeze any Zone-state behavior, and the repository remains in the correct research-only state.
