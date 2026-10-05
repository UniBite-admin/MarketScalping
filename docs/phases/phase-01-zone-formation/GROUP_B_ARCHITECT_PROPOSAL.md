# Phase 1 — Group B Architecture Proposal

## 1. Executive conclusion

ARCHITECT RESULT: READY FOR HUMAN REVIEW

This proposal is a structural Group B design for review only. It is not a frozen Group B rule and it does not begin implementation or Phase 2.

The proposal is intentionally conservative. It is based on the frozen Phase 1 inputs and on the repository’s research evidence, but it does not convert that evidence into a frozen implementation choice.

The recommended architecture is:
- same-direction-only zone membership
- evaluate each eligible confirmed swing only against zones of the same direction
- use a causal prior-observations-only rolling tolerance derived from prior same-direction gaps
- use median as the zone center
- represent each zone as center plus member-span geometry, with the explicit span retained as a derived historical property
- reject retroactive mutation and merge history after creation
- define creation only when a same-direction cluster reaches the minimum evidence threshold
- require deterministic tie-breaks by same-direction, nearest center, then earliest creation timestamp, then stable identifier

This is a proposed architecture, not a frozen specification.

## 2. Frozen inputs

FROZEN

The following are already frozen human-approved Phase 1 decisions and remain governing inputs:

- Group A swing semantics remain frozen.
- 15-minute timeframe remains frozen.
- Deterministic UTC-aligned `[bar_start, bar_end)` bar contract remains frozen.
- Event exactly at `bar_end` belongs to the next bar.
- Closed bars are immutable.
- Trailing/incomplete bars are excluded from finalized Group A and Group B evaluation.
- Dataset-end partial bar is discarded.
- Group A observation / confirmation / eligibility causality remains unchanged.

These inputs are authoritative. They are not reopened by this proposal.

## 3. Evidence reviewed

RESEARCH-SUPPORTED

