# Group B Membership Sequential Semantics Audit

## Status

RESEARCH ONLY

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- No production code was modified.
- No production tests were modified.
- No canonical data was modified.
- No new frozen decision was created.
- This document is an audit only.

## 1. Objective

This audit addresses the unresolved Group B root decision:

> Membership Semantics — how an incoming eligible same-direction swing becomes a member of an existing Zone candidate.

The goal is not to invent a final rule. The goal is to determine whether the repository evidence is sufficient to evaluate membership in a minimal causal sequential model without inventing unresolved Zone lifecycle behavior.

This document distinguishes clearly among:

1. Repository fact
2. Frozen decision
3. Existing experimental evidence
4. Research proposal
5. Unresolved decision
6. Decision blocked by another unresolved root decision

## 2. Authoritative evidence inspected

The following sources were reviewed before writing this audit:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_TOLERANCE_ARCHITECTURE_COMPARISON.md](GROUP_B_TOLERANCE_ARCHITECTURE_COMPARISON.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_TOLERANCE_FORMULA_ANALYSIS.md](GROUP_B_TOLERANCE_FORMULA_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md](GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

The audit also checked the repository’s current research and replay expectations for canonical ordering, same-direction separation, and the causal tolerance-history contract.

## 3. Frozen decisions governing this audit

The following are already frozen and authoritative and must not be weakened or reinterpreted:

### 3.1 Group A swing definition

REPOSITORY FACT / FROZEN DECISION

- Swing High: High[i] > High[i - 1] and High[i] > High[i + 1]
- Swing Low: Low[i] < Low[i - 1] and Low[i] < Low[i + 1]
- strict comparisons only
- complete required neighborhood
- confirmation precedes downstream eligibility
- no lookahead
- deterministic canonical replay

### 3.2 15-minute bar contract

REPOSITORY FACT / FROZEN DECISION

- 15-minute UTC bucket
- interval: [bar_start, bar_end)
- event at bar_end belongs to next bar
- closed bars are immutable
- trailing/incomplete bars excluded from finalized evaluation
- final partial bar at dataset end is discarded

### 3.3 Tolerance-history contract

REPOSITORY FACT / FROZEN DECISION

- HIGH and LOW streams remain separate
- only prior legal same-direction gaps are eligible
- current swing excluded from its own tolerance history
- W = 5
- minimum history = 1
- 0 prior legal gaps => no tolerance available
- 1–4 prior legal gaps => use all available
- 5+ prior legal gaps => use the five most recent
- tolerance = median(selected prior legal gaps)

### 3.4 Candidate A center statistic

REPOSITORY FACT / FROZEN DECISION

- center = median(member prices)

This freeze applies to the center statistic itself. It does not freeze the membership rule, zone creation rule, zone identity, overlap semantics, or zone lifecycle.

## 4. Repository facts

### 4.1 REPOSITORY FACT

The canonical research code reconstructs 15-minute bars and identifies eligible swing highs and swing lows in canonical order. It does not implement a live Zone state machine, zone registry, sequential membership engine, or lifecycle.

Evidence:

- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

This is critical: the current repo is descriptive research, not a runtime membership implementation.

### 4.2 REPOSITORY FACT

The descriptive research pipeline repeatedly separates high and low swing streams and treats them as distinct same-direction sequences.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### 4.3 REPOSITORY FACT

The canonical research script reproduces the following counts for the current historical dataset:

- reconstructed bars: 1146
- eligible HIGH swings: 78
- eligible LOW swings: 68

Verified command:

- .\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"

Observed output:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

These counts are valid as descriptive evidence for the canonical historical stream. They are not proof of a final sequential membership decision.

### 4.4 REPOSITORY FACT

The repo contains no authoritative Zone object, member ledger, overlap policy, or live membership state machine that defines how a new swing becomes a member.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md](GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)

This is the decisive evidence boundary: the repo supports the existence of a same-direction stream and a tolerance history, but not the final sequential Zone state needed to evaluate membership.

## 5. What the current research actually measures

### 5.1 EXISTING EXPERIMENTAL EVIDENCE

The current research script is a descriptive clustering experiment. It does not implement a sequential Zone membership evaluation. The key functions in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) show this:

- cluster_swings(swings, tolerance_value)
- mixed_cluster_swings(swings, a_value, r_value)
- summarize_clusters(clusters, total_swings)
- family_results(...)
- mixed_surface(...)

