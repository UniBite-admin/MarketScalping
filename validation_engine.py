from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


def _normalize_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _sorted_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        timestamp = _normalize_datetime(event.get("event_time_utc"))
        normalized.append({**event, "_sort_time": timestamp})
    normalized.sort(key=lambda item: (item["_sort_time"] or datetime.min, str(item.get("market", ""))))
    return [{k: v for k, v in item.items() if k != "_sort_time"} for item in normalized]


@dataclass(frozen=True)
class RobustnessScenario:
    name: str
    assumptions: dict[str, Any]
    base_metric: float
    scenario_metric: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "assumptions": dict(self.assumptions),
            "base_metric": float(self.base_metric),
            "scenario_metric": float(self.scenario_metric),
            "status": "PASS" if self.passed else "FAIL",
        }


@dataclass
class ValidationResult:
    strategy_id: str
    dataset_id: str
    baseline_identity: str
    development_window: dict[str, Any]
    validation_window: dict[str, Any]
    oos_window: dict[str, Any]
    walk_forward_summary: dict[str, Any]
    regime_summary: dict[str, Any]
    robustness_summary: dict[str, Any]
    parameter_sensitivity_summary: dict[str, Any]
    statistical_validity_summary: dict[str, Any]
    final_outcome: str = "INCONCLUSIVE"
    reason_codes: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=lambda: ["validation_result", "backtest_result"])
    deterministic: bool = True
    authority_boundary: str = "read_only_evidence"
    repository_revision: str | None = None

    def __post_init__(self) -> None:
        ordered: list[str] = []
        seen: set[str] = set()
        for code in self.reason_codes:
            if code and code not in seen:
                seen.add(code)
                ordered.append(code)
        self.reason_codes = ordered
        if not self.evidence_refs:
            self.evidence_refs = ["validation_result", "backtest_result"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "dataset_id": self.dataset_id,
            "baseline_identity": self.baseline_identity,
            "development_window": dict(self.development_window),
            "validation_window": dict(self.validation_window),
            "oos_window": dict(self.oos_window),
            "walk_forward_summary": dict(self.walk_forward_summary),
            "regime_summary": dict(self.regime_summary),
            "robustness_summary": dict(self.robustness_summary),
            "parameter_sensitivity_summary": dict(self.parameter_sensitivity_summary),
            "statistical_validity_summary": dict(self.statistical_validity_summary),
            "final_outcome": self.final_outcome,
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
            "deterministic": self.deterministic,
            "authority_boundary": self.authority_boundary,
            "repository_revision": self.repository_revision,
        }


def build_validation_windows(events: Iterable[dict[str, Any]], *, development_ratio: float = 0.5, validation_ratio: float = 0.25, oos_ratio: float = 0.25) -> dict[str, dict[str, Any]]:
    canonical = _sorted_events(events)
    if not canonical:
        return {
            "development": {"start_index": 0, "end_index": -1, "start_utc": None, "end_utc": None, "time_order_safe": True},
            "validation": {"start_index": 0, "end_index": -1, "start_utc": None, "end_utc": None, "time_order_safe": True},
            "oos": {"start_index": 0, "end_index": -1, "start_utc": None, "end_utc": None, "time_order_safe": True},
        }

    total = len(canonical)
    development_end = max(1, min(total - 1, int(total * development_ratio)))
    validation_end = max(development_end + 1, min(total - 1, development_end + max(1, int(total * validation_ratio))))
    oos_start = validation_end + 1
    if oos_start >= total:
        oos_start = max(development_end + 1, total - 1)

    def _window(start_index: int, end_index: int) -> dict[str, Any]:
        if start_index < 0 or end_index < 0 or start_index >= total or end_index >= total:
            return {"start_index": start_index, "end_index": end_index, "start_utc": None, "end_utc": None, "time_order_safe": False}
        start_event = canonical[start_index]
        end_event = canonical[end_index]
        return {
            "start_index": start_index,
            "end_index": end_index,
            "start_utc": start_event.get("event_time_utc"),
            "end_utc": end_event.get("event_time_utc"),
            "time_order_safe": _normalize_datetime(start_event.get("event_time_utc")) <= _normalize_datetime(end_event.get("event_time_utc")),
        }

    development = _window(0, max(0, development_end - 1))
    validation = _window(max(1, development_end), validation_end)
    oos = _window(oos_start, total - 1)
    if validation["start_index"] >= validation["end_index"]:
        validation = {**validation, "time_order_safe": False}
    if oos["start_index"] >= oos["end_index"]:
        oos = {**oos, "time_order_safe": False}
    if oos["end_index"] == oos["start_index"] and oos["start_index"] >= 0:
        oos = {**oos, "time_order_safe": True}

    return {
        "development": development,
        "validation": validation,
        "oos": oos,
    }


