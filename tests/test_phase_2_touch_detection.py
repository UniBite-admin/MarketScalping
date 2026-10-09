import unittest

from tools.research.phase_1_zone_runtime import Phase1Zone
from tools.research.phase_2_touch_detection import (
    Phase2Zone,
    classify_phase_2_event,
    create_first_zone,
    is_zone_touch,
)


class Phase2TouchDetectionTests(unittest.TestCase):
    def test_bootstrap_formation_event_creates_first_zone(self):
        zone = create_first_zone(100.0, 103.0)
        self.assertEqual(zone.seed_price, 100.0)
        self.assertEqual(zone.member_prices, (100.0, 103.0))
        self.assertEqual(zone.bootstrap_gap, 3.0)
        self.assertEqual(zone.center, 101.5)
        self.assertTrue(zone.current_swing_excluded_from_history)

    def test_bootstrap_gap_is_recorded_separately_from_normal_gap_history(self):
        zone = create_first_zone(100.0, 103.0)
        self.assertEqual(zone.bootstrap_gap, 3.0)
        self.assertTrue(zone.current_swing_excluded_from_history)
        self.assertIn("not inserted into normal gap history", zone.note.lower())

    def test_first_post_seed_swing_is_formation_not_touch(self):
        event = classify_phase_2_event(seed_price=100.0, current_swing_price=103.0, zone=None)
        self.assertEqual(event["kind"], "FORMATION")
        self.assertEqual(event["bootstrap_gap"], 3.0)
        self.assertFalse(event["is_touch"])

    def test_phase_1_membership_predicate_is_used_exactly(self):
        zone = create_first_zone(100.0, 103.0)
        self.assertTrue(is_zone_touch(zone, 99.5, 2.0))
        self.assertTrue(is_zone_touch(zone, 103.5, 2.0))
        self.assertFalse(is_zone_touch(zone, 103.5000001, 2.0))
        self.assertFalse(is_zone_touch(zone, 99.4999999, 2.0))

    def test_phase_2_uses_the_authoritative_phase_1_runtime_membership_rule(self):
        zone = create_first_zone(100.0, 103.0)
        runtime_zone = Phase1Zone("HIGH", (100.0, 103.0), zone.center, 2.0)
        self.assertEqual(is_zone_touch(zone, 101.5, 2.0), runtime_zone.contains_price(101.5))
        self.assertTrue(is_zone_touch(zone, 103.5, 2.0))
        self.assertFalse(is_zone_touch(zone, 103.5000001, 2.0))

    def test_same_input_produces_same_decision(self):
        first = classify_phase_2_event(seed_price=100.0, current_swing_price=103.0, zone=None)
        second = classify_phase_2_event(seed_price=100.0, current_swing_price=103.0, zone=None)
        self.assertEqual(first, second)
        self.assertEqual(first["kind"], "FORMATION")


if __name__ == "__main__":
    unittest.main()
