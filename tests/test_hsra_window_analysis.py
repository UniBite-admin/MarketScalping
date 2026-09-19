from datetime import datetime, timezone
from pathlib import Path

from tools.hsra.window_analysis import evaluate_candidate, find_largest_valid_window


def _write_csv(path: Path, header: str, rows: list[str]):
    with path.open('w', encoding='utf-8') as fh:
        fh.write(header + '\n')
        for row in rows:
            fh.write(row + '\n')


def test_rejects_pre_first_trade_quotes(tmp_path):
    quotes = tmp_path / 'quotes.csv'
    trades = tmp_path / 'trades.csv'
    _write_csv(quotes, 'timestamp,market,bid,ask,quote_id', [
        '2019-12-01T00:59:00Z,BTC-EUR,6800.0,6810.0,q1',
        '2019-12-01T01:00:00Z,BTC-EUR,6801.0,6811.0,q2',
    ])
    _write_csv(trades, 'timestamp,market,price,trade_id', [
        '2019-12-01T01:00:30Z,BTC-EUR,6802.0,t1',
    ])
    candidate = evaluate_candidate(quotes, trades, datetime(2019, 12, 1, 0, 59, 0, tzinfo=timezone.utc), datetime(2019, 12, 1, 1, 0, 30, tzinfo=timezone.utc))
    assert candidate.valid is False
    assert candidate.reason == 'pre_first_trade_quotes_present'


def test_finds_largest_valid_window_deterministically(tmp_path):
    quotes = tmp_path / 'quotes.csv'
    trades = tmp_path / 'trades.csv'
    _write_csv(quotes, 'timestamp,market,bid,ask,quote_id', [
        '2019-12-01T00:00:00Z,BTC-EUR,6700.0,6710.0,q0',
        '2019-12-01T00:05:00Z,BTC-EUR,6710.0,6720.0,q1',
        '2019-12-01T00:10:00Z,BTC-EUR,6720.0,6730.0,q2',
        '2019-12-01T00:15:00Z,BTC-EUR,6730.0,6740.0,q3',
    ])
    _write_csv(trades, 'timestamp,market,price,trade_id', [
        '2019-12-01T00:05:00Z,BTC-EUR,6715.0,t1',
        '2019-12-01T00:12:00Z,BTC-EUR,6725.0,t2',
    ])
    best = find_largest_valid_window(quotes, trades)
    assert best is not None
    assert best.start == datetime(2019, 12, 1, 0, 5, 0, tzinfo=timezone.utc)
    assert best.end == datetime(2019, 12, 1, 0, 15, 0, tzinfo=timezone.utc)
    assert best.valid is True


def test_returns_none_when_no_valid_window_exists(tmp_path):
    quotes = tmp_path / 'quotes.csv'
    trades = tmp_path / 'trades.csv'
    _write_csv(quotes, 'timestamp,market,bid,ask,quote_id', [
        '2019-12-01T00:00:00Z,BTC-EUR,6700.0,6710.0,q0',
    ])
    _write_csv(trades, 'timestamp,market,price,trade_id', [
        '2019-12-01T00:05:00Z,BTC-EUR,6715.0,t1',
    ])
    best = find_largest_valid_window(quotes, trades)
    assert best is None