def analyze_walk_forward(folds: list[dict[str, Any]]) -> dict[str, Any]:
    if not folds:
        return {
            "status": "INCONCLUSIVE",
            "reason_codes": ["no_walk_forward_folds"],
            "fold_count": 0,
            "passed": 0,
            "failed": 0,
            "folds": [],
            "summary": "No walk-forward folds were provided.",
        }

    normalized_folds: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    reason_codes: list[str] = []
    for index, fold in enumerate(folds):
        fold_id = fold.get("fold_id", f"fold_{index + 1}")
        candidate_final_equity = float(fold.get("candidate_final_equity", 0.0))
        baseline_final_equity = float(fold.get("baseline_final_equity", 0.0))
        status = str(fold.get("status", "FAIL")).upper()
        if status not in {"PASS", "FAIL", "INCONCLUSIVE"}:
            status = "FAIL"
        if candidate_final_equity >= baseline_final_equity and status == "PASS":
            passed += 1
        else:
            failed += 1
            if status != "FAIL":
                status = "FAIL"
        normalized_folds.append({"fold_id": fold_id, "status": status, "candidate_final_equity": candidate_final_equity, "baseline_final_equity": baseline_final_equity, "training_window": fold.get("training_window", {}), "validation_window": fold.get("validation_window", {})})

    if failed > 0:
        reason_codes.append("walk_forward_instability")
    if len(folds) < 2:
        reason_codes.append("insufficient_walk_forward_evidence")
    if passed == len(folds):
        final_status = "PASS"
    elif failed > 0:
        final_status = "FAIL"
    else:
        final_status = "INCONCLUSIVE"

    return {
        "status": final_status,
        "reason_codes": sorted(set(reason_codes)),
        "fold_count": len(folds),
        "passed": passed,
        "failed": failed,
        "folds": normalized_folds,
        "summary": f"Walk-forward evaluation completed across {len(folds)} folds with {passed} passing and {failed} failing folds.",
    }


def analyze_regimes(regimes: list[dict[str, Any]]) -> dict[str, Any]:
    if not regimes:
        return {
            "status": "INCONCLUSIVE",
            "reason_codes": ["no_regime_data"],
            "regimes": [],
            "summary": "No regime analysis data was supplied.",
        }

    normalized: list[dict[str, Any]] = []
    failures: list[str] = []
    for index, regime in enumerate(regimes):
        name = regime.get("name", f"regime_{index + 1}")
        candidate = float(regime.get("candidate_return", 0.0))
        baseline = float(regime.get("baseline_return", 0.0))
        status = str(regime.get("status", "FAIL")).upper()
        if status not in {"PASS", "FAIL", "INCONCLUSIVE"}:
            status = "FAIL"
        if candidate < baseline or status == "FAIL":
            failures.append(name)
        normalized.append({"name": name, "candidate_return": candidate, "baseline_return": baseline, "status": status})

    reason_codes: list[str] = []
    if failures:
        reason_codes.append("regime_failure")
    if not normalized or len(normalized) < 2:
        reason_codes.append("insufficient_regime_evidence")
    final_status = "FAIL" if failures else ("PASS" if len(normalized) >= 1 else "INCONCLUSIVE")
    return {
        "status": final_status,
        "reason_codes": sorted(set(reason_codes)),
        "regimes": normalized,
        "summary": f"Regime analysis covers {len(normalized)} segments; failure detected in: {', '.join(failures) if failures else 'none'}.",
    }


