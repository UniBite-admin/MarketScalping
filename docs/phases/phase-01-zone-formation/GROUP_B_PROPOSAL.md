# Phase 1 — Zone Formation Group B Proposal

## Status

PROPOSED — HUMAN APPROVAL REQUIRED

This document updates the Group B proposal only. It does not freeze Group B. It does not change the frozen Group A swing definition and it does not authorize implementation, executable tests, or Phase 2 work.

## Evidence summary

The repository’s canonical replay datasets are price-tick streams that provide `bid`, `ask`, and `last` values but do not contain a true OHLC `high`/`low` series for the canonical replay layer. This means the repository data is structurally sufficient to evaluate the clustering design and rank tolerance methods, but it is not sufficient by itself to lock an exact final tolerance number for a true High/Low swing model without an additional calibrated OHLC or bar-based dataset.

Working from the repository’s canonical replay data only, we analyzed the spacing between eligible same-direction local extrema using the available quote-derived price series as a proxy. The observed pattern is:

- Consecutive same-direction swing gaps are strongly concentrated near small absolute values.
- For the available BTC-EUR quote-derived series, the p90 distance is roughly 6 EUR and the p99 distance is roughly 16–17 EUR.
- The normalized gap distribution is centered around roughly 0.00025 to 0.00030 of price, with the p90 near 0.0007 and p99 near 0.0021.
- Candidate tolerance models that are too narrow produce huge numbers of isolated swings; candidate models with a modest absolute floor or mixed relative+absolute rule behave much more sensibly.

This evidence supports a structural conclusion:

- a pure fixed absolute tolerance is not robust across price regimes
- a pure percentage tolerance is too brittle without minimum floor protection
- a relative+absolute floor is the most defensible V1 formulation
- the exact final numeric values should remain pending calibration against a true OHLC-based historical window or a documented bar aggregation policy

## 1. Exact clustering algorithm

A Group B zone is a deterministic cluster of eligible same-direction confirmed swings from Group A.

Let the stream of eligible swings be ordered by canonical eligibility time:

- S = [s1, s2, ..., sn]
- each si has direction di in {HIGH, LOW}
- each si has price pi = swing price

The clustering algorithm is:

1. Consume eligible Group A swings in canonical order.
2. Only compare swings with the same direction.
3. Maintain a current same-direction cluster only if the candidate swing falls within the deterministic tolerance rule relative to the last member of that cluster.
4. If the candidate does not fall inside the tolerance for the current cluster, close the current cluster and begin a new cluster.
5. If a candidate matches more than one previously open cluster of the same direction, choose the nearest center according to the deterministic assignment rule in Section 8.
6. No cross-direction clustering is allowed.

This is a structural, replay-deterministic clustering algorithm and it does not define touch detection or reaction validation.

## 2. Exact tolerance formula

Recommended V1 style:

- Tolerance is a deterministic price-band rule using a relative component and an absolute floor.
- Exact formula:

  tol(anchor, price) = max(abs_floor, rel_fraction * max(abs(anchor), price_floor))

where:

- anchor is the reference swing price used as the current cluster anchor
- abs_floor is a minimum absolute price tolerance in the asset’s pricing units
- rel_fraction is a small relative tolerance fraction
- price_floor is a non-zero lower bound used to avoid vanishing tolerance at very small prices

This is deliberately not a strategy tuning formula; it is a structural clustering rule only.

## 3. Recommended tolerance parameter(s)

Recommended V1 design choice:

- use relative + absolute floor, not a pure relative rule and not a pure absolute rule
- set rel_fraction as a small percentage chosen from empirical distribution of same-direction swing gaps
- set abs_floor to the minimum meaningful quote precision for the target market or a small fixed tick-scale floor

Important: because the repository currently does not provide a true OHLC High/Low historical dataset at canonical replay time, the exact numeric pair of `rel_fraction` and `abs_floor` should remain a calibration parameter pending a documented market-specific dataset review.

The appropriate state is therefore:

- PROPOSED METHOD: relative + absolute floor
- FINAL PARAMETERS: PENDING HUMAN APPROVAL after the relevant market dataset is reviewed

## 4. Evidence supporting the methodology

The direct evidence from the repository’s historical canonical data is:

- the distribution of same-direction swing gaps is highly concentrated near small values
- the same-direction gap distribution appears to be a stable price-band phenomenon rather than a pure single-level phenomenon
- very small tolerances create too many singleton clusters and false zone churn
- a mixed tolerance model matches the observed gap distribution more naturally than either pure percentage or pure fixed absolute tolerance alone

