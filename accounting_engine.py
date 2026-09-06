from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class SimulatedOrder:
    order_id: str
    trade_id: str
    timestamp_utc: str
    symbol: str
    side: str
    reference_price: float
    position_size: float
    strategy: str
    signal: str
    confidence: float | None


@dataclass
class SimulatedFill:
    fill_id: str
    order_id: str
    trade_id: str
    timestamp_utc: str
    symbol: str
    side: str
    reference_price: float
    execution_price: float
    position_size: float
    fee_paid: float
    slippage_impact: float


@dataclass
class OpenPosition:
    trade_id: str
    symbol: str
    side: str
    entry_timestamp_utc: str
    entry_price: float
    entry_execution_price: float
    position_size: float
    entry_fee: float
    entry_slippage: float
    strategy: str
    signal: str
    confidence: float | None


@dataclass
class ClosedTrade:
    trade_id: str
    timestamp_utc: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    position_size: float
    gross_pnl: float
    fees: float
    slippage: float
    net_pnl: float
    holding_time_seconds: float
    strategy: str
    signal: str
    confidence: float | None
    close_reason: str
    entry_timestamp_utc: str
    exit_timestamp_utc: str

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "trade_id",
            "timestamp_utc",
            "symbol",
            "side",
            "entry_price",
            "exit_price",
            "position_size",
            "gross_pnl",
            "fees",
            "slippage",
            "net_pnl",
            "holding_time_seconds",
            "strategy",
            "signal",
            "confidence",
            "close_reason",
            "entry_timestamp_utc",
            "exit_timestamp_utc",
        ]

    def to_csv_row(self) -> list[str]:
        return [
            self.trade_id,
            self.timestamp_utc,
            self.symbol,
            self.side,
            _fmt(self.entry_price),
            _fmt(self.exit_price),
            _fmt(self.position_size),
            _fmt(self.gross_pnl),
            _fmt(self.fees),
            _fmt(self.slippage),
            _fmt(self.net_pnl),
            _fmt(self.holding_time_seconds),
            self.strategy,
            self.signal,
            _fmt(self.confidence),
            self.close_reason,
            self.entry_timestamp_utc,
            self.exit_timestamp_utc,
        ]


@dataclass
class AccountSnapshot:
    timestamp_utc: str
    starting_balance: float
    available_balance: float
    realized_pnl: float
    unrealized_pnl: float
    equity: float
    cumulative_fees: float
    cumulative_slippage: float
    peak_equity: float
    current_drawdown: float
    maximum_drawdown: float

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "timestamp_utc",
            "starting_balance",
            "available_balance",
            "realized_pnl",
            "unrealized_pnl",
            "equity",
            "cumulative_fees",
            "cumulative_slippage",
            "peak_equity",
            "current_drawdown",
            "maximum_drawdown",
        ]

    def to_csv_row(self) -> list[str]:
        return [
            self.timestamp_utc,
            _fmt(self.starting_balance),
            _fmt(self.available_balance),
            _fmt(self.realized_pnl),
            _fmt(self.unrealized_pnl),
            _fmt(self.equity),
            _fmt(self.cumulative_fees),
            _fmt(self.cumulative_slippage),
            _fmt(self.peak_equity),
            _fmt(self.current_drawdown),
            _fmt(self.maximum_drawdown),
        ]


