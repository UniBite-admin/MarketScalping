# Phase 2 — Touch Detection Decision Register

## Status

HUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION

This document records the narrow Phase 2 formation-state decision for the first valid Zone. This decision is intentionally limited to initial Zone creation semantics and does not define final Touch Detection behavior or unresolved Zone lifecycle behavior.

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
15. This Phase 2 decision does NOT define:
    - final Touch Detection semantics
    - bar-vs-swing touch semantics
    - touch timestamps
    - repeated touches
    - same-bar multiple touches
    - touch confirmation
    - Zone lifecycle
    - multiple active Zones
    - overlap/merge
    - retirement/replacement
    - later Zone member-update semantics

## Scope boundary

This Phase 2 decision is a narrow formation-state decision only. Its sole purpose is to define the first valid Zone creation event under the approved bootstrap semantics.

It does not define:
- final Zone geometry beyond the initial two-member Zone creation event
- final Touch Detection semantics
- lifecycle transitions after Zone creation
- unresolved Zone identity semantics
- unresolved Zone overlap/merge semantics
- later member updates or history mutation

## Phase 1 integrity

All Phase 1 frozen decisions remain authoritative and unchanged. This Phase 2 decision is not a Phase 1 rewrite. It is a separate Phase 2 step that records the approved initial formation-state exception required to create the first valid Zone.

## Governance note

The bootstrap formation event is distinct from normal post-Zone membership. The bootstrap event is not described as the normal Phase 1 membership predicate being applied before a valid Zone exists, and no temporary center is introduced.