@dataclass(frozen=True)
class SensitivityObservation:
    value: float
    metric: float

    def as_dict(self) -> dict[str, Any]:
        return {"value": float(self.value), "metric": float(self.metric)}


def analyze_parameter_sensitivity(parameter_map: dict[str, Any], *, base_value: float | None = None) -> dict[str, Any]:
    if not parameter_map:
        return {
            "status": "INCONCLUSIVE",
            "reason_codes": ["no_parameter_sensitivity_data"],
            "parameters": [],
            "summary": "No parameter sensitivity data was supplied.",
        }

    if len(parameter_map) != 1:
        parameters = []
        for key, value in parameter_map.items():
            if isinstance(value, dict):
                parameter_items = [{"name": str(key), "value": item, "metric": metric} for item, metric in value.items()]
            else:
                parameter_items = [{"name": str(key), "value": value, "metric": 0.0}]
            parameters.extend(parameter_items)
    else:
        key, value = next(iter(parameter_map.items()))
        if isinstance(value, dict):
            parameters = [{"name": str(key), "value": item, "metric": metric} for item, metric in value.items()]
        else:
            parameters = [{"name": str(key), "value": value, "metric": 0.0}]

    observations = [SensitivityObservation(float(item["value"]), float(item["metric"])) for item in parameters]
    base_metric = next((obs.metric for obs in observations if base_value is not None and float(obs.value) == float(base_value)), observations[0].metric if observations else 0.0)
    metric_span = max((obs.metric for obs in observations), default=0.0) - min((obs.metric for obs in observations), default=0.0)
    reason_codes: list[str] = []
    if base_metric < 0.0 or metric_span > 0.05:
        reason_codes.append("parameter_fragility")
    final_status = "FAIL" if reason_codes else "PASS"
    return {
        "status": final_status,
        "reason_codes": sorted(set(reason_codes)),
        "parameters": parameters,
        "base_value": base_value,
        "base_metric": base_metric,
        "metric_span": metric_span,
        "summary": f"Parameter sensitivity span={metric_span:.6f}; selected base value={base_value}.",
    }


def analyze_robustness(scenarios: Iterable[RobustnessScenario | dict[str, Any]]) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    scenario_list = list(scenarios)
    if not scenario_list:
        return {
            "status": "INCONCLUSIVE",
            "reason_codes": ["no_robustness_scenarios"],
            "scenarios": [],
            "summary": "No robustness scenarios were supplied.",
        }

    invalid = []
    for scenario in scenario_list:
        if isinstance(scenario, RobustnessScenario):
            current = scenario.as_dict()
        elif isinstance(scenario, dict):
            current = {
                "name": scenario.get("name", "unnamed_scenario"),
                "assumptions": dict(scenario.get("assumptions", {})),
                "base_metric": float(scenario.get("base_metric", 0.0)),
                "scenario_metric": float(scenario.get("scenario_metric", 0.0)),
                "status": str(scenario.get("status", "FAIL")).upper(),
            }
        else:
            invalid.append(str(scenario))
            continue
        status = current.get("status", "PASS")
        if status not in {"PASS", "FAIL", "INCONCLUSIVE"}:
            status = "FAIL"
        if current.get("scenario_metric", 0.0) < current.get("base_metric", 0.0) * 0.9 and status != "FAIL":
            status = "FAIL"
        if status == "FAIL":
            current["status"] = "FAIL"
        else:
            current["status"] = "PASS"
        normalized.append(current)

    failures = [item for item in normalized if item.get("status") == "FAIL"]
    reason_codes = ["robustness_failure"] if failures else []
    final_status = "FAIL" if failures else "PASS"
    return {
        "status": final_status,
        "reason_codes": reason_codes,
        "scenarios": normalized,
        "summary": f"Robustness scenarios evaluated: {len(normalized)}; failed scenarios={len(failures)}.",
    }


