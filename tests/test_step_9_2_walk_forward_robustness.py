import unittest

from validation_engine import (
    RobustnessScenario,
    ValidationResult,
    build_validation_result,
    build_validation_windows,
    analyze_parameter_sensitivity,
    analyze_regimes,
    analyze_robustness,
    analyze_walk_forward,
    assess_statistical_validity,
)


class Step9_2WalkForwardRobustnessTests(unittest.TestCase):
    def _fixture_events(self):
        return [
            {"event_time_utc": "2025-01-01T00:00:00Z", "market": "BTC-EUR", "last": 100.0},
            {"event_time_utc": "2025-01-01T01:00:00Z", "market": "BTC-EUR", "last": 101.0},
            {"event_time_utc": "2025-01-01T02:00:00Z", "market": "BTC-EUR", "last": 102.0},
            {"event_time_utc": "2025-01-01T03:00:00Z", "market": "BTC-EUR", "last": 103.0},
            {"event_time_utc": "2025-01-01T04:00:00Z", "market": "BTC-EUR", "last": 99.0},
            {"event_time_utc": "2025-01-01T05:00:00Z", "market": "BTC-EUR", "last": 100.0},
            {"event_time_utc": "2025-01-01T06:00:00Z", "market": "BTC-EUR", "last": 104.0},
            {"event_time_utc": "2025-01-01T07:00:00Z", "market": "BTC-EUR", "last": 105.0},
            {"event_time_utc": "2025-01-01T08:00:00Z", "market": "BTC-EUR", "last": 106.0},
            {"event_time_utc": "2025-01-01T09:00:00Z", "market": "BTC-EUR", "last": 98.0},
        ]

    def test_validation_windows_are_time_ordered_and_separated(self):
        windows = build_validation_windows(self._fixture_events())
        self.assertEqual(set(windows.keys()), {"development", "validation", "oos"})
        self.assertLess(windows["development"]["end_index"], windows["validation"]["start_index"])
        self.assertLess(windows["validation"]["end_index"], windows["oos"]["start_index"])
        self.assertTrue(windows["development"]["time_order_safe"])
        self.assertTrue(windows["validation"]["time_order_safe"])
        self.assertTrue(windows["oos"]["time_order_safe"])

    def test_walk_forward_rejects_instability_across_folds(self):
        folds = [
            {"fold_id": "fold_1", "training_window": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T02:00:00Z"}, "validation_window": {"start": "2025-01-01T03:00:00Z", "end": "2025-01-01T04:00:00Z"}, "candidate_final_equity": 1100.0, "baseline_final_equity": 1000.0, "status": "PASS"},
            {"fold_id": "fold_2", "training_window": {"start": "2025-01-01T02:00:00Z", "end": "2025-01-01T04:00:00Z"}, "validation_window": {"start": "2025-01-01T05:00:00Z", "end": "2025-01-01T06:00:00Z"}, "candidate_final_equity": 960.0, "baseline_final_equity": 1000.0, "status": "FAIL"},
            {"fold_id": "fold_3", "training_window": {"start": "2025-01-01T04:00:00Z", "end": "2025-01-01T06:00:00Z"}, "validation_window": {"start": "2025-01-01T07:00:00Z", "end": "2025-01-01T08:00:00Z"}, "candidate_final_equity": 980.0, "baseline_final_equity": 1000.0, "status": "FAIL"},
        ]
        summary = analyze_walk_forward(folds)
        self.assertEqual(summary["status"], "FAIL")
        self.assertIn("walk_forward_instability", summary["reason_codes"])
        self.assertEqual(len(summary["folds"]), 3)

    def test_regime_and_robustness_and_sensitivity_are_reported(self):
        regimes = [
            {"name": "trending", "candidate_return": 0.04, "baseline_return": 0.02, "status": "PASS"},
            {"name": "range", "candidate_return": -0.03, "baseline_return": 0.01, "status": "FAIL"},
        ]
        robustness = [
            RobustnessScenario("fee_up", {"fee_rate": 0.002}, 0.05, 0.04, True),
            RobustnessScenario("slippage_up", {"slippage_bps": 40}, 0.05, -0.01, False),
        ]
        sensitivity = analyze_parameter_sensitivity({"threshold": {0.2: 0.04, 0.4: 0.02, 0.6: -0.03}}, base_value=0.4)
        regime_summary = analyze_regimes(regimes)
        robustness_summary = analyze_robustness(robustness)
        self.assertEqual(regime_summary["status"], "FAIL")
        self.assertEqual(robustness_summary["status"], "FAIL")
        self.assertEqual(sensitivity["status"], "FAIL")
        self.assertIn("parameter_fragility", sensitivity["reason_codes"])

    def test_validation_result_is_evidence_only_and_reports_failure_semantics(self):
        result = build_validation_result(
            strategy_id="strategy-9.2",
            dataset_id="dataset-9.2",
            baseline_identity="baseline-9.2",
            development_window={"start_utc": "2025-01-01T00:00:00Z", "end_utc": "2025-01-01T03:00:00Z"},
            validation_window={"start_utc": "2025-01-01T04:00:00Z", "end_utc": "2025-01-01T06:00:00Z"},
            oos_window={"start_utc": "2025-01-01T07:00:00Z", "end_utc": "2025-01-01T09:00:00Z"},
            walk_forward_summary={"status": "FAIL", "reason_codes": ["walk_forward_instability"], "folds": [{"fold_id": "f1", "status": "FAIL"}]},
            regime_summary={"status": "FAIL", "reason_codes": ["regime_failure"], "regimes": [{"name": "range", "status": "FAIL"}]},
            robustness_summary={"status": "PASS", "reason_codes": [], "scenarios": []},
            parameter_sensitivity_summary={"status": "FAIL", "reason_codes": ["parameter_fragility"], "parameters": [{"name": "threshold", "status": "FAIL"}]},
            statistical_validity_summary={"status": "INCONCLUSIVE", "reason_codes": ["insufficient_statistical_evidence"], "method": "descriptive_only"},
        )
        self.assertIsInstance(result, ValidationResult)
        self.assertEqual(result.final_outcome, "FAIL")
        self.assertEqual(result.authority_boundary, "read_only_evidence")
        self.assertIn("walk_forward_instability", result.reason_codes)
        self.assertIn("parameter_fragility", result.reason_codes)
        self.assertTrue(result.deterministic)
        self.assertIn("validation_result", result.evidence_refs)


if __name__ == "__main__":
    unittest.main()
