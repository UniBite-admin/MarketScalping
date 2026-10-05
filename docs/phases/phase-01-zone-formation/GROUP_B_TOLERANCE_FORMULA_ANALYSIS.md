# Group B Tolerance Formula Analysis

## Status

- Group B: NOT FROZEN
- research / architecture analysis only
- no production implementation
- no numerical parameter frozen

## 1. Objective

This analysis determines whether the available evidence supports a specific mathematical form for the rolling prior-gap absolute tolerance architecture.

The governing foundation remains:

- Group A swing definition is frozen.
- the 15-minute operational bar contract is frozen.
- eligible confirmed swings are separate by direction.
- observations are ordered by eligibility time in canonical replay order.
- the current swing is excluded from the history used to evaluate itself.
- Group B remains NOT FROZEN.

The task is not to find a profitable parameter. It is to ask a narrower, architecture-level question:

"Does the evidence justify a specific mathematical form for the rolling prior-gap absolute tolerance, or is the evidence still insufficient to distinguish the mathematically plausible forms?"

## 2. Frozen Inputs

FROZEN

- Group A swing semantics.
- 15-minute UTC-aligned closed-bar contract.
- event at bar_end belongs to the next bar.
- closed bars are immutable.
- trailing / partial bars are excluded from finalized evaluation.
- final partial bar at dataset end is discarded.
- no look-ahead.

RESEARCH-SUPPORTED

- high and low sequences are distinct.
- same-direction consecutive spacings are meaningful.
- mixed high+low and mixed-direction calibration is not a valid basis for same-direction tolerance.
- the gap distributions are heavy-tailed and direction-dependent.

REMAINING UNRESOLVED

- exact rolling statistic to use
- exact window model
- exact minimum-history gate
- exact tolerance update timing
- exact fallback behavior when history is insufficient

## 3. Input Gap Series

For a same-direction sequence of eligible confirmed swings:

- H = [h_1, h_2, ..., h_n] for highs
- L = [l_1, l_2, ..., l_n] for lows

The legal observed price for each swing is the price value produced by the frozen Group A swing record:

- swing high uses the high-price field of the bar at the confirmed swing event
- swing low uses the low-price field of the bar at the confirmed swing event

The project evidence does not justify introducing a different price source or a new transformed price for this analysis.

Define the absolute same-direction gap sequence:

- g_k = |p_k - p_{k-1}|

where p_k is the price of the k-th eligible confirmed swing of the same direction.

This is the input series for the tolerance estimator.

### Causal availability of g_k

A gap g_k becomes causally available only after both p_k and p_{k-1} are legal prior observations for the current swing being evaluated.

For an evaluation at current swing S_i, the legal gap history is:

- {g_k : k < i and both swings are eligible and same-direction}

Not legal for evaluating S_i:

- g_i = |p_i - p_{i-1}| when computed from the current swing itself
- any future same-direction swing j > i
- any gap formed from unconfirmed or yet-to-be-eligible swings

This is the key causal boundary. The exact point of evaluation matters: the current swing cannot create its own tolerance history.

## 4. Current-Swing Causality

### Architecture 1: YES, allow g_i to participate in tolerance used for S_i

This creates a self-referential rule:

- the current swing value is used to define the tolerance that determines whether the current swing is accepted into a zone or cluster

This is circular in the causal dataflow because the tolerance used to evaluate membership is based on the same observation being evaluated.

That architecture is not structurally clean and is not consistent with the project’s frozen causal principle.

### Architecture 2: NO, exclude the current swing from the history used to evaluate itself

This is the project-supported direction:

- for swing S_i, tolerance is computed from prior legal same-direction gaps only
- S_i does not contribute to the tolerance used to evaluate S_i
- after the decision, the current swing may be appended to the historical stream for future evaluations under an explicit post-decision state update rule

This is the only architecture consistent with the project’s current semantic foundation and with no-look-ahead.

### Conclusion on causality

The evidence supports the NO architecture.

This means the mathematically correct general form is not:

- T_i = f({|p_i - p_{i-1}|, earlier gaps})

but rather:

- T_i = f({|p_j - p_{j-1}| : j < i and both p_j, p_{j-1} are legal prior same-direction observations})

The current swing value is excluded from the tolerance history used to evaluate itself.

