import unittest
from unittest.mock import patch

from replay_runner import ReplayRunner


class ReplayRunnerTests(unittest.TestCase):
    def _fixture_events(self):
        ordered = [
            {
                "event_time_utc": "2025-01-01T12:00:01Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95000.0,
                "ask": 95001.0,
                "last": 95000.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:02Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95001.0,
                "ask": 95002.0,
                "last": 95001.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:03Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95002.0,
                "ask": 95003.0,
                "last": 95002.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:04Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95003.0,
                "ask": 95004.0,
                "last": 95003.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:05Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95004.0,
                "ask": 95005.0,
                "last": 95004.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:06Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95005.0,
                "ask": 95006.0,
                "last": 95005.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:07Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95006.0,
                "ask": 95007.0,
                "last": 95006.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:08Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95007.0,
                "ask": 95008.0,
                "last": 95007.5,
            },
        ]

        return [ordered[4], ordered[0], ordered[6], ordered[2], ordered[1], ordered[7], ordered[3], ordered[5]]

    def test_minimal_historical_replay_succeeds_and_is_chronological(self):
        runner = ReplayRunner(position_max_hold_events=2)
        result = runner.replay(self._fixture_events())

        expected_times = tuple(
            [
                "2025-01-01T12:00:01+00:00",
                "2025-01-01T12:00:02+00:00",
                "2025-01-01T12:00:03+00:00",
                "2025-01-01T12:00:04+00:00",
                "2025-01-01T12:00:05+00:00",
                "2025-01-01T12:00:06+00:00",
                "2025-01-01T12:00:07+00:00",
                "2025-01-01T12:00:08+00:00",
            ]
        )

        self.assertEqual(result.events_total, 8)
        self.assertEqual(result.events_rejected, 0)
        self.assertEqual(result.events_processed, 8)
        self.assertEqual(result.event_timestamps, expected_times)
        self.assertEqual(result.strategy_timestamps, expected_times)
        self.assertEqual(result.risk_timestamps, expected_times)
        self.assertEqual(result.execution_timestamps, expected_times)
        self.assertEqual(result.position_timestamps, expected_times[5:])
        self.assertEqual(result.closed_trade_count, 1)
        self.assertGreater(result.strategy_decisions, 0)
        self.assertGreater(result.risk_decisions, 0)
        self.assertGreater(result.execution_events, 0)
        self.assertGreater(result.position_events, 0)
        self.assertIsNotNone(result.final_account_balance)
        self.assertIsNotNone(result.final_equity)
        self.assertIsNotNone(result.realized_pnl)
        self.assertTrue(all(ts in expected_times for ts in result.account_timestamps))

    def test_same_dataset_replayed_twice_is_identical(self):
        runner = ReplayRunner(position_max_hold_events=2)
        dataset = self._fixture_events()

        first = runner.replay(dataset)
        second = runner.replay(dataset)

        self.assertEqual(first, second)

    def test_replay_accepts_single_pass_generator_input(self):
        runner = ReplayRunner(position_max_hold_events=2)

        class SinglePassGenerator:
            def __init__(self, items):
                self._iterator = iter(items)
                self._consumed = False

            def __iter__(self):
                if self._consumed:
                    raise RuntimeError("single-pass iterable was re-iterated")
                self._consumed = True
                return self._iterator

        result = runner.replay(SinglePassGenerator(self._fixture_events()))

        self.assertEqual(result.events_processed, 8)
        self.assertEqual(result.events_rejected, 0)
        self.assertEqual(result.dataset_status, "CANONICALIZED")

    def test_summary_mode_streams_chronological_input_without_timestamp_traces(self):
        runner = ReplayRunner(position_max_hold_events=2)

        result = runner.replay(
            iter(sorted(self._fixture_events(), key=lambda item: item["event_time_utc"])),
            assume_canonical_chronological=True,
            summary_mode=True,
        )

        self.assertEqual(result.events_processed, 8)
        self.assertEqual(result.events_rejected, 0)
        self.assertEqual(result.event_timestamps, ())
        self.assertEqual(result.strategy_timestamps, ())
        self.assertEqual(result.dataset_status, "CANONICALIZED")

    def test_same_timestamp_events_follow_canonical_original_index_order(self):
        runner = ReplayRunner(position_max_hold_events=2)
        captured = []

        class DummyEngine:
            def handle_control_message(self, message, event_time_utc=None):
                captured.append((event_time_utc, message.get("lastPrice", message.get("price"))))

        with patch.object(ReplayRunner, "_build_engine", return_value=DummyEngine()):
            result = runner.replay([
                {
                    "event_time_utc": "2025-01-01T12:00:00Z",
                    "event_type": "ticker",
                    "market": "BTC-EUR",
                    "bid": 99.0,
                    "ask": 100.0,
                    "last": 99.5,
                },
                {
                    "event_time_utc": "2025-01-01T12:00:00Z",
                    "event_type": "ticker",
                    "market": "BTC-EUR",
                    "bid": 100.0,
                    "ask": 101.0,
                    "last": 100.5,
                },
            ])

        self.assertEqual(result.events_processed, 2)
        self.assertEqual([price for _, price in captured], [99.5, 100.5])
        self.assertEqual(result.event_timestamps, ("2025-01-01T12:00:00+00:00", "2025-01-01T12:00:00+00:00"))

    def test_canonical_dataset_state_and_replay_eligibility_are_explicit(self):
        runner = ReplayRunner(position_max_hold_events=2)
        success = runner.replay(self._fixture_events())
        self.assertEqual(success.dataset_status, "CANONICALIZED")
        self.assertEqual(success.canonicalization_result, "SUCCESS")

        rejected = runner.replay([
            {
                "event_time_utc": "2025-01-01T12:00:00Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 95000.0,
                "ask": 95001.0,
                "last": 0.0,
            }
        ])
        self.assertEqual(rejected.dataset_status, "REJECTED")
        self.assertEqual(rejected.canonicalization_result, "REJECTED")

    def test_invalid_timestamp_is_rejected_without_wall_clock_fallback(self):
        runner = ReplayRunner(position_max_hold_events=2)
        result = runner.replay(
            [
                {
                    "event_time_utc": "2025-01-01T12:00:00",
                    "event_type": "ticker",
                    "market": "BTC-EUR",
                    "bid": 95000.0,
                    "ask": 95001.0,
                    "last": 95000.5,
                }
            ]
        )

        self.assertEqual(result.events_total, 1)
        self.assertEqual(result.events_processed, 0)
        self.assertEqual(result.events_rejected, 1)
        self.assertIn(("invalid_event_time_utc", 1), result.rejection_reasons)
        self.assertEqual(result.event_timestamps, ())

    def test_invalid_market_and_price_data_are_rejected_safely(self):
        runner = ReplayRunner(position_max_hold_events=2)
        result = runner.replay(
            [
                {
                    "event_time_utc": "2025-01-01T12:00:00Z",
                    "event_type": "ticker",
                    "market": "btc-eur",
                    "bid": -1.0,
                    "ask": 0.0,
                    "last": 0.0,
                }
            ]
        )

        self.assertEqual(result.events_processed, 0)
        self.assertEqual(result.events_rejected, 1)
        self.assertIn(("invalid_market", 1), result.rejection_reasons)

    def test_invalid_price_data_is_rejected_safely(self):
        runner = ReplayRunner(position_max_hold_events=2)
        result = runner.replay(
            [
                {
                    "event_time_utc": "2025-01-01T12:00:00Z",
                    "event_type": "ticker",
                    "market": "BTC-EUR",
                    "bid": -1.0,
                    "ask": 95001.0,
                    "last": 95000.5,
                }
            ]
        )

        self.assertEqual(result.events_processed, 0)
        self.assertEqual(result.events_rejected, 1)
        self.assertIn(("non_positive_bid", 1), result.rejection_reasons)

    def test_replay_rejects_non_finite_numeric_values(self):
        runner = ReplayRunner(position_max_hold_events=2)
        invalid_cases = [
            {"event_time_utc": "2025-01-01T12:00:00Z", "event_type": "ticker", "market": "BTC-EUR", "bid": float("nan"), "ask": 95001.0, "last": 95000.5},
            {"event_time_utc": "2025-01-01T12:00:00Z", "event_type": "ticker", "market": "BTC-EUR", "bid": 95000.0, "ask": float("inf"), "last": 95000.5},
            {"event_time_utc": "2025-01-01T12:00:00Z", "event_type": "ticker", "market": "BTC-EUR", "bid": 95000.0, "ask": 95001.0, "last": float("-inf")},
            {"event_time_utc": "2025-01-01T12:00:00Z", "event_type": "trade", "market": "BTC-EUR", "last": float("nan")},
            {"event_time_utc": "2025-01-01T12:00:00Z", "event_type": "trade", "market": "BTC-EUR", "last": float("inf")},
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                result = runner.replay([case])
                self.assertEqual(result.events_processed, 0)
                self.assertEqual(result.events_rejected, 1)
                self.assertTrue(any(reason.startswith("invalid_") or reason in {"non_positive_bid", "non_positive_ask", "non_positive_last", "non_positive_price"} for reason, _ in result.rejection_reasons))

    def test_trade_events_use_synthetic_bid_ask_fallback_without_claiming_real_quotes(self):
        from replay_runner import _normalize_replay_event

        normalized, rejection = _normalize_replay_event(
            {
                "event_time_utc": "2025-01-01T12:00:00Z",
                "event_type": "trade",
                "market": "BTC-EUR",
                "last": 123.45,
            },
            0,
        )

        self.assertEqual(rejection, "")
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized.last, 123.45)
        self.assertEqual(normalized.bid, 123.45)
        self.assertEqual(normalized.ask, 123.45)

    def test_trade_replay_path_fail_closes_historical_trade_only_events(self):
        runner = ReplayRunner(position_max_hold_events=2)

        with patch("replay_runner.MarketDataEngine.handle_control_message") as mock_handle:
            result = runner.replay(
                [
                    {
                        "event_time_utc": "2025-01-01T12:00:00Z",
                        "event_type": "trade",
                        "market": "BTC-EUR",
                        "last": 123.45,
                    }
                ],
                assume_canonical_chronological=True,
                summary_mode=True,
            )

        mock_handle.assert_not_called()
        self.assertEqual(result.events_total, 1)
        self.assertEqual(result.events_processed, 0)
        self.assertEqual(result.events_rejected, 1)
        self.assertIn(("historical_trade_only_event", 1), result.rejection_reasons)
        self.assertEqual(result.event_timestamps, ())

    def test_mixed_historical_replay_does_not_reuse_stale_quote_state_for_trade_only_event(self):
        runner = ReplayRunner(position_max_hold_events=2)

        result = runner.replay(
            [
                {
                    "event_time_utc": "2025-01-01T12:00:00Z",
                    "event_type": "ticker",
                    "market": "BTC-EUR",
                    "bid": 100.0,
                    "ask": 101.0,
                    "last": 100.5,
                },
                {
                    "event_time_utc": "2025-01-01T12:00:01Z",
                    "event_type": "trade",
                    "market": "BTC-EUR",
                    "last": 100.75,
                },
            ],
            assume_canonical_chronological=True,
        )

        self.assertEqual(result.events_total, 2)
        self.assertEqual(result.events_processed, 1)
        self.assertEqual(result.events_rejected, 1)
        self.assertIn(("historical_trade_only_event", 1), result.rejection_reasons)
        self.assertEqual(result.event_timestamps, ("2025-01-01T12:00:00+00:00",))
        self.assertEqual(result.strategy_timestamps, ("2025-01-01T12:00:00+00:00",))
        self.assertEqual(result.risk_timestamps, ("2025-01-01T12:00:00+00:00",))
        self.assertEqual(result.execution_timestamps, ("2025-01-01T12:00:00+00:00",))
        self.assertEqual(result.account_timestamps, ())
        self.assertEqual(result.position_timestamps, ())
        self.assertEqual(result.trade_timestamps, ())

    def test_replay_does_not_start_live_websocket_or_runner(self):
        runner = ReplayRunner(position_max_hold_events=2)
        with patch("replay_runner.MarketDataEngine.run") as mock_run, patch(
            "replay_runner.MarketDataEngine.create_websocket_app"
        ) as mock_create_websocket_app:
            runner.replay(self._fixture_events())

        mock_run.assert_not_called()
        mock_create_websocket_app.assert_not_called()


if __name__ == "__main__":
    unittest.main()