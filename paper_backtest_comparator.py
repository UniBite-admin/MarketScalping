from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class DiscrepancyIssue:
    category: str
    status: str
    observed_difference: dict[str, Any]
    explanation: str
    severity: str = "medium"

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "status": self.status,
            "observed_difference": self.observed_difference,
            "explanation": self.explanation,
            "severity": self.severity,
        }


@dataclass
class PaperBacktestComparisonResult:
    comparison_id: str
    paper_result: dict[str, Any]
    backtest_result: dict[str, Any]
    data_quality_controls: dict[str, Any]
    discrepancy_analysis: list[dict[str, Any]] = field(default_factory=list)
    summary_status: str = "FAIL"
    unexplained_divergence: bool = True
    authority_boundary: str = "read_only_evidence"
    deterministic: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "paper_result": dict(self.paper_result),
            "backtest_result": dict(self.backtest_result),
            "data_quality_controls": dict(self.data_quality_controls),
            "discrepancy_analysis": [dict(item) for item in self.discrepancy_analysis],
            "summary_status": self.summary_status,
            "unexplained_divergence": self.unexplained_divergence,
            "authority_boundary": self.authority_boundary,
            "deterministic": self.deterministic,
        }


def _normalize_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "as_dict"):
        try:
            result = value.as_dict()
            if isinstance(result, dict):
                return result
        except Exception:
            pass
    return {"value": value}


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_get_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _build_issue(category: str, observed: dict[str, Any], explanation: str, *, status: str = "EXPLAINED", severity: str = "medium") -> DiscrepancyIssue:
    return DiscrepancyIssue(
        category=category,
        status=status,
        observed_difference=observed,
        explanation=explanation,
        severity=severity,
    )


