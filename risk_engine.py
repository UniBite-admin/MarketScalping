from __future__ import annotations

import csv
import math
import os
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from strategy_engine import StrategyDecision


@dataclass(frozen=True)
class RiskState:
    available_balance: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    open_position_exists: bool
    open_position_side: str | None
    open_position_size: float | None
    open_position_entry_price: float | None
    current_drawdown: float
    maximum_drawdown: float
    recovery_status: str
    financial_valid: bool = False
    is_valid: bool = False
    daily_loss: float | None = None
    daily_loss_reference_utc: str | None = None
    consecutive_losses: int | None = None

    @classmethod
    def from_accounting(cls, accounting_state) -> "RiskState":
        if accounting_state is None:
            return cls(
                available_balance=0.0,
                equity=0.0,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                open_position_exists=False,
                open_position_side=None,
                open_position_size=None,
                open_position_entry_price=None,
                current_drawdown=0.0,
                maximum_drawdown=0.0,
                recovery_status="INVALID",
                financial_valid=False,
                is_valid=False,
            )

        recovery_status = str(getattr(accounting_state, "recovery_status", "INVALID"))
        available_balance = float(getattr(accounting_state, "available_balance", 0.0))
        equity = float(getattr(accounting_state, "equity", available_balance))
        realized_pnl = float(getattr(accounting_state, "realized_pnl", 0.0))
        unrealized_pnl = float(getattr(accounting_state, "unrealized_pnl", 0.0))
        current_drawdown = float(getattr(accounting_state, "current_drawdown", 0.0))
        maximum_drawdown = float(getattr(accounting_state, "maximum_drawdown", 0.0))

        daily_loss = _coerce_float_or_none(getattr(accounting_state, "daily_loss", None))
        daily_loss_reference_utc = _coerce_str_or_none(getattr(accounting_state, "daily_loss_reference_utc", None))
        consecutive_losses = _coerce_int_or_none(getattr(accounting_state, "consecutive_losses", None))

        open_position = getattr(accounting_state, "open_position", None)
        open_position_exists = open_position is not None
        open_position_side = getattr(open_position, "side", None) if open_position_exists else None
        open_position_size = float(getattr(open_position, "position_size", 0.0)) if open_position_exists else None
        open_position_entry_price = float(getattr(open_position, "entry_price", 0.0)) if open_position_exists else None

        financial_valid = recovery_status == "VALID" and all(
            math.isfinite(value)
            for value in (
                available_balance,
                equity,
                realized_pnl,
                unrealized_pnl,
                current_drawdown,
                maximum_drawdown,
            )
        )

        if open_position_exists:
            financial_valid = financial_valid and open_position_side in {"LONG", "SHORT"}
            financial_valid = financial_valid and open_position_size is not None and open_position_size > 0.0
            financial_valid = financial_valid and open_position_entry_price is not None and open_position_entry_price > 0.0

        return cls(
            available_balance=available_balance,
            equity=equity,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            open_position_exists=open_position_exists,
            open_position_side=open_position_side,
            open_position_size=open_position_size,
            open_position_entry_price=open_position_entry_price,
            current_drawdown=current_drawdown,
            maximum_drawdown=maximum_drawdown,
            recovery_status=recovery_status,
            financial_valid=financial_valid,
            is_valid=financial_valid,
            daily_loss=daily_loss,
            daily_loss_reference_utc=daily_loss_reference_utc,
            consecutive_losses=consecutive_losses,
        )


@dataclass
class RiskDecision:
    timestamp_utc: str
    market: str
    strategy_action: str
    risk_action: str
    approved: bool
    reason: str
    signal_strength: float
    spread_pct: float
    tick_interval_ms: float | None
    candidates_last_minute: int

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "timestamp_utc",
            "market",
            "strategy_action",
            "risk_action",
            "approved",
            "reason",
            "signal_strength",
            "spread_pct",
            "tick_interval_ms",
            "candidates_last_minute",
        ]

    def to_csv_row(self) -> list[str]:
        return [
            self.timestamp_utc,
            self.market,
            self.strategy_action,
            self.risk_action,
            str(self.approved),
            self.reason,
            _fmt(self.signal_strength),
            _fmt(self.spread_pct),
            _fmt(self.tick_interval_ms),
            str(self.candidates_last_minute),
        ]


