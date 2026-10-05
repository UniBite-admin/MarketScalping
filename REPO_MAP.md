# MarketScalping Repository Map

**1. Purpose**
- Short: Lightweight navigation index to help agents and humans orient in the repository without scanning every file.

**2. System Pipeline**
- LIVE/PAPER:
  Market Data -> Feature Signal -> Strategy -> Risk -> Execution -> Accounting -> Position Projection
- HISTORICAL:
  Historical Source -> Validation / Canonicalization -> Replay -> Feature Signal -> Strategy -> Risk -> Execution Simulation -> Accounting -> Position Projection -> Reporting

**3. Authority Model**
- ExecutionEngine: execution journal / intake (evidence-only).
- AccountingEngine: authoritative financial ledger (source-of-truth for balances/PnL).
- PositionManager: derived projection from accounting (no independent financial authority).
- RiskEngine: pre-commit gate only (no financial authority).
- ReplayRunner / BacktestEngine: determinism / replay orchestration (replay builds pipeline outputs; accounting remains authoritative).

**4. Core Modules**
| File | Role | Depends on / feeds | Authority / notes |
|------|------|--------------------|------------------|
| accounting_engine.py | Authoritative ledger & persistence | execution_engine.py, position_manager.py | AccountingEngine = financial source-of-truth (see ADR 0002) |
| execution_engine.py | Execution intake & simulated execution behavior | risk_engine.py | Execution journal; no direct ledger authority |
| position_manager.py | Position projection / lifecycle view | accounting_engine.py | Derived from accounting state |
| risk_engine.py | Risk gating / decision records | strategy_engine.py, accounting_engine.py (partial) | Pre-commit decision; does not mutate ledger |
| market_data_engine.py | Live pipeline orchestrator (paper sessions support) | feature_signal_engine.py, strategy_engine.py, risk_engine.py, execution_engine.py, accounting_engine.py | Coordinates live/paper flow |
| replay_runner.py | Replay runner that feeds MarketDataEngine for historical runs | historical data / canonical JSONL | Handles sorting/normalization for replay; note: materializes normalized events depending on mode |
| backtest_engine.py | Deterministic backtesting & analytics | replay_runner.py, backtest_execution_model.py, accounting_engine.py | Produces BacktestResult and analytics |
| binance_trade_adapter.py | Binance archive audit + canonicalization | data/raw/binance_public | Converts ZIP->JSONL canonical events |
| bitvavo_trade_collector.py | Bitvavo historical collector | network / Bitvavo API | Collector for Bitvavo raw windows (pagination semantics implemented) |
| historical_dataset.py | Dataset acquisition / manifest / validation | bitvavo_trade_collector.py | Aggregates windows, produces manifest + per-file SHA256 |
| feature_signal_engine.py | Feature extraction for strategy input | market_data_engine.py | Produces features CSV used by StrategyEngine |
| strategy_engine.py | Deterministic baseline strategy decisions | feature_signal_engine.py | Writes strategy CSV; persistence batch controls |
| backtest_execution_model.py | Execution simulation model | backtest_engine.py | Execution outcome modeling and fills |
| tools/ | Utilities and orchestrator tooling | various | Orchestrator and agent helpers (roadmap loader, tools for QA/monitoring) |
| tools/hsra/ | Historical State-Reconstruction Adapter (HSRA) | data/raw/quotes + data/raw/trades -> data/canonical | Offline deterministic adapter that reconstructs `last` from trades for canonical replay input when the requested window is complete. Produces `canonical_events.jsonl`, `provenance_sidecar.jsonl`, and `metadata.json` (strict fail-closed semantics). |

**5. Historical Data Layer**
- Bitvavo collector: `bitvavo_trade_collector.py` — collects raw windows, implements pagination/cursor; input: Bitvavo API; output: per-window JSONL under `data/raw/...`; status: implemented (collector behaviour and pagination checks present).
- Historical dataset manager: `historical_dataset.py` — builds dataset manifests, validates per-file SHA256, freeze semantics; input: collector output; output: dataset manifest + raw files; status: implemented.
- Binance adapter/archive: `binance_trade_adapter.py` — ZIP streaming audit and canonicalization to JSONL; input: Binance trade ZIP; output: canonical JSONL + SHA256; status: tests present (`tests/test_binance_trade_adapter.py`).
- Replay layer: `replay_runner.py` — normalizes events and replays through `MarketDataEngine`; input: canonical JSONL or iterable of events; output: pipeline CSVs and replay metrics; status: implemented; constraint: currently materializes normalized events (SQLite or by list) which is a scaling constraint.
 - Replay layer: `replay_runner.py` — normalizes events and replays through `MarketDataEngine`; input: canonical JSONL or iterable of events; output: pipeline CSVs and replay metrics; status: implemented; constraint: the non-streaming path inserts normalized events into a temporary SQLite DB and then iterates an ordered SELECT (disk-backed ordering), while the streaming path feeds the engine directly; this non-streaming behavior is a scaling constraint.