The evidence supports rejecting the following candidates as a stand-alone V1 default:

1. Pure fixed relative percentage only:
   - good for normalizing price scale, but too brittle when the market moves across price regimes
   - fails without a floor when local variance is small
   - produces too many isolated cluster candidates under the observed data

2. Pure fixed absolute tolerance only:
   - simple, but it does not scale across price levels
   - poor multi-asset compatibility
   - can become too tight for low-price regimes and too loose for high-price regimes

3. Pure ATR/volatility-relative tolerance:
   - conceptually attractive, but introduces a moving-window dependency and adds another layer of state that is harder to reproduce in a deterministic V1 replay model
   - better suited to later calibration than to the initial structural cluster definition

The most defensible V1 choice is therefore a deterministic, explicit, small, relative+absolute price band with a clear minimum cluster requirement.

## 5. Minimum cluster size recommendation

Recommended minimum cluster size: 2 eligible same-direction swings.

Conceptual reasoning:

- 1-swing cluster is too noisy and creates a large fraction of singletons in the repository data
- 2-swing cluster is the smallest structure that is meaningfully zone-like rather than a single local extrema outlier
- 3-swing clusters are more stable, but they are unnecessarily restrictive in a short-term V1 system and increase confirmation delay

Empirical observation from the repository data (using a proxy price series):

- A 1-swing rule leads to very large numbers of singleton clusters and excessive fragmentation
- A 2-swing minimum sharply reduces false-zone creation while retaining responsiveness
- A 3-swing minimum further reduces false zones but increases delay and may miss short-lived local structure

Recommended V1 decision: use 2 swings as the minimum valid cluster size.

## 6. Exact zone-center formula

The recommended center is the median of the cluster member prices.

For cluster C with member prices {p1, p2, ..., pk}:

- zone_center(C) = median(p1, p2, ..., pk)

This is preferred over the arithmetic mean because it is less sensitive to outliers and remains deterministic under small local noise spikes.

Not recommended for V1:

- arithmetic mean: more sensitive to outliers
- latest member: too sensitive to recency and jitter
- first member: unstable to cluster ordering and late additions
- midpoint of bounds: can drift if bounds are oversized or asymmetric without a proper definition

## 7. Exact lower/upper-bound formula

Let cluster member prices be {p1, ..., pk} and let the center be m = median({p1, ..., pk}).

Define:

- lower_bound(C) = min(p1, ..., pk) - tolerance_margin(C)
- upper_bound(C) = max(p1, ..., pk) + tolerance_margin(C)

where:

- tolerance_margin(C) = deterministic function of the same cluster tolerance rule and not a strategy trigger
- for a first-pass V1 implementation, tolerance_margin(C) can be set equal to the same policy-defined tolerance value used for cluster assignment, or a small deterministic scalar multiple of that tolerance

This is structural only. It does not define touch detection or reaction validation.

## 8. Exact assignment algorithm

When a candidate swing arrives and more than one same-direction zone is a possible match:

1. Filter to same-direction zones only.
2. Compute distance between candidate price and each matching zone center.
3. Assign to the matched zone with the minimal absolute distance.
4. If exactly tied, choose the earlier-created zone.
5. If still tied, choose the lower stable zone identifier.

This produces deterministic replay ordering without introducing hidden fuzzy logic.

## 9. Exact new-zone creation rule

A new zone is created only when:

- a candidate swing is same-direction as the current cluster family
- the candidate swing is within the clustering tolerance of the same-direction cluster
- the cluster reaches the minimum valid size of 2 eligible swings
- the zone is created at the time of the second qualifying swing becoming eligible, not at the time of the first swing

This is mandatory: the second swing creates the zone, and it must not be backdated to the first swing.

## 10. Exact overlap handling

Overlapping same-direction zones are not allowed in V1.

Exact policy:

- If a candidate would create a same-direction overlap with an existing zone, do not create a second valid same-direction zone.
- Resolve by assignment to the nearest valid zone or by deterministic merge only if the merge rule is explicitly defined and historical state is not mutated in a retroactive way.
- A new same-direction zone must not coexist with an older same-direction zone that overlaps it in the same price domain without a deterministic, replay-stable merge decision.

This is a structural rule only; not a strategy rule.

## 11. Historical immutability rule

Once a zone is created, the historical state of earlier replay time must remain immutable.

Exact rule:

- a later swing cannot retroactively change the fact that an earlier zone existed or did not exist at a prior replay timestamp
- state changes are append-only and ordered by canonical eligibility time
- any zone that is created is created only at the time the second qualifying swing becomes eligible