class AccountingEngine:
    """Minimal simulation-only accounting model with explicit order/fill/position/trade stages."""

    def __init__(
        self,
        trade_ledger_path: str,
        account_state_path: str,
        open_position_state_path: str,
        logger,
        enabled: bool = True,
        strategy_name: str = "baseline_momentum",
        starting_balance: float = 1000.0,
        order_notional_eur: float = 10.0,
        fee_rate: float = 0.001,
        slippage_bps: float = 1.0,
    ):
        self.trade_ledger_path = trade_ledger_path
        self.account_state_path = account_state_path
        self.open_position_state_path = open_position_state_path
        self.logger = logger
        self.enabled = enabled
        self.strategy_name = strategy_name
        self.starting_balance = starting_balance
        self.order_notional_eur = order_notional_eur
        self.fee_rate = fee_rate
        self.slippage_bps = slippage_bps

        self.available_balance = starting_balance
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.equity = starting_balance
        self.cumulative_fees = 0.0
        self.cumulative_slippage = 0.0
        self.peak_equity = starting_balance
        self.current_drawdown = 0.0
        self.maximum_drawdown = 0.0
        self._last_mark_price: float | None = None
        self._processed_successful_execution_ids: set[str] = set()
        self._processed_successful_execution_id_order: list[str] = []
        self._max_processed_successful_ids = 10000

        self.open_position: OpenPosition | None = None

        self._trade_counter = 0
        self._order_counter = 0
        self._fill_counter = 0

        self._prepare_output_files()
        self._restore_state_on_startup()

    def _prepare_output_files(self) -> None:
        for path in [self.trade_ledger_path, self.account_state_path, self.open_position_state_path]:
            output_dir = os.path.dirname(path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(self.trade_ledger_path):
            with open(self.trade_ledger_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(ClosedTrade.csv_headers())
            self.logger.info("trade_ledger_initialized path=%s", self.trade_ledger_path)

        if not os.path.exists(self.account_state_path):
            with open(self.account_state_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(AccountSnapshot.csv_headers())
            self.logger.info("account_state_initialized path=%s", self.account_state_path)

    def _restore_state_on_startup(self) -> None:
        self._trade_counter = max(self._trade_counter, self._max_trade_counter_from_ledger())

        if not os.path.exists(self.open_position_state_path):
            return

        try:
            with open(self.open_position_state_path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
        except Exception as exc:
            self.logger.error("accounting_state_restore_error path=%s error=%s", self.open_position_state_path, exc)
            return

        account_state = state.get("account_state") or {}
        self.available_balance = float(account_state.get("available_balance", self.available_balance))
        self.realized_pnl = float(account_state.get("realized_pnl", self.realized_pnl))
        self.unrealized_pnl = float(account_state.get("unrealized_pnl", self.unrealized_pnl))
        self.equity = float(account_state.get("equity", self.equity))
        self.cumulative_fees = float(account_state.get("cumulative_fees", self.cumulative_fees))
        self.cumulative_slippage = float(account_state.get("cumulative_slippage", self.cumulative_slippage))
        self.peak_equity = float(account_state.get("peak_equity", self.peak_equity))
        self.current_drawdown = float(account_state.get("current_drawdown", self.current_drawdown))
        self.maximum_drawdown = float(account_state.get("maximum_drawdown", self.maximum_drawdown))
        self._last_mark_price = _float_or_none(state.get("last_mark_price"))

        counters = state.get("counters") or {}
        self._trade_counter = max(self._trade_counter, int(counters.get("trade_counter", self._trade_counter)))
        self._order_counter = max(self._order_counter, int(counters.get("order_counter", self._order_counter)))
        self._fill_counter = max(self._fill_counter, int(counters.get("fill_counter", self._fill_counter)))

        processed_ids = state.get("processed_successful_execution_ids")
        if isinstance(processed_ids, list):
            self._processed_successful_execution_id_order = [str(x) for x in processed_ids if x]
            if len(self._processed_successful_execution_id_order) > self._max_processed_successful_ids:
                self._processed_successful_execution_id_order = self._processed_successful_execution_id_order[
                    -self._max_processed_successful_ids :
                ]
            self._processed_successful_execution_ids = set(self._processed_successful_execution_id_order)

        open_position_raw = state.get("open_position")
        if isinstance(open_position_raw, dict):
            entry_execution_price = _float_or_none(open_position_raw.get("entry_execution_price"))
            entry_price = float(open_position_raw["entry_price"])
            self.open_position = OpenPosition(
                trade_id=str(open_position_raw["trade_id"]),
                symbol=str(open_position_raw["symbol"]),
                side=str(open_position_raw["side"]),
                entry_timestamp_utc=str(open_position_raw["entry_timestamp_utc"]),
                entry_price=entry_price,
                entry_execution_price=entry_execution_price if entry_execution_price is not None else entry_price,
                position_size=float(open_position_raw["position_size"]),
                entry_fee=float(open_position_raw["entry_fee"]),
                entry_slippage=float(open_position_raw["entry_slippage"]),
                strategy=str(open_position_raw["strategy"]),
                signal=str(open_position_raw["signal"]),
                confidence=_float_or_none(open_position_raw.get("confidence")),
            )
            self._trade_counter = max(self._trade_counter, _trade_number(self.open_position.trade_id))

        self.logger.info(
            "accounting_state_restored path=%s open_position=%s realized_pnl=%.10f available_balance=%.10f",
            self.open_position_state_path,
            self.open_position is not None,
            self.realized_pnl,
            self.available_balance,
        )

    @property
    def slippage_rate(self) -> float:
        return self.slippage_bps / 10000.0

    def update_mark_to_market(self, bid: float | None, ask: float | None, timestamp_utc: str | None = None) -> None:
        if not self.enabled:
            return

        if self.open_position is None:
            self.unrealized_pnl = 0.0
            self._last_mark_price = None
            self._recompute_equity(open_market_value=None)
            self._persist_account_snapshot(timestamp_utc)
            return

        mark_price = bid if self.open_position.side == "LONG" else ask
        if mark_price is None or mark_price <= 0:
            self._persist_account_snapshot(timestamp_utc)
            return

        self._last_mark_price = mark_price
        self.unrealized_pnl = (mark_price - self.open_position.entry_price) * self.open_position.position_size
        open_market_value = mark_price * self.open_position.position_size
        self._recompute_equity(open_market_value=open_market_value)
        self._persist_account_snapshot(timestamp_utc)

    def process_execution(
        self,
        execution_event,
        bid: float | None,
        ask: float | None,
        timestamp_utc: str | None = None,
        signal: str | None = None,
        confidence: float | None = None,
    ) -> ClosedTrade | None:
        if not self.enabled:
            return None

        self.update_mark_to_market(bid=bid, ask=ask, timestamp_utc=timestamp_utc)

        if execution_event is None:
            return None

        if execution_event.execution_action != "SIMULATED_ORDER_PREPARED":
            return None

        ts = timestamp_utc or _now_iso()
        successful_event_id = self._extract_successful_execution_id(execution_event=execution_event, fallback_timestamp_utc=ts)
        if successful_event_id in self._processed_successful_execution_ids:
            self.logger.info("accounting_duplicate_successful_fill_ignored id=%s", successful_event_id)
            return None

        if self.open_position is None:
            opened = self._open_position_from_fill(
                execution_event=execution_event,
                ask=ask,
                timestamp_utc=ts,
                signal=signal,
                confidence=confidence,
            )
            if not opened:
                return None
            self._remember_processed_successful_execution_id(successful_event_id)
            self.update_mark_to_market(bid=bid, ask=ask, timestamp_utc=ts)
            return None

        closed_trade = self._close_position_from_fill(execution_event=execution_event, bid=bid, timestamp_utc=ts)
        self._persist_closed_trade(closed_trade)
        self._remember_processed_successful_execution_id(successful_event_id)
        self.update_mark_to_market(bid=bid, ask=ask, timestamp_utc=ts)
        return closed_trade

    def _open_position_from_fill(
        self,
        execution_event,
        ask: float | None,
        timestamp_utc: str,
        signal: str | None,
        confidence: float | None,
    ) -> bool:
        if ask is None or ask <= 0:
            self.logger.warning("accounting_open_skipped reason=missing_ask")
            return False

        reference_price = ask
        execution_price = reference_price * (1 + self.slippage_rate)

        notional = min(self.order_notional_eur, self.available_balance)
        if notional <= 0:
            self.logger.warning("accounting_open_skipped reason=insufficient_balance")
            return False

        position_size = notional / execution_price
        entry_fee = (position_size * execution_price) * self.fee_rate
        entry_slippage = (execution_price - reference_price) * position_size

        if self.available_balance < (position_size * execution_price + entry_fee):
            self.logger.warning("accounting_open_skipped reason=insufficient_balance_after_fee")
            return False

        self._trade_counter += 1
        self._order_counter += 1
        self._fill_counter += 1

        trade_id = f"TRD-{self._trade_counter:06d}"
        order = SimulatedOrder(
            order_id=f"ORD-{self._order_counter:06d}",
            trade_id=trade_id,
            timestamp_utc=timestamp_utc,
            symbol=execution_event.market,
            side="BUY",
            reference_price=reference_price,
            position_size=position_size,
            strategy=self.strategy_name,
            signal=signal or execution_event.reason,
            confidence=confidence,
        )
        fill = SimulatedFill(
            fill_id=f"FIL-{self._fill_counter:06d}",
            order_id=order.order_id,
            trade_id=trade_id,
            timestamp_utc=timestamp_utc,
            symbol=execution_event.market,
            side="BUY",
            reference_price=reference_price,
            execution_price=execution_price,
            position_size=position_size,
            fee_paid=entry_fee,
            slippage_impact=entry_slippage,
        )

        self.available_balance -= (position_size * execution_price + entry_fee)
        self.cumulative_fees += entry_fee
        self.cumulative_slippage += entry_slippage

        self.open_position = OpenPosition(
            trade_id=trade_id,
            symbol=execution_event.market,
            side="LONG",
            entry_timestamp_utc=timestamp_utc,
            entry_price=fill.execution_price,
            entry_execution_price=fill.execution_price,
            position_size=position_size,
            entry_fee=entry_fee,
            entry_slippage=entry_slippage,
            strategy=self.strategy_name,
            signal=order.signal,
            confidence=confidence,
        )

        self.logger.info(
            "accounting_open trade_id=%s order_id=%s fill_id=%s entry_price=%.10f size=%.10f fee=%.10f",
            trade_id,
            order.order_id,
            fill.fill_id,
            fill.execution_price,
            fill.position_size,
            fill.fee_paid,
        )
        return True

    def _close_position_from_fill(self, execution_event, bid: float | None, timestamp_utc: str) -> ClosedTrade:
        if self.open_position is None:
            raise RuntimeError("close called with no open position")

        if bid is None or bid <= 0:
            raise RuntimeError("cannot close position without valid bid")

        reference_price = bid
        execution_price = reference_price * (1 - self.slippage_rate)

        self._order_counter += 1
        self._fill_counter += 1
        order_id = f"ORD-{self._order_counter:06d}"
        fill_id = f"FIL-{self._fill_counter:06d}"

        position = self.open_position
        exit_notional = position.position_size * execution_price
        exit_fee = exit_notional * self.fee_rate
        exit_slippage = (reference_price - execution_price) * position.position_size

        gross_pnl = (execution_price - position.entry_price) * position.position_size
        total_fees = position.entry_fee + exit_fee
        total_slippage = position.entry_slippage + exit_slippage
        net_pnl = gross_pnl - total_fees

        entry_time = datetime.fromisoformat(position.entry_timestamp_utc.replace("Z", "+00:00"))
        exit_time = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
        holding_time_seconds = max((exit_time - entry_time).total_seconds(), 0.0)

        self.available_balance += (exit_notional - exit_fee)
        self.realized_pnl += net_pnl
        self.unrealized_pnl = 0.0
        self.cumulative_fees += exit_fee
        self.cumulative_slippage += exit_slippage
        self._recompute_equity(open_market_value=None)

        closed_trade = ClosedTrade(
            trade_id=position.trade_id,
            timestamp_utc=timestamp_utc,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=execution_price,
            position_size=position.position_size,
            gross_pnl=gross_pnl,
            fees=total_fees,
            slippage=total_slippage,
            net_pnl=net_pnl,
            holding_time_seconds=holding_time_seconds,
            strategy=position.strategy,
            signal=position.signal,
            confidence=position.confidence,
            close_reason=execution_event.reason,
            entry_timestamp_utc=position.entry_timestamp_utc,
            exit_timestamp_utc=timestamp_utc,
        )

        self.logger.info(
            "accounting_close trade_id=%s order_id=%s fill_id=%s gross=%.10f fees=%.10f net=%.10f",
            position.trade_id,
            order_id,
            fill_id,
            gross_pnl,
            total_fees,
            net_pnl,
        )

        self.open_position = None
        self._last_mark_price = None
        return closed_trade

    def _persist_closed_trade(self, trade: ClosedTrade) -> None:
        with open(self.trade_ledger_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(trade.to_csv_row())
        self._persist_runtime_state()

    def _persist_account_snapshot(self, timestamp_utc: str | None = None) -> None:
        snapshot = AccountSnapshot(
            timestamp_utc=timestamp_utc or _now_iso(),
            starting_balance=self.starting_balance,
            available_balance=self.available_balance,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            equity=self.equity,
            cumulative_fees=self.cumulative_fees,
            cumulative_slippage=self.cumulative_slippage,
            peak_equity=self.peak_equity,
            current_drawdown=self.current_drawdown,
            maximum_drawdown=self.maximum_drawdown,
        )

        with open(self.account_state_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(snapshot.to_csv_row())

        self._persist_runtime_state()

    def _persist_runtime_state(self) -> None:
        state = {
            "version": 1,
            "timestamp_utc": _now_iso(),
            "open_position": None,
            "account_state": {
                "starting_balance": self.starting_balance,
                "available_balance": self.available_balance,
                "realized_pnl": self.realized_pnl,
                "unrealized_pnl": self.unrealized_pnl,
                "equity": self.equity,
                "cumulative_fees": self.cumulative_fees,
                "cumulative_slippage": self.cumulative_slippage,
                "peak_equity": self.peak_equity,
                "current_drawdown": self.current_drawdown,
                "maximum_drawdown": self.maximum_drawdown,
            },
            "counters": {
                "trade_counter": self._trade_counter,
                "order_counter": self._order_counter,
                "fill_counter": self._fill_counter,
            },
            "processed_successful_execution_ids": self._processed_successful_execution_id_order,
            "last_mark_price": self._last_mark_price,
        }

        if self.open_position is not None:
            state["open_position"] = {
                "trade_id": self.open_position.trade_id,
                "symbol": self.open_position.symbol,
                "side": self.open_position.side,
                "entry_timestamp_utc": self.open_position.entry_timestamp_utc,
                "entry_price": self.open_position.entry_price,
                "entry_execution_price": self.open_position.entry_execution_price,
                "position_size": self.open_position.position_size,
                "entry_fee": self.open_position.entry_fee,
                "entry_slippage": self.open_position.entry_slippage,
                "strategy": self.open_position.strategy,
                "signal": self.open_position.signal,
                "confidence": self.open_position.confidence,
            }

        with open(self.open_position_state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    def _max_trade_counter_from_ledger(self) -> int:
        if not os.path.exists(self.trade_ledger_path):
            return 0

        max_trade = 0
        with open(self.trade_ledger_path, "r", newline="", encoding="utf-8") as csv_file:
            for row in csv.DictReader(csv_file):
                max_trade = max(max_trade, _trade_number(row.get("trade_id", "")))
        return max_trade

    def _extract_successful_execution_id(self, execution_event, fallback_timestamp_utc: str) -> str:
        for attr in ["execution_event_id", "fill_id", "order_id"]:
            value = getattr(execution_event, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()

        # Deterministic fallback for backward compatibility in tests/custom events.
        parts = [
            str(getattr(execution_event, "market", "")),
            str(getattr(execution_event, "execution_action", "")),
            str(getattr(execution_event, "reason", "")),
            str(getattr(execution_event, "strategy_action", "")),
            str(getattr(execution_event, "risk_action", "")),
            _fmt(_float_or_none(getattr(execution_event, "signal_strength", None))),
            _fmt(_float_or_none(getattr(execution_event, "spread_pct", None))),
            str(getattr(execution_event, "timestamp_utc", "") or fallback_timestamp_utc),
        ]
        return "fallback|" + "|".join(parts)

    def _remember_processed_successful_execution_id(self, event_id: str) -> None:
        if event_id in self._processed_successful_execution_ids:
            return

        self._processed_successful_execution_ids.add(event_id)
        self._processed_successful_execution_id_order.append(event_id)

        if len(self._processed_successful_execution_id_order) > self._max_processed_successful_ids:
            removed = self._processed_successful_execution_id_order.pop(0)
            self._processed_successful_execution_ids.discard(removed)

        self._persist_runtime_state()

    def _recompute_equity(self, open_market_value: float | None) -> None:
        if self.open_position is None or open_market_value is None:
            self.equity = self.available_balance
        else:
            self.equity = self.available_balance + open_market_value

        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        if self.peak_equity > 0:
            self.current_drawdown = max((self.peak_equity - self.equity) / self.peak_equity, 0.0)
        else:
            self.current_drawdown = 0.0

        if self.current_drawdown > self.maximum_drawdown:
            self.maximum_drawdown = self.current_drawdown


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10f}"


def _float_or_none(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _trade_number(trade_id: str) -> int:
    if not isinstance(trade_id, str):
        return 0
    parts = trade_id.split("-")
    if len(parts) != 2 or parts[0] != "TRD":
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
