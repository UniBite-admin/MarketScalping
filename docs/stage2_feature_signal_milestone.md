# Stage 2 Milestone: Feature / Signal Engine (Slice 1)

## 1) What are we doing?

We are converting live market updates into deterministic feature rows.

## 2) Why are we doing it?

Strategy and ML components must consume structured numeric features, not raw websocket messages.

## 3) What are we going to build?

The first feature slice writes one CSV row per market update with:

- `bid`, `ask`, `last`
- `spread_abs`, `spread_pct`, `mid_price`
- `micro_return_1`, `micro_return_5`
- `spread_change_1`, `spread_change_5`
- `tick_interval_ms`
- quality flags: `is_valid`, `validation_errors`

Output file:

- [data/features_btc_eur.csv](data/features_btc_eur.csv)

## 4) What do I need to do?

1. Run the market data app.
2. Let it run for 2 to 5 minutes.
3. Stop with Ctrl+C.
4. Open [data/features_btc_eur.csv](data/features_btc_eur.csv) and inspect the newest rows.

Run command:

```powershell
.\.venv\Scripts\python.exe .\market_data.py
```

## 5) How will we test it?

- File [data/features_btc_eur.csv](data/features_btc_eur.csv) exists.
- Header row contains all expected fields.
- New rows are appended during runtime.
- `is_valid` eventually becomes `True` once bid/ask/last are all present.
- `tick_interval_ms` is positive for rows after the first tick.
- No crash in market data runtime.

## 6) How will we know it is successful?

Pass this milestone if all are true:

1. Feature file is created automatically.
2. Feature rows append in real time.
3. Core calculated fields (`spread_abs`, `spread_pct`, `mid_price`) are populated when bid/ask exist.
4. Validation flags behave logically (`missing_core_fields` only when last/bid/ask incomplete).
5. Market data process remains stable.

After this pass, we can build the next slice: feature quality summary tooling and a clean in-memory handoff contract for Strategy Engine input.