# Stage 2 Follow-up: Feature Quality + Strategy Handoff Contract

## What was added

1. Feature quality summarizer:

- [tools/summarize_feature_quality.py](tools/summarize_feature_quality.py)

2. In-memory handoff contract for next layer:

- `StrategyInput` dataclass in [feature_signal_engine.py](feature_signal_engine.py)
- Accessor path:
  - `FeatureSignalEngine.get_latest_strategy_input()`
  - `MarketDataEngine.get_latest_strategy_input()`

## Why this matters

- We now have objective feature health metrics.
- Strategy layer can consume a clean typed input object instead of parsing raw CSV or websocket events.

## How to run the quality report

```powershell
.\.venv\Scripts\python.exe .\tools\summarize_feature_quality.py
```

JSON output:

```powershell
.\.venv\Scripts\python.exe .\tools\summarize_feature_quality.py --json
```

## Expected interpretation

- Some invalid rows at startup are normal while partial updates fill bid/ask/last.
- `missing_core_fields` should reduce once stream stabilizes.
- Outlier counts are for review, not automatic rejection yet.

## Contract for upcoming Strategy Engine

The next stage should accept `StrategyInput` objects only when available.

Required fields guaranteed by contract when non-None:

- `bid`, `ask`, `last`
- `spread_abs`, `spread_pct`, `mid_price`
- timestamp and market metadata

Optional fields that may be None during short warm-up windows:

- `micro_return_1`, `micro_return_5`
- `spread_change_1`, `spread_change_5`
- `tick_interval_ms`

## Gate

If this report and contract look good to you, next build step is:

- Strategy Engine baseline skeleton that consumes `StrategyInput` and emits deterministic "no-trade / candidate-trade" decisions (still no execution).