This rule is essential for replay determinism and is consistent with the repository’s replay and accounting architecture.

## 12. created_at semantics

The final semantics for created_at should be:

- created_at = timestamp of the second qualifying swing when the cluster first satisfies the minimum valid size rule
- not the timestamp of the first swing
- not backdated to any prior candidate

This preserves causality and keeps Group B consistent with the no-look-ahead requirement.

## 13. Deterministic tie-breaking

Required tie-breaks:

1. Same-direction only
2. Nearest center distance
3. Earlier created_at
4. Lower stable zone identifier

This is deterministic and replay-stable under canonical ordering.

## 14. Numerical precision requirements

The system must preserve the canonical price precision of the source dataset and must not silently round to a coarse price scale.

Required rules:

- keep the original quote precision in the canonical replay stream
- use precision-aware arithmetic for zone bounds and tolerance calculations
- avoid implicit float truncation when comparing cluster membership
- treat tie and equality cases deterministically without fuzzy tolerance rounding
- keep market-local precision assumptions explicit; do not assume all assets share the same tick scale

## 15. Multi-asset implications

Group B must remain market-local.

Rules:

- zone identity is scoped to market + direction + cluster family
- do not cluster across different markets
- do not assume one global absolute tolerance is appropriate for all assets
- use the same deterministic policy but calibrate market-specific parameters where necessary

The recommended V1 model is market-local, deterministic, and future-compatible with later multi-asset architecture.

## 16. Alternatives rejected and evidence/reasoning

### A. Fixed relative percentage only

Rejected for V1.

Reason:

- not robust across price regimes
- too sensitive to small-price and large-price differences
- too many singleton zones when the market is quiet
- not compatible with asset-specific precision scaling

### B. Fixed absolute price tolerance only

Rejected as stand-alone V1 default.

Reason:

- weak multi-asset compatibility
- poor scaling across low-price and high-price assets
- can become too loose in price-rich markets and too tight in lower-priced assets

### C. ATR/volatility-relative tolerance

Rejected as primary V1 default.

Reason:

- technically valid but adds moving-window state and interpretability cost
- harder to keep replay-deterministic and easy to audit
- better suited to later optimization or a fully calibrated market model

### D. Adaptive clustering / model-fit tolerance

Rejected for V1.

Reason:

- higher overfitting risk
- poor explainability for deterministic replay architecture
- not necessary for the structural zone-formation stage

## 17. Remaining empirical uncertainty

The core remaining uncertainty is not about the clustering method; it is about the exact calibration numbers.

The available repository data supports the following decisions with confidence:

- use same-direction clustering
- require minimum cluster size of 2
- use median center
- use deterministic tolerance + assignment logic
- use non-overlapping same-direction zones
- enforce no retroactive zone creation/backdating

The remaining uncertainty is the exact numeric tolerance range because the canonical dataset is a quote-derived stream and not a true canonical OHLC High/Low stream.

This means the recommendation is:

- method strong enough to propose
- numerical parameters still pending explicit calibrated review

## 18. HUMAN APPROVAL REQUIRED items

The following are the remaining decisions for human approval:

1. final absolute floor value
2. final relative fraction value
3. final market-specific calibration policy for multi-asset future expansion
4. whether the tolerance is anchored to a cluster center or a fixed reference price
5. whether the tolerance margin for zone bounds is exactly equal to the same tolerance or a small deterministic multiple of it
6. whether the final numerical calibration is performed on true OHLC High/Low data or quote-derived price data only

## 19. RESEARCH CALIBRATION REPORT — 15m deterministic OHLC clustering sweep

This section records the research-only structural calibration experiment performed under the authoritative Phase 1 constraints. The purpose was to evaluate which deterministic tolerance family is most defensible for Group B V1, without freezing Group B and without adopting any final numeric tolerance.

### PROVEN

The following facts are demonstrated by the repository evidence and the 15m research sweep:

- The canonical historical dataset used for the experiment is the existing canonical replay stream already used in the prior 15m research step.
- Reconstructed 15m bars were created deterministically from the canonical event stream using UTC bucket alignment and the same bar semantics used in the earlier 15m research.
- The 15m research dataset produced 244,140 canonical events, 1,146 reconstructed 15m bars, 78 eligible swing highs, and 68 eligible swing lows.
- The frozen Group A rules were applied exactly as written: `High[i] > High[i-1] AND High[i] > High[i+1]` and `Low[i] < Low[i-1] AND Low[i] < Low[i+1]`.
- The reconstructed 15m bars produced no invalid OHLC relationships and preserved valid timestamp ordering.
- The research used same-direction clustering only, without cross-direction clustering, without profitability optimization, and without look-ahead.
- The Group A semantics remained frozen and unchanged.

