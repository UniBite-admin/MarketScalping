# Phase 2 â€” Touch Detection Audit

## Status

HUMAN APPROVED â€” PHASE 2 FORMATION-STATE DECISION

This audit records the repository evidence boundary for the approved Phase 2 formation-state decision and the post-Zone touch semantic. It explicitly separates the bootstrap formation event from normal post-Zone membership and records that Existing Zone Membership is the Touch event after a valid Zone exists.

## Human decision record (dated 2026-10-08)

Decision A â€” approved Phase 2 formation-state boundary.

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

### Phase 2 explicit acceptance (dated 2026-10-09)

Phase 2 acceptance: ACCEPTED.

Human decision: "I accept Phase 2 based on the current evidence."

This acceptance applies only to the approved Phase 2 scope documented in the existing Phase 2 decision records. It does not independently authorize Phase 2 freeze or progression to Phase 3.

## 5. Acceptance matrix and verification evidence (dated 2026-10-09)

This section records the evidence reconciliation for the requirement IDs present in TEST_REQUIREMENTS.md. It does not replace the earlier human decision or the semantic-freeze record. It records the current evidence status for continuation of the approved narrow boundary only.

| Requirement ID | Required behavior | Exact test method name, if one exists | Evidence examined | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| T2-01 | The first eligible same-direction swing becomes the persistent seed/candidate. | tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_confirmed_and_eligible_inputs_are_processed_in_temporal_order; tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_unconfirmed_or_ineligible_swings_do_not_update_zone_state | Phase1ReplayState.process_eligible_swing and its seed creation branch | PASS | Assertions verify that a first eligible swing creates a SEED and that no later swing replaces it before Zone creation. |
| T2-02 | The seed remains unchanged until the first valid Zone is formed. | tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_confirmed_and_eligible_inputs_are_processed_in_temporal_order; tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_future_events_do_not_affect_decisions_before_they_are_eligible | Phase1ReplayState.process_eligible_swing before and after Zone creation | PASS | The seed persists until a valid Zone is created; later eligible swings do not mutate the pending seed before Zone creation. |
| T2-03 | The first subsequent eligible same-direction swing after the seed creates the first valid Zone. | tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_bootstrap_formation_event_creates_first_zone; tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_first_post_seed_swing_is_formation_not_touch | create_first_zone and classify_phase_2_event for the formation event | PASS | Assertions verify that the first post-seed swing becomes the second member and creates the first Zone. |
| T2-04 | The normal Phase 1 membership predicate is not applied before Zone creation. | tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_first_post_seed_swing_is_formation_not_touch | classify_phase_2_event with zone=None and creation semantics | PASS | The event is classified as FORMATION, is_touch is False, and the bootstrap path is distinct from post-Zone membership. |
| T2-05 | T_boot = abs(current_swing_price - seed_price) for the formation event only. | tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_bootstrap_formation_event_creates_first_zone | create_first_zone and Phase2Zone.bootstrap_gap | PASS | Assertions confirm bootstrap_gap equals abs(swing - seed). |
| T2-06 | T_boot is temporary and not inserted into normal gap history G. | tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_bootstrap_gap_does_not_enter_normal_gap_history; tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_bootstrap_gap_is_recorded_separately_from_normal_gap_history | Phase1ReplayState.history_by_side and the Phase 2 note field | PASS | The bootstrap gap is tracked separately and the runtime history remains unchanged. |
| T2-07 | The current swing remains excluded from normal tolerance history. | tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_current_swing_is_excluded_from_its_own_tolerance_history | Phase1ReplayState.compute_tolerance and history_by_side | PASS | The test asserts the current swing price is not in the tolerance-history list. |
| T2-08 | The first valid Zone contains exactly the seed and the first subsequent eligible same-direction swing. | tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_bootstrap_formation_event_creates_first_zone; tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_confirmed_and_eligible_inputs_are_processed_in_temporal_order | Phase2Zone.member_prices and Phase1ReplayState.zone_by_side | PASS | Assertions confirm the Zone contains exactly two members and those two members are the seed and the post-seed swing. |
| T2-09 | The Zone center is created after Zone formation as the median of member prices. | tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_zone_center_is_median_of_current_member_prices | Phase1Zone.center and median helper | PASS | Assertions verify center = median(member prices) for the first valid Zone. |
| T2-10 | Post-Zone membership uses the frozen Phase 1 rule abs(incoming_swing_price - current_zone_center) <= current_tolerance. | tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_phase_1_membership_predicate_is_used_exactly; tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_phase_2_uses_the_authoritative_phase_1_runtime_membership_rule | is_zone_touch and Phase1Zone.contains_price | PASS | The boundary-inclusive test and authoritative-runtime comparison are both asserted. |
| T2-11 | W = 5 and minimum history = 1 remain unchanged. | tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_high_and_low_history_do_not_contaminate_each_other; tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_current_swing_is_excluded_from_its_own_tolerance_history | Phase1ReplayState.w, min_history, compute_tolerance, select_recent_gaps | PASS | The runtime uses the same W = 5/min_history = 1 semantics and keeps HIGH and LOW histories separate. |
| T2-12 | Identical canonical input produces the same deterministic seed and Zone result. | tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_identical_ordered_inputs_replay_to_identical_state; tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_same_input_produces_same_decision | Phase1ReplayState.replay_events and classify_phase_2_event | PASS | The tests assert identical replay produces identical state and identical decision. |
| T2-13 | No look-ahead is used in the formation decision. | tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_future_events_do_not_affect_decisions_before_they_are_eligible | Phase1ReplayState.process_eligible_swing with ordered eligibility checks | PASS | The decision is based only on known eligible and confirmed factors; future events are not used. |
| T2-14 | No Phase 1 frozen decision is amended, weakened, or replaced. | tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_phase_2_uses_the_authoritative_phase_1_runtime_membership_rule; tests.test_phase_1_zone_runtime.Phase1ZoneRuntimeTests.test_bootstrap_gap_does_not_enter_normal_gap_history | Phase2 helper delegates to the frozen Phase 1 runtime membership logic | PASS | The implementation preserves the frozen Phase 1 membership predicate and separates the bootstrap exception from normal history. |
| T2-15 | Once a valid Zone exists, any later eligible observation satisfying abs(incoming_swing_price - current_zone_center) <= current_tolerance is a Zone Touch; the first post-seed swing that creates the Zone is a Formation event only. | tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_phase_1_membership_predicate_is_used_exactly; tests.test_phase_2_touch_detection.Phase2TouchDetectionTests.test_first_post_seed_swing_is_formation_not_touch | classify_phase_2_event and is_zone_touch | PASS | Assertions verify both the exact membership boundary and the distinction between Formation and Touch semantics. |

### Focused verification result

Command executed:
python -m unittest tests.test_phase_1_zone_runtime tests.test_phase_2_touch_detection tests.test_phase_runner -v

Observed result:
Ran 29 tests in 0.657s
OK

### Acceptance interpretation

This evidence is sufficient to record the narrow Phase 2 semantic boundary and implementation authorization as supported by the frozen Phase 1 rule and the targeted runtime tests. It does not convert the Phase 2 work into a broad phase freeze or a full phase acceptance.

The repository's authoritative roadmap still requires explicit phase acceptance before advancing beyond the current phase, and the implementation authorization in DECISIONS.md explicitly excludes broader lifecycle work, broader Phase 2 semantics, freeze, and full Phase 2 acceptance.