## 5. Statistic Comparison

The candidate statistics are evaluated as possible definitions of f(·) on the prior-gap series.

### A. Rolling median

Definition:

- median(G)

where G is the set or ordered list of legal prior same-direction absolute gaps.

Mathematical form:

- if G = [g_1, g_2, ..., g_m], then median(G) = middle value of ordered G, or average of two middle values if even length

Sensitivity to outliers:

- low

Sensitivity to regime shifts:

- moderate; it follows the central tendency of the prior history and does not react strongly to a few extreme gaps

Sample-size behavior:

- stable as soon as the sample is not degenerate
- robust for small to medium samples
- less sensitive to long-tail distortion than mean

Minimum observations required:

- mathematically exists for m >= 1
- but for robust interpretation, a minimum-history gate is still necessary because one gap may be unstable

Deterministic behavior:

- yes

Parameter count:

- low

Hidden assumptions:

- the choice to use a central statistic is a design decision, not a forced mathematical law

Interpretability:

- strong; median is easy to explain as the central prior-gap scale

Compatibility with causal replay:

- strong

Evidence assessment:

- median is the most defensible robust-central candidate under long-tail, skewed gap distributions

### B. Rolling arithmetic mean

Definition:

- mean(G) = (1/m) * sum(g_k)

Sensitivity to outliers:

- high

Sensitivity to regime shifts:

- high because one or more very large gaps can materially drag the estimate upward

Sample-size behavior:

- works mathematically with m >= 1
- but it can be strongly distorted by outliers and tail-heavy observations

Minimum observations required:

- mathematically exists for m >= 1
- but not meaningful under a long-tailed distribution without careful interpretation

Deterministic behavior:

- yes

Parameter count:

- low

Hidden assumptions:

- a strong assumption that the average past gap is a sensible tolerance basis in a highly skewed distribution

Interpretability:

- easy but easily misleading in tail-heavy distributions

Compatibility with causal replay:

- strong

Evidence assessment:

- mathematically valid, but not the strongest candidate for the actual BTC-EUR same-direction gap data because the project’s descriptive evidence shows long-tail behavior and a skewed distribution

### C. Rolling trimmed mean

Definition:

- trimmed mean of G after removing the lowest and highest q% of values

Sensitivity to outliers:

- moderate to low depending on trim fraction

Sensitivity to regime shifts:

- moderate

Sample-size behavior:

- requires enough observations to trim without losing too much information
- more complex than median or mean

Minimum observations required:

- not justified by current evidence
- introduces a new design choice: trim fraction, number to remove, and handling of small samples

Deterministic behavior:

- yes

Parameter count:

- medium

Hidden assumptions:

- trim fraction is arbitrary unless justified by evidence

Interpretability:

- moderate, but requires more explanation and more implementation rules

Compatibility with causal replay:

- strong if the trim rule is fixed

Evidence assessment:

- not justified by the current repo evidence as a minimal root architecture
- adds complexity without a strong project-grounded reason

### D. Rolling percentile / quantile

Definition:

- q-percentile of G, such as p50, p60, p75, etc.

Sensitivity to outliers:

- low to moderate depending on q

Sensitivity to regime shifts:

- depends on q

Sample-size behavior:

- mathematically well-defined for reasonable sample sizes
- more granular than median

Minimum observations required:

- one or more, but small-sample quantiles can be unstable

Deterministic behavior:

- yes

Parameter count:

- low to moderate depending on whether q is fixed or adaptive

Hidden assumptions:

- the quantile level must be chosen explicitly

Interpretability:

- moderate

Compatibility with causal replay:

- strong

Evidence assessment:

- a valid candidate family, but the project evidence does not yet justify a specific quantile level
- without a chosen q, this is a template rather than a final mathematical rule

### E. Expanding median

Definition:

- median of all legal prior absolute gaps accumulated over time

Sensitivity to outliers:

- low

Sensitivity to regime shifts:

- moderate, but it can be slow to react to regime changes because the full history remains in the estimator

Sample-size behavior:

- eventually stable, but can be overly anchored to early history

Minimum observations required:

- mathematically exists with one observation, but implementation semantics still require a guard

Deterministic behavior:

- yes

Parameter count:

- low

Hidden assumptions:

- assumes early history remains relevant as valid evidence for the current regime

Interpretability:

- strong

Compatibility with causal replay:

- strong

Evidence assessment:

- plausible, but the evidence does not justify it over a rolling history because some old observations may become stale relative to later structural conditions

### F. Expanding mean

Definition:

- mean of all legal prior gaps

Sensitivity to outliers:

- high

Sensitivity to regime shifts:

- high, and potentially distorted by long-tailed historical extremes

Evidence assessment:

- not preferred under the observed heavy-tail distribution

### Evidence-based comparison

Under the actual project evidence, the strongest simple candidates are:

1. rolling median
2. expanding median
3. rolling percentile / quantile
4. rolling mean (weaker due to tail sensitivity)
5. trimmed mean (only if justified; current evidence does not justify it)

The strongest case is for a robust central statistic, with median as the default robust choice. However, the repository evidence does not yet justify freezing median as the unique final form. It only supports median as the strongest current mathematical candidate.

## 6. Expanding vs Rolling History

### A. Expanding history

Definition:

- include every legal prior same-direction absolute gap that is available up to time t

Parameters introduced:

- none beyond the chosen statistic

State complexity:

- low to moderate

Regime adaptability:

- slower to adapt because historical extremes remain in the estimator

Sensitivity to early-history conditions:

- high: early observations may persist for a long time

Sensitivity to sparse observations:

- high when the sample is small; low once the sample grows

Reproducibility:

- strong

Risk of overfitting:

- low, but may reflect stale structure

Evidence support:

- reasonable as a baseline, but not clearly superior to rolling history for a dynamic same-direction process

### B. Fixed-count rolling history

Definition:

- include only the most recent N legal prior same-direction gaps

Parameters introduced:

- N, the count window

State complexity:

- moderate

Regime adaptability:

- stronger than expanding history because attention is placed on recent structure

Sensitivity to early-history conditions:

- low once the window fills

Sensitivity to sparse observations:

- moderate; early in the series, N may be unavailable

Reproducibility:

- strong if N is fixed and the update ordering is deterministic

Risk of overfitting:

- moderate if N is tuned to a single historical slice

Evidence support:

- structurally plausible; this is the natural rolling architecture when the project wants a causal adaptation not driven by all prior history

### C. Time-based rolling history

Definition:

- include only gaps whose eligibility times fall within a fixed time interval

Parameters introduced:

- time interval length, decision on exact inclusion at boundaries

State complexity:

- moderate to high, because time-based history needs careful boundary semantics

Regime adaptability:

- can be useful

Sensitivity to early-history conditions:

- low if the interval is large enough

Sensitivity to sparse observations:

- can be high in sparse periods

Reproducibility:

- strong if interval semantics are explicitly fixed

Risk of overfitting:

- moderate if such a window is chosen for convenience rather than evidence

Evidence support:

- not strongly justified by the current project evidence
- adds a second time-dimension semantics beyond the actual root issue

### Conclusion on history model

The evidence does not justify freezing a fixed-count or time-based history length, but it does support the principle that a rolling or adaptive history is structurally more defensible than an expanding full-history estimator when the price gap process is regime-sensitive and long-tailed.

Among the candidate history models, fixed-count rolling is the simplest explicit form to reason about and test. However, its exact N remains intentionally unresolved.

## 7. Chronological Evidence

The canonical dataset was inspected only in chronological descriptive form, not as a tuning dataset.

The purpose was to answer whether the data suggests a history model that adapts over time or whether the process is effectively static.

The evidence shows:

- gap magnitudes differ materially between high and low sequences
- gap magnitudes differ materially across historical segments
- the absolute and relative gap distributions are highly skewed
- the mean is more exposed to long-tail distortion than the median
- price scale changes over the dataset, so a fixed absolute tolerance would not keep the same meaning across time
- recent same-direction gaps likely carry more information about the current structural regime than very early gaps

These findings support adaptive history and a robust central statistic, but they do not yet establish a single optimal rolling rule.

The most defensible interpretation is:

- the data supports the idea that tolerance should adapt to the observed same-direction gap process
- the data does not yet justify a final window or final statistic

## 8. Small-Sample Behavior

The architecture must remain valid in sparse data conditions.

### Zero prior gaps

