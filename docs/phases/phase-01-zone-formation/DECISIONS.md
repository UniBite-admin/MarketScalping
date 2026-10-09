# Phase 1 — Zone Formation Decision Register

## Status

FROZEN — HUMAN APPROVED

This document records the frozen specification for Phase 1 Group A. It is not execution logic and it is not a frozen implementation. It is the approved design for the swing definition only.

## Final Human-Approved Freeze Record (2026-10-06)

This Phase 1 scope is now explicitly frozen under human approval as of 2026-10-06.

### Accepted frozen scope

The accepted Phase 1 scope is intentionally narrow and does not broaden beyond the evidence-based governance contract.

- Group A swing definition remains frozen:
  - strict swing-high definition
  - strict swing-low definition
  - High only for highs
  - Low only for lows
  - required left/right neighborhood
  - confirmation timing
  - eligibility timing
  - deterministic canonical replay ordering
  - no-lookahead behavior
- 15-minute UTC bar contract remains frozen as the authoritative Group B input contract:
  - 15-minute timeframe
  - UTC aligned
  - half-open `[bar_start, bar_end)`
  - event exactly at `bar_end` belongs to next bar
  - closed bars immutable
  - incomplete trailing bar excluded
  - empty buckets omitted
  - Group A applied only to closed bars
- accepted narrow Group B contract remains frozen:
  - W = 5
  - minimum history = 1
  - HIGH and LOW handled separately
  - prior same-direction legal gaps
  - current swing excluded from its own tolerance history
  - tolerance = median of selected prior legal gaps
  - center = median(member prices)
  - membership predicate: `abs(incoming_swing_price - current_zone_center) <= current_tolerance`
  - creation rule: first eligible same-direction swing = candidate/seed; first subsequent qualifying same-direction swing = valid Zone creation

### Evidence boundary

The maximum lifecycle-independent evidence established by the frozen contract is:

FIRST VALID ZONE → IMMEDIATE NEXT UNIQUE SAME-DIRECTION SWING → MATHEMATICAL MEMBER/NON_MEMBER/UNCLASSIFIABLE CLASSIFICATION

Anything beyond that boundary is not part of the accepted Phase 1 freeze and remains outside the frozen contract.

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

### Rejected evidence

The previous historical counts:

- HIGH: 27 valid Zone creations
- LOW: 23 valid Zone creations

remain explicitly classified as:

REJECTED AS LIFECYCLE-INDEPENDENT EVIDENCE

These counts must not be reintroduced as accepted Phase 1 evidence.

### Governance status

- Phase 1 status: FROZEN / HUMAN APPROVED
- Group B overall status: NOT FROZEN
- Phase 2 status: NOT STARTED
- production behavior: UNCHANGED
- human approval date: 2026-10-06

This freeze is a governance freeze only. It does not start Phase 2, does not implement unresolved lifecycle behavior, does not modify production trading code, does not modify executable tests, and does not silently broaden the Phase 1 contract.

## Additional approved governance decision

The human project authority has approved the deterministic 15-minute operational bar contract for Phase 1 Group B input use, as follows:
- 15-minute timeframe
- UTC-aligned deterministic buckets
- interval: `[bar_start, bar_end)`
- event exactly at `bar_end` belongs to the next bar
- a bar becomes closed when replay passes `bar_end`
- closed bars are immutable
- trailing/incomplete bars are excluded from finalized Group A and Group B evaluation
- the final partial bar at dataset end is discarded

This approval does not modify or reinterpret the frozen Group A swing definition. It is a separate human-approved Phase 1 governance decision for the bar input contract only.

## Additional approved Group B tolerance-history decision

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

The approved mathematical form is:

- Let G be the ordered sequence of prior legal same-direction gaps available before evaluating the current swing.
- If |G| = 0: no tolerance available.
- If 1 <= |G| < 5: use all elements of G.
- If |G| >= 5: use the five most recent elements of G.
- Tolerance = median(selected legal gaps)

This is a bounded, human-approved design parameter for Group B tolerance history. It does not freeze the entire Group B architecture, the member-to-zone rule, zone geometry, overlap handling, or any other unresolved Group B root decision. Group B remains NOT FROZEN as a whole, and Phase 2 remains NOT STARTED.

## Additional approved Candidate A center-statistic decision

FROZEN — HUMAN APPROVED

The human project authority has explicitly approved the center statistic for Candidate A — Point-Center Zone:

- CENTER STATISTIC: median(member prices)
- STATUS: FROZEN — HUMAN APPROVED

This approval is intentionally narrow. It freezes only the center statistic for Candidate A. It does not freeze the membership rule, zone creation rule, zone update timing, zone identity, overlap handling, merge behavior, zone width, lifecycle semantics, or historical snapshot semantics. Those remain unresolved Group B decisions. Group B remains NOT FROZEN as a whole, and Phase 2 remains NOT STARTED.

## Additional approved Group B membership decision

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

Additional rationale recorded for governance clarity:
- A/D is the simplest defensible membership rule under the current frozen center semantics.
- The 86 A-vs-B disagreements demonstrate materially different geometry, not evidence that A/D is invalid.
- Repository evidence does not require nearest-member semantics.

## Additional approved Group B zone creation decision

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

## Implementation status

This repository now includes a narrow runtime implementation for the frozen Phase 1 tolerance-history and membership semantics in [tools/research/phase_1_zone_runtime.py](../../../../tools/research/phase_1_zone_runtime.py). It is intentionally limited to the frozen rules already approved for the first valid Zone and will not broaden into unresolved lifecycle behavior. The implementation is verified by focused tests in [tests/test_phase_1_zone_runtime.py](../../../../tests/test_phase_1_zone_runtime.py), but it does not mark the entire Phase 1 scope as complete or frozen beyond the authoritative acceptance criteria.

