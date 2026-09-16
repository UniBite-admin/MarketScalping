from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

from backtest_engine import BacktestResult


@dataclass(frozen=True)
class BaselineBenchmarkConfig:
    market: str = "BTC-EUR"
    initial_capital: float = 1000.0
    fee_rate: float = 0.001
    spread_pct: float = 0.001
    slippage_bps: float = 10.0
    latency_ticks: int = 0
    benchmark_type: str = "BUY_AND_HOLD"
    dataset_id: str | None = None
    evaluation_window_start_utc: str | None = None
    evaluation_window_end_utc: str | None = None
    repository_revision: str | None = None
    model_costs: bool = True
    frozen: bool = True
    config_version: str = "step_9_1_v1"

    def configuration_identity(self) -> str:
        payload = {
            "market": self.market,
            "initial_capital": self.initial_capital,
            "fee_rate": self.fee_rate,
            "spread_pct": self.spread_pct,
            "slippage_bps": self.slippage_bps,
            "latency_ticks": self.latency_ticks,
            "benchmark_type": self.benchmark_type,
            "dataset_id": self.dataset_id,
            "evaluation_window_start_utc": self.evaluation_window_start_utc,
            "evaluation_window_end_utc": self.evaluation_window_end_utc,
            "repository_revision": self.repository_revision,
            "model_costs": self.model_costs,
            "config_version": self.config_version,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "initial_capital": self.initial_capital,
            "fee_rate": self.fee_rate,
            "spread_pct": self.spread_pct,
            "slippage_bps": self.slippage_bps,
            "latency_ticks": self.latency_ticks,
            "benchmark_type": self.benchmark_type,
            "dataset_id": self.dataset_id,
            "evaluation_window_start_utc": self.evaluation_window_start_utc,
            "evaluation_window_end_utc": self.evaluation_window_end_utc,
            "repository_revision": self.repository_revision,
            "model_costs": self.model_costs,
            "frozen": self.frozen,
            "config_version": self.config_version,
            "configuration_identity": self.configuration_identity(),
        }


@dataclass
class BaselineResult:
    baseline_type: str
    dataset_id: str
    evaluation_window: dict[str, str | None]
    initial_capital: float
    final_equity: float
    realized_pnl: float
    gross_pnl: float
    total_costs: float
    trade_count: int
    drawdown: float
    benchmark_identity: str
    observed_assumptions: dict[str, Any]
    modeled_assumptions: dict[str, Any]
    authority_boundary: str = "read_only_evidence"
    deterministic: bool = True
    status: str = "PASS"

    def as_dict(self) -> dict[str, Any]:
        return {
            "baseline_type": self.baseline_type,
            "dataset_id": self.dataset_id,
            "evaluation_window": self.evaluation_window,
            "initial_capital": self.initial_capital,
            "final_equity": self.final_equity,
            "realized_pnl": self.realized_pnl,
            "gross_pnl": self.gross_pnl,
            "total_costs": self.total_costs,
            "trade_count": self.trade_count,
            "drawdown": self.drawdown,
            "benchmark_identity": self.benchmark_identity,
            "observed_assumptions": self.observed_assumptions,
            "modeled_assumptions": self.modeled_assumptions,
            "authority_boundary": self.authority_boundary,
            "deterministic": self.deterministic,
            "status": self.status,
        }


@dataclass
class BaselineComparisonResult:
    comparison_id: str
    candidate_result: dict[str, Any]
    buy_and_hold: BaselineResult
    no_trade: BaselineResult
    benchmark_config: BaselineBenchmarkConfig
    candidate_final_equity: float
    candidate_pnl: float
    candidate_trade_count: int
    absolute_delta_vs_buy_and_hold: float
    relative_delta_vs_buy_and_hold: float
    absolute_delta_vs_no_trade: float
    relative_delta_vs_no_trade: float
    status: str
    reproducibility_metadata: dict[str, Any]
    authority_boundary: str = "read_only_evidence"

    def as_dict(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "candidate_result": self.candidate_result,
            "buy_and_hold": self.buy_and_hold.as_dict(),
            "no_trade": self.no_trade.as_dict(),
            "benchmark_config": self.benchmark_config.as_dict(),
            "candidate_final_equity": self.candidate_final_equity,
            "candidate_pnl": self.candidate_pnl,
            "candidate_trade_count": self.candidate_trade_count,
            "absolute_delta_vs_buy_and_hold": self.absolute_delta_vs_buy_and_hold,
            "relative_delta_vs_buy_and_hold": self.relative_delta_vs_buy_and_hold,
            "absolute_delta_vs_no_trade": self.absolute_delta_vs_no_trade,
            "relative_delta_vs_no_trade": self.relative_delta_vs_no_trade,
            "status": self.status,
            "reproducibility_metadata": self.reproducibility_metadata,
            "authority_boundary": self.authority_boundary,
        }


