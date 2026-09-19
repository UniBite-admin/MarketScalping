from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from .reader import iter_quotes, iter_trades


@dataclass(frozen=True)
class WindowCandidate:
    start: datetime
    end: datetime
    duration_seconds: float
    quote_count: int
    trade_count: int
    valid: bool
    reason: Optional[str] = None


def _sort_valid_quotes(quotes: Iterable[object]) -> list[object]:
    return sorted((q for q in quotes if getattr(q, 'ts', None) is not None), key=lambda q: q.ts)


def _sort_valid_trades(trades: Iterable[object]) -> list[object]:
    return sorted((t for t in trades if getattr(t, 'ts', None) is not None), key=lambda t: t.ts)


def evaluate_candidate(quotes_path: str | Path, trades_path: str | Path, start: datetime, end: datetime) -> WindowCandidate:
    quotes = _sort_valid_quotes(iter_quotes(Path(quotes_path)))
    trades = _sort_valid_trades(iter_trades(Path(trades_path)))
    q_in = [q for q in quotes if start <= q.ts <= end]
    t_in = [t for t in trades if start <= t.ts <= end]
    if not t_in:
        return WindowCandidate(start=start, end=end, duration_seconds=(end - start).total_seconds(), quote_count=len(q_in), trade_count=0, valid=False, reason='no_trades_in_requested_window')
    first_trade_ts = min(t.ts for t in t_in)
    pre_first_trade_quotes = [q for q in q_in if q.ts < first_trade_ts]
    if pre_first_trade_quotes:
        return WindowCandidate(
            start=start,
            end=end,
            duration_seconds=(end - start).total_seconds(),
            quote_count=len(q_in),
            trade_count=len(t_in),
            valid=False,
            reason='pre_first_trade_quotes_present',
        )
    return WindowCandidate(start=start, end=end, duration_seconds=(end - start).total_seconds(), quote_count=len(q_in), trade_count=len(t_in), valid=True, reason=None)


def find_largest_valid_window(quotes_path: str | Path, trades_path: str | Path) -> Optional[WindowCandidate]:
    quotes = _sort_valid_quotes(iter_quotes(Path(quotes_path)))
    trades = _sort_valid_trades(iter_trades(Path(trades_path)))
    if not quotes or not trades:
        return None
    best: Optional[WindowCandidate] = None
    for trade in trades:
        start = trade.ts
        future_quotes = [q for q in quotes if q.ts >= start]
        if not future_quotes:
            continue
        end = max(q.ts for q in future_quotes)
        candidate = evaluate_candidate(quotes_path, trades_path, start, end)
        if candidate.valid:
            if best is None or candidate.duration_seconds > best.duration_seconds:
                best = candidate
    return best


def find_largest_candidate_by_contract(quotes_path: str | Path, trades_path: str | Path) -> tuple[Optional[WindowCandidate], list[WindowCandidate]]:
    quotes = _sort_valid_quotes(iter_quotes(Path(quotes_path)))
    trades = _sort_valid_trades(iter_trades(Path(trades_path)))
    if not quotes or not trades:
        return None, []
    candidates: list[WindowCandidate] = []
    for trade in trades:
        start = trade.ts
        future_quotes = [q for q in quotes if q.ts >= start]
        if not future_quotes:
            continue
        end = max(q.ts for q in future_quotes)
        candidates.append(evaluate_candidate(quotes_path, trades_path, start, end))
    valid = [c for c in candidates if c.valid]
    best = max(valid, key=lambda c: (c.duration_seconds, c.quote_count, c.trade_count), default=None)
    return best, valid


if __name__ == '__main__':
    quotes_path = Path('data/tmp_tardis/BTCEUR_quotes_20191201.csv.gz')
    trades_path = Path('data/tmp_tardis/BTCEUR_trades_20191201.csv.gz')
    candidate, valid = find_largest_candidate_by_contract(quotes_path, trades_path)
    print('best_candidate', candidate)
    print('valid_candidate_count', len(valid))