These functions describe whether adjacent swings remain within a tolerance and how clusters summarize the sequence. They do not evaluate:

- current Zone candidate state
- current zone center
- distance from incoming swing to the zone center
- nearest member distance
- member-envelope logic
- zone creation event
- multiple-rules / overlap resolution
- historical mutation when new members are added

### 5.2 RESEARCH PROPOSAL ONLY

The repository does include a descriptive comparison of candidate reference semantics, but those are not a final sequential model. The prior audit records that the candidate rule families are structurally different under the descriptive model:

- Candidate A / D: center-distance / center ± tolerance forms are mathematically equivalent under a symmetric point-center geometry.
- Candidate B: nearest-member rule
- Candidate C: member-envelope / interval rule

The previous audit notes descriptive outcomes such as:

- Candidate A / D: 22 HIGH joins, 14 LOW joins
- Candidate B: 64 HIGH joins, 54 LOW joins
- Candidate C: 51 HIGH joins, 41 LOW joins

These are valuable comparative signals for a descriptive clustering model, but they are not proof of sequential membership behavior inside a real Zone candidate state.

This is a key distinction:

- descriptive clustering comparison: valid research evidence
- sequential membership engine: not yet defined by repo evidence

## 6. Minimal causal sequential model

### 6.1 What the repo can support right now

A minimal causal sequential model is possible only in a narrow, explicit sense:

- eligible swing sequence is canonical and ordered by eligibility time
- tolerance is computed only from prior legal same-direction gaps
- the current swing is excluded from its own tolerance history
- a Zone candidate must already exist before membership is evaluated
- membership is decided only using already-available information
- the decision does not use future swings

This is the strongest evidence-supported minimal model.

### 6.2 What it cannot yet support

The repo evidence does not yet support a final, measured membership decision because the following are unresolved root decisions:

- zone creation trigger
- first-member semantics
- whether a single member is treated as a valid zone or only a candidate seed
- what constitutes a Zone candidate state
- how member history is stored
- whether the zone center is fixed or recomputed as members accumulate
- what it means to be “in” or “out” of a zone when multiple candidate zones exist
- overlap / merge / coexistence rules
- zone identity and historical snapshot behavior

These are not implementation details; they are root blockers.

### 6.3 Minimal state required

The minimum state needed to evaluate membership without invention is:

- current eligible swing
- same-direction Zone candidate state
- zone center statistic
- current tolerance for the relevant direction
- member list or equivalent member representation only if the zone already exists
- causal ordering metadata

This is not yet a full zone lifecycle. It is only the smallest state needed to assess whether an incoming swing can be treated as a candidate member.

## 7. Candidate rule evaluation

### Candidate A — center-distance

Definition:

- incoming swing belongs if abs(P_new - center) <= tolerance

Status:

- RESEARCH PROPOSAL / NOT FROZEN
- This is the simplest point-center model and is consistent with the frozen center statistic.
- It can be expressed cleanly in a minimal sequential model once a Zone candidate already exists.

Evidence support:

- The center statistic is frozen: median(member prices).
- The repo’s research and design docs treat center-based membership as a natural candidate.

But the repo still does not define:

- when a zone candidate exists
- whether the center is fixed or recomputed
- whether membership is evaluated against the current center or an immutable historical center

### Candidate B — nearest member

Definition:

- incoming swing belongs if min(abs(P_new - member_price)) <= tolerance

Status:

- RESEARCH PROPOSAL / NOT FROZEN
- Requires a real member set and a causal state model.
- It is intellectually reasonable, but it is not supportable as a final rule without deciding the Zone-creation and member-state semantics.

Evidence support:

- It is a natural geometric interpretation of membership.
- It does not require a formal interval definition.

Blocker:

- the repo does not define a persistent member set, zone identity, or creation semantics.

### Candidate C — member envelope

Definition:

- incoming swing belongs if it lies within the tolerance boundary of the existing member envelope

Status:

- RESEARCH PROPOSAL / NOT FROZEN
- Requires a zone interval definition such as member min/max, center ± tolerance, or another envelope rule.
- This is a valid structural idea, but it is not frozen.

Blocker:

- the repo does not define the interval geometry or how the envelope is updated over time.

### Candidate D — center ± tolerance

Definition:

- incoming swing belongs if center - tolerance <= P_new <= center + tolerance

Status:

- MATHEMATICALLY EQUIVALENT TO A under a symmetric point-center interpretation

Formal equivalence:

