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