# Phase 2 — Touch Detection Audit

## Status

HUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION

This audit records the repository evidence boundary for the approved Phase 2 formation-state decision. It explicitly separates the bootstrap formation event from normal post-Zone membership and rejects any claim that the normal membership predicate is applied before a valid Zone exists.

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

The following remain explicitly outside this approved Phase 2 formation-state decision:

- final Touch Detection semantics
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

## 4. Audit conclusion

The approved Phase 2 formation-state decision is internally consistent with the repository boundary because it preserves the Phase 1 rule set and clearly limits itself to the first valid Zone creation event.

It does not claim that the first post-seed swing qualifies under the normal membership predicate before Zone creation, and it does not introduce a temporary Zone center or any other unapproved pre-Zone algorithm.
