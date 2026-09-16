# STEP 7.1 Historical Data Contract

## Status

Accepted for architecture definition only.

## Scope

This document defines the authoritative raw-vs-canonical historical data contract for Step 7.1, using the repository implementation and tests as the only source of truth. This contract is design-only and does not change runtime behavior.

## Current state

The repository contains three distinct layers:

1. Raw market data collection in [bitvavo_trade_collector.py](../../bitvavo_trade_collector.py)
2. Replay normalization in [replay_runner.py](../../replay_runner.py)
3. Runtime market-message processing in [market_data_engine.py](../../market_data_engine.py)

The direct evidence is:

- [bitvavo_trade_collector.py](../../bitvavo_trade_collector.py) validates raw Bitvavo trade rows and retains `trade_id`, `amount`, `price`, and `side` in `BitvavoHistoricalTrade`.
- [replay_runner.py](../../replay_runner.py) normalizes replay events into `_NormalizedReplayEvent` with `event_time_utc`, `event_type`, `market`, `bid`, `ask`, and `last` only.
- [market_data_engine.py](../../market_data_engine.py) processes `ticker` and `trade` messages using `bestBid`/`bestAsk`/`lastPrice` for ticker and `price` for trade; `parse_trade_message` discards quote-side fields and stores only `last`.
- [tests/test_bitvavo_trade_collector.py](../../tests/test_bitvavo_trade_collector.py) requires unique raw `trade_id` de-duping and deterministic ordering.
- [tests/test_replay_runner.py](../../tests/test_replay_runner.py) requires deterministic replay ordering and rejects invalid timestamps, markets, and prices before replay begins.

## Problem / gap

The repository does not define a single contract document for Step 7.1. The implementation reveals a real split between raw historical records and replay canonical events, and the contract must distinguish those layers explicitly. Without this distinction, the system would incorrectly conflate raw exchange records, replay-normalized state, and financial execution identity.

## Architectural decision

The system MUST enforce the following contract boundaries:

- Raw Bitvavo data is raw historical evidence and retains original fields.
- Canonical replay input is a normalized market-state stream used by the deterministic simulator.
- Financial execution identity is a separate domain: `execution_event_id` in [execution_engine.py](../../execution_engine.py) and accounting state in [accounting_engine.py](../../accounting_engine.py).
- Replay ordering and event normalization are owned by [replay_runner.py](../../replay_runner.py), not by the raw collector.

## Blocker decisions

### BLOCKER 1 — Trade bid/ask fallback

Decision: C

Repository evidence proves that the runtime genuinely requires a synthetic bid/ask fallback when a trade event has no quote-side values. The proof is in [replay_runner.py](../../replay_runner.py):

- for `event_type == "trade"`, `last` is required
- `bid` and `ask` are set to `last` when absent or non-positive
- `event_type == "ticker"` requires real bid/ask/last values

This is not a raw Bitvavo field. It is a replay invariant required by downstream processing. The canonical contract MUST state:

- For a trade event, `last` is the observed execution price.
- `bid` and `ask` MUST be treated as synthetic quote placeholders and MUST equal `last` when quote-side values are unavailable.
- The value is not a real bid/ask quote and MUST NOT be interpreted as a genuine market quote.
- The runtime contract requires this synthetic quote for downstream compatibility, even though the actual Bitvavo raw trade payload does not supply bid or ask.

This is the repository-grounded invariant. The contract MUST NOT claim that raw trade rows include bid/ask.

### BLOCKER 2 — Canonical duplicates

Decision:

The repository defines three different duplicate concepts and they MUST remain distinct.

1. Raw duplicates
   - In [bitvavo_trade_collector.py](../../bitvavo_trade_collector.py), raw duplicate handling is by raw `trade_id`.
   - The collector rejects duplicate `trade_id` values in the same fetch window and increments `duplicated`.
   - Only the first accepted row for a given `trade_id` remains in the raw output.

2. Canonical replay multiplicity
   - [replay_runner.py](../../replay_runner.py) does not deduplicate canonical events by timestamp or by `last` value.
   - The replay stream is ordered by `(event_time_dt, original_index)` and processed in that order.
   - Multiple valid replay events with different timestamps or different original indexes are distinct events.

3. Financial execution identity
   - In [accounting_engine.py](../../accounting_engine.py), duplication is keyed by `execution_event_id`, not by raw trade ID.
   - If the same `execution_event_id` reappears, accounting returns `DUPLICATE` and applies no financial effect.
   - This is the authoritative idempotency boundary for financial state.

Normative rule:

- Raw duplicate detection MUST use raw `trade_id`.
- Replay multiplicity MUST be preserved as event count, not deduplicated by canonical event shape.
- Financial duplicate detection MUST use `execution_event_id` and MUST be enforced by the accounting layer.
- A raw-trade duplicate and a financial duplicate are different domains and MUST NOT be conflated.

### BLOCKER 3 — Raw-to-canonical information loss

Decision: retain in raw, omit from canonical replay contract

