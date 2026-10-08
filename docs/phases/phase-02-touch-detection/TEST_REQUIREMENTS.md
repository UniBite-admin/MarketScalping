# Phase 2 — Touch Detection Test Requirements

## Status

HUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION

This document defines deterministic test requirements for the approved Phase 2 formation-state behavior and the approved post-Zone touch semantic. It does not define unresolved lifecycle tests.

## Human decision record (dated 2026-10-08)

Decision A — approved Phase 2 formation-state boundary.

This human decision records the approved Phase 2 semantics for the first valid Zone creation event and the exact post-Zone touch semantic:

- Pre-Zone state: no valid Zone exists, therefore no valid Zone center exists.
- First post-seed formation event: the first subsequent eligible same-direction swing is accepted as the second member and creates the first valid Zone.
- Bootstrap calculation for that event only:
  T_boot = abs(current_swing_price - seed_price)
- T_boot is temporary only for the formation event and is not inserted into G.
- Current swing remains excluded from normal tolerance history.
- Post-Zone touch semantic: once a valid Zone exists, the exact observable market event classified as a Touch is existing Zone Membership under the frozen Phase 1 membership predicate.
- In practical terms, any later eligible observation that satisfies:
  abs(incoming_swing_price - current_zone_center) <= current_tolerance
  is a Zone Touch.
- The first post-seed swing that creates the Zone is a Formation event, not a Touch.
- The frozen Phase 1 membership rule remains the authority for post-Zone touch classification.

Mandatory boundaries of Decision A:
- This decision defines the approved post-Zone touch semantic: Existing Zone Membership is the Touch event.
- This decision is limited to the first valid Zone formation event and the subsequent post-Zone touch classification after a valid Zone exists.
- It does not authorize any pre-Zone membership test, temporary center, midpoint rule, interval rule, or other pre-Zone qualification rule.
- It does not redefine or replace the frozen Phase 1 membership predicate; it preserves it as the post-Zone authority.
- It does not define later lifecycle semantics, multiple active Zone handling, overlap/merge semantics, retirement/replacement rules, or member-update semantics.
- Any broader touch or lifecycle interpretation remains outside the approved scope and requires a separate human decision.

## Phase 2 semantic freeze

The approved Phase 2 semantic boundary is:

- Pre-Zone state: no valid Zone exists, therefore no valid Zone center exists.
- First post-seed formation event: the first subsequent eligible same-direction swing is accepted as the second member and creates the first valid Zone.
- Bootstrap calculation for that event only:
  T_boot = abs(current_swing_price - seed_price)
- T_boot is temporary only for the formation event and is not inserted into G.
- Current swing remains excluded from normal tolerance history.
- Post-Zone touch semantic: once a valid Zone exists, existing Zone Membership is the Touch event under the frozen Phase 1 membership predicate.
- The first post-seed swing that creates the Zone is Formation only; it is not a Touch.

This is intentionally narrow and preserves the frozen Phase 1 membership predicate as the authority for post-Zone touch classification.

The following remain explicitly outside this approved Phase 2 decision:

- bar-vs-swing touch semantics
- touch timestamps
- repeated touches
- same-bar multiple touches
- touch confirmation
- Zone lifecycle semantics
- multiple active Zones
- overlap/merge
- retirement/replacement
- later Zone member-update semantics

## 1. Required Phase 2 formation-state tests

### T2-01 — persistent seed
- Given a sequence where no valid Zone exists,
- when the first eligible same-direction swing is observed,
- then that swing becomes the persistent seed/candidate.

### T2-02 — seed remains unchanged until first valid Zone formation
- Given a valid seed/candidate,
- when subsequent eligible same-direction swings are observed before the first valid Zone exists,
- then the seed remains unchanged.

### T2-03 — first post-seed swing creates the first valid Zone
- Given a persistent seed and a subsequent eligible same-direction swing,
- when the first valid Zone is formed,
- then the first subsequent eligible same-direction swing is accepted as the second member and the first valid Zone contains exactly the seed and that swing.

### T2-04 — no normal membership predicate before Zone creation
- Given a seed and a first subsequent eligible same-direction swing,
- then the normal Phase 1 membership predicate is not applied to that first post-seed swing because no valid Zone center exists yet.

### T2-05 — bootstrap value is computed for the formation event only
- Given the seed and the first subsequent eligible same-direction swing,
- then T_boot = abs(current_swing_price - seed_price).

### T2-06 — T_boot is not inserted into G
- Given the formation event,
- then T_boot is temporary only for this event and is not inserted into normal gap history G.

### T2-07 — current swing excluded from normal tolerance history
- Given the first post-seed formation event,
- then the current swing remains excluded from normal tolerance history.

### T2-08 — exact two-member first Zone
- Given the first valid Zone creation event,
- then the Zone contains exactly the seed and the first subsequent eligible same-direction swing.

### T2-09 — center is created after Zone formation
- Given a first valid Zone exists,
- then center = median(member prices).

### T2-10 — transition to frozen Phase 1 membership semantics
- Given a valid Zone exists,
- then subsequent membership evaluation uses the normal Phase 1 rule:
  abs(incoming_swing_price - current_zone_center) <= current_tolerance

### T2-11 — W=5 and minimum-history=1 remain unchanged
- Given the first Zone exists,
- then the Phase 1 tolerance-history rules continue to operate unchanged with W = 5 and minimum history = 1.

### T2-12 — deterministic replay
- Given identical canonical input sequence,
- then the same seed, same bootstrap formation event, and same first valid Zone result must occur deterministically.

### T2-13 — no look-ahead
- Given the formation event,
- then the decision uses only already-known seed and current swing information and does not rely on future data.

### T2-14 — Phase 1 integrity
- Given the approved Phase 2 decision,
- then no Phase 1 frozen decision is amended, weakened, or replaced.

## 2. Approved semantic test requirement

### T2-15 — approved post-Zone touch semantic
- Given a valid Zone exists,
- when a later eligible observation satisfies:
  abs(incoming_swing_price - current_zone_center) <= current_tolerance
- then that observation is a Zone Touch.
- The first post-seed swing that creates the first valid Zone is a Formation event only and is not a Touch.

## 3. Out-of-scope tests

The following remain outside the approved Phase 2 test set:

- touch timestamps
- repeated-touch policy
- same-bar multiple-touch policy
- touch confirmation policy
- Zone lifecycle behavior
- multiple active Zone behavior
- overlap/merge
- retirement/replacement
- later member-update semantics

## 4. Test status

These Phase 2 test requirements are limited to the approved formation-state behavior and the approved post-Zone touch semantic. They do not authorize production implementation or executable test creation in this stage.