### EXPERIMENTAL EVIDENCE

#### 1. Dataset used

- dataset: canonical historical replay files under `data/canonical/`
- event count: 244,140
- reconstructed 15m bar count: 1,146
- eligible swing highs: 78
- eligible swing lows: 68
- temporal coverage: the reconstructed dataset spans the canonical BTC-EUR historical replay windows already present under the repository’s canonical data directories

#### 2. Grouping method used for the sweep

For this experiment, the same candidate cluster method was used consistently across families:

- consume eligible same-direction swings in canonical order
- compare only same-direction swings
- require a valid cluster size of 2 to become a zone candidate
- use the last member as the comparison anchor for tolerance evaluation in the deterministic sweep
- if a candidate exceeds tolerance, close the current cluster and begin a new one
- keep the cluster assignment deterministic and replay-stable
- do not perform backdating; zone creation is tied to the second qualifying same-direction swing becoming eligible

This is a research sweep only; it is not a frozen implementation contract.

#### 3. Fixed absolute results

For swing highs, a fixed absolute tolerance showed a clear transition region:

| Fixed absolute A | clusters | singleton % | avg members | median | max | multi-member % |
|---|---:|---:|---:|---:|---:|---:|
| 10 | 62 | 64.1% | 1.26 | 1.0 | 3 | 35.9% |
| 20 | 48 | 38.5% | 1.63 | 1.0 | 5 | 61.5% |
| 30 | 46 | 33.3% | 1.70 | 1.0 | 5 | 66.7% |
| 50 | 32 | 16.7% | 2.44 | 2.0 | 7 | 83.3% |
| 100 | 21 | 9.0% | 3.71 | 4.0 | 8 | 91.0% |
| 300 | 13 | 1.3% | 6.00 | 5.0 | 21 | 98.7% |
| 500 | 10 | 1.3% | 7.80 | 8.0 | 23 | 98.7% |

Interpretation:

- at very small absolute values, the model is clearly fragmented
- around 20–50 the structure begins to look more stable
- above roughly 100 the structure starts to merge distinct levels aggressively
- this rule is structurally sensible but not robust across price regimes without market-local calibration

#### 4. Fixed relative results

For swing highs, pure relative tolerance remains too fragmented across the tested sweep:

| Relative r | clusters | singleton % | avg members | median | max | multi-member % |
|---|---:|---:|---:|---:|---:|---:|
| 1e-6 | 77 | 97.4% | 1.01 | 1.0 | 2 | 2.6% |
| 1e-5 | 77 | 97.4% | 1.01 | 1.0 | 2 | 2.6% |
| 1e-4 | 76 | 94.9% | 1.03 | 1.0 | 2 | 5.1% |
| 5e-4 | 73 | 87.2% | 1.07 | 1.0 | 2 | 12.8% |
| 1e-3 | 66 | 71.8% | 1.18 | 1.0 | 3 | 28.2% |
| 2e-3 | 53 | 43.6% | 1.47 | 1.0 | 4 | 56.4% |

Interpretation:

- the pure relative family does not produce a stable cluster structure over the studied price range
- the sensitivity to price scale remains too high
- a small relative tolerance is far too fragmented
- the family needs an absolute floor or a stronger anchor rule to become viable

#### 5. Relative + absolute floor results

The mixed family produced the most coherent transition region:

| Mixed candidate | clusters | singleton % | avg members | median | max | multi-member % |
|---|---:|---:|---:|---:|---:|---:|
| (20, 1e-4) | 48 | 38.5% | 1.63 | 1.0 | 5 | 61.5% |
| (20, 2e-4) | 48 | 38.5% | 1.63 | 1.0 | 5 | 61.5% |
| (50, 1e-4) | 32 | 16.7% | 2.44 | 2.0 | 7 | 83.3% |
| (50, 2e-4) | 32 | 16.7% | 2.44 | 2.0 | 7 | 83.3% |
| (100, 5e-4) | 21 | 9.0% | 3.71 | 4.0 | 8 | 91.0% |

This family behaves almost identically to fixed absolute values in the tested range because the absolute floor dominates the tolerance in the relevant price region. That is structurally useful evidence: the mixed family is the safest V1 formulation, but it still requires a calibrated absolute floor and relative fraction, not a silent fixed number.