def assess_statistical_validity(summary: dict[str, Any] | None = None, *, sample_size: int | None = None, method: str | None = None, inferential: bool = False) -> dict[str, Any]:
    if summary is None:
        summary = {}
    observed_sample_size = int(summary.get("sample_size", sample_size or 0))
    observed_method = str(summary.get("method", method or "descriptive_only")).lower()
    if observed_method not in {"descriptive_only", "inferential", "confidence_interval", "bootstrap", "t_test", "mann_whitney", "wilcoxon"}:
        observed_method = "descriptive_only"
    if observed_sample_size < 2 or observed_method == "descriptive_only" or not inferential:
        return {
            "status": "INCONCLUSIVE",
            "reason_codes": ["insufficient_statistical_evidence"],
            "method": observed_method,
            "sample_size": observed_sample_size,
            "inferential": inferential,
            "summary": "The result is descriptive evidence only; no strong inferential claim is made.",
        }
    return {
        "status": "PASS",
        "reason_codes": [],
        "method": observed_method,
        "sample_size": observed_sample_size,
        "inferential": inferential,
        "summary": "Statistical validity was assessed using a supported inferential approach.",
    }


def build_validation_result(
    *,
    strategy_id: str,
    dataset_id: str,
    baseline_identity: str,
    development_window: dict[str, Any],
    validation_window: dict[str, Any],
    oos_window: dict[str, Any],
    walk_forward_summary: dict[str, Any],
    regime_summary: dict[str, Any],
    robustness_summary: dict[str, Any],
    parameter_sensitivity_summary: dict[str, Any],
    statistical_validity_summary: dict[str, Any],
    repository_revision: str | None = None,
) -> ValidationResult:
    reason_codes: list[str] = []
    for summary in [walk_forward_summary, regime_summary, robustness_summary, parameter_sensitivity_summary, statistical_validity_summary]:
        for code in summary.get("reason_codes", []):
            if code:
                reason_codes.append(str(code))

    candidate_statuses = [
        walk_forward_summary.get("status", "INCONCLUSIVE"),
        regime_summary.get("status", "INCONCLUSIVE"),
        robustness_summary.get("status", "INCONCLUSIVE"),
        parameter_sensitivity_summary.get("status", "INCONCLUSIVE"),
        statistical_validity_summary.get("status", "INCONCLUSIVE"),
    ]
    if any(status == "FAIL" for status in candidate_statuses):
        final_outcome = "FAIL"
    elif all(status == "PASS" for status in candidate_statuses):
        final_outcome = "PASS"
    else:
        final_outcome = "INCONCLUSIVE"

    evidence_refs = [
        "validation_result",
        "backtest_result",
        "walk_forward_evidence",
        "regime_analysis",
        "robustness_tests",
        "parameter_sensitivity",
        "statistical_validity",
    ]

    return ValidationResult(
        strategy_id=strategy_id,
        dataset_id=dataset_id,
        baseline_identity=baseline_identity,
        development_window=dict(development_window),
        validation_window=dict(validation_window),
        oos_window=dict(oos_window),
        walk_forward_summary=dict(walk_forward_summary),
        regime_summary=dict(regime_summary),
        robustness_summary=dict(robustness_summary),
        parameter_sensitivity_summary=dict(parameter_sensitivity_summary),
        statistical_validity_summary=dict(statistical_validity_summary),
        final_outcome=final_outcome,
        reason_codes=reason_codes,
        evidence_refs=evidence_refs,
        deterministic=True,
        authority_boundary="read_only_evidence",
        repository_revision=repository_revision,
    )


__all__ = [
    "RobustnessScenario",
    "ValidationResult",
    "analyze_parameter_sensitivity",
    "analyze_regimes",
    "analyze_robustness",
    "analyze_walk_forward",
    "assess_statistical_validity",
    "build_validation_result",
    "build_validation_windows",
]