- no legal historical gap exists
- no tolerance can be computed from prior same-direction gaps
- state remains insufficient history

### One prior gap

- mathematically computable for mean/median
- but not structurally stable enough to be a strong tolerance foundation
- a history gate may still be required to avoid a single-sample estimate dominating a decision

### Two prior gaps

- mathematically computable
- median equals average of the two values if even count
- still very sensitive to a single extreme value

### Three prior gaps

- median becomes the middle value and is more robust than mean
- mean still vulnerable to a single outlier

### Small history

- median is more robust in small samples
- mean is more exposed to outlier distortion
- trimmed mean introduces extra assumptions about removal level
- quantile requires a chosen level not justified by repo evidence

### Larger history

- greater stability for all statistics,
- but the behavior still differs substantially between mean and median under heavy-tail data

### Conclusion on small-sample behavior

The evidence supports a minimum-history requirement, but not a final number. It also supports the use of a robust central statistic in small-data conditions because the observed series is skewed and long-tailed.

## 9. Structural Test Results

Each candidate architecture was evaluated on the project’s structural requirements, not from a profitability lens.

### Deterministic replay

All candidate statistics are deterministic if:

- the input gap series is deterministic
- the ordering is canonical and prior-only
- the update step is explicit

### Append-only history

This is the preferred model for the project:

- the current swing may be appended after decision completion
- earlier historical states should not be retroactively reinterpreted

### No future leakage

The NO architecture is required. Any rule that includes current-swing gap information in its own evaluation is not causally valid.

### No self-reference

Median/mean/quantile are all valid as long as they use prior legal gaps, never the current gap.

### Historical immutability

Best preserved under append-only history.

### Sensitivity to one extreme gap

- median: low
- mean: high
- trimmed mean: moderate
- quantile: low to moderate depending on q

### Response to regime changes

- rolling history: adapts to recent regime change behavior
- expanding history: slower, can preserve old regime assumptions too long
- static tolerance: cannot naturally adapt to regime changes

### High/low asymmetry

The project evidence already indicates that highs and lows behave differently. This argues for direction-specific state and direction-specific tolerance estimation.

### Price-scale dependence

- static absolute: high
- static relative: depends on denominator choice
- mixed static: moderate but often dominated by one term
- rolling absolute: lowest dependence on arbitrary price scale due to its based-on-history nature

## 10. Complexity Audit

### Rolling median

Parameters:

- none beyond the history definition and minimum-history gate

State variables:

- the legal same-direction prior-gap sequence and a central-statistic function

New assumptions:

- the system assumes a robust central statistic is appropriate for a heavy-tailed gap process

Failure modes:

- if the window is too short or the history gate is poorly designed, the estimate may be unstable

Justification:

- moderate to strong, because the project data shows heavy tails and a central tendency

### Rolling mean

Parameters:

- none beyond history definition

State variables:

- prior same-direction gap sequence

New assumptions:

- the mean is an acceptable estimator despite skew and tail-heavy gaps

Failure modes:

- long-tail observations disproportionately affect the estimate

Justification:

- weaker than median under the actual project evidence

### Rolling trimmed mean

Parameters:

- trim fraction / removal count

State variables:

- prior same-direction gap sequence plus trim policy

New assumptions:

- explicit trimming rule and small-sample handling

Failure modes:

- additional arbitrary rules without project evidence

Justification:

- weak; complexity is higher than the evidence demands

### Rolling percentile / quantile

Parameters:

- quantile choice

State variables:

- prior same-direction gap sequence

New assumptions:

- a fixed quantile level is a meaningful tolerance target

Failure modes:

- arbitrary quantile choice may be just as hard to justify as a fixed A/r pair

Justification:

- possible but not strongly supported by current evidence

### Complexity conclusion

The simplest architecture that still has meaningful structural validity is the rolling prior-gap absolute tolerance using a robust central statistic. The data supports a robust, central-state estimator more strongly than a mean-driven or trimmed estimator. Median is the strongest current simple candidate, but it is not yet proven to be the unique final form.

## 11. Recommended Mathematical Form

The evidence justifies the general form:

- T_i = S( G_i )

where:

- G_i = [ g_k : k < i, g_k = |p_k - p_{k-1}|, p_k and p_{k-1} are legal prior same-direction eligible confirmed swings ]
- S is a statistic chosen from the prior-gap set

The strongest current candidate is:

- S = median

so the preferred candidate mathematical form is:

- T_i = median( G_i )

with the following constraints:

- G_i includes only prior legal same-direction absolute gaps
- the current swing is excluded from the set used to evaluate itself
- the legal gap series is ordered by eligibility time
- if the series is empty or insufficient under the project’s later minimum-history gate, the tolerance is insufficient-history and is not established

### Unresolved parameters

The evidence does not justify a frozen value for:

- fixed history length N if rolling count-based history is chosen
- time interval if time-based rolling history is chosen
- minimum number of observations required before tolerance is valid
- exact update timing of the tolerance state after the current swing decision
- exact fallback state when insufficient history exists

### Unresolved governance decisions

- whether the final history model is count-based or time-based
- whether median is finally accepted over another robust statistic
- whether a minimum-depth gate is required at this stage or left for later implementation

## 12. Alternatives Rejected or Deferred

### Mean

Rejected as the strongest default because the project’s gap data is heavy-tailed and the mean is more sensitive to extreme gaps. It remains mathematically valid but is less consistent with the actual data shape.

### Trimmed mean

Deferred because the project evidence does not justify a trim rule, and an extra trim fraction creates a new arbitrary design knob without a clear advantage.

### Percentile / quantile

Deferred because a specific quantile level is a governance choice, not an evidence-derived fact. It may be useful later, but it is not justified as the root form in the current evidence set.

### Expanding history with full historical gaps

Deferred because the architecture likely overweights stale early history. It remains an admissible baseline, but it has weaker evidence than rolling history.

### Static tolerance families

Rejected for the current root mathematical form because they do not adapt to the observed same-direction gap scale and they rely on extrinsic scale assumptions that are not frozen by project evidence.

## 13. Remaining Unknowns

The remaining unknowns are not weaknesses of the rolling median concept; they are unresolved design decisions that must be explicitly governed.

- exact window semantics
- minimum historical depth
- fallback when insufficient history exists
- whether the tolerance state is updated immediately after decision or in a separate stage
- whether the final implementation should prioritize median or another robust central statistic
- whether the project eventually prefers an expanding or rolling history

The evidence supports the mathematical direction, but not the final numerical contract.

## 14. Human Decisions Required

The following are genuine governance decisions that cannot be inferred from the current evidence alone:

1. Whether the final statistic is median, another robust statistic, or a quantile-based rule.
2. Whether the project wants a rolling history or an expanding history.
3. Whether a minimum-depth gate is required before a tolerance is considered valid.
4. Whether the tolerance state updates immediately after each decision or only after a separate post-decision pass.
5. Whether the project accepts the current best-supported candidate as the final design direction or keeps it as a research-only recommendation.

## 15. Dependency Impact

This analysis unlocks the following downstream design steps:

- membership rule using a causal tolerance estimate
- cluster creation trigger under a same-direction state machine
- zone center definition using the established same-direction observation stream
- geometry definition and upper/lower bound semantics
- overlap detection and overlap resolution logic

It does not by itself freeze those downstream components. It only clarifies the mathematical foundation of the tolerance estimator.

## 16. Governance Status

- Group A remains frozen
- 15-minute bar contract remains frozen
- Group B remains NOT FROZEN
- Phase 2 remains NOT STARTED
- no production code changed
- no tests changed
- no trading behavior changed
- no numerical tolerance parameter frozen

## Final conclusion

Does the evidence justify a specific mathematical form for rolling prior-gap absolute tolerance?

The evidence supports the general form:

- T_i = median( G_i )

as the strongest current mathematical candidate, where G_i is the legal prior same-direction absolute gap stream and the current swing is excluded from the tolerance history used to evaluate itself.

However, the evidence does not yet justify freezing this as the final Group B rule because the exact history model, minimum-depth gate, and update semantics remain unresolved. The evidence therefore supports a specific mathematical direction but not a final numerical or implementation decision.

In short:

- strong evidence supports the rolling prior-gap absolute architecture
- moderate evidence supports median as the simplest robust central statistic within that architecture
- insufficient evidence to freeze the final formula, final window, or final minimum-history threshold
