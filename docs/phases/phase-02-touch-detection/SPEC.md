# Phase 2 — Touch Detection Specification

## Status

HUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION

This specification defines the approved Phase 2 formation-state boundary and the post-Zone touch semantic. The exact post-Zone event is Existing Zone Membership under the frozen Phase 1 membership predicate; the first post-seed swing remains Formation only.

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

## 1. Scope

This specification covers only the first valid Zone creation boundary:

- the first eligible same-direction swing becomes the seed/candidate
- the first subsequent eligible same-direction swing after the seed is accepted as the second member and creates the first valid Zone
- the bootstrap formation event used only for that first valid Zone creation
- the transition to the normal Phase 1 membership semantics after Zone creation

This specification does not define lifecycle events, repeated-touch policy, touch timestamps, confirmation semantics, or unresolved multi-Zone behavior. It records only the approved post-Zone touch semantic and the bootstrap formation boundary.

## 2. Seed persistence

The first eligible same-direction swing becomes the persistent seed/candidate.

The seed remains unchanged until the first valid Zone is formed.

## 3. Bootstrap formation event

The first subsequent eligible same-direction swing after the seed is accepted as the second member and creates the first valid Zone.

Important boundary:

- No normal Phase 1 membership predicate is applied to this first post-seed swing.
- No valid Zone exists yet.
- Therefore no valid Zone center exists yet.
- Therefore the normal membership test is not evaluated against a Zone center for this formation event.

For this single formation event only:

T_boot = abs(current_swing_price - seed_price)

This bootstrap value is temporary and applies only to this single formation event.

It is not a legal prior same-direction gap and is not inserted into normal gap history G.

The current swing remains excluded from normal tolerance history.

## 4. First valid Zone creation

The first valid Zone contains exactly:

- the seed
- the first subsequent eligible same-direction swing

No additional members are introduced by this formation event.

## 5. Center creation after Zone formation

Once the first valid Zone exists, the center is defined as:

center = median(member prices)

This is the first time a valid Zone center exists, and from that point onward the frozen Phase 1 center and membership semantics apply.

## 6. Transition to normal Phase 1 membership semantics

After Zone creation, the frozen Phase 1 membership predicate applies normally:

abs(incoming_swing_price - current_zone_center) <= current_tolerance

The frozen Phase 1 tolerance-history rules remain unchanged:

- W = 5
- minimum history = 1
- current swing excluded
- HIGH and LOW histories remain separate

## 7. Non-application of pre-Zone membership logic

This specification explicitly does not apply a pre-Zone membership predicate to the first post-seed swing.

It does not define a temporary center.
It does not define a midpoint, seed-price containment rule, interval rule, or any other qualification rule.
It does not reinterpret the Phase 1 membership predicate before valid Zone creation exists.

## 8. Phase 1 integrity

This Phase 2 decision does not modify or reinterpret any Phase 1 frozen decision.

It only defines the single approved formation-state bootstrap needed to create the first valid Zone in a deterministic and explicit way.