- Backtest layer: `backtest_engine.py` & `backtest_execution_model.py` — run deterministic simulations over events; input: normalized events (iterable or list); output: BacktestResult and analytics; status: implemented; constraint: non-streaming normalization path uses list() and can be memory-heavy.
- Notes: No integrated order-book historical quote ingestion is present; CryptoHFTData is not integrated.

**6. Financial State**
- Authoritative components: `accounting_engine.py` (ledger), `execution_engine.py` (journal), `position_manager.py` (projection).
- Recovery / reconciliation ADRs: see `.agent/adr/0002-financial-state-source-of-truth.md` and `.agent/adr/0003-recovery-and-reconciliation.md` for design and invariants.

**7. Agent / Governance Layer**
- `.agent/agents/` — human/agent role guidance: Architect / Developer / QA / Safety agent docs.
- `.agent/contracts/` — machine-readable contracts and step contracts (historical-data, replay, backtest, paper-session contracts).
- `.agent/adr/` — architecture decision records (financial state, recovery, etc.).
- `docs/ROADMAP.md` — AUTHORITATIVE CURRENT ROADMAP for MarketScalping. This is the current governing phase order.
- `.agent/roadmap/master_roadmap.json` — LEGACY/HISTORICAL roadmap artifact retained for evidence only. It is not the current authority and must not be silently remapped to the current 12-phase numbering.
- `.github/agents/` — GitHub-visible agent docs and workflows.

**8. Testing**
- Authoritative test command:

  python -m unittest discover -s tests -p "test*.py" -v

- Focused tests: `tests/test_binance_trade_adapter.py` validates Binance adapter behavior (checksum, streaming canonicalization). Several repository tests exercise orchestrator/agent contracts (many tests under `tests/`).

**9. Important Data / Artifact Locations**
- `data/raw/` — raw collected exchange windows and raw archives.
- `data/canonical/` — canonical JSONL datasets produced by canonicalization.
- `data/paper_sessions/` — evidence and artifacts from paper-session runs.
- `logs/` — runtime logs.
- `reports/` — operator and reporting outputs.

**10. Navigation Rules (for agents)**
1. Read REPO_MAP.md first.
2. Identify the smallest file subset required for the task (use `.agent/contracts/` and ADRs to find authority).
3. Read contracts/ADRs before changing authoritative components (accounting, execution, position, risk).
4. Avoid scanning `data/` large datasets unless the task explicitly requires it.
5. Expand scope only when source-level dependencies require it.
6. When map conflicts with source code, source wins; update the map when authoritative changes occur.

**11. Map Maintenance Rules**
- MUST update REPO_MAP.md when:
  - a new important module is added/removed
  - module responsibility or authority changes
  - a new historical-data source/adapter is integrated
  - pipeline/dependency relationships change
- NOT required for ordinary bug fixes, internal refactors preserving responsibility, tests-only changes, or formatting changes.
- The agent performing a qualifying change must update REPO_MAP.md in the same task.

**12. Current Known State (verified facts only)**
- Current authoritative roadmap: `docs/ROADMAP.md` is the governing roadmap for the MarketScalping Candlestick + Zone Strategy project.
- Legacy/historical roadmap: `.agent/roadmap/master_roadmap.json` remains in the repo as historical evidence only and is not current authority.
- Historical roadmap phase labels must not be silently remapped to the current 12-phase numbering.
- ADRs: `.agent/adr/0002-financial-state-source-of-truth.md` exists and designates AccountingEngine as ledger authority.
- Binance adapter: `binance_trade_adapter.py` exists and has unit tests in `tests/test_binance_trade_adapter.py` (tests observed passing during inspection).
- Bitvavo collector: `bitvavo_trade_collector.py` and `historical_dataset.py` are implemented and used for raw collection and manifest generation.
 - Replay scaling note: `replay_runner.py` and `backtest_engine.py` contain non-streaming materialization paths that are known operational constraints for large datasets: `backtest_engine.py` materializes normalized events in-memory via `list()` and sort, while `replay_runner.py` uses a temporary SQLite insertion followed by an ordered cursor iteration in its non-streaming mode.
- CryptoHFTData is NOT integrated; no file or import indicates integration.

---

Map created by Orchestrator inspection on 2026-09-18. Update this file when pipeline authority or major module responsibilities change.