The proposal is grounded in the repository evidence and the existing research artifacts:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL.md](GROUP_B_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_CALIBRATION_AUDIT.md](GROUP_B_CALIBRATION_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_STRUCTURAL_CALIBRATION_RESEARCH.md](GROUP_B_STRUCTURAL_CALIBRATION_RESEARCH.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/BAR_CONTRACT_DECISION.md](BAR_CONTRACT_DECISION.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
- canonical BTC-EUR research data and metadata under [data/canonical](../../data/canonical)

The repo evidence supports the following structural observations:

- eligible swing highs: 78
- eligible swing lows: 68
- same-direction swing spacing contains a pronounced small central cluster with a large long tail
- high and low behavior are not identical and must be analyzed separately
- mixed high+low spacing is descriptive only and is not valid same-direction calibration evidence
- static mixed A/r values can become inactive and therefore do not represent robust evidence of a practical tolerance model
- a causal tolerance derived from prior same-direction observations is structurally more defensible than a fixed static pair

## 4. Candidate tolerance comparison

PROPOSED / RESEARCH-SUPPORTED / UNKNOWN

### 4.1 Fixed absolute tolerance

PROPOSED but weakly supported

- Determinism: strong
- Causality: strong
- Replayability: strong
- Sensitivity to price scale: poor
- Sensitivity to volatility: low, but not adaptive
- Parameter burden: low
- Overfitting risk: moderate if absolute value is chosen from a narrow sample
- Multi-asset portability: weak without market-specific scaling
- Historical immutability: strong
- Compatibility with frozen architecture: acceptable but not robust

Assessment:
- Simple to reason about.
- Not technically wrong.
- Weak as a general cross-range rule because a fixed price band does not scale with market level.
- Not recommended as the primary Group B design unless the project explicitly accepts market-specific fixed price bands.

### 4.2 Fixed relative tolerance

PROPOSED but weakly supported

- Determinism: strong
- Causality: strong
- Replayability: strong
- Sensitivity to price scale: high, but not controlled by a floor
- Sensitivity to volatility: moderate
- Parameter burden: low
- Overfitting risk: moderate
- Multi-asset portability: poor without explicit scaling
- Historical immutability: strong
- Compatibility with frozen architecture: acceptable only with a floor or explicit normalization guard

Assessment:
- Useful as a conceptual component.
- Too brittle as a standalone rule because it can become vanishingly small at low price levels or too large at high price levels without an explicit floor.
- Not recommended as the sole architecture.

### 4.3 Mixed absolute + relative tolerance

RESEARCH-SUPPORTED but not frozen

The family is:

    distance <= max(A, r * reference_price)

The research shows that this family can be structurally workable, but it is often A-dominant over the actual BTC-EUR swing range. Many candidate A/r pairs display parameter inactivity rather than demonstrably meaningful response.

- Determinism: strong
- Causality: strong when parameters are predeclared and fixed
- Replayability: strong
- Sensitivity to price scale: better than absolute-only, but still weak if A dominates
- Sensitivity to volatility: low to moderate
- Parameter burden: low
- Overfitting risk: moderate
- Multi-asset portability: medium at best
- Historical immutability: strong
- Compatibility with frozen architecture: acceptable but not preferred because the parameter surface is often inactive rather than informative

Assessment:
- A credible research family, but not a preferred final architecture because the evidence does not justify a single stable static pair.
- The problem is not that the family is invalid; the problem is that it is often dominated by the absolute floor and therefore does not represent a robust structural calibration surface.

### 4.4 ATR-derived tolerance

PROPOSED but not preferred

- Determinism: possible
- Causality: possible if based on prior observations only
- Replayability: possible
- Sensitivity to price scale: moderate
- Sensitivity to volatility: high
- Parameter burden: high
- Overfitting risk: moderate to high
- Multi-asset portability: medium
- Historical immutability: strong if applied as snapshot-only state
- Compatibility with frozen architecture: lower because it adds additional state and more moving parts than required for Phase 1

Assessment:
- More complex than required.
- Not the right Phase 1 design unless a strong repo-backed need exists.
- Better suited to later strategy calibration stages than to the initial structural Zone Formation design.

### 4.5 Prior-observation-derived structural tolerance

RECOMMENDED PROPOSAL

Preferred design:
- maintain separate same-direction histories for swing highs and swing lows
- compute a tolerance from the set of prior same-direction absolute gaps observed before the current swing becomes eligible
- use the median of those prior gaps as the tolerance base for the next assignment / zone creation decision

This is the simplest causal tolerance model consistent with the repository evidence.

- Determinism: strong
- Causality: strong when based only on observations available before the current swing
- Replayability: strong
- Sensitivity to price scale: moderate; adapts to observed price-history structure without a hidden regime rule
- Sensitivity to volatility: moderate; reflects realized gaps rather than broad volatility assumptions
- Parameter burden: low
- Overfitting risk: lower than a static A/r pair if it remains a robust prior-gap statistic and not an overfit sample statistic
- Multi-asset portability: reasonable because it is local to the observed same-direction spacing and does not require explicit market-regime labels
- Historical immutability: strong if applied only to future decisions and not retroactively to earlier historical zones
- Compatibility with frozen architecture: strong, because it is simple, same-direction, and causal

Assessment:
- Most compatible with the repository evidence and the Phase 1 simplicity principle.
- It is not a final frozen tolerance value; it is a proposed architecture for human review.

### 4.6 Other materially simpler candidates

UNKNOWN / NOT RECOMMENDED

Other candidates are possible, but the repository evidence does not justify them sufficiently for a Phase 1 vote. This includes arbitrary percentile policies, market-regime labels, stronger adaptive volatility rules, and any rule that depends on future knowledge or the entire historical sample being available at time T.

## 5. Recommended membership model

PROPOSED

### 5.1 Operational rule

For each eligible confirmed swing at time t, evaluate it only against active zones of the same direction.

- high swings only join high/resistance zones
- low swings only join low/support zones
- cross-direction membership is not permitted

This is required because the research showed that mixed high+low spacing is not valid same-direction evidence.

### 5.2 Eligible zones

A zone is eligible for membership only if:
- it has the same direction as the new swing
- it was created at or before the current swing’s eligibility time
- it has not been closed by snapshot immutability semantics
- it remains active in the historical replay state

### 5.3 Distance reference

The distance for comparison is the absolute difference between the candidate swing price and the current zone center.

The reference is the zone center, not the last member price, not a future observation, and not an arbitrary market-wide anchor.

### 5.4 Multiple qualifying zones

If more than one same-direction zone qualifies:
- compute absolute distance from candidate price to each zone center
- choose the nearest qualifying center
- if there is a tie, apply the deterministic tie-break order below

### 5.5 Deterministic tie-break

Deterministic tie-break order:
1. same direction only
2. nearest center distance
3. earliest creation timestamp
4. stable zone identifier ascending

This ensures replay stability and avoids set-order randomness.

### 5.6 New zone creation

A new same-direction zone is created only when the following are true:
- there is at least one prior same-direction candidate already in the historical stream
- the current swing is eligible under the frozen Group A rules
- the new candidate is same-direction and not a retroactive backfill
- the current observation set provides enough historical evidence to establish a valid zone under the selected minimum cluster rule

The new zone does not backdate itself. The creation timestamp is the timestamp of the second qualifying swing or the earliest moment the minimum cluster requirement is first satisfied.

### 5.7 Minimum evidence before valid zone

The recommended minimum evidence is:
- at least 2 eligible same-direction swings in the same direction
- at least one prior same-direction gap available for the causal tolerance statistic

This is the smallest simple requirement that avoids a single-swing zone being treated as a stable zone.

## 6. Recommended tolerance model

RECOMMENDED PROPOSAL

The recommended tolerance family is:

- same-direction only
- prior-observations-only rolling median of same-direction absolute gaps
- direction-specific: highs use highs, lows use lows
- no mixed high+low calibration
- no future knowledge, no whole-sample tuning, no P&L-driven parameter selection

Formal expression:

- Let G_d = the ordered list of prior same-direction absolute gaps that are fully observed before the current candidate becomes eligible.
- Let tolerance_d = median(G_d)
- A candidate swing is assigned to a zone if the absolute price distance from the zone center is less than or equal to the current tolerance_d.

This is intentionally simple and returns to the evidence that:
- same-direction gaps have a strong central concentration
- larger long-tail gaps exist
- a rolling median is more robust than a fixed static A/r pair in a causal design

The rule is proposed, not frozen.

## 7. Causality contract

PROPOSED

### 7.1 Available historical observations

At time t, the project may use only:
- eligible confirmed swings with historical time <= t
- same-direction gaps fully known before the current swing is evaluated
- no future observation beyond the current event’s frozen Group A confirmation rule

### 7.2 Excluded observations

Excluded from the causal tolerance calculation:
- future swings
- mixed-direction swings
- unconfirmed Group A swings
- ineligible or boundary-invalid swings
- trailing/incomplete bars
- any event that is not available at the time of evaluation

### 7.3 Current swing inclusion

The current swing must not contribute to the tolerance used to classify itself.

This is the key causal rule:
- previous-observations-only is architecturally acceptable
- current-swing-inclusive is not the preferred production interpretation, because it creates circularity and weakens the clarity of the causal contract

### 7.4 Tolerance change over time

The tolerance may change over time as new prior same-direction gaps become available, but it can only change for future decisions.

### 7.5 Historical immutability

Once a zone has been created, later tolerance changes do not mutate its historical membership or geometry.

This preserves replay immutability and ensures that earlier historical decisions are frozen as snapshots.

## 8. Center definition

PROPOSED

Recommended center:
- median of the current zone member prices

Reasons:
- deterministic
- simple to compute
- less sensitive to outlier swings than a mean
- easier to explain than last-member or fixed-anchor choices
- stable under replay

Rejected simpler alternatives:
- mean: more sensitive to outliers and noise
- last-member price: recency bias and unstable under late membership updates
- fixed first-member anchor: introduces historical anchoring artifacts and is not robust under replay

## 9. Zone geometry

PROPOSED

The simplest explicit zone geometry is:
- center = median(member_prices)
- min_price = minimum member price
- max_price = maximum member price
- derived interval = [min_price, max_price]

This is a historical property and not a touch rule.

Consequences:
- geometry is derived from actual members, not a separate tolerance-type state
- membership remains determined by center distance and tolerance
- later Phase 2 touch logic can use this geometry without conflating it with the zone creation rule
- this keeps the design separate from later touch detection and avoids accidentally defining Phase 2 behavior in Phase 1

## 10. Overlap policy

PROPOSED

Recommended behavior:
- same-direction zones must not be created in a way that retroactively overlaps an existing active same-direction zone with the same historical snapshot semantics
- if a candidate would overlap an existing active same-direction zone, do not create a second same-direction zone at that time
- assign the candidate to the nearest same-direction active zone if it belongs under the existing tolerance rule
- if no active same-direction zone qualifies, then create a new zone only after the minimum evidence threshold is met

This is simpler than merge logic and avoids historical mutation.

Historical consequence:
- no retroactive merge
- no retroactive membership rewrite
- no hidden reordering of historical zone state

## 11. Minimum cluster requirement

PROPOSED

The evidence does not justify treating 2 as mathematically guaranteed. However, it is the smallest minimum cluster requirement that is structurally meaningful and consistent with the causal Phase 1 architecture.

Recommended minimum cluster requirement:
- minimum 2 eligible swings of the same direction

This remains a proposal only and not a frozen Group B rule.

Rationale:
- 1 swing is too weak to be treated as a stable zone
- 2 swings is the smallest nontrivial structure
- the research evidence does not justify a more complex threshold without additional formal calibration and review

## 12. Zone creation timing

PROPOSED

A new zone becomes observable/created at the moment the minimum cluster requirement is first satisfied in causal historical replay order.

Important constraints:
- never backdated
- never created using future observations
- creation time is the time of the later qualifying swing or the first moment the minimum cluster requirement is satisfied
- once created, the zone is inserted into historical state as a snapshot at that time

## 13. Historical immutability

PROPOSED

Once a zone exists at historical time t:
- its earlier membership cannot be changed by later swings
- its center and geometry cannot be retroactively rewritten
- later tolerance changes cannot retroactively alter historical zone membership
- later swings can only affect future zone creation and future assignment decisions
- historical state is append-only and snapshot-based

This is required to keep replay deterministic and to prevent hidden backfilling or future-causal mutation.

## 14. Deterministic tie-break rules

PROPOSED

Required ordering and tie-break rules:

1. Sort eligible swings by canonical eligibility time.
2. Split by direction: highs and lows are separate streams.
3. For a given direction, evaluate only active same-direction zones.
4. Choose nearest zone center by absolute price distance.
5. Resolve exact ties by earliest creation timestamp.
6. Resolve any remaining ties by stable zone identifier ascending.
7. Never rely on unordered collections or set iteration for final decisions.

This ensures deterministic replay and stable historical snapshots.

## 15. Multi-asset considerations

PROPOSED / UNKNOWN

The proposal is intentionally not BTC-EUR-specific in structure because it is direction-based, causal, and derived from observed same-direction spacing rather than from explicit market-regime labels.

However, the current evidence is only from BTC-EUR canonical research data. The architecture is portable in form, but not yet validated across multiple assets.

Therefore:
- multi-asset portability is a design strength of the approach
- multi-asset validation remains unknown and requires explicit later review
- no new asset-specific rule is justified in the current proposal

## 16. Research validation

RESEARCH-SUPPORTED

The existing research supports a limited architecture conclusion:
- same-direction gap structure exists
- a rolling prior-gap median is a feasible causal tolerance candidate
- high and low should be modeled separately
- mixed high+low spacing is not valid same-direction evidence
- fixed A/r static settings are often inactive rather than informative
- simple causal tolerance structures are more defensible than arbitrary static pairs

The research does not support a final exact parameter value, exact minimum cluster threshold beyond the general 2-swing proposal, or a final Group B freeze.

The evidence also does not support suppressing uncertainty by declaring a single “best” tolerance value.

## 17. Remaining uncertainties

UNKNOWN / HUMAN DECISION REQUIRED

The following items remain unresolved and therefore remain subject to human approval before any Group B freeze:

- exact final minimum cluster threshold beyond the proposed 2-swing minimum
- exact final tolerance statistic to be used for operational assignment, if any other than the proposed prior-gap median
- exact zone geometry representation if the project wants a stricter lower/upper bound than the center-plus-span representation
- exact overlap policy if the project decides to merge rather than reject or assign
- exact zone lifecycle rules beyond the creation and immutability principles proposed here
- whether this architecture remains acceptable across additional markets

## 18. Exact decisions still requiring human approval

HUMAN DECISION REQUIRED

The following decisions remain pending explicit human approval:

1. Whether the prior-observations-only rolling median of same-direction gaps is the preferred Group B tolerance model.
2. Whether minimum cluster size 2 is acceptable as the initial operational threshold.
3. Whether zone overlap should be rejected, assigned, or merged as an operational rule.
4. Whether the center should be median and the geometry should be center-plus-span.
5. Whether the proposed causal state model is acceptable without an explicit future-sample parameter calibration step.
6. Whether the project is comfortable leaving Group B in a proposed, not frozen, state while the architecture is reviewed.

## 19. Explicit statement that Group B is not frozen

GROUP B: NOT FROZEN

This proposal intentionally does not freeze Group B. It defines an architecture for review only.

The only frozen elements remain:
- Group A swing semantics
- 15-minute bar contract
- Group A causality timing

Everything else in Group B remains subject to explicit human review before freeze.
