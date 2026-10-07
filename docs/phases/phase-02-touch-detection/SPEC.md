# Phase 2 — Touch Detection Specification

## Status

HUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION

This specification defines the initial Phase 2 formation-state behavior required to establish the first valid Zone. This is not the final Touch Detection specification and does not define unresolved Zone lifecycle semantics.

## 1. Scope

This specification covers only the first valid Zone creation boundary:

- the first eligible same-direction swing becomes the seed/candidate
- the first subsequent eligible same-direction swing after the seed is accepted as the second member and creates the first valid Zone
- the bootstrap formation event used only for that first valid Zone creation
- the transition to the normal Phase 1 membership semantics after Zone creation

This specification does not define final Touch Detection, bar-vs-swing touch behavior, lifecycle events, or unresolved multi-Zone semantics.

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
