import unittest
from datetime import datetime, timedelta, timezone

from phase5_contracts import BreakoutParameters, PatternEvent, PinBarParameters, deduplicate_pattern_events
from phase5_pattern_engine import (
    CanonicalCandle,
    detect_breakout_events,
    detect_engulfing_events,
    detect_pin_bar_events,
    detect_shrinking_events,
    detect_three_bar_continuation_events,
    detect_three_bar_reversal_events,
)


def dt(s: str):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


class TestPhase5PatternEngine(unittest.TestCase):
    def candle(self, idx: int, ts: str, open_: float, high: float, low: float, close_: float):
        ts_dt = dt(ts)
        return CanonicalCandle(
            index=idx,
            timestamp_utc=ts_dt.isoformat().replace("+00:00", "Z"),
            open_time_utc=(ts_dt - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            close_time_utc=ts_dt.isoformat().replace("+00:00", "Z"),
            open=open_,
            high=high,
            low=low,
            close=close_,
        )

    def test_engulfing_valid_bullish_and_bearish(self):
        bullish = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 106.0, 90.0, 90.0),
            self.candle(1, "2024-01-01T00:01:00Z", 88.0, 112.0, 87.0, 109.0),
        ]
        events = detect_engulfing_events(bullish)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].pattern_type, "ENGULFING")
        self.assertEqual(events[0].direction, 1)
        self.assertEqual(events[0].trigger_attribution.trigger_candle, "second_candle")

        bearish = [
            self.candle(0, "2024-01-01T00:00:00Z", 90.0, 100.0, 90.0, 100.0),
            self.candle(1, "2024-01-01T00:01:00Z", 111.0, 111.0, 88.0, 88.0),
        ]
        events = detect_engulfing_events(bearish)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].direction, -1)

    def test_engulfing_rejects_invalid_cases(self):
        neutral_first = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 101.0, 99.0, 100.0),
            self.candle(1, "2024-01-01T00:01:00Z", 88.0, 112.0, 87.0, 109.0),
        ]
        self.assertEqual(detect_engulfing_events(neutral_first), [])

        same_direction = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 106.0, 90.0, 90.0),
            self.candle(1, "2024-01-01T00:01:00Z", 92.0, 101.0, 90.0, 94.0),
        ]
        self.assertEqual(detect_engulfing_events(same_direction), [])

        lower_body = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 106.0, 90.0, 90.0),
            self.candle(1, "2024-01-01T00:01:00Z", 95.0, 101.0, 94.0, 99.0),
        ]
        self.assertEqual(detect_engulfing_events(lower_body), [])

    def test_pin_bar_valid_and_directional_midpoint(self):
        params = PinBarParameters(0.35, 1.5, 0.45)

        bullish_valid = self.candle(0, "2024-01-01T00:00:00Z", 100.0, 110.0, 90.0, 106.0)
        self.assertEqual(len(detect_pin_bar_events([bullish_valid], params)), 1)

        bearish_valid = self.candle(0, "2024-01-01T00:00:00Z", 100.0, 130.0, 70.0, 85.0)
        self.assertEqual(len(detect_pin_bar_events([bearish_valid], params)), 1)

        too_large_body_ratio = self.candle(0, "2024-01-01T00:00:00Z", 100.0, 109.0, 90.0, 107.0)
        self.assertEqual(detect_pin_bar_events([too_large_body_ratio], params), [])

        invalid_midpoint = self.candle(0, "2024-01-01T00:00:00Z", 104.0, 110.0, 90.0, 96.0)
        self.assertEqual(detect_pin_bar_events([invalid_midpoint], params), [])

    def test_three_bar_continuation_exact_rule(self):
        valid = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 104.0, 96.0, 104.0),
            self.candle(1, "2024-01-01T00:01:00Z", 103.0, 104.5, 101.0, 101.0),
            self.candle(2, "2024-01-01T00:02:00Z", 101.0, 110.0, 98.0, 109.0),
        ]
        events = detect_three_bar_continuation_events(valid)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].direction, 1)
        self.assertEqual(events[0].trigger_attribution.trigger_candle, "third_candle")

        too_large_second = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 104.0, 96.0, 104.0),
            self.candle(1, "2024-01-01T00:01:00Z", 104.5, 105.0, 100.0, 101.0),
            self.candle(2, "2024-01-01T00:02:00Z", 101.0, 110.0, 98.0, 109.0),
        ]
        self.assertEqual(detect_three_bar_continuation_events(too_large_second), [])

        wrong_direction = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 104.0, 96.0, 104.0),
            self.candle(1, "2024-01-01T00:01:00Z", 103.0, 104.5, 101.0, 101.0),
            self.candle(2, "2024-01-01T00:02:00Z", 101.0, 103.0, 100.0, 101.0),
        ]
        self.assertEqual(detect_three_bar_continuation_events(wrong_direction), [])

    def test_three_bar_reversal_strict_strength(self):
        strong = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 110.0, 96.0, 104.0),
            self.candle(1, "2024-01-01T00:01:00Z", 101.0, 108.0, 100.0, 103.0),
            self.candle(2, "2024-01-01T00:02:00Z", 103.0, 110.0, 88.0, 96.0),
        ]
        strong_events = detect_three_bar_reversal_events(strong)
        self.assertEqual(len(strong_events), 1)
        self.assertEqual(strong_events[0].direction, -1)
        self.assertEqual(strong_events[0].strength, "STRONG")

        weak = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 110.0, 96.0, 104.0),
            self.candle(1, "2024-01-01T00:01:00Z", 101.0, 108.0, 100.0, 103.0),
            self.candle(2, "2024-01-01T00:02:00Z", 103.0, 109.0, 95.0, 100.0),
        ]
        weak_events = detect_three_bar_reversal_events(weak)
        self.assertEqual(len(weak_events), 1)
        self.assertEqual(weak_events[0].direction, -1)
        self.assertEqual(weak_events[0].strength, "WEAK")

        same_direction = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 110.0, 96.0, 104.0),
            self.candle(1, "2024-01-01T00:01:00Z", 101.0, 108.0, 100.0, 103.0),
            self.candle(2, "2024-01-01T00:02:00Z", 103.0, 108.0, 101.0, 107.0),
        ]
        self.assertEqual(detect_three_bar_reversal_events(same_direction), [])

    def test_breakout_requires_close_crossing(self):
        valid = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 100.5, 99.5, 100.2),
            self.candle(1, "2024-01-01T00:01:00Z", 100.2, 100.7, 99.8, 100.4),
            self.candle(2, "2024-01-01T00:02:00Z", 100.4, 100.8, 100.0, 100.6),
            self.candle(3, "2024-01-01T00:03:00Z", 100.8, 101.4, 100.4, 101.2),
            self.candle(4, "2024-01-01T00:04:00Z", 101.4, 102.0, 101.2, 101.8),
        ]
        breakout_events = detect_breakout_events(valid, BreakoutParameters(0.10))
        self.assertEqual(len(breakout_events), 1)
        self.assertEqual(breakout_events[0].direction, 1)

        wick_only = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 100.6, 99.7, 100.1),
            self.candle(1, "2024-01-01T00:01:00Z", 100.2, 100.9, 99.8, 100.4),
            self.candle(2, "2024-01-01T00:02:00Z", 100.5, 101.0, 100.1, 100.7),
            self.candle(3, "2024-01-01T00:03:00Z", 100.8, 101.5, 100.4, 100.9),
            self.candle(4, "2024-01-01T00:04:00Z", 100.9, 101.8, 100.6, 100.7),
        ]
        self.assertEqual(detect_breakout_events(wick_only, BreakoutParameters(0.10)), [])

    def test_shrinking_pairwise_body_decay(self):
        valid = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 103.5, 98.5, 103.0),
            self.candle(1, "2024-01-01T00:01:00Z", 103.0, 105.5, 102.0, 105.0),
            self.candle(2, "2024-01-01T00:02:00Z", 105.0, 106.5, 104.5, 106.0),
            self.candle(3, "2024-01-01T00:03:00Z", 106.0, 108.5, 103.0, 104.2),
            self.candle(4, "2024-01-01T00:04:00Z", 104.2, 107.0, 100.0, 102.0),
        ]
        events = detect_shrinking_events(valid)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].direction, 1)
        self.assertEqual(events[0].trigger_attribution.trigger_candle, "opposite_direction_reversal_candle")

        invalid = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 103.5, 98.5, 103.0),
            self.candle(1, "2024-01-01T00:01:00Z", 103.0, 105.5, 102.0, 105.0),
            self.candle(2, "2024-01-01T00:02:00Z", 105.0, 106.5, 104.5, 106.0),
            self.candle(3, "2024-01-01T00:03:00Z", 104.5, 108.0, 103.0, 108.0),
            self.candle(4, "2024-01-01T00:04:00Z", 108.0, 109.0, 100.0, 102.0),
        ]
        self.assertEqual(detect_shrinking_events(invalid), [])

    def test_cross_pattern_dedup_and_ordering(self):
        bullish = [
            self.candle(0, "2024-01-01T00:00:00Z", 100.0, 106.0, 90.0, 90.0),
            self.candle(1, "2024-01-01T00:01:00Z", 88.0, 112.0, 87.0, 109.0),
        ]
        event = detect_engulfing_events(bullish)[0]
        duplicate = PatternEvent(
            pattern_type="ENGULFING",
            direction=1,
            detection_timestamp="2024-01-01T00:01:00Z",
            candle_start_timestamp="2024-01-01T00:00:00Z",
            candle_end_timestamp="2024-01-01T00:01:00Z",
            candle_indices=(0, 1),
            source_candle_references=("candle_0", "candle_1"),
        )
        deduped = deduplicate_pattern_events([event, duplicate])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].event_identity, ("ENGULFING", 1, "2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"))


if __name__ == "__main__":
    unittest.main()
