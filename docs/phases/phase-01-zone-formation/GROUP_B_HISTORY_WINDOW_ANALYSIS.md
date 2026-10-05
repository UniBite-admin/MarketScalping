# Group B History Window Analysis

## Status

- Group B: NOT FROZEN
- research / architecture analysis only
- no production implementation
- no numerical tolerance parameter frozen
- no production behavior change
- no executable test modified

## 1. Objective

This document addresses the remaining open research question for the current Group B tolerance candidate:

> The strongest current tolerance architecture candidate is a causal rolling prior-gap absolute tolerance using the median:
>
> T_i = median(G_i)
>
> where G_i contains only legal prior same-direction absolute price gaps, and the current swing must not contribute to the tolerance used to evaluate itself.

That candidate remains a RESEARCH CANDIDATE, not a frozen decision.

The purpose of this analysis is not to optimize a strategy. It is to determine whether the evidence supports a defensible historical-memory architecture for G_i and a defensible minimum-history rule.

The question is therefore:

- should G_i be expanding, fixed-count rolling, or time-based rolling?
- when does G_i contain enough legal observations to support a tolerance?
- can the historical state be made causally safe and replay-stable without inventing arbitrary thresholds?

## 2. Authoritative Inputs

FROZEN / HUMAN APPROVED

- Group A swing definition remains frozen.
- 15-minute UTC-aligned closed-bar contract remains frozen.
- bar interval semantics remain `[bar_start, bar_end)`.
- event exactly at `bar_end` belongs to the next bar.
- closed bars are immutable.
- trailing / incomplete bars are excluded from finalized evaluation.
- final partial bar at dataset end is discarded.
- no look-ahead is allowed.

SUPPORTING RESEARCH EVIDENCE

- canonical dataset and research tooling already used in the Phase 1 Group B research
- same-direction high and low sequences are structurally distinct
- mixed-direction and mixed-head+low calibration is not valid for same-direction tolerance analysis
- same-direction gap distributions are long-tailed and direction-dependent
- rolling prior-gap tolerance remains the strongest current architecture candidate

## 3. Exact Gap-Series Definition

For each direction separately:

- HIGH sequence: H = [h_1, h_2, ..., h_n]
- LOW sequence: L = [l_1, l_2, ..., l_n]

where each element is a legal eligible confirmed swing according to the frozen Group A semantics and the frozen 15-minute bar contract.

For consecutive same-direction swings, define:

- g_i = |S_i - S_{i-1}|

where S_i is the price of the i-th eligible confirmed swing in that direction.

This is a legal absolute price gap measured from the same-direction swing series and does not mix highs and lows.

### What qualifies as S_i

A swing S_i is:

- a confirmed, eligible same-direction swing produced by the frozen Group A logic
- ordered in canonical replay order by eligibility time
- not a future swing
- not a partial or trailing bar artifact
- not a swing that depends on information not yet available under the frozen causal rule

### Ordering rule

Gaps are ordered by the eligibility time of the corresponding swing observations.

The order is therefore:

- canonical replay order
- eligibility-time ordering
- same-direction grouping only

### Why HIGH and LOW must remain separate

The existing evidence already shows that:

- the high and low gap distributions are materially different
- same-direction high/low behavior is not symmetric in a way that justifies a single common tolerance stream
- mixed high+low calibration is structurally invalid for same-direction tolerance calibration

Therefore, the legal gap series for the tolerance estimator is direction-specific:

- G_high = [g_high_1, g_high_2, ...]
- G_low = [g_low_1, g_low_2, ...]

### Why the current swing cannot contribute to its own tolerance

For swing S_i, the tolerance used to evaluate S_i must be computed from history available before S_i becomes eligible.

Therefore:

- g_i = |S_i - S_{i-1}| is NOT legal input to the tolerance used for S_i
- any future gap after S_i is also not legal for evaluating S_i
- the current swing’s own gap is excluded to preserve no look-ahead and to avoid circular self-reference

This is required by the project’s causal semantics and by the previously established research conclusions.

## 4. Dataset and Evidence Basis

This analysis uses the same canonical BTC-EUR dataset and the same 15-minute reconstructed bar research already used for the preceding Group B analysis.

The relevant evidence already established by prior research is:

- HIGH: count 78, median absolute gap ≈ 33.78, p90 ≈ 553.87, p95 ≈ 1532.47
- LOW: count 68, median absolute gap ≈ 35.85, p90 ≈ 589.51, p95 ≈ 1781.97
- the distributions are heavy-tailed and direction-dependent
- the median and tail values differ materially, which is consistent with a robust central statistic rather than a naïve mean-based estimate
- static A/r families were structurally usable but not uniquely justified
- a rolling prior-gap median remains the strongest structural candidate

These are descriptive statistics, not final decisions.

## 5. Expanding Median Analysis

### Definition