- |P_new - center| <= tolerance
- is exactly equivalent to
- center - tolerance <= P_new <= center + tolerance

Therefore:

- Candidate A and Candidate D are not distinct rules under the current frozen center definition and symmetric tolerance.
- They are the same geometric test expressed in alternate algebraic form.

This is an important finding: A and D are not independent decisions.

## 8. Distinguishability of candidate rules

### 8.1 Which rules are actually distinguishable?

Under the current frozen definitions, the following are distinguishable only in a descriptive sense:

- center-based membership (A / D)
- nearest-member membership (B)
- member-envelope / interval membership (C)

However, the repo does not provide a final Zone state that lets those differences become real sequential decisions. Without a zone state and a creation trigger, the difference between A/B/C is mostly conceptual rather than operational.

### 8.2 Which are mathematically equivalent?

- A and D are mathematically equivalent under the current frozen center definition and a symmetric tolerance.

### 8.3 Which are blocked?

- B and C are blocked by missing zone geometry and missing member-set semantics.
- A is blocked by missing Zone creation / first-member semantics, even though it is mathematically clean.

## 9. Does the repo support one rule as a defensible proposal?

### 9.1 Short answer

No final winner is yet supportable.

### 9.2 Why not

The repo evidence supports a very narrow conclusion:

- Candidate A / D is the cleanest and simplest membership test once a Zone candidate already exists.
- Candidate B and C are plausible, but they require a more explicit zone geometry and member-state contract than the repo currently supplies.
- None of them is frozen.
- The more fundamental blocker is that the repo does not yet define a Zone candidate state or a creation trigger in a causal sequential way.

### 9.3 Best available proposal

PROPOSAL ONLY — NOT FROZEN

A minimal, repository-aligned proposal is:

- The incoming same-direction eligible swing is evaluated against an existing same-direction Zone candidate only after the zone exists.
- A zone candidate is defined only by prior causal evidence and the approved center statistic.
- The simplest sequential membership test is the center-distance form:
  - abs(P_new - center) <= tolerance
- This is equivalent to center ± tolerance under the current frozen symmetric interpretation.
- This proposal remains preliminary and intentionally does not freeze the rest of the zone lifecycle.

This is acceptable as a research proposal only. It is not a freeze decision.

## 10. Sequential model boundary and blocker analysis

### 10.1 Can membership semantics be evaluated now using a minimal sequential model?

Yes, but only in a limited, provisional, research-only sense.

A minimal sequential model can be defined as:

1. Stream of eligible same-direction swings in canonical order
2. Causal tolerance history built from prior legal same-direction gaps
3. Existing same-direction Zone candidate state
4. Zone center = median(member prices)
5. Incoming same-direction eligible swing
6. Membership decision based on comparison to current zone state
7. Resulting candidate state update for future swings

This is a legitimate controlled model boundary.

### 10.2 What prevents turning it into a final rule?

The following unresolved root decisions block a final freeze:

- zone creation / first-member semantics
- zone candidate state definition
- member-set mutation semantics
- center update timing
- overlap / merge rules
- multiple-zone assignment semantics
- historical snapshot semantics
- exact lifecycle behavior

Without these, a final sequential membership rule is not yet deterministically meaningful in the repository’s architecture.

## 11. Data analysis findings

### 11.1 Canonical counts

The repo’s canonical research implementation confirms:

- reconstructed bars: 1146
- eligible HIGH swings: 78
- eligible LOW swings: 68

These are valid counts for the descriptive historical research stream.

### 11.2 Sequential membership opportunities

The repo does not currently provide a final sequential membership opportunity count because there is no sequential zone-state engine in the codebase. As a result:

- sequential membership opportunities are not directly measurable from the repo as a frozen contract
- this is an explicit blocker, not a failure of the audit

### 11.3 Candidate memberships/rejections

The descriptive experiment does provide comparative cluster counts, but those are not sequential decision outcomes. They are clustering summaries under a chosen tolerance and reference geometry. This should be treated as evidence only, not as final membership logic.

The repo docs record that candidate rules differ materially under descriptive clustering:

- A / D: smaller number of joins
- B: materially larger number of joins
- C: intermediate outcome between A/D and B

These differences matter structurally, but they are not proof of which rule is correct in a real sequential Zone state.

### 11.4 Sensitivity to the current causal tolerance state

The repo’s research is sensitive to the chosen tolerance model because the tolerance state itself is derived from prior legal same-direction gaps. That is a valid causal dependency.

