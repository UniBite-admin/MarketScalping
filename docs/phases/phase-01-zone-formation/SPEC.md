# Phase 1 — Zone Formation Specification

## Status

FROZEN — HUMAN APPROVED

This specification is the frozen Phase 1 Group A swing definition. It is intentionally not runtime logic, but it is the approved and frozen specification for the swing definition itself.

## Final Human-Approved Freeze Record (2026-10-06)

This Phase 1 scope is now explicitly frozen under human approval as of 2026-10-06.

### Accepted frozen scope

The accepted Phase 1 scope is intentionally narrow and is limited to the evidence-backed governance contract currently recorded in the repository:

- Group A swing definition remains frozen
- 15-minute UTC bar contract remains frozen as the authoritative Group B input contract
- narrow Group B tolerance-history semantics remain frozen
- narrow Group B center statistic remains frozen
- narrow Group B membership rule remains frozen
- narrow Group B creation rule remains frozen

### Evidence boundary

The maximum lifecycle-independent evidence presently established by the repository is:

FIRST VALID ZONE → IMMEDIATE NEXT UNIQUE SAME-DIRECTION SWING → MATHEMATICAL MEMBER/NON_MEMBER/UNCLASSIFIABLE CLASSIFICATION

This boundary is accepted as the maximum valid Phase 1 evidence under the frozen contract. Nothing beyond this boundary is accepted as a frozen Phase 1 decision.

### Unresolved lifecycle boundary

The following remain explicitly NOT FROZEN:

- active Zone identity
- multiple Zone behavior
- Zone persistence
- Zone retirement
- Zone replacement
- Zone overlap/merge
- member-set update semantics
- center update after a member
- tolerance update after a member
- non-member transition behavior
- candidate behavior after valid Zone creation
- candidate/Zone coexistence
- any later lifecycle behavior

### Rejected lifecycle-independent evidence

The earlier historical counts:

- HIGH: 27 valid Zone creations
- LOW: 23 valid Zone creations

remain explicitly classified as:

REJECTED AS LIFECYCLE-INDEPENDENT EVIDENCE

These counts are not part of the accepted Phase 1 frozen contract.

### Governance status

- Phase 1 status: FROZEN / HUMAN APPROVED
- Group B overall status: NOT FROZEN
- Phase 2 status: NOT STARTED
- production behavior: UNCHANGED
- human approval date: 2026-10-06

This is a governance freeze only; it does not implement unresolved lifecycle behavior, does not start Phase 2, and does not broaden the authorized Phase 1 scope.

## 1. Objective

Define a deterministic and causally valid Phase 1 swing rule that can support future zone formation, touch detection, reaction validation, and confluence logic without relying on undocumented assumptions or hidden look-ahead.

The project requires:
- Data → Test → Validate → Automate → Control → Scale
- deterministic replay ordering
- UTC-normalized timestamps
- no silent assumptions
- no live look-ahead
- explicit human approval for technical design

A Phase 1 human approval has now been recorded for the deterministic 15-minute operational bar contract used as the authoritative Group B input contract:
- 15-minute timeframe
- UTC-aligned deterministic buckets
- interval: `[bar_start, bar_end)`
- event exactly at `bar_end` belongs to the next bar
- bar closes when replay passes its `bar_end` boundary
- closed bars are immutable
- trailing/incomplete bars are excluded from finalized Group A and Group B evaluation
- final partial bar at dataset end is discarded

This approval does not alter the frozen Group A swing semantics or declare Group B frozen.

## 1A. Approved Group B tolerance-history semantics

FROZEN — HUMAN APPROVED

The human project authority has approved the following bounded tolerance-history semantics for Group B evaluation:

- W = 5 prior legal same-direction gaps
- minimum history = 1 prior legal same-direction gap
- if 0 prior legal same-direction gaps exist, no tolerance is available and Group B membership cannot be evaluated
- if 1 to 4 prior legal same-direction gaps exist, use all available prior legal gaps
- if 5 or more prior legal same-direction gaps exist, use the five most recent prior legal gaps
- the current swing is excluded from its own tolerance history
- HIGH and LOW swing streams remain separate
- prior observations are ordered by canonical replay / eligibility order
- legal gaps are absolute price gaps between consecutive eligible same-direction observations under the already-established same-direction sequence semantics

Exact mathematical form:

- Let G be the ordered sequence of prior legal same-direction gaps available before evaluating the current swing.
- If |G| = 0: no tolerance available.
- If 1 <= |G| < 5: use all elements of G.
- If |G| >= 5: use the five most recent elements of G.
- Tolerance = median(selected legal gaps)

This is the human-approved historical tolerance rule for the current bounded Group B research context. It does not freeze the whole Group B architecture, member-to-zone rules, zone geometry, overlap behavior, or any unresolved Group B root decisions beyond the approved tolerance-history semantics themselves.

## 1B. Approved Candidate A center-statistic decision

FROZEN — HUMAN APPROVED

The human project authority has explicitly approved the center statistic for Candidate A — Point-Center Zone:

- center statistic = median(member prices)
- status = FROZEN — HUMAN APPROVED

This approval freezes only the center statistic for Candidate A. It does not freeze the membership rule, zone creation rule, zone update timing, zone identity, multiple-zone handling, overlap behavior, merge behavior, zone width, lifecycle semantics, or historical snapshot semantics. Those remain unresolved Group B decisions. Group B remains NOT FROZEN as a whole, and Phase 2 remains NOT STARTED.

## 1C. Approved Group B membership decision

FROZEN — HUMAN APPROVED

The human project authority has explicitly approved the following membership rule for a valid Zone:

- incoming eligible swing is a member when abs(incoming_swing_price - current_zone_center) <= current_tolerance
- current_zone_center = median(member prices)
- current_tolerance = causal tolerance from the frozen HIGH/LOW-specific tolerance history
- HIGH and LOW remain separate
- the current incoming swing is not included in the tolerance used to evaluate itself
- strict causal ordering is preserved
- membership is evaluated only from already-known state

This approval is intentionally narrow. It freezes only the membership rule for a valid Zone under the current frozen center-statistic and tolerance-history semantics. It does not freeze zone creation, member-set update semantics, zone geometry, overlap, merge, lifecycle, identity, or any other unresolved Group B root decision. Candidate B (nearest-member distance) is explicitly not the membership rule. Candidate C remains unresolved/blocked. Group B remains NOT FROZEN as a whole, and Phase 2 remains NOT STARTED.

Rationale recorded for governance clarity:
- A/D is the simplest defensible membership rule under the current frozen center semantics.
- The 86 A-vs-B disagreements demonstrate materially different geometry, not evidence that A/D is invalid.
- Repository evidence does not require nearest-member semantics.

## 1D. Approved Group B Zone Creation decision

FROZEN — HUMAN APPROVED

The human project authority has explicitly approved the following Zone Creation rule:

- the first eligible same-direction swing is a SEED / CANDIDATE
- the first eligible same-direction swing does NOT create a valid Zone
- a valid Zone is created when a second same-direction swing qualifies as a member under the already-frozen Group B membership rule
- "qualifies as a member" means abs(incoming_swing_price - current_zone_center) <= current_tolerance
- current_zone_center is the median of the current member prices
- current_tolerance is the already-frozen causal HIGH/LOW-specific tolerance history, with:
  - W = 5
  - minimum tolerance history = 1
  - current swing excluded from its own tolerance history
  - HIGH and LOW histories remain separate
- no additional numerical threshold is introduced
- minimum tolerance history = 1 is NOT reinterpreted as the minimum Zone member count; these are separate decisions
- the two-member requirement applies only to Zone creation:
  - member #1 = seed/candidate
  - member #2 = valid Zone creation trigger