For swing S_i, define:

- T_i = median(all legal prior same-direction gaps available before S_i)

This is an expanding history estimator.

### Structure

The history grows as more legal same-direction swings become available.

### Causality

SUPPORTED

- it is causal if computed only from prior legal gaps
- the current swing must not be included

### No self-reference

SUPPORTED

- self-reference is avoided by definition

### Deterministic replay

SUPPORTED

- deterministic as long as the input stream and ordering are deterministic

### Append-only behavior

PARTIALLY SUPPORTED

- new later observations do not alter the legal prior set for already-evaluated swings, if the historical state is snapshot-based
- however, an expanding estimator naturally changes in descriptive value as new data arrives, which means the estimate used for earlier historical events may be stable only if snapshots are preserved

### Historical immutability

UNRESOLVED

- an expanding estimator can be recomputed later with more data, creating ambiguity between:
  - historical tolerance snapshot used at decision time
  - retrospective descriptive statistic after the fact

This distinction must remain explicit if the system is to remain causally sound.

### Regime adaptation

PARTIALLY SUPPORTED

- expanding history follows the overall long-run gap scale
- but it is slower to react to later regime changes because old observations are still included

### Outlier sensitivity

SUPPORTED (low to moderate for median)

- median is not strongly distorted by a few extreme gaps
- this is one reason it is structurally attractive in heavy-tailed distributions

### Sparse observations

SUPPORTED / UNRESOLVED

- mathematically defined from the first available prior gap onward
- but a very small sample may be statistically weak and should not produce a strong tolerance claim without a minimum-history gate

### High/Low asymmetry

SUPPORTED

- expanding median must be computed separately per direction because high and low histories differ materially

### Price-scale behavior

PARTIALLY SUPPORTED

- expanding median does not require a fixed arbitrary reference price
- but it still reflects the observed historical scale, which can be broad and regime-sensitive

### Implementation complexity

LOW

- minimal state: a same-direction legal gap sequence

### Assessment

Expanding median is structurally defensible as a candidate, but it has a known weakness:

- it can become inertial and retain stale historical information beyond what is relevant to the current regime

That is not a fatal flaw, but it is a design trade-off.

## 6. Fixed-Count Rolling Median Analysis

### Definition

For swing S_i:

- T_i = median(last W legal prior same-direction gaps)

where W is a research variable chosen from a small structural probe only.

### Structure

The history is bounded to the most recent W legal prior gaps.

### Causality

SUPPORTED

- if W is defined as a count of legal prior gaps only, then the calculation uses no future information
- the current swing must still be excluded from its own tolerance computation

### No self-reference

SUPPORTED

- the current gap is excluded by design

### Deterministic replay

SUPPORTED

- deterministic if W is fixed and the legal-gap sequence is ordered deterministically

### Append-only behavior

SUPPORTED

- a later observation does not affect the already-computed tolerance used for prior swings, provided snapshot semantics are preserved

### Historical immutability

SUPPORTED

- fixed-count rolling history is naturally compatible with historical snapshots because the state is bounded and can be defined as a window of prior legal observations

### Regime adaptation

SUPPORTED

- the window adapts more quickly to recent spacing characteristics than an expanding history

### Outlier sensitivity

SUPPORTED (low for median)

- a single extreme gap affects only the recent window, not the entire historical record

### Sparse observations

PARTIALLY SUPPORTED

- when observations are few, a bounded window may be mathematically defined but not statistically meaningful
- this points again to a minimum-history gate rather than a tuned W

### High/Low asymmetry

SUPPORTED

- each direction keeps its own bounded history

### Price-scale behavior

SUPPORTED

- it follows the recent same-direction scale rather than imposing a fixed assumption on the whole price span

### Complexity

MODERATE

- additional state: the bounded window and its update rule

### Assessment

Fixed-count rolling median is structurally attractive because it is:

- causal
- deterministic
- adaptive to recent same-direction structure
- naturally compatible with append-only historical snapshots

Its main unresolved issue is not whether it is good conceptually, but whether the project has any evidence to justify a specific W. The current evidence does not justify a final W.

## 7. Time-Based Rolling Median Analysis

### Definition

For swing S_i:

- T_i = median(prior same-direction legal gaps whose observation times fall within a fixed time window)

### Structural defensibility

This architecture is only defensible if the project evidence supports a meaningful time-based regime notion.

### Existing evidence basis

The current project evidence does not justify introducing a new time-window semantics as a necessary requirement for the tolerance architecture.

The repository evidence supports:

- same-direction legal gaps
- eligibility-time ordering
- historical causal state

It does not support a frozen project-specific time interval as a required tolerance mechanism.

### Causality

SUPPORTED in principle

- it can be causal if it uses only prior legal gaps within the time interval

### Determinism

SUPPORTED in principle

- if the time interval boundary rules are completely specified