def _parse_event_time(value: Any) -> datetime | None:
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


def _extract_price(event: dict[str, Any]) -> float | None:
    for key in ("last", "close", "mid_price", "price"):
        value = event.get(key)
        if value is not None:
            try:
                price = float(value)
            except (TypeError, ValueError):
                continue
            if price > 0:
                return price
    bid = event.get("bid")
    ask = event.get("ask")
    if bid is not None and ask is not None:
        try:
            return (float(bid) + float(ask)) / 2.0
        except (TypeError, ValueError):
            return None
    return None


def _valid_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if _extract_price(event) is None:
            continue
        valid.append(event)
    valid.sort(key=lambda item: (_parse_event_time(item.get("event_time_utc")) or datetime.min, str(item.get("market", ""))))
    return valid


def compute_no_trade_baseline(events: Iterable[dict[str, Any]], *, config: BaselineBenchmarkConfig) -> BaselineResult:
    canonical = _valid_events(events)
    dataset_id = config.dataset_id or hashlib.sha256(
        json.dumps({"events": canonical}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    evaluation_window = {
        "start_utc": canonical[0].get("event_time_utc") if canonical else None,
        "end_utc": canonical[-1].get("event_time_utc") if canonical else None,
    }
    observed = {
        "event_count": len(canonical),
        "first_event_time_utc": evaluation_window["start_utc"],
        "last_event_time_utc": evaluation_window["end_utc"],
        "market": config.market,
        "dataset_id": dataset_id,
    }
    modeled = {
        "model_costs": config.model_costs,
        "fee_rate": config.fee_rate,
        "spread_pct": config.spread_pct,
        "slippage_bps": config.slippage_bps,
        "latency_ticks": config.latency_ticks,
        "cost_model_applied": config.model_costs,
    }
    final_equity = float(config.initial_capital)
    pnl = 0.0
    total_costs = 0.0
    return BaselineResult(
        baseline_type="NO_TRADE",
        dataset_id=dataset_id,
        evaluation_window=evaluation_window,
        initial_capital=float(config.initial_capital),
        final_equity=final_equity,
        realized_pnl=pnl,
        gross_pnl=0.0,
        total_costs=total_costs,
        trade_count=0,
        drawdown=0.0,
        benchmark_identity=config.configuration_identity(),
        observed_assumptions=observed,
        modeled_assumptions=modeled,
        status="PASS",
    )


def compute_buy_and_hold_baseline(events: Iterable[dict[str, Any]], *, config: BaselineBenchmarkConfig) -> BaselineResult:
    canonical = _valid_events(events)
    if not canonical:
        return BaselineResult(
            baseline_type="BUY_AND_HOLD",
            dataset_id=config.dataset_id or "EMPTY_DATASET",
            evaluation_window={"start_utc": None, "end_utc": None},
            initial_capital=float(config.initial_capital),
            final_equity=float(config.initial_capital),
            realized_pnl=0.0,
            gross_pnl=0.0,
            total_costs=0.0,
            trade_count=1,
            drawdown=0.0,
            benchmark_identity=config.configuration_identity(),
            observed_assumptions={"event_count": 0, "first_event_time_utc": None, "last_event_time_utc": None},
            modeled_assumptions={"model_costs": config.model_costs, "fee_rate": config.fee_rate, "spread_pct": config.spread_pct, "slippage_bps": config.slippage_bps},
            status="PASS",
        )

    dataset_id = config.dataset_id or hashlib.sha256(
        json.dumps({"events": canonical}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    start_event = canonical[0]
    end_event = canonical[-1]
    start_price = _extract_price(start_event)
    end_price = _extract_price(end_event)
    if start_price is None or end_price is None or start_price <= 0:
        return BaselineResult(
            baseline_type="BUY_AND_HOLD",
            dataset_id=dataset_id,
            evaluation_window={"start_utc": start_event.get("event_time_utc"), "end_utc": end_event.get("event_time_utc")},
            initial_capital=float(config.initial_capital),
            final_equity=float(config.initial_capital),
            realized_pnl=0.0,
            gross_pnl=0.0,
            total_costs=0.0,
            trade_count=1,
            drawdown=0.0,
            benchmark_identity=config.configuration_identity(),
            observed_assumptions={"event_count": len(canonical), "first_event_time_utc": start_event.get("event_time_utc"), "last_event_time_utc": end_event.get("event_time_utc")},
            modeled_assumptions={"model_costs": config.model_costs, "fee_rate": config.fee_rate, "spread_pct": config.spread_pct, "slippage_bps": config.slippage_bps},
            status="PASS",
        )

    quantity = float(config.initial_capital) / float(start_price)
    gross_value = quantity * float(end_price)
    gross_pnl = gross_value - float(config.initial_capital)
    total_costs = 0.0
    if config.model_costs:
        entry_cost = quantity * float(start_price) * (config.fee_rate + config.spread_pct + (config.slippage_bps / 10000.0))
        exit_cost = quantity * float(end_price) * (config.fee_rate + config.spread_pct + (config.slippage_bps / 10000.0))
        total_costs = entry_cost + exit_cost
    final_equity = float(config.initial_capital) + gross_pnl - total_costs
    pnl = gross_pnl - total_costs
    drawdown = 0.0 if final_equity >= config.initial_capital else (config.initial_capital - final_equity) / max(config.initial_capital, 1e-9)
    observed = {
        "event_count": len(canonical),
        "first_event_time_utc": start_event.get("event_time_utc"),
        "last_event_time_utc": end_event.get("event_time_utc"),
        "market": config.market,
        "dataset_id": dataset_id,
        "start_price": start_price,
        "end_price": end_price,
    }
    modeled = {
        "model_costs": config.model_costs,
        "fee_rate": config.fee_rate,
        "spread_pct": config.spread_pct,
        "slippage_bps": config.slippage_bps,
        "latency_ticks": config.latency_ticks,
        "entry_cost": (quantity * float(start_price) * (config.fee_rate + config.spread_pct + (config.slippage_bps / 10000.0))) if config.model_costs else 0.0,
        "exit_cost": (quantity * float(end_price) * (config.fee_rate + config.spread_pct + (config.slippage_bps / 10000.0))) if config.model_costs else 0.0,
        "trade_count": 1,
    }
    return BaselineResult(
        baseline_type="BUY_AND_HOLD",
        dataset_id=dataset_id,
        evaluation_window={"start_utc": start_event.get("event_time_utc"), "end_utc": end_event.get("event_time_utc")},
        initial_capital=float(config.initial_capital),
        final_equity=final_equity,
        realized_pnl=pnl,
        gross_pnl=gross_pnl,
        total_costs=total_costs,
        trade_count=1,
        drawdown=drawdown,
        benchmark_identity=config.configuration_identity(),
        observed_assumptions=observed,
        modeled_assumptions=modeled,
        status="PASS",
    )


def _safe_candidate_metrics(candidate_result: Any) -> dict[str, Any]:
    if isinstance(candidate_result, dict):
        return {
            "final_equity": float(candidate_result.get("final_equity", candidate_result.get("final_equity_value", 0.0))),
            "pnl": float(candidate_result.get("realized_pnl", candidate_result.get("pnl", 0.0))),
            "trade_count": int(candidate_result.get("trade_count", candidate_result.get("trade_count_value", 0))),
            "drawdown": float(candidate_result.get("drawdown", 0.0)),
            "costs": float(candidate_result.get("total_costs", 0.0)),
            "dataset_id": candidate_result.get("dataset_id", "candidate_dataset"),
            "status": candidate_result.get("status", "PASS"),
        }
    if isinstance(candidate_result, BacktestResult):
        metrics = candidate_result.metrics or {}
        analytics = candidate_result.analytics
        performance = analytics.performance_summary if analytics is not None else None
        return {
            "final_equity": float(candidate_result.final_equity),
            "pnl": float(candidate_result.realized_pnl),
            "trade_count": int(metrics.get("trade_count", 0 if performance is None else performance.trade_count)),
            "drawdown": float(metrics.get("max_drawdown", 0.0 if performance is None else performance.max_drawdown)),
            "costs": float(metrics.get("total_fees", 0.0)),
            "dataset_id": candidate_result.dataset_id,
            "status": candidate_result.validation_status,
        }
    if hasattr(candidate_result, "final_equity"):
        return {
            "final_equity": float(getattr(candidate_result, "final_equity")),
            "pnl": float(getattr(candidate_result, "realized_pnl", 0.0)),
            "trade_count": int(getattr(candidate_result, "trade_count", 0)),
            "drawdown": float(getattr(candidate_result, "drawdown", 0.0)),
            "costs": float(getattr(candidate_result, "total_costs", 0.0)),
            "dataset_id": getattr(candidate_result, "dataset_id", "candidate_dataset"),
            "status": getattr(candidate_result, "status", "PASS"),
        }
    return {"final_equity": 0.0, "pnl": 0.0, "trade_count": 0, "drawdown": 0.0, "costs": 0.0, "dataset_id": "candidate_dataset", "status": "PASS"}


def build_baseline_comparison(
    candidate_result: Any,
    events: Iterable[dict[str, Any]],
    *,
    config: BaselineBenchmarkConfig,
) -> BaselineComparisonResult:
    buy_and_hold = compute_buy_and_hold_baseline(events, config=config)
    no_trade = compute_no_trade_baseline(events, config=config)
    candidate = _safe_candidate_metrics(candidate_result)
    candidate_final_equity = float(candidate["final_equity"])
    candidate_pnl = float(candidate["pnl"])
    candidate_trade_count = int(candidate["trade_count"])

    abs_vs_buy = candidate_final_equity - buy_and_hold.final_equity
    rel_vs_buy = abs_vs_buy / max(abs(buy_and_hold.final_equity), 1e-9)
    abs_vs_no_trade = candidate_final_equity - no_trade.final_equity
    rel_vs_no_trade = abs_vs_no_trade / max(abs(no_trade.final_equity), 1e-9)
    success_threshold = max(buy_and_hold.final_equity, no_trade.final_equity)
    status = "PASS" if candidate_final_equity > success_threshold else "FAILED_BASELINE_COMPARISON"

    comparison_id = hashlib.sha256(
        json.dumps(
            {
                "candidate_final_equity": candidate_final_equity,
                "candidate_pnl": candidate_pnl,
                "buy_and_hold_final_equity": buy_and_hold.final_equity,
                "no_trade_final_equity": no_trade.final_equity,
                "benchmark_identity": config.configuration_identity(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    reproducibility_metadata = {
        "dataset_id": config.dataset_id or buy_and_hold.dataset_id,
        "repository_revision": config.repository_revision,
        "starting_capital": config.initial_capital,
        "benchmark_configuration": config.as_dict(),
        "cost_assumptions": {
            "fee_rate": config.fee_rate,
            "spread_pct": config.spread_pct,
            "slippage_bps": config.slippage_bps,
            "latency_ticks": config.latency_ticks,
            "model_costs": config.model_costs,
        },
        "evaluation_window": {
            "start_utc": config.evaluation_window_start_utc or buy_and_hold.evaluation_window["start_utc"],
            "end_utc": config.evaluation_window_end_utc or buy_and_hold.evaluation_window["end_utc"],
        },
        "strategy_configuration": getattr(candidate_result, "strategy_configuration", {}) if hasattr(candidate_result, "strategy_configuration") else {},
        "source_of_truth": "baseline_benchmark_evidence_only",
    }

    return BaselineComparisonResult(
        comparison_id=comparison_id,
        candidate_result={
            "final_equity": candidate_final_equity,
            "realized_pnl": candidate_pnl,
            "trade_count": candidate_trade_count,
            "drawdown": candidate.get("drawdown", 0.0),
            "costs": candidate.get("costs", 0.0),
            "dataset_id": candidate.get("dataset_id", "candidate_dataset"),
            "status": candidate.get("status", "PASS"),
        },
        buy_and_hold=buy_and_hold,
        no_trade=no_trade,
        benchmark_config=config,
        candidate_final_equity=candidate_final_equity,
        candidate_pnl=candidate_pnl,
        candidate_trade_count=candidate_trade_count,
        absolute_delta_vs_buy_and_hold=abs_vs_buy,
        relative_delta_vs_buy_and_hold=rel_vs_buy,
        absolute_delta_vs_no_trade=abs_vs_no_trade,
        relative_delta_vs_no_trade=rel_vs_no_trade,
        status=status,
        reproducibility_metadata=reproducibility_metadata,
        authority_boundary="read_only_evidence",
    )


__all__ = [
    "BaselineBenchmarkConfig",
    "BaselineResult",
    "BaselineComparisonResult",
    "compute_no_trade_baseline",
    "compute_buy_and_hold_baseline",
    "build_baseline_comparison",
]
