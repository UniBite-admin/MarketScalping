import unittest

from phase5_contracts import (
    BreakoutParameters,
    CandidateIndex,
    CandidateParameters,
    PatternEvent,
    PinBarParameters,
    TriggerAttribution,
    deduplicate_pattern_events,
)


class TestPhase5Contracts(unittest.TestCase):
    def test_trigger_attribution_is_deterministic(self):
        attribution = TriggerAttribution.from_pattern("ENGULFING", 1, candle_index=42, timestamp_utc="2024-01-01T00:00:00Z")
        self.assertEqual(attribution.pattern_type, "ENGULFING")
        self.assertEqual(attribution.direction, 1)
        self.assertEqual(attribution.trigger_candle, "second_candle")
        self.assertEqual(attribution.as_dict()["candle_index"], 42)

    def test_pattern_event_has_stable_identity_and_deduplication(self):
        event_a = PatternEvent(
            pattern_type="PIN_BAR",
            direction="bullish",
            detection_timestamp="2024-01-01T00:00:00Z",
            candle_start_timestamp="2024-01-01T00:00:00Z",
            candle_end_timestamp="2024-01-01T00:01:00Z",
            candle_indices=(10, 11, 12),
            source_candle_references=("candle_10", "candle_11", "candle_12"),
        )
        event_b = PatternEvent(
            pattern_type="PIN_BAR",
            direction=1,
            detection_timestamp="2024-01-01T00:00:00Z",
            candle_start_timestamp="2024-01-01T00:00:00Z",
            candle_end_timestamp="2024-01-01T00:01:00Z",
            candle_indices=(10, 11, 12),
            source_candle_references=("candle_10", "candle_11", "candle_12"),
        )

        self.assertEqual(event_a.pattern_id, event_b.pattern_id)
        self.assertEqual(event_a.event_identity, event_b.event_identity)
        deduped = deduplicate_pattern_events([event_a, event_b])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].pattern_id, event_a.pattern_id)

    def test_candidate_parameters_are_deterministic(self):
        params = CandidateParameters(
            pattern_type="PIN_BAR",
            direction="bearish",
            pin_bar=PinBarParameters(
                body_max_ratio=0.35,
                wick_to_body_min_ratio=1.5,
                non_dominant_wick_max_ratio=0.45,
            ),
        )
        self.assertEqual(params.direction, -1)
        self.assertEqual(params.grid_tuple, (0.35, 1.5, 0.45))
        self.assertEqual(params.identity_key, ("PIN_BAR", -1, (0.35, 1.5, 0.45)))

    def test_candidate_index_has_stable_identity(self):
        params = CandidateParameters(
            pattern_type="BREAKOUT",
            direction=1,
            breakout=BreakoutParameters(normalized_consolidation_threshold=0.125),
        )
        idx_a = CandidateIndex.from_parameters(params, ordinal=5)
        idx_b = CandidateIndex.from_parameters(params, ordinal=5)
        self.assertEqual(idx_a.identity_key, idx_b.identity_key)
        self.assertEqual(idx_a.index_key, idx_b.index_key)
        self.assertEqual(idx_a.as_dict()["ordinal"], 5)


if __name__ == "__main__":
    unittest.main()