This approval is intentionally narrow. It freezes only the creation semantics for when a valid Zone first becomes valid under the already-frozen center and membership rules. It does not freeze member-set update semantics beyond the approved creation rule, final Zone geometry/boundaries, zone expansion/broadening behavior, multiple simultaneous zones, overlap handling, merge behavior, zone identity, lifecycle/state transitions, historical snapshot semantics, or any other Group B decision not explicitly approved by the human.

The following remain unresolved / NOT FROZEN unless already independently frozen by prior human approval:
- member-set update semantics beyond the approved creation rule
- final Zone geometry / boundaries
- zone expansion / broadening behavior
- multiple simultaneous zones
- overlap handling
- merge behavior
- zone identity
- lifecycle / state transitions
- historical snapshot semantics
- any other Group B decision not explicitly approved by the human

Group B remains NOT FROZEN overall, and Phase 2 remains NOT STARTED.

## 2. Authoritative evidence used

This proposal is grounded in repo evidence and architecture constraints:
- [docs/ROADMAP.md](../../ROADMAP.md) is the authoritative current roadmap.
- [replay_runner.py](../../replay_runner.py) establishes deterministic chronological ordering over canonical events.
- [feature_signal_engine.py](../../feature_signal_engine.py) rejects non-monotonic timestamps and validates the price stream before downstream processing.
- The repository does not contain an authoritative Phase 1 swing rule; therefore the proposal is deliberately documented as a candidate V1 design rather than a frozen rule.

## 3. Research integrity

A. Established repository facts
- The system uses canonical historical ordering and timestamp validation.
- There is no approved Phase 1 swing rule in the current repo state.
- Historical values remain historical evidence only.

B. Engineering reasoning
- A 1-left / 1-right local extremum is the lowest-complexity local turnover detector suitable for V1.
- Wider windows may be more stable, but they also increase confirmation delay and reduce responsiveness for short-term structure.

C. Empirical hypotheses
- A wider symmetric window may produce fewer but more stable swings.
- A narrower window may produce more high-frequency swings and more churn in zone formation.
- The repo currently does not include empirical evidence proving which alternative is superior for this exact system objective.

D. Proposed V1 design
- Use a strict local-extrema rule with explicit confirmation timing and deterministic boundary handling.

## 4. Definitions

- Swing observation: the raw candidate event at candle index i when a valid local extremum condition is present in the canonical historical stream.
- Swing high: a local maximum in the high-price series.
- Swing low: a local minimum in the low-price series.
- Swing candle timestamp: the timestamp attached to the candle index being evaluated.
- Confirmation time: the timestamp at which the final required neighbor becomes observable in canonical order and the full candidate test can be evaluated.
- Eligibility time: the timestamp at which the confirmed swing may affect downstream Phase 1 logic. For this specification, confirmation time and eligibility time are semantically identical because the same final observation is both the confirmation and the first valid downstream use moment.
- Causal eligibility: a state in which the swing was created using data available at the time the decision is being evaluated, without relying on future data in the same decision path.

## 5. Proposed Group A — Swing Definition

### A1 — Swing High

Decision: PROPOSED

Technical rule:
- For candle index i, a swing high exists if and only if:
  - 1 <= i < n - 1
  - high[i] > high[i - 1]
  - high[i] > high[i + 1]

Exact mathematical definition:
- swing_high(i) = (1 <= i < n - 1) AND (high[i] > high[i - 1]) AND (high[i] > high[i + 1])

### A2 — Swing Low

Decision: PROPOSED

Technical rule:
- For candle index i, a swing low exists if and only if:
  - 1 <= i < n - 1
  - low[i] < low[i - 1]
  - low[i] < low[i + 1]

Exact mathematical definition:
- swing_low(i) = (1 <= i < n - 1) AND (low[i] < low[i - 1]) AND (low[i] < low[i + 1])

