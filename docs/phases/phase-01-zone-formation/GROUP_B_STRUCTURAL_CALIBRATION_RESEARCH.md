## 1. Objective

PROVEN

This research task evaluates whether a simple structural calibration method can replace arbitrary static A/r selection while remaining deterministic, causal, replayable, simple, testable, resistant to obvious overfitting, and compatible with the Phase 1 simplicity principle.

PROVEN

This is not an optimization exercise. It is not a search for the parameter that produces the “best” clustering. It is a causal structure check to determine whether a defensible calibration statistic exists at all.

PROVEN

The current research posture is preserved:
- Group A is frozen and human-approved.
- Group B is not frozen.
- The current architectural conclusion is a research hypothesis only: B. KEEP MIXED FAMILY WITH STRUCTURAL CALIBRATION.
- No tolerance is frozen.
- No 15-minute timeframe is frozen.
- No OHLC reconstruction contract is frozen.
- No Phase 2 work begins.
- No production trading logic is modified.
- No profitability, P&L, or trade-performance metrics are used.
- No look-ahead is introduced.

## 2. Authoritative Inputs

PROVEN

The following sources were treated as authoritative for this research:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL.md](GROUP_B_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_CALIBRATION_AUDIT.md](GROUP_B_CALIBRATION_AUDIT.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
- [tools/research/research_15m_groupb_output.json](../../tools/research/research_15m_groupb_output.json)

PROVEN

The Group A swing definition remains frozen and unchanged. The research scope is limited to measuring structural spacing between eligible same-direction swings without redefining swing semantics.

## 3. Structural Distance Evidence

PROVEN

The previous report treated highs and lows as a combined same-direction series. That is a methodological error. Same-direction calibration must not mix swing highs and swing lows into one spacing sequence because the sequence can contain:

high → low → high → low

This is mixed-direction data, not same-direction data. It may be useful as descriptive context, but it is not evidence for same-direction structural calibration.

### Methodological Correction

PROVEN

The corrected evidence was recomputed separately for:
- swing highs
- swing lows

PROVEN

The corrected interpretation is:
1. Highs and lows are independent same-direction streams under the frozen Group A semantics.
2. A combined result may be retained only as mixed-direction descriptive analysis and must not be used as evidence for same-direction calibration.
3. The calibrated candidate must be evaluated separately for each direction unless a documented, direction-neutral rule is explicitly adopted.
4. The rolling-calibration semantics must distinguish whether the statistic uses only prior observations or includes the current swing itself.

PROVEN

For high/low-only evidence:

- swing highs: count = 78; median absolute gap = 33.78; p90 absolute gap = 553.87; p95 absolute gap = 1532.47; median relative gap = 0.00354; p90 relative gap = 0.06728
- swing lows: count = 68; median absolute gap = 35.85; p90 absolute gap = 589.51; p95 absolute gap = 1781.97; median relative gap = 0.00420; p90 relative gap = 0.07183

PROVEN

The central pattern is consistent across both directions:
- a small median gap cluster exists
- the p90 and p95 values are much larger, indicating a long tail
- the relative spacing remains in the same overall order of magnitude for both directions

EXPERIMENTAL EVIDENCE

This supports the limited statement that same-direction swing spacing contains observable structure. It does not support freezing a final numeric tolerance.

PROVEN

The previous combined result is not discarded as a meaningless artifact, but it is reclassified as mixed-direction descriptive analysis rather than same-direction calibration evidence.

## 4. Candidate Calibration Methods

PROPOSED

Candidate A — fixed statistic derived from historical/research distribution
- required inputs: same-direction swing gaps from historical research bars
- calculation: choose a fixed statistic such as median, p90, or p95 of prior same-direction distances
- state required: fixed constant selected offline, or no state if treated as a predeclared parameter
- when available: after the historical sample is available
- zone creation time: yes, if fixed before replay begins
- future information: yes if derived from the full historical sample after the fact; therefore it is a research descriptive statistic unless predeclared before runtime
- determinism: yes
- replayability: yes
- implementation complexity: low
- overfitting risk: moderate if derived from a narrow sample and then treated as a final production constant

PROPOSED

Candidate B — rolling/causal median of recent same-direction swing distances
- required inputs: recent same-direction gap history only
- calculation: tolerance_i = median(gaps_known_before_i)
- state required: rolling window of prior same-direction gaps
- when available: once at least one prior same-direction gap exists; in practice, after the second eligible swing of that direction is available
- zone creation time: yes, if every value used is available before the current swing becomes eligible
- future information: no
- determinism: yes
- replayability: yes
- implementation complexity: low
- overfitting risk: low to moderate

PROPOSED

Candidate C — rolling/causal robust percentile of recent same-direction swing distances
- required inputs: recent same-direction gap history only
- calculation: tolerance_i = p90(gaps_known_before_i) or p95(gaps_known_before_i)
- state required: rolling window of prior same-direction gaps
- when available: once the history is long enough to support the chosen percentile statistic
- zone creation time: yes, if computed from prior observations only
- future information: no
- determinism: yes
- replayability: yes
- implementation complexity: low to moderate
- overfitting risk: moderate

PROPOSED

Candidate D — simple price-normalized structural distance
- required inputs: recent relative gaps and current price level
- calculation: tolerance_i = k × recent_relative_gap_stat × current_price
- state required: prior relative-gap statistic and current price reference
- when available: after prior same-direction observations exist
- zone creation time: yes, if calculated from prior observations only
- future information: no
- determinism: yes
- replayability: yes
- implementation complexity: low
- overfitting risk: moderate unless k is fixed and the normalization remains explicit

PROVEN

These are the only simple candidates supported by the current evidence. They remain simpler than ATR or volatility-derived calibration and do not require machine learning or hidden regime logic.

## 5. Causality Analysis

PROVEN

For every candidate, the relevant test is this:

“If a zone is created at time T, can the tolerance used for that zone be calculated using information available at or before T?”

PROVEN

This must be defined explicitly for the rolling methods:

A. PREVIOUS-OBSERVATIONS-ONLY
- tolerance_i is calculated using only same-direction gaps fully known before swing i becomes eligible
- this is the preferred production interpretation
- this excludes the gap ending at the current swing unless the current swing is explicitly part of the prior history and already known at T

B. CURRENT-SWING-INCLUSIVE
- tolerance_i may include the gap associated with the current swing itself
- this is still causal only if the current swing is already observed and eligible at the moment the tolerance is used
- it is not a future-aware method, but it is more aggressive than the previous-observations-only interpretation

PROVEN

Under the frozen Group A timing rules, the preferred production approach is A. PREVIOUS-OBSERVATIONS-ONLY. This is more conservative and matches the causal requirement more directly. A current-swing-inclusive rule may be used for research, but it should be reported as such and not treated as the stronger production interpretation.

PROVEN

Candidate A is a research descriptive statistic when computed from the full sample after the fact. It is not automatically causal for production.

PROVEN

Candidate B, when interpreted as previous-observations-only, is causal for a zone created at time T because the statistic can be computed from prior eligible same-direction swings and prior gaps only.

PROVEN

Candidate C is causal when calculated from a rolling history ending before time T.

PROVEN

Candidate D is causal when the relative-gap statistic and price reference are both based on information available at or before T.

PROVEN

The critical distinction is therefore not whether a statistic is “rolling”, but whether it is calculated from prior observations only or from the current swing itself.

## 6. Chronological Behavior

EXPERIMENTAL EVIDENCE

The corrected chronological causal check used previous-observations-only rolling gaps, and the statistic was computed only from gaps that existed before each new swing became eligible.

PROVEN

For a previous-observations-only rolling method:
- the statistic is first defined when at least one prior same-direction gap exists
- under this rule, the relevant minimum requirement is effectively: the second eligible swing of a direction creates the earliest point at which a prior gap can be evaluated
- the statistic then updates progressively as more prior swings become eligible

EXPERIMENTAL EVIDENCE

Highs rolling median with window 12 ends at 33.30 and remains in the tens-of-EUR band over the observed history. Lows rolling median with window 12 ends at 27.24 and remains in the same order of magnitude, with no collapse toward zero and no explosive drift.

PROVEN

This supports the limited statement that the signal has a reasonable stable order of magnitude under causal prior-only use. It does not support claiming that a particular rolling median is the final correct tolerance.

## 7. Clustering Sanity Check

EXPERIMENTAL EVIDENCE

The corrected clustering sanity check was performed separately for highs and lows, using absolute-gap window tolerances derived from the observed structural distribution.

For highs:
- median absolute gap tolerance: 33.78
- p90 absolute gap tolerance: 553.87
- p95 absolute gap tolerance: 1532.47

For lows:
- median absolute gap tolerance: 35.85
- p90 absolute gap tolerance: 589.51
- p95 absolute gap tolerance: 1781.97

PROVEN

These values show the same trade-off previously identified, but without the invalid mixed-direction contamination:
- smaller tolerance values create many clusters and fragmentation
- larger tolerance values create fewer clusters but increase the risk of obvious over-merging
- the correct structural question is whether a rule stays within the observed spacing distribution without collapsing into either extreme

PROVEN

Lower singleton percentage is not automatically better. Smaller cluster count is not automatically better. Wider clusters are not automatically better. The evidence is only relevant if it preserves a clear relationship to the same-direction spacing signal without obvious over-merging or obvious fragmentation.

## 8. Complexity Comparison

PROVEN

The comparison under the Phase 1 simplicity principle is:

1. static mixed A/r
- implementation complexity: low
- causal support: yes if fixed in advance
- structural insight: weak because the absolute floor often dominates the effective tolerance

2. simple causal structural calibration
- implementation complexity: low to moderate
- causal support: yes if based on prior observations only
- structural insight: moderate to strong because it tracks actual observed swing spacing

3. ATR/volatility-derived calibration
- implementation complexity: moderate
- causal support: yes
- structural insight: not yet justified by the present evidence
- additional state: yes

PROVEN

The corrected evidence does not justify adding ATR/volatility machinery before a simpler prior-observation-based structural rule is explored. Simple before complex remains the governing principle.

## 9. Evidence Classification

PROVEN
- same-direction swing spacing contains real structure in both swing highs and swing lows
- the median gap is small, while p90 and p95 gaps are much larger, indicating a long-tailed spacing distribution
- the evidence supports researching a causal tolerance derived from prior swing observations
- the previous mixed-direction combined result is invalid as same-direction calibration evidence

EXPERIMENTAL EVIDENCE
- previous-observations-only rolling median and rolling percentile values remain in a stable order of magnitude over the observed sequence
- the structural trade-off is between fragmentation and over-merging
- a small structural rule derived from prior gaps is more credible than an arbitrary static constant

PROPOSED
- a rolling median of prior same-direction gaps is a defensible research candidate
- a rolling robust percentile of prior same-direction gaps is also defensible
- a simple normalized version is plausible but requires explicit design and caution

UNKNOWN
- which exact window size is best in a broader replay set
- whether one rule generalizes across other assets or sampling windows
- whether the final production version should use median, percentile, or normalized-price scaling

REQUIRES HUMAN APPROVAL
- any decision to freeze a final calibration method
- any decision to freeze a final tolerance value
- any decision to move from research-only structural calibration to formal Group B freeze

## 10. Architectural Conclusion

PROVEN

The single final conclusion is:

B. STRUCTURAL CALIBRATION IS SUPPORTED AS A RESEARCH DIRECTION, BUT NO FINAL METHOD IS JUSTIFIED

PROVEN

This is the strongest evidence-supported conclusion under the corrected methodology. The evidence supports the following limited statement:

“Same-direction swing spacing contains enough observable structure to justify researching a causal tolerance derived from prior swing observations.”

PROVEN

The evidence does not justify the stronger claim that a rolling median is the correct final tolerance, and it does not justify freezing any tolerance or any calibration method.

## 11. Remaining Unknowns

UNKNOWN

The remaining unknowns are narrow and specific:
- which rolling statistic should be preferred under a full causal replay test
- what the minimum required history should be before a structural tolerance is defined reliably
- whether the chosen rule remains stable under different time windows or assets
- whether the final rule should be direction-specific or a shared calculation with directional normalization

PROPOSED

The next correct action is a narrow causal rule test using only prior same-direction observations, not a frozen parameter selection and not an implementation.

## 12. Governance Status

PROVEN

- Group A: FROZEN
- Group B: NOT FROZEN
- 15m timeframe: NOT FROZEN
- OHLC contract: NOT FROZEN
- exact tolerance: NOT FROZEN
- calibration method: NOT FROZEN
- Phase 2: NOT STARTED
- production behavior: UNCHANGED
- profitability optimization: NOT USED
- look-ahead: NOT INTRODUCED

PROVEN

This research remains a no-freeze, no-implementation, no-Phase-2 specification check.

## 13. Safety Check

PROVEN

The following safety conditions remain satisfied:

- Group A remains FROZEN.
- Group B remains NOT FROZEN.
- No exact tolerance was frozen.
- No calibration method was frozen.
- No timeframe was frozen.
- No OHLC contract was frozen.
- No production trading behavior changed.
- No Phase 2 work started.
- No profitability optimization was used.
- No look-ahead was introduced.

PROVEN

No production modules were modified. No executable trading logic was changed. The work remains a research-only structural calibration review under the governing Phase 1 constraints.

Final explicit governance status:
- Group A: FROZEN
- Group B: NOT FROZEN
- 15m timeframe: NOT FROZEN
- OHLC contract: NOT FROZEN
- exact tolerance: NOT FROZEN
- calibration method: NOT FROZEN unless conclusion C is genuinely supported
- Phase 2: NOT STARTED
- production behavior: UNCHANGED
- profitability optimization: NOT USED
- look-ahead: NOT INTRODUCED