### Complexity

HIGHER THAN REQUIRED

- introduces time-window boundaries and boundary semantics that the project has not yet justified

### Evidence assessment

REJECTED / UNDER-JUSTIFIED

The current evidence does not demonstrate a structural advantage of time-based rolling semantics over fixed-count rolling semantics for the Phase 1 Group B tolerance architecture.

Therefore:

- time-based rolling median is not rejected as mathematically impossible
- it is rejected as currently under-justified for the Phase 1 research question
- the project should not invent a time interval before evidence shows it is needed

## 8. Minimum-History Analysis

The project must explicitly decide what to do when there is not enough legal prior gap history.

### Case A — 0 prior gaps

- mathematically: tolerance cannot be computed from prior same-direction gaps
- status: insufficient history
- conclusion: no tolerance established

### Case B — 1 prior gap

- mathematically defined for median and mean
- structurally weak because one prior gap is an extremely small sample
- high risk of unstable discrimination
- conclusion: a tolerance is technically defined, but not structurally strong enough to be treated as a meaningful default

### Case C — 2 prior gaps

- mathematically defined
- median is the average of the two values if even count
- still sensitive to a single extreme gap
- can be unstable

### Case D — 3 prior gaps

- median becomes a robust central value
- mean remains vulnerable to outlier distortion
- more stable than 1 or 2, but still minimal evidence

### Case E — sufficient history

- once enough legal prior gaps exist, robust central-statistic behavior becomes more meaningful
- this is the point where the tolerance begins to contain information beyond a single local condition

### Minimum-history conclusion

UNRESOLVED

The current evidence does not justify a specific minimum such as 3, 5, 10, or 20. The project evidence supports only this principle:

- 0 prior legal gaps ⇒ insufficient history
- very small history ⇒ mathematically defined but structurally weak
- minimum-history requirement is necessary in principle, but the exact threshold is not justified by the data alone

This is not a freeze decision. It is a research conclusion that a minimum-history gate is necessary but not yet numerically specified.

## 9. Small-Sample Behavior

The earliest observations are important because they determine whether the system can safely produce a valid tolerance in the online replay stream.

### First eligible same-direction swing

- no prior gap exists
- tolerance not established
- must remain insufficient history

### Second eligible same-direction swing

- one prior gap exists
- tolerance can be defined mathematically
- but it is not robust enough to be treated as a stable historical tolerance unless the system intentionally accepts a minimal-sample estimate

### Third eligible same-direction swing

- two prior gaps exist
- median is defined but sensitive to the exact two-gap sample

### Fourth eligible same-direction swing

- three prior gaps exist
- the median becomes more stable and more structure-aware than the mean

### Summary

The evidence supports the following:

- median is more robust than mean in the earliest stages
- a minimum-history gate is conceptually necessary
- the exact threshold is not yet justified by project evidence

Therefore:

- small-sample behavior is a design requirement
- the minimum-history threshold remains unresolved

## 10. Historical Immutability Analysis

### Critical test

Suppose swing S_i is evaluated using history H_i.

Later swings S_{i+1}, S_{i+2}, ... arrive.

Can any of those later observations change T_i?

### Expanding median

YES, in a descriptive sense

- later observations can change the full historical gap set and thus change the expanding median if it is recomputed retrospectively
- this is not automatically invalid, but it must be separated from the historical snapshot used by a previously evaluated swing

### Fixed-count rolling median

YES, if the window definition is interpreted as a retrospective recomputation of the most recent W gaps applied to earlier evaluations

- but the rule can be made historical-snapshot-safe by defining that earlier evaluations use a snapshot of the legal gap history at the time of decision

### Time-based rolling median

YES, similarly

- if later gaps enter the time window, the retrospective estimate can change
- this requires explicit snapshot semantics to ensure a historical decision remains not retroactively altered

### Distinction: historical snapshot vs retrospective descriptive statistic

This distinction is crucial.

- historical snapshot: the tolerance used for a past decision is tied to the legal prior gap history as it existed at that decision time
- retrospective descriptive statistic: a later re-run over the full dataset gives a different number for the same past decision

The project’s requirement is causal and replay-safe, so historical snapshots are the preferred semantics.

Therefore, any architecture that implies earlier decisions can be retroactively changed by later observations must either:

- be explicitly treated as a descriptive post-hoc statistic, not a causal policy
- or be ruled out as structurally unsafe for a frozen decision pipeline

## 11. Regime Adaptation Analysis

The dataset shows that the same-direction spacing process is not static.

The evidence supports:

- long-tail gap distribution
- materially different high and low behavior
- changing absolute and relative gap scale over time
- stronger central structure near lower gaps with sparse but much larger outliers

### Expanding history

PARTIALLY SUPPORTED

- it does not react quickly to new conditions because older observations remain included
- it may become inertial and fail to reflect a later regime shift

