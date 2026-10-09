# Phase 2 — Touch Model Research

## Status

RESEARCH ARTIFACT ONLY

This document is a research note intended to reconcile the approved Phase 2 formation-state boundary with the broader concept of “touch detection.” It does not define final Touch Detection semantics, does not alter any frozen Phase 1 behavior, and does not claim approval for later lifecycle logic.

## Human decision record (dated 2026-10-08)

Decision A — approved Phase 2 formation-state boundary.

This human decision records the approved Phase 2 semantics for the first valid Zone creation event and the approved post-Zone touch semantic:

- Pre-Zone state: no valid Zone exists, therefore no valid Zone center exists.
- First post-seed formation event: the first subsequent eligible same-direction swing is accepted as the second member and creates the first valid Zone.
- Bootstrap calculation for that event only:
  T_boot = abs(current_swing_price - seed_price)
- T_boot is temporary only for the formation event and is not inserted into G.
- Current swing remains excluded from normal tolerance history.
- Post-Zone touch semantic: once a valid Zone exists, Existing Zone Membership is the Touch event under the frozen Phase 1 membership predicate.
- In practical terms, any later eligible observation satisfying:
  abs(incoming_swing_price - current_zone_center) <= current_tolerance
  is a Zone Touch.
- The first post-seed swing that creates the first valid Zone is Formation only, not a Touch.
- Frozen Phase 1 membership logic remains the authority for post-Zone touch classification.

Mandatory boundaries of Decision A:
- This decision defines the approved post-Zone touch semantic: Existing Zone Membership is the Touch event.
- This decision is limited to the first valid Zone formation event and the subsequent post-Zone touch classification after a valid Zone exists.
- It does not redefine or replace the frozen Phase 1 membership predicate.
- It does not authorize any pre-Zone membership test, temporary center, midpoint rule, interval rule, or other pre-Zone qualification rule.
- It does not resolve touch timestamps, repeated-touch policy, same-bar multiplicity, touch confirmation, bar-vs-swing behavior beyond the approved eligible-swing membership rule, multiple active Zones, overlap or merge, retirement or replacement, or later Zone member-update semantics.
- Any broader timing, confirmation, lifecycle, or member-update interpretation remains outside the approved scope and requires a separate human decision.

## Phase 2 semantic freeze

The approved Phase 2 semantic boundary is:

- Pre-Zone state: no valid Zone exists, therefore no valid Zone center exists.
- First post-seed formation event: the first subsequent eligible same-direction swing is accepted as the second member and creates the first valid Zone.
- Bootstrap calculation for that event only:
  T_boot = abs(current_swing_price - seed_price)
- T_boot is temporary only for the formation event and is not inserted into G.
- Current swing remains excluded from normal tolerance history.
- Post-Zone touch semantic: once a valid Zone exists, Existing Zone Membership is the Touch event under the frozen Phase 1 membership predicate.
- In practical terms, any later eligible observation satisfying abs(incoming_swing_price - current_zone_center) <= current_tolerance is a Zone Touch.
- The first post-seed swing that creates the first valid Zone is Formation only, not Touch.

This is intentionally narrow and is not a redefinition of the Phase 1 membership predicate.

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

## Objective

The objective of this research is to describe the most defensible interpretation of the repository evidence while staying within the explicit Phase 2 approval boundary.

The governing rule is narrow: only facts stated in the approved Phase 1 and Phase 2 documentation may be treated as evidence. Anything beyond that remains open research, not repository fact.

## Executive summary

The repository evidence supports a single, explicitly limited bootstrap event for the first valid Zone:

- the first eligible same-direction swing becomes the persistent seed/candidate
- the first subsequent eligible same-direction swing becomes the second member
- that second member creates the first valid Zone
- the normal Phase 1 membership predicate is not applied to that bootstrap event because no valid Zone center exists yet
- the temporary bootstrap value is defined as:
  T_boot = abs(current_swing_price - seed_price)
- T_boot is temporary, single-use, and not inserted into normal gap history G

This is a formation-state rule plus the approved post-Zone Touch classification, not a complete lifecycle or timing model.

The repository does authorize the approved post-Zone touch semantic: once a valid Zone exists, Existing Zone Membership is the Touch event under the frozen Phase 1 membership predicate. Broader timing, repeated-touch, confirmation, and lifecycle rules remain unresolved and explicitly outside the approved Phase 2 scope.

## Authoritative evidence boundary

The evidence for this research is limited to the repository’s approved Phase 1 and Phase 2 documentation:

- [docs/phases/phase-01-zone-formation/SPEC.md](../phase-01-zone-formation/SPEC.md)
- [docs/phases/phase-02-touch-detection/SPEC.md](SPEC.md)
- [docs/phases/phase-02-touch-detection/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-02-touch-detection/EVIDENCE_ASSESSMENT.md](EVIDENCE_ASSESSMENT.md)
- [docs/ROADMAP.md](../../ROADMAP.md)

The primary design fact is that Phase 1 frozen logic remains authoritative. Phase 2 only approves a limited formation-state exception needed to create the first valid Zone.

## What the repository explicitly supports

The approved evidence supports the following sequence:

1. A valid Zone does not yet exist.
2. The first eligible same-direction swing becomes the seed/candidate.
3. The seed remains unchanged until the first valid Zone is formed.
4. The next eligible same-direction swing becomes the second member and forms the first valid Zone.
5. Because no valid Zone exists yet, no valid Zone center exists yet.
6. Therefore the normal Phase 1 membership predicate is not applied to this formation event.
7. The temporary bootstrap value is computed as:
   T_boot = abs(current_swing_price - seed_price)
8. T_boot is not added to normal tolerance history.
9. After first Zone creation, the center is defined as median(member prices).
10. After the Zone exists, the frozen Phase 1 membership test applies normally:
    abs(incoming_swing_price - current_zone_center) <= current_tolerance

This produces a clear model boundary:

- before Zone creation: no pre-Zone membership rule is allowed to masquerade as a normal touch test
- at Zone creation: a single bootstrap event creates the first valid Zone
- after Zone creation: standard Zone center and tolerance logic governs later membership behavior

## What the repository explicitly does not support

The repository evidence explicitly rejects or defers multiple broader interpretations:

- a temporary Zone center before valid Zone creation
- a midpoint or seed-price containment rule before Zone creation
- a general touch model that applies before the first valid Zone exists
- touch timestamps, confirmation, or validity rules
- repeated-touch semantics
- same-bar multiple-touch semantics
- bar-vs-swing touch definitions
- lifecycle semantics such as overlap, merge, retirement, or replacement
- multi-Zone behavior and inter-Zone membership conflicts
- any claim that the bootstrap formation event is already a final touch-detection specification

The evidence is therefore intentionally conservative and narrow: it documents the first valid Zone formation event only.

## Research interpretation of “touch” in the current repository state

The repository-accurate interpretation is:

- the approved post-Zone semantic is: Existing Zone Membership is the Touch event under the frozen Phase 1 membership predicate
- a later eligible swing satisfying abs(incoming_swing_price - current_zone_center) <= current_tolerance is classified as a Zone Touch
- the first post-seed swing that creates the first valid Zone remains Formation only, not Touch
- the approved semantics are limited to the membership-based post-Zone Touch classification
- broader timing, repeated-touch, same-bar multiplicity, confirmation, and lifecycle semantics remain unresolved unless separately approved
- this document remains research-only and is not a claim of code/test implementation

In other words, the current Phase 2 evidence supports an approved post-Zone membership-based Touch classification plus the required bootstrap formation-state transition, while broader lifecycle and timing semantics remain outside the current approval boundary.

## Recommended model posture

The research recommendation is to keep the model posture strictly bounded:

1. Use the approved formation-state language only.
2. Treat the first post-seed same-direction swing as the bootstrap confirmation of the first valid Zone.
3. Keep the temporary bootstrap gap isolated to the formation event.
4. Preserve frozen Phase 1 center and tolerance semantics after Zone creation.
5. Explicitly defer all broader touch semantics to a later design milestone.

This posture aligns with the roadmap and preserves the repository’s documented governance boundary.

## Conclusion

The current repository evidence authorizes the approved post-Zone Touch semantic: once a valid Zone exists, Existing Zone Membership is the Touch event under the frozen Phase 1 membership predicate. It also authorizes the first valid Zone bootstrap event and keeps broader timing, repeated-touch, confirmation, and lifecycle rules outside the current Phase 2 approval.

That means the correct research conclusion is:

- the bootstrap event is real and approved
- the post-Zone Touch rule is approved as Existing Zone Membership under the frozen Phase 1 membership predicate
- the first post-seed swing that creates the first valid Zone is Formation only, not Touch
- broader timing, repeated-touch, same-bar multiplicity, confirmation, and lifecycle semantics remain unresolved and intentionally outside current scope
- any future touch semantics must be defined explicitly and approved before they can be treated as repository truth

## Boundary statement

This document is intentionally a research artifact. It is not a change to production logic, not an approval of later lifecycle behavior, and not a claim that the system has a finalized touch detection engine. It is a careful record of the repository’s current evidence and the precise boundary of what is actually supported.
