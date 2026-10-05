# Group B Zone Creation + First-Member Decision Audit V2

## Status

RESEARCH ONLY

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- This document is an evidence audit only.
- No production code was modified.
- No production tests were modified.
- No canonical data was modified.
- No frozen decision was modified.

## 1. Objective

This audit continues the control-bound Phase 1 Group B research on the unresolved root decision:

> When does a Zone first become a valid Zone, and what role does the first eligible same-direction swing play?

The prior membership audit established that membership cannot be frozen independently while the zone creation and first-member semantics remain unresolved. This document tests the smallest defensible creation alternatives against the repository’s actual evidence, without inventing a rule.

The central question is:

> Is the repository evidence sufficient to support the proposal that the first eligible same-direction swing is only a candidate/seed and that the Zone becomes valid only after a subsequent qualifying same-direction observation?

The audit also evaluates whether the previously mentioned 2-member baseline is actually supported by evidence or is only a convenient simplification.

## 2. Evidence reviewed

Authoritative and relevant repository evidence inspected:

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
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

This audit also used the existing canonical reconstruction and the same-direction descriptive research pipeline already present in the repo.

## 3. Frozen decisions preserved exactly

These decisions remain authoritative and are not reinterpreted:

### 3.1 Group A swing definition

- Swing High: High[i] > High[i - 1] and High[i] > High[i + 1]
- Swing Low: Low[i] < Low[i - 1] and Low[i] < Low[i + 1]
- strict comparisons only
- full required neighborhood
- no lookahead
- confirmation precedes downstream eligibility

### 3.2 15-minute bar contract

- 15-minute UTC bucket
- interval: [bar_start, bar_end)
- event at bar_end belongs to next bar
- closed bars are immutable
- incomplete trailing bar excluded
- final partial bar at dataset end is discarded

### 3.3 Tolerance-history contract

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

- center = median(member prices)

This freeze applies to the center statistic itself and not to the unresolved zone creation logic.

## 4. Repository facts

### 4.1 REPOSITORY FACT

The repo’s canonical research implementation reconstructs 15-minute bars and identifies confirmed eligible swing highs and swing lows in canonical order. It does not implement a valid Zone lifecycle, a Zone registry, a first-member rule, or a membership engine.

Evidence:

- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### 4.2 REPOSITORY FACT

The canonical research pipeline reproduces the actual same-direction swing counts for the current dataset:

- reconstructed bars: 1146
- eligible HIGH swings: 78
- eligible LOW swings: 68

Verified command:

- .\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"

Observed output:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

These are descriptive historical counts, not proof of a final zone creation rule.

### 4.3 REPOSITORY FACT

The repo intentionally separates HIGH and LOW streams and repeatedly treats same-direction history as distinct. That supports the use of direction-specific eligible sequences, but it does not answer the question of when a Zone first becomes valid.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEQUENTIAL_SEMANTICS_AUDIT.md)

### 4.4 REPOSITORY FACT

The repository contains no authoritative Zone creation rule, no final first-member semantics, and no accepted minimum member count.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md](GROUP_B_ZONE_CREATION_FIRST_MEMBER_AUDIT.md)

## 5. Required distinction: swing vs candidate vs valid Zone

This distinction is central and must not be blurred.

### 5.1 Swing existence

A swing exists when a confirmed eligible same-direction swing is produced under the frozen Group A definition.

### 5.2 Candidate/seed existence

A candidate/seed can exist as a structural state prior to a Zone being valid, but this is not a frozen rule. It is a conceptual distinction only.

### 5.3 Valid Zone existence

A valid Zone exists only when a design rule explicitly decides that the structural evidence threshold has been satisfied.

The current repo does not provide a final design rule for that threshold.

### 5.4 Tolerance availability

Tolerance may become available after one or more prior legal same-direction gaps under the frozen minimum-history rule.

However:

- minimum history = 1 does not imply minimum zone members = 1
- minimum history = 1 does not imply the first swing automatically forms a Zone
- minimum history = 1 is a tolerance-history condition, not a Zone-creation condition

This distinction is required by the repo’s own governance language.

### 5.5 Membership of later swings

The membership decision for later swings depends on a valid Zone state already existing. It cannot be evaluated meaningfully before the Zone creation and first-member semantics are determined.

## 6. Option A: first eligible same-direction swing immediately creates a valid Zone

### 6.1 State after the first eligible swing

A single eligible swing exists. Under Option A, that swing becomes a valid Zone immediately.

### 6.2 When does a Zone first become valid?

At the exact moment the first eligible swing is confirmed and eligible under the frozen Group A logic.

### 6.3 Causal information available at that moment

At that point, the system has:

- the current swing value
- the canonical replay ordering
- the current direction stream
- no prior same-direction legal gaps
- no tolerance available under the frozen rule if there are zero prior legal gaps

### 6.4 Can the frozen tolerance rule be applied?

Not in any meaningful way for the first swing itself. The frozen rule says:

- 0 prior legal gaps => no tolerance available

Therefore, a first swing cannot be shown to be valid because of prior tolerance history alone.

### 6.5 Can the frozen median center be computed?

Not on a single-member set in a way that gives a meaningful center state beyond the trivial value equal to the sole member price. The repo does freeze the center statistic, but this does not mean a one-member structure is a valid Zone by default.

### 6.6 Can membership be evaluated subsequently without circularity?

It is possible in a trivial sense, but it has a circular ambiguity: a one-member Zone is being treated as a fully valid Zone before it has enough evidence to be interpreted as a stable zone. This is precisely the kind of assumption the repo explicitly warns against.

### 6.7 Additional undocumented parameter?

Option A requires no additional parameter, but it does require the undocumented assumption that a one-member structure is a valid Zone. That is a design rule, not a parameter.

### 6.8 Hidden lookahead?

No direct lookahead is required, but the design does silently converts a swing into a completed Zone without any threshold check. That is not a temporal lookahead issue; it is a semantics issue.

### 6.9 Requires unresolved lifecycle / overlap / merge semantics?

Not necessarily for the first creation, but it creates a brittle state immediately: a valid Zone is created from a single observation, a structure the project repeatedly treats as weak or fragmented in research docs.

### 6.10 Deterministic reproducibility from current data?

Yes, the event is deterministic, but the determinism does not make the rule justified. It only means the rule is mechanically reproducible.

### 6.11 Assessment

Option A is mechanically simple, but it is not justified by the repo’s own cautionary evidence.

Conclusion: not defensible as the current repository-supported rule.

## 7. Option B: first eligible swing creates a candidate/seed; the Zone becomes valid after the next qualifying same-direction observation

### 7.1 State after the first eligible swing

After the first same-direction eligible swing, the system has:

- one eligible swing in the direction-specific sequence
- a candidate or seed state
- no valid Zone yet
- no tolerance from prior legal same-direction gaps

This is the critical separation the repo evidence supports.

### 7.2 When does a Zone first become valid?

At the second eligible same-direction swing, provided the second observation is in the same direction and can be evaluated under the causal same-direction sequence semantics.

This is the smallest defensible threshold consistent with the repo’s repeated caution that single-swing structures are weak and fragmented.

### 7.3 Causal information available at that moment

At the second eligible swing, the system has:

- the first and second observed values in the same direction
- a valid same-direction sequence of two eligible observations
- either one prior legal gap or a just-available same-direction gap history depending on exact implementation ordering
- a tolerance may become available under the frozen rule if one prior legal same-direction gap is available for the second swing

This is not a lookahead event because the second swing is evaluated only after its own confirmation and eligibility.

### 7.4 Can the frozen tolerance rule be applied?

Yes, but only at the moment the second eligible swing is available to be evaluated.

The minimum-history rule is compatible with this because:

- if the first swing is the prior legal observation and the second swing is current, then there is one prior legal same-direction gap and tolerance can be computed under the frozen rule

This does not prove the second swing creates a Zone automatically; it only indicates the tolerance becomes available after one legal prior gap.

### 7.5 Can the frozen median center be computed?

If the system treats the two same-direction swings as the initial Zone member set, then the median of two member prices is well defined and deterministic. But the repo still does not freeze whether the center is recomputed on every later member addition or whether the Zone becomes valid only after the second observation.

The median statistic itself is frozen, but the zone-validity trigger is not.

### 7.6 Can membership subsequently be evaluated without circularity?

Yes, provided the Zone is defined as valid only after the second same-direction observation is available and the current zone state is established from those same observations. This is a clean causal sequence and avoids the circularity of a one-member Zone being treated as a finished Zone.

### 7.7 Additional undocumented parameter?

No new parameter is required by the evidence. The requirement is primarily a state transition rule, not a numeric parameter.

### 7.8 Hidden lookahead?

No, as long as validity is determined only after the second swing becomes eligible in canonical order.

### 7.9 Requires unresolved lifecycle / overlap / merge semantics?

Not for the first moment of validity. It still leaves unresolved the broader lifecycle, but those issues do not have to be invented to evaluate the first valid Zone.

### 7.10 Deterministic reproducibility from current data?

Yes, this is reproducible because it depends only on:

- canonical same-direction sequence ordering
- the first and second eligible observations in the same direction
- the frozen tolerance-history rule
- the frozen median center definition

### 7.11 Assessment

This is the strongest proposal supported by current repo evidence because it matches the project’s repeated concern that single-swing structures are weak and fragmented, while remaining consistent with the causal tolerance rule.

Conclusion: Option B is the simplest defensible proposal, but still only as PROPOSAL ONLY — NOT FROZEN.

## 8. Option C: a Zone requires more than two observations

### 8.1 Why this is not automatically supported

The repo provides no concrete threshold beyond a repeated caution that single-swing structures are weak. It does not provide a measured justification for 3, 4, or more observations as a required minimum.

### 8.2 What would be required to support it?

A repository-supported reason would need to be specific, such as:

- a measured stability analysis showing that 2-member Zones are structurally unstable
- a deterministic design requirement for a minimum member count
- a demonstrated need for a larger evidence threshold before a valid Zone exists

The current repo does not contain that evidence.

### 8.3 Assessment

Option C remains unsupported as a current repo fact. It should be treated as an open research idea, not a repository-valid rule.

Conclusion: no evidence supports Option C as a current specification.

## 9. Is the 2-member baseline actually supported?

### 9.1 What the evidence supports

The repo evidence supports the statement that a first eligible swing is not enough to justify a stable Zone by default.

It also supports the idea that a two-swing same-direction structure is a reasonable minimal baseline for a valid Zone candidate because:

- it separates observation from valid Zone
- it matches the causal availability of one prior legal same-direction gap
- it avoids building a Zone from a single isolated observation
- it is consistent with the narrow earlier research proposal that minimum cluster size may be 2

### 9.2 What the evidence does not support

The repo does not prove that 2 members is the optimal or final rule. It does not prove a 2-member threshold is necessary in every case, nor does it prove that a 2-member Zone is the only valid design.

Therefore:

- the 2-member baseline is weakly supportable as a practical research proposal
- it is not actually frozen
- it is not proven by a causal experiment in the repo

Conclusion: the 2-member baseline is a reasonable proposal, but not a repository fact.

## 10. Comparison across the options

| Option | First state after first swing | Zone validity point | Tolerance available? | Median center available? | Evidence support | Freeze status |
| --- | --- | --- | --- | --- | --- | --- |
| A | first swing is immediately a valid Zone | immediate | no for first swing | trivially yes, but weakly meaningful | weak, not supported by repo evidence | not defensible |
| B | first swing is a candidate/seed | after second same-direction eligible swing | yes at second swing under prior-gap rule | yes for two-member set | strongest repo-aligned proposal | proposal only |
| C | first swing is a candidate, but zone requires more than two observations | after 3+ observations | possible after enough history | yes, but requires extra threshold | unsupported by current repo evidence | not supported |