### A3 — Candle fields

Decision: PROPOSED

Technical rule:
- High is used for swing-high detection.
- Low is used for swing-low detection.
- Open, Close, and Volume are excluded from the V1 pivot definition unless a later phase provides a justified requirement.

### A4 — Equality semantics

Decision: PROPOSED

Technical rule:
- Equality is not a swing in V1.
- This includes:
  - high[i] == high[i - 1]
  - high[i] == high[i + 1]
  - low[i] == low[i - 1]
  - low[i] == low[i + 1]

All such cases are explicitly non-eligible.

### A5 — Boundary behavior

Decision: PROPOSED

Technical rule:
- First candle: not eligible.
- Last candle: not eligible.
- Insufficient prior candles: not eligible.
- Insufficient confirmation candles: not eligible.
- Incomplete historical window: not eligible; no inference and no retroactive backfill.

No other boundary behavior is permitted in V1.

## 6. Exact causal timing

For any observed candle index i:
- swing candle timestamp = timestamp[i]
- confirmation time = timestamp[i + 1] when the final required neighboring observation becomes observable in canonical stream order
- eligibility time = confirmation time, because the candidate may first affect downstream logic at the same moment it is confirmed

This rule must not allow a swing candidate to affect downstream decisions before the required confirmation information is observable.

In practical terms, for a 1-left / 1-right local-extrema rule, the candidate cannot be used until the right-side observation is available in the canonical history. The system therefore distinguishes raw observation time from confirmation and eligibility time, but it does not create a separate semantic timestamp when the confirmation and eligibility are the same event.

## 7. Why the 1-left / 1-right rule is recommended as V1

The current proposal is a better V1 default than a wider multi-candle window because:
- it minimizes assumptions
- it is easy to reason about
- it is deterministic
- it is easy to test
- it keeps the design compatible with later zone lifecycle logic
- it avoids over-specifying the system before enough empirical evidence exists

Wider windows may be investigated later, but they are not required for V1 unless the architecture team has a strong evidence-based reason to prefer them.

## 8. Determinism constraints

Two replay runs must produce the same swing set when the input history, ordering, and timestamps are equal. To preserve this property, the design must explicitly define:
- strict inequality rules
- first/last candle exclusion
- missing neighbor exclusion
- no retroactive fill-in at end-of-history
- no use of Open/Close/Volume unless separately approved
- deterministic ordering by canonical timestamp and stable index

## 9. Downstream compatibility

This design remains compatible with later Phase 1 and downstream systems:
- zone clustering: the confirmed pivot is a natural anchor for later zone creation
- zone center/geometry: local extrema produce a stable anchor value
- touch detection: later price interaction can reference the established pivot and zone bounds
- reaction validation: later phases can test isotopic directional response around the pivot
- zone lifecycle: a confirmed swing is a valid origin point for lifecycle transitions
- confluence: later indicators can be layered on top of the pivot structure
- candlestick pattern engine: the pivot foundation remains simple and explainable
- strategy engine: the strategy may later depend on a deterministic pivot entry point, without relying on hidden heuristics

## 10. Human approval boundary

This specification is now frozen for Group A. No additional rule invention is required for the swing definition because the rule set is complete, deterministic, and causally defined within the approved scope.

## 11. Frozen status

Status:
- FROZEN — HUMAN APPROVED
- READY FOR HUMAN FREEZE: superseded by the final approved freeze

## 12. Freeze boundary

This freeze applies only to Group A — Swing Definition. It does not freeze any later Phase 1 decisions or downstream zone logic.

The following remain future decisions under the current roadmap:
- clustering tolerance
- zone center
- zone upper/lower bounds
- assignment to existing zones
- new-zone creation
- overlapping-zone behavior
- zone lifecycle
- touch detection
- reaction validation
- confluence
- candlestick patterns
- strategy decisions

No executable tests are created or modified in this freeze step.
