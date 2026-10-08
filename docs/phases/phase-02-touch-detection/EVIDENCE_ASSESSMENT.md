# Phase 2 — Evidence Assessment

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

## Objective

This document is a research-only evidence assessment for the approved Phase 2 formation-state boundary and the approved post-Zone touch semantic. Its purpose is to record what the repository authoritatively supports, what remains explicitly unresolved, and where the approved Phase 2 decision ends before any later lifecycle semantics are introduced.

This assessment does not define a new touch model, a pre-zone membership rule, a lifecycle state machine, or any later Zone behavior. It preserves the frozen Phase 1 contract and the narrow Phase 2 approval without inventing semantics.

## Authoritative inputs

The source of truth for this assessment is limited to the repository’s approved documentation and governance records:

- [docs/phases/phase-01-zone-formation/SPEC.md](../phase-01-zone-formation/SPEC.md) — frozen Phase 1 Zone Formation specification
- [docs/phases/phase-02-touch-detection/SPEC.md](SPEC.md) — approved Phase 2 formation-state specification
- [docs/phases/phase-02-touch-detection/DECISIONS.md](DECISIONS.md) — human-approved Phase 2 decision register
- [docs/phases/phase-02-touch-detection/AUDIT.md](AUDIT.md) — repository audit boundary for the Phase 2 decision
- [docs/ROADMAP.md](../../ROADMAP.md) — authoritative current roadmap, including Phase 2 = Touch Detection and Phase 4 = Zone Lifecycle

The governing rule is simple: only facts stated in these authoritative sources are treated as approved evidence. Everything else remains research-only or unresolved.

## Exact chronological event sequence

The approved chronological sequence, as documented in the frozen Phase 1 and Phase 2 approvals, is:

1. A valid Zone does not yet exist.
2. The first eligible same-direction swing becomes the persistent seed/candidate.
3. The seed remains unchanged until the first valid Zone is formed.
4. The first subsequent eligible same-direction swing arrives after the seed.
5. For this single formation event only, the normal Phase 1 membership predicate is not applied because no valid Zone exists yet and therefore no valid Zone center exists.
6. The bootstrap calculation for this single event is:
   T_boot = abs(current_swing_price - seed_price)
7. T_boot is temporary and applies only to the formation event.
8. T_boot is not a legal prior same-direction gap and is not inserted into normal gap history G.
9. The current swing remains excluded from normal tolerance history.
10. The first subsequent eligible same-direction swing is accepted as the second member and creates the first valid Zone.
11. The first valid Zone contains exactly:
   - the seed
   - the first subsequent eligible same-direction swing
12. Once the valid Zone exists, the center is defined as median(member prices).
13. After Zone creation, the frozen Phase 1 membership predicate applies normally:
   abs(incoming_swing_price - current_zone_center) <= current_tolerance
14. The frozen Phase 1 tolerance-history rules remain unchanged.

This sequence is the maximum evidence the repository currently authorizes for Phase 2. It is not a general touch lifecycle and is not a claim about later Zone behavior.

## Observable evidence

The repository evidence is explicit about what is and is not observed in the approved boundary:

- Phase 1 states that the first eligible same-direction swing is a seed/candidate and does not create a valid Zone.
- Phase 1 states that a valid Zone is created when a second same-direction swing qualifies as a member under the existing membership rule.
- Phase 2 confirms that the first post-seed swing is accepted as the second member and creates the first valid Zone.
- Phase 2 explicitly states that no normal Phase 1 membership predicate is applied to this first post-seed swing because no valid Zone exists yet.
- Phase 2 explicitly states that no valid Zone center exists before the first valid Zone is created.
- Phase 2 explicitly states that T_boot is temporary, single-use, and not inserted into the normal gap history G.
- Phase 2 explicitly records that the current swing remains excluded from normal tolerance history.
- Phase 2 explicitly rejects any claim that a temporary center, midpoint rule, interval rule, or pre-zone membership predicate is introduced.
- The same Phase 2 documentation explicitly states that broader touch timestamps, repeated-touch policy, same-bar multiple-touch policy, touch confirmation policy, and Zone lifecycle semantics remain outside scope, while the human-approved post-Zone touch semantic is recorded separately.