## 11. What the current data does and does not permit

### 11.1 Supported by current data

The current canonical data supports the following with actual counts:

- 1146 reconstructed 15-minute bars
- 78 eligible HIGH swings
- 68 eligible LOW swings
- same-direction sequences exist and are structurally meaningful
- the earliest same-direction tolerance can become available only after enough prior legal observations exist under the frozen rule

### 11.2 Not supported by current data

The current data does not support a final answer to:

- whether a one-swing structure should be a valid Zone
- whether 2 members is the optimal threshold
- whether more than 2 members are required
- whether a stable Zone should be based on a fixed center or a mutable center
- whether overlap or merge behavior is acceptable at the earliest stage of a Zone

Those require decisions not yet present in the repo.

## 12. Root decision impact

This decision is the direct prerequisite to the membership decision.

Once the repo resolves:

- whether an initial same-direction swing is only a seed
- whether a valid Zone begins at two same-direction observations
- whether a Zone can exist with one member

then membership semantics become evaluable in a meaningful way.

Without that resolution, membership becomes circular or undefined because the target object does not yet have a valid state.

## 13. Smallest next decision after this one

The smallest next decision after zone creation / first-member semantics is:

> Define the exact Zone candidate state and member-set update semantics for the first valid Zone.

That is the next root decision because once the Zone creation trigger is accepted, the system can define:

- member list or equivalent state
- center update timing
- tolerance update timing
- membership decision ordering
- future sequential membership evaluation

## 14. Required conclusion

### 1. Is Option A defensible?

No. It is not supported by the repo’s own cautionary evidence that a single-swing structure is structurally weak.

### 2. Is Option B defensible?

Yes, as a proposal only. It is the simplest repository-aligned rule because it separates:

- swing existence
- candidate seed existence
- valid Zone existence
- tolerance availability
- member evaluation

This is the clearest design fit with the repo evidence.

### 3. Is there evidence for Option C?

No concrete evidence supports a threshold above two observations. This is not supported by current repo facts.

### 4. Is the previously proposed 2-member baseline actually supported?

It is weakly supported as a practical proposal, but not proven as the final rule. It is not frozen.

### 5. Which option is the simplest defensible PROPOSAL?

Option B.

PROPOSAL ONLY — NOT FROZEN

### 6. What evidence is still missing before this can be frozen?

The repo still needs a definitive rule for:

- zone candidate state
- first valid Zone semantics
- member-set update semantics
- center update timing
- whether center is fixed or recomputed
- whether a two-member Zone immediately becomes a valid Zone by design or only after a later confirmatory condition

### 7. Does membership semantics become evaluable after resolving this decision?

Yes, after this decision is fixed, membership semantics become meaningful. Before that, the valid Zone object itself is undefined.

### 8. What is the next smallest root decision after this one?

The next smallest root decision is the exact Zone candidate state and member-set update semantics required once a valid Zone is created.

## 15. Governance verification

This audit was documentation-only and did not alter production files.

The exact evidence command used for the canonical data was:

- .\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"

Observed output:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

The exact repository integrity check used at the end was:

- git diff --check; Write-Host '---'; git status --short --untracked-files=all

This produced no diff-check errors, and the status output confirms the repository still contains unrelated existing modifications but no production code or tests were modified by this audit task.

## Final audit result

The current repository evidence supports a proposal that the first eligible swing is a candidate/seed, not automatically a valid Zone, and that a valid Zone becomes established only after a subsequent qualifying same-direction observation.

This is the simplest defensible proposal consistent with the repo evidence.

It is therefore:

PROPOSAL ONLY — NOT FROZEN

It is not a freeze, and it does not authorize starting Phase 2.