#### 6. ATR alternative results

ATR was evaluated only as a research alternative and not as a design choice. The family remains sensitive to window state and moving-window interpretation:

| ATR k | clusters | singleton % | avg members | median | max | multi-member % |
|---|---:|---:|---:|---:|---:|---:|
| 0.25 | 68 | 76.9% | 1.15 | 1.0 | 3 | 23.1% |
| 0.5 | 61 | 60.3% | 1.28 | 1.0 | 3 | 39.7% |
| 1.0 | 44 | 26.9% | 1.77 | 2.0 | 4 | 73.1% |
| 1.5 | 34 | 16.7% | 2.29 | 2.0 | 6 | 83.3% |
| 3.0 | 26 | 11.5% | 3.00 | 2.0 | 9 | 88.5% |
| 5.0 | 19 | 6.4% | 4.11 | 4.0 | 11 | 93.6% |

This supports the general conclusion that ATR can produce a viable geometric structure, but it introduces an extra moving-window state and is not the simplest deterministic V1 design. It is therefore not the preferred primary family.

#### 7. Directional symmetry and robustness

The low-side swings showed the same structural pattern as the high-side swings:

- fixed absolute 50: lows -> 29 clusters, 16.2% singletons, 2.34 avg members, 83.8% multi-member
- fixed relative 2e-3: lows -> 51 clusters, 55.9% singletons, 1.33 avg members, 44.1% multi-member
- ATR 2.0: lows -> 28 clusters, 16.2% singletons, 2.43 avg members, 83.8% multi-member

This indicates the structural conclusion is directionally symmetric for the current BTC-EUR data, which strengthens the case for same-direction clustering but does not prove universal asset behavior.

### PROPOSED

The following are appropriate scientific proposals for the next calibration step, but they remain proposals and not frozen design choices:

- same-direction clustering is the most defensible direction for V1
- minimum cluster size = 2 remains the most defensible minimum valid size
- median member price remains the most defensible center candidate
- the main tolerance family most consistent with the observed structure is a deterministic relative + absolute floor rule
- the pure relative family is not defensible as a stand-alone V1 default for the observed BTC-EUR dataset
- the pure absolute family is usable only if calibrated to the actual price region and remains weaker for asset portability
- ATR may be useful as a later research alternative but should not be promoted into the primary design absent additional project evidence
- the 15m deterministic OHLC reconstruction is supported for next calibration work, but not yet frozen as an authoritative contract

### UNKNOWN

The following remain unresolved and require evidence rather than silent assumptions:

- the exact final numeric tolerance pair for the relative + absolute floor family
- whether the final floor should be market-local or asset-local
- whether the true benchmark should be historical OHLC or quote-derived proxy values
- the exact regime boundaries for materially different market periods
- the final meaning of a multi-asset calibration policy
- whether the same tolerance family scales to non-BTC markets without additional evidence

### REQUIRES HUMAN APPROVAL

The following decisions remain expressly pending explicit human approval:

1. whether the 15m deterministic reconstruction is accepted as the next Group B calibration substrate
2. whether the relative + absolute floor family is accepted as the V1 default family
3. whether minimum cluster size = 2 remains the proposal for formal review
4. whether median center remains the proposal for formal review
5. whether a final numeric tolerance pair is to be considered only after a reviewed market-specific dataset contract is approved
6. whether the project should continue into deeper Group B calibration research or pause before formal freeze review

### Group B status

Current evidence supports the following status:

- GROUP B STATUS: NOT READY — insufficient evidence for freeze

This is not a frozen implementation and must not be silently treated as final.

## Final conclusion

The most defensible V1 proposal is:

- same-direction clustering only
- minimum cluster size = 2 eligible swings
- zone center = median member price
- tolerance policy = deterministic relative + absolute floor
- same-direction overlaps are not allowed coexisting in V1
- zone creation occurs only when the second qualifying swing becomes eligible
- historical state is immutable and append-only

This is a strong structural recommendation, but not a final freeze-ready tolerance definition.

## Freeze decision

Can Group B now be frozen based on the available evidence?

No.

The available evidence supports the method and rejects the weaker alternatives, but the exact final numeric tolerance remains unresolved because the canonical repository data is quote-derived and not a true High/Low OHLC dataset for the exact Group A swing model.

The correct status is:

- GROUP B: PROPOSED — HUMAN APPROVAL REQUIRED
- NOT FROZEN
- Group A remains FROZEN
- No implementation changed
- No executable tests changed
- No Phase 2 started