Repository evidence shows the fields are required in the raw collector and not required in the replay pipeline:

- [bitvavo_trade_collector.py](../../bitvavo_trade_collector.py) requires and stores `trade_id`, `amount`, and `side` in `BitvavoHistoricalTrade`.
- [replay_runner.py](../../replay_runner.py) canonical `_NormalizedReplayEvent` contains only `event_time_utc`, `event_type`, `market`, `bid`, `ask`, and `last`.
- [market_data_engine.py](../../market_data_engine.py) consumes only `market` and `price` for trade events; it does not read raw `amount`, `side`, or `trade_id` values.
- [execution_engine.py](../../execution_engine.py), [risk_engine.py](../../risk_engine.py), and [accounting_engine.py](../../accounting_engine.py) use `execution_event_id` and market/price state, not raw trade fields.

Normative rule:

- `trade_id`, `amount`, and `side` MUST be retained in the raw historical collector output.
- These fields MUST be omitted from the canonical replay event contract because the runtime replay path does not consume them and does not require them for deterministic replay.
- Any contract that requires them at canonical replay time would contradict the repository implementation and test behavior.
- Raw-layer retention is required for auditability; canonical replay intentionally omits them to preserve a minimal market-state model.

### BLOCKER 4 — Formal contract artifact

Decision: exact artifact path

The formal Step 7.1 contract artifact MUST live at:

`.agent/contracts/step-7.1-historical-data-contract.md`

This path is chosen because the repository already holds canonical workflow contracts under `.agent/contracts/`, while Step 7.1 is a repository-level architecture contract rather than a runtime code change. No other repository file is modified in this task.

### BLOCKER 5 — Numeric contract

Decision: explicit finite-number requirement with current-code divergence noted

Normative numeric rules:

- A raw Bitvavo price or amount MUST parse as a finite positive decimal or float value.
- A canonical replay `last` MUST be finite and greater than zero.
- A canonical replay `bid` and `ask` MUST be finite and greater than zero when they are real quote values.
- For trade events without a quote-side input, the synthetic fallback MUST still preserve a finite and positive `last` value and the synthetic `bid`/`ask` fallback MUST also be finite and positive.
- `NaN` and `Infinity` MUST be rejected at the contract boundary.

Repository evidence vs. current implementation:

- [replay_runner.py](../../replay_runner.py) explicitly checks for positive numeric values for `bid`, `ask`, and `last` but does not call `math.isfinite` before comparison.
- [risk_engine.py](../../risk_engine.py) uses `math.isfinite` when establishing financial validity, which is the stronger architecture requirement.
- [market_data_engine.py](../../market_data_engine.py) accepts numeric values via `float(...)` with no finite-number guard in parsing, so current runtime behavior is weaker than the contract requirement.

Therefore:

- Architecture requirement: all numeric contract values MUST be finite real numbers; `NaN` and `Infinity` MUST be rejected.
- Current code behavior: the runtime does not fully enforce finite-number validation before all price comparisons. This is a repository gap and requires human decision if the implementation is to be tightened later.

This is recorded as: REPOSITORY GAP — HUMAN DECISION REQUIRED.

### BLOCKER 6 — Ordering

Decision: raw order is not authoritative; canonical replay ordering is authoritative

Repository evidence:

- [bitvavo_trade_collector.py](../../bitvavo_trade_collector.py) accepts raw rows, deduplicates by `trade_id`, and sorts the accepted records by `(event_time_utc, trade_id)` before writing.
- [replay_runner.py](../../replay_runner.py) normalizes all valid raw events, then sorts canonical replay events by `(event_time_dt, original_index)` before invoking `MarketDataEngine`.
- [tests/test_bitvavo_trade_collector.py](../../tests/test_bitvavo_trade_collector.py) and [tests/test_replay_runner.py](../../tests/test_replay_runner.py) enforce deterministic chronological ordering.

Normative rule:

- Raw source order is not authoritative and MUST NOT be treated as the replay ordering source.
- Collector output MUST be sorted by timestamp and ID before persistence.
- Canonical replay ordering MUST be owned by [replay_runner.py](../../replay_runner.py) and MUST operate on `(event_time_utc, original_index)` after normalization.
- The runtime engine MUST process the canonical sorted stream in chronological order and MUST NOT rely on the original raw fetch order.
- Deterministic replay MUST produce the same sequence for the same dataset on repeated execution.

## Affected components

- [bitvavo_trade_collector.py](../../bitvavo_trade_collector.py)
- [replay_runner.py](../../replay_runner.py)
- [market_data_engine.py](../../market_data_engine.py)
- [feature_signal_engine.py](../../feature_signal_engine.py)
- [execution_engine.py](../../execution_engine.py)
- [accounting_engine.py](../../accounting_engine.py)
- [risk_engine.py](../../risk_engine.py)
- [tests/test_bitvavo_trade_collector.py](../../tests/test_bitvavo_trade_collector.py)
- [tests/test_replay_runner.py](../../tests/test_replay_runner.py)
- [tests/test_accounting_baseline.py](../../tests/test_accounting_baseline.py)
- [tests/test_safety_and_accounting_audit.py](../../tests/test_safety_and_accounting_audit.py)
- [ADR 0002](../adr/0002-financial-state-source-of-truth.md)
- [ADR 0003](../adr/0003-recovery-and-reconciliation.md)

