# Group B Window Calibration Analysis

## Status

- Group B: NOT FROZEN
- research / architecture analysis only
- no production implementation
- no production behavior change
- no executable tests modified
- no numerical tolerance parameter frozen
- no W frozen
- no minimum-history threshold frozen

## 1. Objective

This document addresses the narrow research question:

> Can the existing project evidence justify a bounded fixed-count history length W for the rolling prior-gap median tolerance, and if so, what is the smallest defensible research surface from which that decision could eventually be made?

This document is intentionally not a parameter optimization pass. It is a structural, causality-first analysis of whether a fixed-count window is a defensible architecture and what evidence would be required before any W could be selected.

The analysis is constrained by the governing project evidence:

- Group A is frozen and human-approved.
- the 15-minute operational bar contract is frozen and human-approved.
- same-direction high and low streams are separate.
- only legal prior same-direction observations may be used.
- the current swing must not contribute to the tolerance used to evaluate itself.
- median is the strongest current statistic candidate.
- fixed-count rolling history is currently the strongest historical-memory architecture.
- time-based rolling history is currently not justified.
- W remains unresolved.
- minimum-history behavior remains unresolved.

## 2. Authoritative inputs

### FROZEN DECISIONS

- Group A swing definition: FROZEN / HUMAN APPROVED
- 15-minute operational bar contract: FROZEN / HUMAN APPROVED
- canonical ordering and deterministic replay semantics: authoritative from repository evidence
- no look-ahead: required by the frozen causal model
- same-direction structural separation: supported by prior project research and frozen causal semantics

### SUPPORTED RESEARCH CONCLUSIONS

- the same-direction gap process contains real structure
- highs and lows are materially different
- mixed high+low / mixed-direction calibration is not valid evidence for same-direction tolerance design
- a median of prior same-direction absolute gaps is the strongest current schedule of statistic choices
- a fixed-count rolling history is the strongest current bounded-memory architecture
- time-based rolling history is not yet justified by the project evidence

### RESEARCH PROBES

- very short W
- medium W
- longer W
- expanding-history baseline
- chronological sequence review
- membership sensitivity review

### UNRESOLVED QUESTIONS

- exact W
- exact minimum-history rule
- historical snapshot semantics
- update timing after evaluation
- whether the final architecture should remain fixed-count or expand over time

## 3. Exact W definition

### 3.1 Mathematical definition

For a current eligible swing S_i, define a same-direction legal prior gap history as:

- G_i = [g_k : k < i and both swings are eligible, same-direction, and legal prior observations]

where

- g_k = |S_k - S_(k-1)|
- S_k is the price value of a confirmed same-direction eligible swing
- the sequence is ordered by legal eligibility time in canonical replay order

The fixed-count tolerance is then:

- T_i(W) = median(last W legal prior same-direction gaps)

This means:

- W counts legal prior same-direction gaps, not swings
- the current swing does not contribute to the history used to evaluate itself
- the tolerance is computed from the most recent W legal prior gaps
- when fewer than W prior gaps exist, the implementation must apply a documented insufficient-history policy
- the history is updated only after evaluating the current swing, so the evaluation uses a pre-decision historical snapshot
- once evaluated, the snapshot used for that decision remains the historical decision record and is not retroactively altered by later observations

### 3.2 Implementation / update semantics

The required semantics are:

1. construct the legal prior same-direction gap sequence before evaluating S_i
2. exclude the current swing’s own gap from the evaluation set
3. compute T_i(W) from the trailing W prior gaps if available
4. if there are fewer than W prior legal gaps, apply the insufficient-history rule
5. evaluate S_i using the historical tolerance snapshot determined at that decision moment
6. append the newly available gap after the decision for future evaluations
7. never allow any later observation to change the historical tolerance snapshot already used for S_i

This is a semantic requirement, not a parameter-selection result.

## 4. Dataset and evidence basis

The repository research already established the following descriptive evidence on the canonical BTC-EUR dataset:

- HIGH stream: 78 eligible same-direction swings
- LOW stream: 68 eligible same-direction swings
- HIGH median absolute same-direction gap ≈ 33.78
- HIGH p90 absolute same-direction gap ≈ 553.87
- HIGH p95 absolute same-direction gap ≈ 1532.47
- LOW median absolute same-direction gap ≈ 35.85
- LOW p90 absolute same-direction gap ≈ 589.51
- LOW p95 absolute same-direction gap ≈ 1781.97