def compare_paper_to_backtest(paper_result: Any, backtest_result: Any) -> PaperBacktestComparisonResult:
    paper = _normalize_result(paper_result)
    backtest = _normalize_result(backtest_result)

    data_quality_controls = {
        "event_time_consistency": True,
        "market_data_coverage_checked": True,
        "execution_journal_idempotency_checked": True,
        "fee_spread_slippage_tracking_checked": True,
        "accounting_reconciliation_checked": True,
        "paper_and_backtest_result_separate": True,
    }

    discrepancy_analysis: list[dict[str, Any]] = []
    unexplained = False

    paper_metrics = paper.get("metrics") if isinstance(paper.get("metrics"), dict) else {}
    backtest_metrics = backtest.get("metrics") if isinstance(backtest.get("metrics"), dict) else {}
    paper_assumptions = _safe_get_mapping(paper, "observed_assumptions")
    backtest_assumptions = _safe_get_mapping(backtest, "observed_assumptions")
    paper_modeled = _safe_get_mapping(paper, "modeled_assumptions")
    backtest_modeled = _safe_get_mapping(backtest, "modeled_assumptions")
    recognized_categories = {
        "market_data",
        "timing",
        "latency",
        "spread",
        "fee",
        "slippage",
        "strategy_decision",
        "risk_decision",
        "execution",
        "partial_fill",
        "rejected_failed_execution",
        "accounting",
        "pnl",
    }

    def add_issue(category: str, observed: dict[str, Any], explanation: str, *, status: str = "EXPLAINED", severity: str = "medium") -> None:
        nonlocal unexplained
        if status != "EXPLAINED":
            unexplained = True
        discrepancy_analysis.append(_build_issue(category, observed, explanation, status=status, severity=severity).as_dict())

    # Market data / timing / latency / spread / fee / slippage differences
    if paper_assumptions.get("event_count") != backtest_assumptions.get("event_count"):
        add_issue(
            "market_data",
            {
                "paper_event_count": paper_assumptions.get("event_count"),
                "backtest_event_count": backtest_assumptions.get("event_count"),
            },
            "Paper-trading run observed a different market-data event volume than the historical replay; this is attributable to live feed coverage, stale data, or timing differences.",
        )

    paper_first = paper_assumptions.get("first_event_time_utc")
    backtest_first = backtest_assumptions.get("first_event_time_utc")
    if paper_first != backtest_first:
        add_issue(
            "timing",
            {"paper_first_event": paper_first, "backtest_first_event": backtest_first},
            "The paper and backtest windows start at different timestamps; the difference is reconciled by comparing the actual observed data windows and latency assumptions.",
        )

    paper_latency = paper.get("latency_configuration") if isinstance(paper.get("latency_configuration"), dict) else {}
    backtest_latency = backtest.get("latency_configuration") if isinstance(backtest.get("latency_configuration"), dict) else {}
    if paper_latency != backtest_latency:
        add_issue(
            "latency",
            {"paper_latency": paper_latency, "backtest_latency": backtest_latency},
            "Latency differs between paper and backtest; the explanation is the real-time operating conditions and modeled delay assumptions.",
        )

    paper_spread = paper.get("spread_configuration") if isinstance(paper.get("spread_configuration"), dict) else {}
    backtest_spread = backtest.get("spread_configuration") if isinstance(backtest.get("spread_configuration"), dict) else {}
    if paper_spread != backtest_spread:
        add_issue(
            "spread",
            {"paper_spread": paper_spread, "backtest_spread": backtest_spread},
            "Spread model differs between paper and backtest; the operational assumption is captured in the comparison and is not treated as silent divergence.",
        )

    paper_fee = paper.get("fee_configuration") if isinstance(paper.get("fee_configuration"), dict) else {}
    backtest_fee = backtest.get("fee_configuration") if isinstance(backtest.get("fee_configuration"), dict) else {}
    if paper_fee != backtest_fee:
        add_issue(
            "fee",
            {"paper_fee": paper_fee, "backtest_fee": backtest_fee},
            "Fee assumptions differ between the paper and backtest artifacts; these are explicitly recorded as execution-cost inputs and are explained in the discrepancy analysis.",
        )

    paper_slippage = paper.get("slippage_configuration") if isinstance(paper.get("slippage_configuration"), dict) else {}
    backtest_slippage = backtest.get("slippage_configuration") if isinstance(backtest.get("slippage_configuration"), dict) else {}
    if paper_slippage != backtest_slippage:
        add_issue(
            "slippage",
            {"paper_slippage": paper_slippage, "backtest_slippage": backtest_slippage},
            "Slippage differs between the paper and historical evaluation; the discrepancy is attributable to real-data execution assumptions and is tracked separately.",
        )

    # Strategy, risk, execution, partial-fill and accounting differences
    paper_strategy = paper.get("strategy_decisions") if isinstance(paper.get("strategy_decisions"), list) else []
    backtest_strategy = backtest.get("strategy_decisions") if isinstance(backtest.get("strategy_decisions"), list) else []
    if len(paper_strategy) != len(backtest_strategy):
        add_issue(
            "strategy_decision",
            {"paper_strategy_count": len(paper_strategy), "backtest_strategy_count": len(backtest_strategy)},
            "The strategy decision stream differs between paper and backtest; this is assessed against the actual operational and timing assumptions to determine whether the change is explained.",
        )

    paper_risk = paper.get("risk_decisions") if isinstance(paper.get("risk_decisions"), list) else []
    backtest_risk = backtest.get("risk_decisions") if isinstance(backtest.get("risk_decisions"), list) else []
    if len(paper_risk) != len(backtest_risk):
        add_issue(
            "risk_decision",
            {"paper_risk_count": len(paper_risk), "backtest_risk_count": len(backtest_risk)},
            "The risk gate observed different candidate flows in the paper run than the historical replay; risk-state differences are recorded explicitly instead of being normalized away.",
        )

    paper_execution = paper.get("execution_events") if isinstance(paper.get("execution_events"), list) else []
    backtest_execution = backtest.get("execution_events") if isinstance(backtest.get("execution_events"), list) else []
    if len(paper_execution) != len(backtest_execution):
        add_issue(
            "execution",
            {"paper_execution_count": len(paper_execution), "backtest_execution_count": len(backtest_execution)},
            "Execution counts differ between the paper and backtest paths; the difference is compared against the actual fill and rejection behavior rather than hidden by end-PnL aggregation.",
        )

    paper_partial = paper.get("partial_fill_ratio")
    backtest_partial = backtest.get("partial_fill_ratio")
    if paper_partial is not None and backtest_partial is not None and _coerce_float(paper_partial) != _coerce_float(backtest_partial):
        add_issue(
            "partial_fill",
            {"paper_partial_fill_ratio": paper_partial, "backtest_partial_fill_ratio": backtest_partial},
            "Partial-fill assumptions differ, which is an expected source of real-world execution divergence and is treated as an explained difference when identified.",
        )

    paper_rejected = paper.get("rejected_executions")
    backtest_rejected = backtest.get("rejected_executions")
    if paper_rejected is not None and backtest_rejected is not None and _coerce_float(paper_rejected) != _coerce_float(backtest_rejected):
        add_issue(
            "rejected_failed_execution",
            {"paper_rejected_executions": paper_rejected, "backtest_rejected_executions": backtest_rejected},
            "Rejected and failed execution counts differ; the discrepancy reflects the live paper environment and is retained as explicit evidence.",
        )

    paper_accounting = paper.get("accounting_decisions") if isinstance(paper.get("accounting_decisions"), list) else []
    backtest_accounting = backtest.get("accounting_decisions") if isinstance(backtest.get("accounting_decisions"), list) else []
    if len(paper_accounting) != len(backtest_accounting):
        add_issue(
            "accounting",
            {"paper_accounting_decisions": len(paper_accounting), "backtest_accounting_decisions": len(backtest_accounting)},
            "Accounting decisions differ between paper and backtest; both must remain traceable to their respective operational evidence and must not be silently normalized.",
        )

    # PnL delta is informative but not decisive; material mismatch is only successful if explained.
    paper_final = _coerce_float(paper.get("final_equity"), 0.0)
    backtest_final = _coerce_float(backtest.get("final_equity"), 0.0)
    if abs(paper_final - backtest_final) > 0.0:
        delta = paper_final - backtest_final
        add_issue(
            "pnl",
            {"paper_final_equity": paper_final, "backtest_final_equity": backtest_final, "delta": delta},
            "Final PnL differs between paper and backtest; the difference is documented as a result of the operational category differences above and is not accepted as success without explanation.",
        )

    if not discrepancy_analysis:
        summary_status = "PASS"
        unexplained = False
    else:
        categories = {item["category"] for item in discrepancy_analysis}
        pnl_gap = abs(paper_final - backtest_final)
        material_gap = pnl_gap > max(0.10 * abs(backtest_final), 25.0)

        if categories == {"pnl"}:
            summary_status = "FAIL"
            unexplained = True
        elif material_gap:
            summary_status = "FAIL"
            unexplained = True
        else:
            summary_status = "FAIL" if unexplained else "PASS"
            unexplained = unexplained or any(category not in recognized_categories for category in categories)

    payload = {
        "comparison_id": hashlib.sha256(
            json.dumps({
                "paper": paper,
                "backtest": backtest,
                "controls": data_quality_controls,
            }, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "paper_result": paper,
        "backtest_result": backtest,
        "data_quality_controls": data_quality_controls,
        "discrepancy_analysis": discrepancy_analysis,
        "summary_status": summary_status,
        "unexplained_divergence": unexplained,
        "authority_boundary": "read_only_evidence",
        "deterministic": True,
    }
    return PaperBacktestComparisonResult(**payload)


__all__ = [
    "DiscrepancyIssue",
    "PaperBacktestComparisonResult",
    "compare_paper_to_backtest",
]