However, the repo does not yet define the Zone candidate state that would turn that tolerance into a membership decision. Therefore, the sensitivity is real, but it is still at the descriptive level, not the final sequential engine level.

### 11.5 Cases where candidate rules disagree

The sequential model cannot yet produce a final disagreement matrix because there is no live Zone state contract. Still, the descriptive research supports the following:

- A and D are equivalent under a symmetric point-center rule.
- B and C differ from A/D because they rely on different reference geometries.
- The difference between A and B/C is not just numeric; it is structural because B/C depend on a member set or envelope rather than a single center.

These are meaningful structural differences, but not final choice evidence.

## 12. Root decisions that remain unresolved

The following remain unresolved and therefore block a final membership freeze:

1. Zone creation trigger
2. first-member semantics
3. whether a single member is a valid Zone or only a seed candidate
4. exact zone candidate state definition
5. exact member-set representation
6. center update timing after new members are added
7. zone geometry / interval definition
8. overlap resolution
9. multiple-zone assignment semantics
10. historical snapshot / mutation semantics
11. tie-break rules for equal distances or simultaneous candidate zones
12. exact membership ordering inside the same direction and same time bucket

These are not minor details. They are root blockers.

## 13. Required conclusions

### 1. Can membership semantics be evaluated now using a minimal sequential model?

Yes, but only in a limited, provisional, research-only form. The minimal model is possible at the level of:

- eligible swings in canonical order
- causal tolerance history
- existing same-direction zone candidate
- current center and tolerance
- incoming candidate swing
- membership test

But the repo does not yet define the full Zone candidate / creation semantics needed to freeze the rule.

### 2. Which candidate rules are actually distinguishable under the frozen definitions?

The distinguishable geometric concepts are:

- A / D: center-distance / center ± tolerance
- B: nearest-member
- C: member-envelope / interval

However, A and D are mathematically equivalent under the frozen symmetric center definition.

### 3. Are A and D mathematically equivalent?

Yes.

Under the current definitions, the rule:

- abs(P_new - center) <= tolerance

is exactly equivalent to:

- center - tolerance <= P_new <= center + tolerance

Therefore A and D are the same rule written differently.

### 4. Where do A/B/C produce different membership outcomes?

They differ structurally when the zone state is defined by:

- a single center versus a member list versus an envelope

The repo’s descriptive clustering notes show that these reference geometries materially change membership counts. But those are descriptive, not frozen sequential outcomes.

### 5. Does existing evidence support one candidate as a defensible proposal?

Yes, but only in a narrow sense.

The cleanest and simplest proposal is Candidate A / D, because it is consistent with the frozen center statistic and the minimum state needed for a causal sequential membership test.

But it is still only a proposal, not a frozen rule.

### 6. What unresolved root decision(s) still block freezing membership?

The decisive blockers are:

- zone creation / first-member semantics
- zone candidate state definition
- member-set semantics
- zone geometry / envelope semantics
- overlap / multi-zone / merge rules
- historical state mutation semantics

### 7. Does zone creation / first-member semantics need to be resolved first?

Yes.

This is the primary blocker. Without a zone creation and first-member definition, a final membership rule is not yet meaningful in the repo architecture.

### 8. What is the smallest next decision required to continue without assumptions?

The smallest next decision is:

> Define the state transition from “eligible same-direction swing” to “ Zone candidate / first member / valid Zone.”

This must be settled before a final sequential membership rule can be frozen.

## 14. Final conclusion

The repository evidence supports a minimal, causal, sequential membership experiment, but it does not support a final membership freeze.

The strongest evidence-based statement is:

- A and D are mathematically equivalent under the frozen center definition and symmetric tolerance.
- B and C are conceptually valid but depend on unresolved zone state and geometry definitions.
- The center-distance formulation is the simplest prospective proposal once a Zone candidate already exists.
- However, membership semantics cannot be frozen until the Zone creation / first-member semantics and the minimal Zone candidate state are explicitly resolved.

Therefore the correct status is:

PROPOSAL ONLY — NOT FROZEN

This audit does not freeze membership, does not create a Zone rule, and does not start Phase 2.

## 15. Audit integrity check

This audit was written as a documentation-only research task and did not modify:

- production code
- production tests
- canonical data
- any frozen decision

The governing evidence set was used and the existing research script was run to confirm the canonical counts.

The canonical count verification command was:

- .\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"

Observed result:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

This means the reported document remains reproducible from the documented sources and the existing canonical historical pipeline.
