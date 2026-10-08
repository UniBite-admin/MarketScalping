# Phase 2 — Touch Detection Decision Register

## Status

HUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION

This document records the Phase 2 formation-state decision and the approved post-Zone touch semantic for the first valid Zone. The first post-seed event is Formation only, and once a valid Zone exists, Existing Zone Membership is the Touch event under the frozen Phase 1 membership predicate.

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

## Approved formation-state decision

The human project authority has explicitly approved the following Phase 2 formation-state semantics:

1. The first eligible same-direction swing becomes the persistent seed/candidate.
2. The seed remains unchanged until the first valid Zone is formed.
3. The first subsequent eligible same-direction swing after the seed is accepted as the second member and creates the first valid Zone.
4. The normal Phase 1 membership predicate is NOT applied to this first post-seed swing because no valid Zone exists yet and therefore no Zone center exists.
5. For this single bootstrap formation event:
   T_boot = abs(current_swing_price - seed_price)
6. T_boot is temporary and applies only to this single formation event.
7. T_boot is NOT a legal prior same-direction gap.
8. T_boot is NOT inserted into normal gap history G.
9. The current swing remains excluded from normal tolerance history.
10. The first valid Zone contains exactly:
    - the seed
    - the first subsequent eligible same-direction swing
11. Once the Zone exists:
    center = median(member prices)
12. After Zone creation, the frozen Phase 1 membership predicate applies normally:
    abs(incoming_swing_price - current_zone_center) <= current_tolerance
13. The frozen Phase 1 tolerance-history rules remain unchanged:
    - W = 5
    - minimum history = 1
    - current swing excluded
    - HIGH and LOW histories remain separate
14. This Phase 2 decision does NOT amend, reinterpret, weaken, or replace any Phase 1 frozen decision.
15. This Phase 2 decision defines the approved post-Zone touch semantic:
    - Existing Zone Membership is the Touch event
    - bar-vs-swing touch semantics remain outside scope
    - touch timestamps remain outside scope
    - repeated touches remain outside scope
    - same-bar multiple touches remain outside scope
    - touch confirmation remains outside scope
    - Zone lifecycle remains outside scope
    - multiple active Zones remain outside scope
    - overlap/merge remain outside scope
    - retirement/replacement remain outside scope
    - later Zone member-update semantics remain outside scope

## Scope boundary

This Phase 2 decision is a narrow formation-state decision and the approved post-Zone touch semantic. Its sole purpose is to define the first valid Zone creation event under the approved bootstrap semantics and to record that Existing Zone Membership is the Touch event after a valid Zone exists.

It does not define:
- final Zone geometry beyond the initial two-member Zone creation event
- lifecycle transitions after Zone creation
- unresolved Zone identity semantics
- unresolved Zone overlap/merge semantics
- later member updates or history mutation

## Phase 1 integrity

All Phase 1 frozen decisions remain authoritative and unchanged. This Phase 2 decision is not a Phase 1 rewrite. It is a separate Phase 2 step that records the approved initial formation-state exception required to create the first valid Zone.

## Governance note

The bootstrap formation event is distinct from normal post-Zone membership. The bootstrap event is not described as the normal Phase 1 membership predicate being applied before a valid Zone exists, and no temporary center is introduced.