These are the observable repository facts. The evidence supports the approved first valid Zone formation bootstrap and the approved post-Zone touch semantic, but it does not authorize a broader touch lifecycle model.

## Candidate classifications without silently choosing semantics

The following classifications are possible labels in research discussion, but the repository does not authorize silent semantic selection beyond the approved formation-state decision:

- Seed / candidate: supported as the first eligible same-direction swing.
- Bootstrap formation trigger: supported for the single first post-seed event that creates the first valid Zone.
- First valid Zone creation event: supported and explicitly approved.
- Pre-Zone membership test: not supported; explicitly rejected by the Phase 2 audit.
- Temporary center / midpoint / seed-containment rule: not supported; explicitly rejected.
- Touch event: approved as the post-Zone semantic classification; once a valid Zone exists, Existing Zone Membership is the Touch event.
- Lifecycle event: not approved; explicitly outside the Phase 2 decision.

The correct research posture is therefore: classify using the approved Phase 2 language only, and do not silently equate the bootstrap event with a later touch or lifecycle concept.

## Evidence-based conclusions

The evidence supports the following conclusions only:

- Phase 1 freezes the core center, tolerance-history, membership, and creation semantics for the first valid Zone only after a valid Zone and valid center exist.
- Phase 2 approves a narrow bootstrap exception for the first valid Zone creation event.
- The approved Phase 2 rule preserves the Phase 1 frozen rules and does not reinterpret them.
- The first post-seed same-direction swing is accepted as the second member and creates the first valid Zone without applying the normal pre-Zone membership predicate.
- The bootstrap calculation is explicitly temporary and not part of the normal gap history G.
- The repository currently supports a precise formation-state boundary and an approved post-Zone touch semantic: Existing Zone Membership is the Touch event; lifecycle semantics and pre-zone semantics remain outside the approved Phase 2 boundary.

## Unsupported/unresolved semantics

The following remain unsupported or explicitly unresolved by the authoritative repository evidence:

- broader bar-vs-swing touch semantics beyond the approved rule
- touch timestamps
- repeated touches
- same-bar multiple touches
- touch confirmation
- Zone lifecycle semantics
- active Zone identity semantics
- multiple active Zone behavior
- overlap/merge behavior
- retirement/replacement behavior
- later member-update semantics
- any pre-Zone membership predicate beyond the documented bootstrap formation-state exception
- any temporary center or midpoint rule not explicitly approved in the frozen contract

The repository does not authorize these as Phase 2 facts.

## Phase 2 vs Phase 4 boundary

The roadmap is explicit: Phase 2 is Touch Detection and Phase 4 is Zone Lifecycle. The current Phase 2 evidence does not cross the Phase 4 boundary.

The approved Phase 2 boundary is intentionally narrow:

- Phase 2 covers the bootstrap formation-state event needed to create the first valid Zone.
- Phase 4 covers lifecycle semantics, which remain explicitly outside the approved Phase 2 decision.
- Therefore, the repository evidence does not allow a Phase 2 claim that the first post-seed event is a later lifecycle state, a touch event with confirmation semantics, or any other Zone lifecycle behavior.

This separation is consistent with the Phase 2 audit and the Phase 1 freeze boundary.

## Minimum additional evidence required

To move beyond the approved narrow Phase 2 decision, the repository would require at least:

1. a specific, human-approved definition of touch semantics, including exactly what counts as a touch and when it is observed
2. a rule for bar-vs-swing comparisons, if the system distinguishes them
3. a definition of confirmation or validity for touch events, if that is part of the intended model
4. a clear lifecycle model covering initial Zone state, persistence, overlap, replacement, and retirement
5. a decision on whether multiple Zones can coexist and how they interact
6. explicit governance that resolves any candidate semantics before they are treated as approved

Without these items, any broader interpretation would be speculation rather than evidence-backed design.

## Human freeze readiness: NO

Human freeze readiness is: NO.

Reason: the repository currently freezes the Phase 1 geometry and the narrow bootstrap semantics, but it does not authorize a broader lifecycle or confirmation model. The approved post-Zone touch semantic is explicitly defined as Existing Zone Membership is the Touch event after a valid Zone exists, while unresolved lifecycle, timestamp, repeated-touch, and confirmation semantics remain outside the approved freeze.
