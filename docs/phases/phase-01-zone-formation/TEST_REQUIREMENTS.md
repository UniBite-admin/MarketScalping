# Phase 1 — Zone Formation Test Requirements

## Status

FROZEN — HUMAN APPROVED

This document defines the required deterministic test categories for the frozen Phase 1 Group A swing definition. It does not create executable tests and does not modify the project’s test suite.

## Required deterministic test set

### A1 — normal swing high
- Input sequence contains a candle where high[i] is greater than both neighboring highs.
- Expected: one swing-high candidate observed at index i.

## Approved Group B tolerance-history test requirements

FROZEN — HUMAN APPROVED

The following design tests are required to validate the approved Group B tolerance-history semantics. These are documentation requirements only and do not modify production code or executable tests.

### B1 — zero prior legal gaps
- Input stream contains a candidate swing with no legal prior same-direction gap history.
- Expected: no tolerance is available and membership cannot be evaluated.

### B2 — one to four prior legal gaps
- Input stream contains a candidate swing with 1 to 4 prior legal same-direction gaps.
- Expected: the tolerance uses all available prior legal gaps.

### B3 — five or more prior legal gaps
- Input stream contains a candidate swing with at least 5 prior legal same-direction gaps.
- Expected: the tolerance uses the five most recent prior legal gaps, not all prior gaps.

### B4 — current-swing exclusion from its own tolerance history
- Input stream contains a candidate swing for which the current swing would otherwise appear in its own gap history.
- Expected: the current swing is excluded from the tolerance used to evaluate itself.

### B5 — HIGH and LOW separation
- Input stream contains both high-side and low-side swing sequences.
- Expected: each direction uses only its own legal prior same-direction gap history.

### B6 — canonical ordering and replay safety
- Input stream is replayed in canonical order under the frozen bar contract.
- Expected: the legal gap history is ordered by canonical replay / eligibility order and remains causally consistent.

### B7 — no time-based or relative normalization rule
- Input stream is evaluated under the approved Group B tolerance-history semantics.
- Expected: no time-based rolling window, ATR rule, relative-price transformation, or alternate statistic is introduced by the approved decision.

These requirements are intentionally narrow and bounded. They freeze only the approved tolerance-history semantics and do not freeze the broader Group B architecture.

### B8 — Candidate A center-statistic requirement

FROZEN — HUMAN APPROVED

The following design test is required to validate the approved Candidate A center-statistic decision:

- Candidate A center statistic = median(member prices)
- Expected: for any valid same-direction member set, the center value is the median of the member prices in the set.
- Scope: this requirement freezes only the center statistic. It does not freeze membership semantics, zone creation, zone lifecycle, or any other Group B root decision.

### B9 — Candidate A / D membership-rule requirement

FROZEN — HUMAN APPROVED

The following design test is required to validate the approved Group B membership decision:

- For a valid Zone, an incoming eligible swing is a member when abs(incoming_swing_price - current_zone_center) <= current_tolerance.
- current_zone_center = median(member prices)
- current_tolerance = causal tolerance from the frozen HIGH/LOW-specific tolerance history
- HIGH and LOW remain separate
- the current incoming swing is excluded from the tolerance used to evaluate itself
- strict causal ordering is preserved
- membership is evaluated only from already-known state
- Expected: the rule is deterministic, causal, and consistent with the current frozen center and tolerance semantics.
- Scope: this requirement freezes only the membership rule for a valid Zone under the current frozen center-statistic and tolerance-history semantics. It does not freeze zone creation, member-set update semantics, zone geometry, overlap, merge, lifecycle, identity, or any other unresolved Group B root decision.

Candidate B (nearest-member distance) is explicitly not the membership rule. Candidate C remains unresolved/blocked.

### B10 — Zone creation requirement

FROZEN — HUMAN APPROVED

The following design test is required to validate the approved Group B Zone Creation decision:

- the first eligible same-direction swing is a SEED / CANDIDATE
- the first eligible same-direction swing does NOT create a valid Zone
- a valid Zone is created when a second same-direction swing qualifies as a member under the already-frozen Group B membership rule
- a swing qualifies as a member when abs(incoming_swing_price - current_zone_center) <= current_tolerance
- current_zone_center is the median of the current member prices
- current_tolerance is the already-frozen causal HIGH/LOW-specific tolerance history under the W=5 / minimum-history=1 contract
- HIGH and LOW histories remain separate
- the current swing is excluded from its own tolerance history
- no additional numerical threshold is introduced
- minimum tolerance history = 1 is not reinterpreted as the minimum Zone member count; these are separate decisions
- Expected: the Zone exists in candidate state after the first eligible same-direction swing and becomes a valid Zone only at the second qualifying same-direction member
- Scope: this requirement freezes only the Zone creation boundary under the already-frozen center and membership rules. It does not freeze member-set update semantics beyond the approved creation rule, final Zone geometry, broadening behavior, overlap handling, merge behavior, zone identity, lifecycle/state transitions, historical snapshot semantics, or any other unresolved Group B decision.

Group B remains NOT FROZEN overall, and Phase 2 remains NOT STARTED.

### A2 — normal swing low
- Input sequence contains a candle where low[i] is lower than both neighboring lows.
- Expected: one swing-low candidate observed at index i.

### A3 — equality rejection
- Input sequence contains equal highs or equal lows at the neighbor boundary.
- Expected: no swing is recorded for the center candle in any equality case.

### A4 — first-candle boundary
- Input sequence begins with the first candle.
- Expected: the first candle is not eligible for swing detection.

### A5 — last-candle boundary
- Input sequence ends with the last candle.
- Expected: the last candle is not eligible for swing detection.

### A6 — incomplete confirmation window
- Input sequence contains a candidate with a missing right neighbor or missing left neighbor.
- Expected: the candidate is not eligible and no swing is emitted.

### A7 — confirmation timing
- Input sequence contains a valid pivot candidate after the final required neighbor becomes available.
- Expected: confirmation occurs exactly when the final required neighbor is observable in canonical order.

### A8 — eligibility timing
- Input sequence contains a confirmed candidate.
- Expected: the candidate may affect downstream Phase 1 logic only at its eligibility time, which is the confirmation time for this rule.

### A9 — no future influence before confirmation
- Input sequence shows a candidate that is not yet confirmed.
- Expected: downstream logic does not treat it as a valid swing before confirmation is available.

### A10 — deterministic replay
- The same candle sequence is replayed twice under identical canonical ordering.
- Expected: the swing sequence is identical across both runs.

## Phase 1 operational bar contract test obligations

The human-approved bar contract introduces these required test obligations for the Phase 1 governance suite. These are documentation requirements only; implementation remains deferred unless future governance explicitly requires it.

- `[start, end)` membership rule for 15-minute buckets
- event timestamp exactly equal to `bar_end` belongs to the next bar
- trailing/incomplete bar is excluded from finalized Group A and Group B evaluation
- closed bar immutability after `bar_end` boundary is reached
- deterministic replay under identical canonical ordering
- dataset-end partial bar behavior: final partial bar is discarded

## Future suite structure

The future tests must verify:
- deterministic replay stability
- strict inequality semantics
- no look-ahead beyond the required adjacent observations
- exact localized pivot behavior
- explicit rejection of plateau and incomplete-window cases
- exact output reproducibility for identical canonical input streams
- the approved 15-minute bar contract semantics listed above

## Required status

Status:
- FROZEN — HUMAN APPROVED
- READY FOR HUMAN FREEZE: superseded by the final approved freeze

## Freeze invariants

The Group A freeze is intentionally limited to the swing definition and must not be silently changed or reinterpreted. No executable tests are modified, created, or run as part of this freeze step.