### Fixed-count rolling history

SUPPORTED

- it adapts more quickly to recent same-direction gap behavior
- it is a better fit to a time-varying process, provided the window is not chosen arbitrarily and the minimum-history gate is enforced

### Time-based rolling history

UNRESOLVED / UNDER-JUSTIFIED

- the evidence does not support a time-based adaptive rule as a necessary requirement
- without a project-defined time interval, this is a hidden assumption, not evidence-based design

## 12. High/Low Asymmetry

The research evidence strongly supports keeping the high and low sequences separate.

This matters because:

- high gap sequences behave differently from low gap sequences
- the same tolerance semantics need not be identical across direction
- a shared or mixed high+low history would blur the actual structure

Therefore, for each direction:

- maintain its own legal gap stream
- compute its own tolerance estimate
- evaluate same-direction membership only

This is a supported design principle.

## 13. Complexity Comparison

| Architecture | Parameters | State | Assumptions | Structural fit | Evidence support |
| --- | --- | --- | --- | --- | --- |
| Expanding median | low | low to moderate | low | moderate | supported |
| Fixed-count rolling median | medium (W) | moderate | moderate | strong | supported as research candidate |
| Time-based rolling median | high (interval + boundary semantics) | moderate to high | high | unresolved | under-justified |

The project’s governing rule remains:

- simple before complex
- causal before adaptive
- deterministic before nuanced

The current evidence does not justify time-based rolling semantics. Fixed-count rolling is the simplest bounded rolling architecture that still adapts to recent same-direction spacing. Expanding median is simpler but less responsive to regime changes.

## 14. Decision Classification

| Decision | Status | Evidence | Remaining uncertainty |
| --- | --- | --- | --- |
| Expanding vs rolling | PARTIALLY SUPPORTED | same-direction gap process is time-varying and long-tailed | final preference depends on tolerance update semantics and minimum-history gate |
| Expanding median | SUPPORTED | robust to outliers and causally valid | can become stale under changing regimes |
| Fixed-count rolling median | SUPPORTED | adapts to recent gap structure and remains causal | exact W remains unresolved |
| Time-based rolling median | REJECTED / UNDER-JUSTIFIED | no project evidence for a required time interval | boundary semantics and need are unresolved |
| Median historical memory | SUPPORTED | median is more robust than mean with tail-heavy gap data | exact rolling vs expanding choice unresolved |
| Minimum-history gate | SUPPORTED in principle | very small sample sizes are structurally weak | exact threshold unresolved |
| Small-sample behavior | SUPPORTED | 0/1/2/3 prior gaps produce weak or undefined tolerance conditions | exact minimum threshold unresolved |
| Historical snapshot semantics | SUPPORTED | causal replay requires immutable historical decisions | must be explicitly enforced in implementation |

## 15. Remaining Unresolved Decisions

The following remain unresolved and must be left unresolved unless the project explicitly decides otherwise:

- exact fixed-count W for rolling median
- exact minimum-history threshold for a valid tolerance
- exact tolerance state update timing after each decision
- exact historical snapshot semantics
- whether the final architecture should be expanding or bounded rolling
- whether the project eventually prefers a different robust statistic than median

## 16. Recommended Next Research Step

The next research step should be narrowly focused on the causal history semantics, not a broad parameter sweep.

Recommended next step:

- define the causal legal-gap set precisely
- define the append-only historical snapshot semantics precisely
- test only a very small number of bounded rolling windows and expanding-history variants in a purely descriptive, not optimization-oriented, way
- leave the exact W and minimum-history threshold unresolved until the causal semantics are explicitly accepted

This is consistent with the project’s governance pattern: DATA → TEST → VALIDATE → AUTOMATE → CONTROL → SCALE.

## 17. Governance Status

- Group A: FROZEN / HUMAN APPROVED
- 15-minute bar contract: FROZEN / HUMAN APPROVED
- Group B: NOT FROZEN
- Phase 2: NOT STARTED
- Production implementation: UNCHANGED
- Production tests: UNCHANGED
- Numerical tolerance parameters: NOT FROZEN

## Final Conclusion

The evidence supports a narrow but important conclusion:

> A causal prior-gap median is a reasonable architecture, but the historical-memory semantics remain unresolved.

More specifically:

- expanding median is structurally defensible but may become too inertial under changing regime conditions
- fixed-count rolling median is structurally stronger as a bounded, causal, adaptable history mechanism
- time-based rolling median is not currently justified by the project evidence and should not be invented without explicit need
- the exact minimum-history threshold remains unresolved
- the exact window size remains unresolved
- the exact historical snapshot semantics remain unresolved

The current evidence does not justify forcing a final choice among expanding and rolling history. It justifies the claim that the architecture should remain a causal prior-gap median framework while the historical-memory semantics remain intentionally unresolved.
