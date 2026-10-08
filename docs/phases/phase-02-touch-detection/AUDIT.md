# Phase 2 — Touch Detection Audit

## Status

HUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION

This audit records the repository evidence boundary for the approved Phase 2 formation-state decision and the post-Zone touch semantic. It explicitly separates the bootstrap formation event from normal post-Zone membership and records that Existing Zone Membership is the Touch event after a valid Zone exists.

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

## 1. Repository evidence boundary

The authoritative Phase 1 evidence states that:

- the first eligible same-direction swing is a SEED / CANDIDATE
- the first eligible same-direction swing does NOT create a valid Zone
- a valid Zone is created when a second same-direction swing qualifies as a member under the already-frozen membership rule
- current_zone_center = median(member prices)
- incoming eligible swing is a member when abs(incoming_swing_price - current_zone_center) <= current_tolerance

This evidence is valid only after a valid Zone and a valid Zone center exist.

The Phase 2 decision approved here is narrower: it records that the first post-seed swing is accepted as the second member and creates the first valid Zone without applying the normal Phase 1 membership predicate because no valid Zone exists yet and therefore no Zone center exists.

## 2. Approved boundary

The approved Phase 2 semantic boundary is:

- Pre-Zone state: no valid Zone exists, therefore no valid Zone center exists.
- First post-seed formation event: the first subsequent eligible same-direction swing is accepted as the second member and creates the first valid Zone.
- Bootstrap calculation for that event only:
  T_boot = abs(current_swing_price - seed_price)
- T_boot is temporary only for the formation event and is not inserted into G.
- Current swing remains excluded from normal tolerance history.
- Post-Zone state: once the Zone exists, center = median(member prices), and normal Phase 1 membership logic applies.

This is intentionally narrow and is not a redefinition of the Phase 1 membership predicate.

## 3. What remains unresolved or out of scope

The following remain explicitly outside this approved Phase 2 decision:

- broader bar-vs-swing touch semantics beyond the approved rule
- touch timestamps
- repeated-touch policy
- same-bar multiple-touch policy
- touch confirmation policy
- Zone lifecycle semantics
- multiple active Zones
- overlap/merge
- retirement/replacement
- later Zone member-update semantics

## 4. Audit conclusion

The approved Phase 2 formation-state decision is internally consistent with the repository boundary because it preserves the Phase 1 rule set and clearly limits itself to the first valid Zone creation event.

It does not claim that the first post-seed swing qualifies under the normal membership predicate before Zone creation, and it does not introduce a temporary Zone center or any other unapproved pre-Zone algorithm.