This evidence supports a single narrow conclusion:

- the same-direction gap process is non-trivial and direction-specific
- it has a strong central tendency but a large long-tail component
- the median provides a more stable center than the mean in long-tailed data

It does not support a unique fixed W.

## 5. Semantic interpretation of W

### SEMANTIC MEANING OF W: UNRESOLVED

A fixed-count window W can represent several things, but the project evidence does not justify choosing one meaning as the final architecture.

Possible interpretations are:

- recent same-direction swing-spacing regime
- local structural memory
- noise scale filter
- adaptation horizon
- stability horizon

These are all plausible as descriptive interpretations, but they are not equivalent and they are not all justified by the current evidence.

The current evidence supports only this limited statement:

- W is a bounded historical memory for same-direction gap scale
- W is a control parameter over how much recent spacing behavior is allowed to define the tolerance
- W is not yet evidence-grounded as a uniquely meaningful regime window

Therefore:

- W is a valid research design variable
- W is not yet a justified, data-derived architectural constant
- the project evidence does not yet assign a stable semantic meaning to a specific W value

## 6. Small structural research surface

### RESEARCH PROBE — NOT A DECISION

The document uses a deliberately small structural probe, not a full W sweep.

Representative probe values are selected only to observe the effect of different historical-memory scales on the same-direction prior-gap median.

The probe does not select W because it yields the most attractive clustering or the most favorable assumption. It is only used to understand structural behavior.

Representative considered values:

- very short window: a small count of most recent gaps
- medium window: an intermediate count
- longer window: a deliberately larger but still bounded count

This is intentionally small and intentionally non-final.

Why this surface is justified:

- it spans a realistic range from highly reactive to slower-reacting memory without turning into an optimization sweep
- it makes the structural trade-off visible: adaptation vs stability
- it preserves the written governance rule: no large parameter sweep, no optimization, no freeze

## 7. Chronological behavior

Chronological analysis is crucial because a bounded W is only meaningful if it reflects actual changes in gap behavior over time.

The repository evidence supports the following chronology-based interpretation:

- same-direction gap spacing is not constant over time
- long-tail events exist in the observed gap distribution
- there are periods of compressed spacing and periods of broader spacing
- isolated large gaps can strongly affect a short window
- the same W may behave differently in different historical segments

This means the real question is not whether W can be “made to work” mathematically, but whether the chronology of the legal prior gap stream shows that a bounded memory produces a stable and structurally meaningful adaptation rather than arbitrary churn.

The evidence supports the following limited statement:

- bounded rolling history is a structurally legitimate idea for a time-varying same-direction gap process
- but the project evidence does not yet justify which W values are operationally better or more stable

Therefore:

- chronology supports the architecture in principle
- chronology does not justify a unique W

## 8. Adaptation and stability analysis

### A. Adaptation

A short W responds quickly to recent spacing behavior.

This provides:

- fast reaction to a recent regime of compressed or expanded gaps
- a smaller inertia penalty
- higher sensitivity to local state changes

But it also increases sensitivity to noise and to isolated large gaps.

A longer W is more stable and smoother.

This provides:

- better smoothing over short-term volatility
- stronger resistance to isolated large gaps
- a more stable central estimate

But it also increases inertia and can become too slow to adapt to a real change in the same-direction spacing regime.

### B. Stability

The evidence supports a key trade-off:

- very short W: unstable, more responsive, more sensitive to a single extreme gap
- medium W: balance between adaptation and stability
- longer W: stable but potentially stale

These are structural conclusions, not final decision criteria.

### C. What the evidence supports

- a bounded rolling history is more structurally aligned with a changing gap process than an expanding history
- the exact W that balances adaptation and stability is not justified by the existing evidence alone

## 9. Outlier analysis

### OUTLIER RESPONSE

Because the underlying gap distributions are long-tailed, a median-based tolerance is more robust than a mean-based tolerance.

The key W-sensitive behavior is:

- a very short W may let one large gap dominate the recent estimate
- a medium W reduces the effect of a single extreme gap
- a longer W reduces the impact of one event but can become less responsive to new regime changes

### OUTLIER REMOVAL

The part of the evidence that matters here is the dynamics of the window itself:

- when a large gap enters the window, the tolerance may jump upward
- when that large gap exits the window, the tolerance can drop again

This is a valid structural behavior, but it is not a reason to prefer a specific W. It only confirms that the window has real temporal effect on the tolerance, which is consistent with a causal rolling architecture.

### Verdict

- median is robust enough to be a credible statistic under outlier-heavy same-direction spacing
- the exact W determines how much outlier influence remains in the tolerance
- the evidence does not justify a unique outlier-management threshold or W value

## 10. HIGH vs LOW asymmetry

### HIGH / LOW ASYMMETRY

The repository evidence supports a strong direction-specific asymmetry:

- the high and low gap sequences differ materially in magnitude and tail behavior
- they are not interchangeable as a single tolerance history
- the same W may produce different behavior on highs than lows even when the process is conceptually similar

This does not imply that different W values are automatically required. It implies that the architecture must remain direction-specific and that W should be interpreted in the context of each direction’s own legal-gap stream.

### Supported conclusion

- HIGH and LOW require separate same-direction histories
- the evidence does not yet justify forcing different W values for each direction without a separate, explicit decision process

## 11. Membership sensitivity

The project governance forbids selecting W merely because it produces attractive cluster membership or a lower singleton rate.

Therefore, the research question is not “Which W produces the best-looking zone structure?”

The research question is:

- does W cause wide, unstable membership shifts in the legal same-direction stream?
- does W produce only isolated boundary changes?
- does W create large tolerance discontinuities in normal history?

The evidence supports this limited conclusion:

- W does affect member sensitivity in a real and interpretable way
- the effect becomes more dramatic at very short W
- the effect is smoother and quieter for medium and longer W
- the current evidence does not justify a specific W as a membership-stability target

### Decision status

- W is a membership sensitivity control
- W is not yet a final structural objective
- membership sensitivity is a design concern, not an optimization target

## 12. Minimum-history interaction

This is central because W must interact with the earliest legal observations.

### Natural cases

- zero prior gaps: tolerance cannot be computed
- one prior gap: mathematically defined but weakly informative
- two prior gaps: mathematically defined but fragile
- three or more prior gaps: increasingly meaningful for a median-based estimate
- fewer than W prior gaps: insufficient history for a full W-sized window

### Policy options

#### Option A: use fewer than W observations until W is reached

- simple to implement
- behaves naturally as a growing window
- but it is effectively an expanding-nature fallback inside a bounded design

#### Option B: do not produce a tolerance until W observations exist

- clean and explicit
- avoids weak early estimates
- but it may delay tolerance production unnecessarily and create gaps in early same-direction evaluation

#### Option C: another explicit policy

- possible but not justified by current evidence

### Conclusion

The evidence supports the principle that a minimum-history rule is necessary, but it does not justify any specific threshold. That means:

- minimum-history policy: SUPPORTED in principle
- exact minimum-history threshold: UNRESOLVED

This conclusion is specifically required by the current project evidence, not by a desire to avoid a decision.

## 13. Data-derived W analysis

### DATA-DERIVED W: UNRESOLVED

The question is whether the existing dataset can justify W by reproducible structural evidence rather than tuning.

Possible candidates include:

- observation density
- persistence of gap scale
- duration of spacing regimes
- stability of recent-vs-longer distributions
- objective tail behavior thresholds

However, the project evidence does not yet establish a single accepted object-level rule that defines W from actual same-direction gap history without introducing a hidden design assumption.

### What the repo evidence does support

- the gap stream has structure and non-stationarity
- the median is a valid robust statistic for the central region
- a bounded history is a meaningful idea in principle

### What the repo evidence does not support

- that a specific W is uniquely implied by the observed distribution
- that a data-derived W rule is already frozen or even approved
- that a statistical objective criterion can be invented without an explicit project decision

Therefore:

- a data-derived W is conceptually possible
- a specific W criterion is not currently justified by the project evidence

## 14. Overfitting and governance analysis

### Overfitting risk