## Governance note

- Current authoritative roadmap: [docs/ROADMAP.md](../../ROADMAP.md)
- Current phase: PHASE 1 — Zone Formation
- Historical rules remain historical evidence only and are not current authority.
- This specification is frozen only for Group A — Swing Definition.
- This freeze does not authorize implementation, executable tests, Group B, or Phase 2.
- The architecture/research process has fully defined the technical rule and the human has approved the frozen specification.
- These decisions must not be silently changed or reinterpreted.

## Freeze-ready Group A contract

### 1. Swing observation

A swing candidate is observed at candle index i when all required local conditions are present in the canonical historical stream and the current candle is interior to the stream:
- i >= 1
- i <= n - 2
- high[i] > high[i - 1] and high[i] > high[i + 1] for a swing high
- low[i] < low[i - 1] and low[i] < low[i + 1] for a swing low

This is the raw observation event. It is a candidate only; it does not yet affect downstream logic.

### 2. Confirmation

A candidate becomes confirmed at the instant the final required neighbor becomes observable in canonical time order. For the 1-left / 1-right rule, the final required neighbor is the right-side neighbor, so the confirmation time is time[i + 1] when the right neighbor is available and the full comparison can be evaluated.

This future candle is allowed for confirmation only because the candidate is not usable before that information is observable. The system does not use future information to make a decision at candle time i; it confirms the prior candidate only after the required data exists.

### 3. Eligibility

A confirmed swing may affect downstream Zone Formation logic at the eligibility timestamp. For this specification, the confirmation time and the eligibility time are semantically identical for the 1-left / 1-right rule because the same final neighbor observation that confirms the candidate is also the earliest moment at which the candidate may be used.

Therefore, the required distinction is:
- swing candle time = time[i]
- confirmation time = time[i + 1] when the required right-side observation becomes visible in canonical replay order
- eligibility time = time[i + 1], because the candidate becomes usable at the same moment it is confirmed

No additional timestamp is introduced because there is no separate semantic event beyond confirmation.

### 4. Boundaries

Exactly one deterministic rule applies to all boundary conditions:
- first candle: not eligible
- last candle: not eligible
- insufficient left neighbor: not eligible
- insufficient right neighbor: not eligible
- incomplete historical window: not eligible
- no retroactive inference, no backfill, no single-sided edge swings

This is the sole boundary definition for Phase 1 Group A.

### 5. Equality

Strict comparisons are required for both swing types:
- equal highs do not qualify
- equal lows do not qualify
- equality with left neighbor does not qualify
- equality with right neighbor does not qualify

The rule is deterministic and non-swing in all equality cases.

### 6. Deterministic replay

Replaying the same candle sequence under the same canonical ordering produces the same swing sequence. The implementation must preserve the canonical order by timestamp and stable index. There is no tie ambiguity for a valid swing because equality is never a valid swing, and there is no hidden tolerance or fuzzy comparison in this specification. Any remaining ambiguity is outside Group A and belongs to later Phase 1 decisions.

### 7. Look-ahead audit

A swing must never influence:
- zone creation
- zone assignment
- zone clustering
- later strategy decisions

before the required confirmation information is observable. This prevents any future-look effect in the downstream pipeline.

### 8. Downstream contract

The output of Group A is a stream of confirmed swing records, each containing only the information required for later Phase 1 decisions:
- swing_type
- candle_index
- candle_time
- price_value
- left_neighbor_index and right_neighbor_index used in the comparison
- confirmation_time
- eligibility_time
- canonical source ordering metadata

This contract does not prematurely define clustering tolerance, zone center, zone boundary, zone lifecycle, touch rules, or reaction rules. Those are later decisions and remain outside Group A.

### 9. Test requirements

The required deterministic tests are:
- normal swing high
- normal swing low
- equality rejection
- first-candle boundary
- last-candle boundary
- incomplete confirmation window
- confirmation timing
- eligibility timing
- no future influence before confirmation
- deterministic replay

These tests are required for the final freeze but they remain design tests, not executable tests yet.

### 10. Final freeze status

FROZEN — HUMAN APPROVED

This specification is complete, deterministic, causal, and internally consistent as the approved Group A swing definition. It is not implementation logic and it is not a frozen runtime state.

## Frozen decisions

### A1 — Swing High
A candle i is a Swing High candidate when:
- High[i] > High[i - 1]
- High[i] > High[i + 1]

### A2 — Swing Low
A candle i is a Swing Low candidate when:
- Low[i] < Low[i - 1]
- Low[i] < Low[i + 1]

### A3 — Required Data
- Swing High detection uses High only.
- Swing Low detection uses Low only.
- Open, Close, and Volume are not inputs to the Phase 1 swing definition.

### A4 — Comparison
- All comparisons are strict.
- Equality never qualifies as a swing.

### A5 — Boundary
- A swing requires the complete required neighborhood.
- The first/last candle and any candle without the required neighboring observations cannot qualify.

## Frozen causality contract

- Swing observation: the raw candidate event at candle index i.
- Confirmation: the moment the final required right-side neighbor becomes observable in canonical replay order.
- Eligibility: the moment the confirmed swing may affect downstream Zone Formation logic.

For this frozen Group A rule, the right-side confirmation is required, and the candidate becomes eligible only after confirmation. No downstream logic may use an unconfirmed swing.

## Frozen non-scope

This freeze applies only to Group A — Swing Definition. It does not freeze:
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

Those remain future decisions under the current roadmap.