class RiskEngine:
    def __init__(
        self,
        output_path: str,
        logger,
        enabled: bool = True,
        emergency_stop: bool = False,
        max_spread_pct: float = 0.02,
        max_tick_interval_ms: float = 2000.0,
        min_signal_strength: float = -1.0,
        max_candidates_per_minute: int = 120,
        max_position_size: float = 1.0,
        max_exposure: float = 1000.0,
        max_risk_per_trade: float = 100.0,
        max_daily_loss: float | None = None,
        max_consecutive_losses: int | None = None,
        persistence_batch_size: int = 1,
    ):
        self.output_path = output_path
        self.logger = logger
        self.enabled = enabled
        self.emergency_stop = emergency_stop
        self.max_spread_pct = max_spread_pct
        self.max_tick_interval_ms = max_tick_interval_ms
        self.min_signal_strength = min_signal_strength
        self.max_candidates_per_minute = max_candidates_per_minute
        self.max_position_size = float(max_position_size)
        self.max_exposure = float(max_exposure)
        self.max_risk_per_trade = float(max_risk_per_trade)
        self.max_daily_loss = None if max_daily_loss is None else float(max_daily_loss)
        self.max_consecutive_losses = None if max_consecutive_losses is None else int(max_consecutive_losses)
        self.persistence_batch_size = max(int(persistence_batch_size), 1)
        self._pending_rows: list[list[str]] = []

        self._candidate_timestamps = deque()
        self._prepare_output_file()

    def _prepare_output_file(self) -> None:
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(self.output_path):
            with open(self.output_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(RiskDecision.csv_headers())

            self.logger.info("risk_output_initialized path=%s", self.output_path)

    def evaluate(
        self,
        strategy_decision: StrategyDecision,
        event_time_utc: str | None = None,
        *,
        risk_state: RiskState | None = None,
        candidate_position_size: float | None = None,
        candidate_entry_notional: float | None = None,
        protected_exit_value: float | None = None,
    ) -> RiskDecision:
        now = self._resolve_event_time(event_time_utc)
        if now is None:
            return self._persist(
                RiskDecision(
                    timestamp_utc=event_time_utc or "",
                    market=strategy_decision.market,
                    strategy_action=strategy_decision.action,
                    risk_action="BLOCKED",
                    approved=False,
                    reason="invalid_event_time_utc",
                    signal_strength=strategy_decision.signal_strength,
                    spread_pct=strategy_decision.spread_pct,
                    tick_interval_ms=strategy_decision.tick_interval_ms,
                    candidates_last_minute=len(self._candidate_timestamps),
                )
            )

        candidates_last_minute = self._count_recent_candidates(now)

        if not self.enabled:
            return self._persist(
                RiskDecision(
                    timestamp_utc=now.isoformat(),
                    market=strategy_decision.market,
                    strategy_action=strategy_decision.action,
                    risk_action="NO_ACTION",
                    approved=False,
                    reason="risk_engine_disabled",
                    signal_strength=strategy_decision.signal_strength,
                    spread_pct=strategy_decision.spread_pct,
                    tick_interval_ms=strategy_decision.tick_interval_ms,
                    candidates_last_minute=candidates_last_minute,
                )
            )

        if strategy_decision.action != "CANDIDATE_TRADE":
            return self._persist(
                RiskDecision(
                    timestamp_utc=now.isoformat(),
                    market=strategy_decision.market,
                    strategy_action=strategy_decision.action,
                    risk_action="NO_ACTION",
                    approved=False,
                    reason="no_strategy_candidate",
                    signal_strength=strategy_decision.signal_strength,
                    spread_pct=strategy_decision.spread_pct,
                    tick_interval_ms=strategy_decision.tick_interval_ms,
                    candidates_last_minute=candidates_last_minute,
                )
            )

        if risk_state is not None and not self._is_valid_risk_state(risk_state):
            return self._persist(
                RiskDecision(
                    timestamp_utc=now.isoformat(),
                    market=strategy_decision.market,
                    strategy_action=strategy_decision.action,
                    risk_action="BLOCKED",
                    approved=False,
                    reason="invalid_risk_state",
                    signal_strength=strategy_decision.signal_strength,
                    spread_pct=strategy_decision.spread_pct,
                    tick_interval_ms=strategy_decision.tick_interval_ms,
                    candidates_last_minute=candidates_last_minute,
                )
            )

        reasons = []
        if self.emergency_stop:
            reasons.append("emergency_stop")

        if strategy_decision.spread_pct > self.max_spread_pct:
            reasons.append("spread_above_risk_limit")

        if (
            strategy_decision.tick_interval_ms is None
            or strategy_decision.tick_interval_ms > self.max_tick_interval_ms
        ):
            reasons.append("tick_interval_above_risk_limit")

        if strategy_decision.signal_strength < self.min_signal_strength:
            reasons.append("signal_below_risk_threshold")

        if candidates_last_minute >= self.max_candidates_per_minute:
            reasons.append("candidate_rate_limit")

        position_limit_reasons = self._evaluate_position_limits(risk_state, candidate_position_size)
        reasons.extend(position_limit_reasons)

        trade_risk_reasons = self._evaluate_trade_risk(
            risk_state=risk_state,
            candidate_entry_notional=candidate_entry_notional,
            protected_exit_value=protected_exit_value,
        )
        reasons.extend(trade_risk_reasons)

        loss_control_reasons = self._evaluate_loss_controls(risk_state)
        reasons.extend(loss_control_reasons)

        approved = len(reasons) == 0
        risk_action = "APPROVED_SIMULATION" if approved else "BLOCKED"
        reason = "risk_checks_passed" if approved else "|".join(reasons)

        decision = RiskDecision(
            timestamp_utc=now.isoformat(),
            market=strategy_decision.market,
            strategy_action=strategy_decision.action,
            risk_action=risk_action,
            approved=approved,
            reason=reason,
            signal_strength=strategy_decision.signal_strength,
            spread_pct=strategy_decision.spread_pct,
            tick_interval_ms=strategy_decision.tick_interval_ms,
            candidates_last_minute=candidates_last_minute,
        )

        if approved:
            self._candidate_timestamps.append(now)

        return self._persist(decision)

    def _evaluate_position_limits(
        self,
        risk_state: RiskState | None,
        candidate_position_size: float | None,
    ) -> list[str]:
        if risk_state is None:
            return []

        if not getattr(risk_state, "financial_valid", False) or not getattr(risk_state, "is_valid", False):
            return ["invalid_risk_state"]

        if getattr(risk_state, "recovery_status", "INVALID") not in {"VALID", "READY"}:
            return ["invalid_risk_state"]

        if self.max_position_size <= 0 or not math.isfinite(self.max_position_size):
            return ["invalid_limit_configuration"]

        if self.max_exposure <= 0 or not math.isfinite(self.max_exposure):
            return ["invalid_limit_configuration"]

        if candidate_position_size is None:
            return []

        try:
            candidate_size = float(candidate_position_size)
        except (TypeError, ValueError):
            return ["invalid_candidate_position_size"]

        if not math.isfinite(candidate_size):
            return ["invalid_candidate_position_size"]

        current_size = float(getattr(risk_state, "open_position_size", 0.0) or 0.0)
        current_entry = float(getattr(risk_state, "open_position_entry_price", 0.0) or 0.0)

        projected_size = current_size + candidate_size if candidate_size >= 0 else max(current_size + candidate_size, 0.0)
        if projected_size > self.max_position_size:
            return ["max_position_size"]

        reference_price = current_entry if current_entry > 0 else 1.0
        projected_exposure = abs(projected_size) * reference_price
        if projected_exposure > self.max_exposure:
            return ["max_exposure"]

        return []

    def _evaluate_trade_risk(
        self,
        *,
        risk_state: RiskState | None,
        candidate_entry_notional: float | None,
        protected_exit_value: float | None,
    ) -> list[str]:
        if candidate_entry_notional is None and protected_exit_value is None:
            return []

        if risk_state is None:
            return ["invalid_risk_state"]

        if not getattr(risk_state, "financial_valid", False) or not getattr(risk_state, "is_valid", False):
            return ["invalid_risk_state"]

        if getattr(risk_state, "recovery_status", "INVALID") not in {"VALID", "READY"}:
            return ["invalid_risk_state"]

        if self.max_risk_per_trade <= 0 or not math.isfinite(self.max_risk_per_trade):
            return ["invalid_max_risk_per_trade"]

        if candidate_entry_notional is None:
            return ["missing_candidate_entry_notional"]

        if protected_exit_value is None:
            return ["missing_protected_exit_value"]

        try:
            entry_notional = float(candidate_entry_notional)
            protected_value = float(protected_exit_value)
        except (TypeError, ValueError):
            return ["invalid_trade_risk_inputs"]

        if not math.isfinite(entry_notional) or not math.isfinite(protected_value):
            return ["invalid_trade_risk_inputs"]

        if entry_notional < 0:
            return ["invalid_candidate_entry_notional"]

        if protected_value < 0:
            return ["invalid_protected_exit_value"]

        if protected_value > entry_notional:
            return ["invalid_protected_exit_value"]

        trade_risk = entry_notional - protected_value
        if trade_risk < 0 or not math.isfinite(trade_risk):
            return ["invalid_trade_risk"]

        if trade_risk > self.max_risk_per_trade:
            return ["max_risk_per_trade"]

        return []

    def _evaluate_loss_controls(self, risk_state: RiskState | None) -> list[str]:
        if self.max_daily_loss is None and self.max_consecutive_losses is None:
            return []

        if risk_state is None:
            return ["invalid_risk_state"]

        if not getattr(risk_state, "financial_valid", False) or not getattr(risk_state, "is_valid", False):
            return ["invalid_risk_state"]

        if getattr(risk_state, "recovery_status", "INVALID") not in {"VALID", "READY"}:
            return ["invalid_risk_state"]

        reasons: list[str] = []

        if self.max_daily_loss is not None:
            daily_limit = float(self.max_daily_loss)
            if not math.isfinite(daily_limit) or daily_limit < 0:
                return ["invalid_max_daily_loss"]

            daily_loss = getattr(risk_state, "daily_loss", None)
            daily_loss_reference_utc = getattr(risk_state, "daily_loss_reference_utc", None)
            if daily_loss is None or daily_loss_reference_utc is None:
                return ["missing_daily_loss_state"]

            try:
                current_daily_loss = float(daily_loss)
            except (TypeError, ValueError):
                return ["invalid_daily_loss_state"]

            if not math.isfinite(current_daily_loss) or current_daily_loss < 0:
                return ["invalid_daily_loss_state"]

            if not _is_valid_iso_utc(daily_loss_reference_utc):
                return ["invalid_daily_loss_state"]

            if current_daily_loss >= daily_limit:
                reasons.append("max_daily_loss")

        if self.max_consecutive_losses is not None:
            max_losses = int(self.max_consecutive_losses)
            if max_losses < 0:
                return ["invalid_max_consecutive_losses"]

            consecutive_losses = getattr(risk_state, "consecutive_losses", None)
            if consecutive_losses is None:
                return ["missing_consecutive_loss_state"]

            try:
                current_consecutive_losses = int(consecutive_losses)
            except (TypeError, ValueError):
                return ["invalid_consecutive_loss_state"]

            if current_consecutive_losses < 0:
                return ["invalid_consecutive_loss_state"]

            if current_consecutive_losses >= max_losses:
                reasons.append("max_consecutive_losses")

        return reasons

    def _is_valid_risk_state(self, risk_state: RiskState | None) -> bool:
        if risk_state is None:
            return False

        if not getattr(risk_state, "financial_valid", False) or not getattr(risk_state, "is_valid", False):
            return False

        if getattr(risk_state, "recovery_status", "INVALID") not in {"VALID", "READY"}:
            return False

        return True

    def _count_recent_candidates(self, now: datetime) -> int:
        while self._candidate_timestamps and (now - self._candidate_timestamps[0]).total_seconds() > 60:
            self._candidate_timestamps.popleft()
        return len(self._candidate_timestamps)

    def _resolve_event_time(self, event_time_utc: str | None) -> datetime | None:
        if event_time_utc is None:
            return datetime.now(timezone.utc)

        try:
            parsed = datetime.fromisoformat(event_time_utc.replace("Z", "+00:00"))
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return None

        return parsed.astimezone(timezone.utc)

    def _persist(self, decision: RiskDecision) -> RiskDecision:
        self._pending_rows.append(decision.to_csv_row())
        if len(self._pending_rows) >= self.persistence_batch_size:
            self.flush()

        self.logger.info(
            "risk_decision action=%s approved=%s reason=%s strength=%.8f spread_pct=%.8f",
            decision.risk_action,
            decision.approved,
            decision.reason,
            decision.signal_strength,
            decision.spread_pct,
        )

        return decision

    def flush(self) -> None:
        if not self._pending_rows:
            return

        with open(self.output_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(self._pending_rows)

        self._pending_rows.clear()

    def close(self) -> None:
        self.flush()


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10f}"


def _coerce_float_or_none(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _coerce_int_or_none(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _coerce_str_or_none(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_valid_iso_utc(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _coerce_float_or_none(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _coerce_int_or_none(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _coerce_str_or_none(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_valid_iso_utc(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None