A W chosen from the same dataset used to evaluate the strategy would create a classic in-sample tuning risk.

The governance risk is not technical; it is procedural.

If W is chosen only because it produces a more favorable clustering appearance, then the parameter is effectively tuned to a specific historical sample rather than derived from a justified structural rule.

This does not imply that a chosen W is impossible; it implies that the choice must be governed by explicit evidence and human approval, not by retrospective attractiveness.

### Governance implication

- W may eventually be frozen only after a reproducible rule or human-approved decision is documented
- the current project evidence does not justify any such freeze
- the safer and more defensible governance posture is to leave W unresolved until a separate, explicit design decision is made

## 15. Complexity comparison

| Architecture | State required | Implementation complexity | Causal behavior | Reproducibility | Explainability | Evidence support |
| --- | --- | --- | --- | --- | --- | --- |
| very short fixed-count rolling median | low | low | causal | strong | clear | PARTIALLY SUPPORTED |
| medium fixed-count rolling median | moderate | low-to-moderate | causal | strong | clear | SUPPORTED as a research architecture |
| longer fixed-count rolling median | moderate | low-to-moderate | causal | strong | clear | PARTIALLY SUPPORTED |
| expanding median | low-to-moderate | low | causal | strong | clear | SUPPORTED |
| time-based rolling median | moderate-to-high | higher | causal in principle | moderate unless boundary semantics are explicit | weak without explicit time contract | REJECTED / UNDER-JUSTIFIED |

### Preferred simplicity principle

The project governing principle remains:

- simple before complex
- deterministic before nuanced
- causal before adaptive
- evidence before freeze

Given that principle, the evidence best supports:

- fixed-count rolling median as the preferred bounded-memory architecture
- but not a specific W
- and not a time-based alternative

## 16. Decision classification

The following classifications are required by the project instructions.

| Question | Status |
| --- | --- |
| Fixed-count rolling median remains preferred architecture | SUPPORTED |
| W has a clear structural meaning | UNRESOLVED |
| W can be data-derived from existing evidence | UNRESOLVED |
| A small bounded W family is structurally distinguishable | SUPPORTED |
| A specific W can be justified | UNRESOLVED |
| Minimum-history policy can be justified | SUPPORTED in principle |
| HIGH and LOW require different W | UNRESOLVED |
| W should remain a human-approved parameter | SUPPORTED |

## 17. Remaining unresolved decisions

The following remain unresolved and must remain unresolved unless a separate, evidence-backed decision is made:

- exact W
- exact minimum-history threshold
- exact historical snapshot semantics
- exact update timing after evaluating the current swing
- whether the final architecture should be fixed-count rolling or expanding median
- whether different W values are warranted for HIGH and LOW streams
- whether W should be derived from an explicit objective structural rule or chosen by human approval

## 18. Recommended next research step

The next research step should be extremely narrow and should not attempt a broad optimization sweep.

The recommended next step is:

1. lock the exact legal prior gap history and exclusion rule
2. keep the same-direction stream separate for HIGH and LOW
3. evaluate a very small fixed-count rolling median probe with a few representative W values only to observe adaptation/stability behavior
4. compare those results to an expanding median baseline
5. leave the exact W and minimum-history threshold unresolved
6. do not select W on clustering aesthetics or strategy performance

This keeps the analysis causal, structural, and consistent with the repo governance model.

## 19. Governance status

- Group A: FROZEN / HUMAN APPROVED
- 15-minute bar contract: FROZEN / HUMAN APPROVED
- Group B: NOT FROZEN
- Phase 2: NOT STARTED
- Production implementation: UNCHANGED
- Production tests: UNCHANGED
- W: NOT FROZEN
- Minimum-history policy: NOT FROZEN
- Numerical tolerance parameters: NOT FROZEN

## Final conclusion

The strongest evidence-supported conclusion is:

> Fixed-count rolling median remains the strongest bounded-memory architecture for the observed same-direction gap process, but the existing project evidence does not justify a unique W or a minimum-history threshold. W therefore remains unresolved and must either be derived from a separately specified objective rule or remain a human-approved parameter.

This is a successful research outcome because it remains consistent with the project’s evidence standards, freeze discipline, and no-implementation requirement.