## Data / control flow impact

The raw historical pipeline writes raw trade rows into JSONL and preserves original values. The canonical replay pipeline converts those rows into a minimal market-state stream for deterministic replay. Financial execution identity is introduced later in the pipeline and is intentionally independent of raw trade IDs. This creates a clean separation:

raw exchange trade -> normalized replay event -> execution event id -> accounting ledger

This separation is required to maintain idempotency and reconciliation across accepted execution events.

## Risks

- Misinterpreting synthetic `bid`/`ask` values as authentic quotes would create false market-state semantics.
- Treating raw `trade_id` as the financial idempotency key would break accounting correctness.
- Omitting raw fields from raw storage would destroy auditability.
- Allowing `NaN` and `Infinity` in price fields would create non-finite state and risk-engine edge cases.
- Relying on raw fetch order instead of canonical sorting would produce nondeterministic replay behavior.

## Testing implications

The following repository tests provide the validation evidence for this contract:

- [tests/test_bitvavo_trade_collector.py](../../tests/test_bitvavo_trade_collector.py): raw collector validation, sorting, ID dedupe, invalid-row rejection
- [tests/test_replay_runner.py](../../tests/test_replay_runner.py): replay normalization, rejection of invalid timestamps/markets/prices, deterministic chronological ordering
- [tests/test_accounting_baseline.py](../../tests/test_accounting_baseline.py): financial idempotency and accepted/duplicate/rejected decision states
- [tests/test_safety_and_accounting_audit.py](../../tests/test_safety_and_accounting_audit.py): pipeline timestamp consistency and recovery invariants

## Open questions

- The current runtime does not enforce finite-number validation consistently across all parsed numeric inputs; this is a contract gap needing explicit implementation later.
- The repository does not define a separate canonical field for synthetic quote provenance; therefore the current implementation requires a documented invariant instead of a richer provenance field.

## ADR-quality decision summary

Context:

The repository contains a raw Bitvavo collection layer, a canonical replay layer, and a separate financial execution layer. The raw collector preserves historical trade identity and amount/side metadata, while the replay engine only needs a minimal market-state stream for deterministic simulation. The financial layer enforces idempotency via `execution_event_id` and not via raw trade IDs.

Decision:

The Step 7.1 contract MUST separate raw historical trade data, canonical replay normalized events, and financial execution identity. Trade events MUST use last-price semantics plus synthetic quote fallback. Raw duplicates are defined by raw `trade_id`; financial duplicates are defined by `execution_event_id`; canonical replay is ordered by timestamp and original index; and numeric values MUST be finite real numbers.

Rationale:

This decision is derived directly from the repository behavior in [bitvavo_trade_collector.py](../../bitvavo_trade_collector.py), [replay_runner.py](../../replay_runner.py), [market_data_engine.py](../../market_data_engine.py), [execution_engine.py](../../execution_engine.py), and [accounting_engine.py](../../accounting_engine.py), and it matches the passing repository tests in [tests/test_bitvavo_trade_collector.py](../../tests/test_bitvavo_trade_collector.py) and [tests/test_replay_runner.py](../../tests/test_replay_runner.py).

Consequences:

- Raw data remains the authoritative record of exchange trade semantics.
- Replay canonical data remains intentionally minimal and deterministic.
- Financial state remains governed by `execution_event_id` and accounting authority rather than raw trade identity.
- Numeric validation must be tightened later to match the architecture requirement.

Alternatives considered:

- A: Preserve real bid/ask fields with provenance distinction. Rejected because the repository does not supply real bid/ask in raw trade payloads and the runtime normalization explicitly falls back to `last`.
- B: Canonical trade events use absent/null bid/ask and last only. Rejected because the runtime pipeline and replay normalization require the downstream quote fields to remain populated for compatibility.
- C: Synthetic bid/ask fallback to `last` is a required runtime invariant. Accepted and explicitly documented above.

## Final binding rule set

The following rules are binding for Step 7.1:

1. Raw historical Bitvavo rows MUST retain `trade_id`, `amount`, `price`, and `side`.
2. Canonical replay events MUST use `event_time_utc`, `event_type`, `market`, `bid`, `ask`, and `last` only.
3. Trade events MUST use `last` as execution price and MUST use synthetic `bid`/`ask` = `last` when quote-side values are absent.
4. Raw duplicate detection MUST use raw `trade_id`.
5. Financial duplicate detection MUST use `execution_event_id`.
6. Replay ordering MUST be deterministic and MUST use canonical sorted timestamps.
7. Numeric values MUST be finite real numbers; `NaN` and `Infinity` MUST be rejected.
8. The repository contract is explicit: raw data and canonical replay are different layers and MUST remain separate.
