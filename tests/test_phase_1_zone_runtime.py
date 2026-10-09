import unittest

from tools.research.phase_1_zone_runtime import Phase1ReplayState, Phase1Zone, compute_tolerance, median


class Phase1ZoneRuntimeTests(unittest.TestCase):
    def test_confirmed_and_eligible_inputs_are_processed_in_temporal_order(self):
        runtime = Phase1ReplayState()
        runtime.record_gap("HIGH", 2.0)
        runtime.record_gap("HIGH", 4.0)
        first = runtime.process_eligible_swing("HIGH", 100.0, observed_index=0, confirmed_index=1, eligible_index=2)
        second = runtime.process_eligible_swing("HIGH", 104.0, observed_index=1, confirmed_index=2, eligible_index=3)
        self.assertEqual(first["kind"], "SEED")
        self.assertEqual(second["kind"], "ZONE_CREATED")
        self.assertEqual(second["zone"].member_prices, (100.0, 104.0))

    def test_unconfirmed_or_ineligible_swings_do_not_update_zone_state(self):
        runtime = Phase1ReplayState()
        runtime.process_eligible_swing("LOW", 75.0, observed_index=0, confirmed_index=0, eligible_index=0, is_confirmed=False, is_eligible=True)
        runtime.process_eligible_swing("LOW", 80.0, observed_index=1, confirmed_index=1, eligible_index=1, is_confirmed=True, is_eligible=False)
        self.assertIsNone(runtime.pending_seed_by_side["LOW"])
        self.assertIsNone(runtime.zone_by_side["LOW"])

    def test_high_and_low_history_do_not_contaminate_each_other(self):
        runtime = Phase1ReplayState()
        runtime.record_gap("HIGH", 2.0)
        runtime.record_gap("HIGH", 4.0)
        runtime.record_gap("LOW", 10.0)
        runtime.record_gap("LOW", 20.0)
        self.assertEqual(compute_tolerance(runtime.history_by_side["HIGH"]), 3.0)
        self.assertEqual(compute_tolerance(runtime.history_by_side["LOW"]), 15.0)

    def test_current_swing_is_excluded_from_its_own_tolerance_history(self):
        runtime = Phase1ReplayState()
        runtime.record_gap("HIGH", 2.0)
        runtime.record_gap("HIGH", 4.0)
        runtime.record_gap("HIGH", 6.0)
        runtime.record_gap("HIGH", 8.0)
        self.assertEqual(runtime.compute_tolerance("HIGH"), 5.0)
        self.assertNotIn(100.0, runtime.history_by_side["HIGH"])

    def test_bootstrap_gap_does_not_enter_normal_gap_history(self):
        runtime = Phase1ReplayState()
        runtime.record_gap("HIGH", 2.0)
        runtime.record_gap("HIGH", 4.0)
        first = runtime.process_eligible_swing("HIGH", 100.0, observed_index=0, confirmed_index=1, eligible_index=2)
        second = runtime.process_eligible_swing("HIGH", 104.0, observed_index=1, confirmed_index=2, eligible_index=3)
        self.assertEqual(first["kind"], "SEED")
        self.assertEqual(second["kind"], "ZONE_CREATED")
        self.assertEqual(second["bootstrap_gap"], 4.0)
        self.assertEqual(runtime.history_by_side["HIGH"], [2.0, 4.0])

    def test_zone_center_is_median_of_current_member_prices(self):
        runtime = Phase1ReplayState()
        runtime.record_gap("HIGH", 2.0)
        runtime.record_gap("HIGH", 4.0)
        runtime.process_eligible_swing("HIGH", 100.0, observed_index=0, confirmed_index=1, eligible_index=2)
        event = runtime.process_eligible_swing("HIGH", 106.0, observed_index=1, confirmed_index=2, eligible_index=3)
        self.assertEqual(event["zone"].center, 103.0)
        self.assertEqual(event["zone"].member_prices, (100.0, 106.0))

    def test_membership_is_inclusive_at_the_boundary(self):
        zone = Phase1Zone("HIGH", (100.0, 108.0), 104.0, 4.0)
        self.assertTrue(zone.contains_price(104.0))
        self.assertTrue(zone.contains_price(100.0))
        self.assertTrue(zone.contains_price(108.0))

    def test_values_just_outside_boundary_are_rejected(self):
        zone = Phase1Zone("HIGH", (100.0, 108.0), 104.0, 4.0)
        self.assertFalse(zone.contains_price(108.0000001))
        self.assertFalse(zone.contains_price(99.9999999))

    def test_identical_ordered_inputs_replay_to_identical_state(self):
        first = Phase1ReplayState()
        first.record_gap("HIGH", 2.0)
        first.record_gap("HIGH", 4.0)
        events = [
            {"side": "HIGH", "price": 100.0, "observed_index": 0, "confirmed_index": 1, "eligible_index": 2, "is_confirmed": True, "is_eligible": True},
            {"side": "HIGH", "price": 106.0, "observed_index": 1, "confirmed_index": 2, "eligible_index": 3, "is_confirmed": True, "is_eligible": True},
            {"side": "HIGH", "price": 103.0, "observed_index": 2, "confirmed_index": 3, "eligible_index": 4, "is_confirmed": True, "is_eligible": True},
        ]
        second = Phase1ReplayState()
        second.record_gap("HIGH", 2.0)
        second.record_gap("HIGH", 4.0)
        first.replay_events(events)
        second.replay_events(list(events))
        self.assertEqual(first.events, second.events)
        self.assertEqual(first.zone_by_side["HIGH"].member_prices, second.zone_by_side["HIGH"].member_prices)

    def test_future_events_do_not_affect_decisions_before_they_are_eligible(self):
        runtime = Phase1ReplayState()
        runtime.record_gap("HIGH", 2.0)
        runtime.record_gap("HIGH", 4.0)
        runtime.process_eligible_swing("HIGH", 100.0, observed_index=0, confirmed_index=0, eligible_index=0, is_confirmed=True, is_eligible=True)
        runtime.process_eligible_swing("HIGH", 104.0, observed_index=1, confirmed_index=1, eligible_index=1, is_confirmed=True, is_eligible=True)
        runtime.process_eligible_swing("HIGH", 103.0, observed_index=2, confirmed_index=2, eligible_index=2, is_confirmed=True, is_eligible=True)
        self.assertEqual(runtime.events[0]["kind"], "SEED")
        self.assertEqual(runtime.events[1]["kind"], "ZONE_CREATED")

    def test_median_helper_matches_authoritative_definition(self):
        self.assertEqual(median([2.0, 4.0, 6.0]), 4.0)
        self.assertEqual(median([2.0, 4.0]), 3.0)


if __name__ == "__main__":
    unittest.main()
