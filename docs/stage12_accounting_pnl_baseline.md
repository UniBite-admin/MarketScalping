# Stage 12 Milestone: Accounting and PnL Baseline

## Scope

This stage adds a simulation-only accounting baseline with explicit separation of:

- Order intent
- Simulated fill
- Open position
- Closed trade

No live trading, API keys, leverage, or AI/ML are introduced.

## Architecture

Data flow:

SIGNAL -> RISK APPROVAL -> ORDER -> SIMULATED FILL -> POSITION -> EXIT -> CLOSED TRADE -> REALIZED PnL -> EQUITY

Implementation:

- Accounting engine: [accounting_engine.py](accounting_engine.py)
- Runtime integration: [market_data_engine.py](market_data_engine.py)
- Trade ledger output: [data/trade_ledger_btc_eur.csv](data/trade_ledger_btc_eur.csv)
- Account state output: [data/account_state_btc_eur.csv](data/account_state_btc_eur.csv)
- Open-position recovery checkpoint: [data/accounting_open_position_state_btc_eur.json](data/accounting_open_position_state_btc_eur.json)

Checkpoint design:

- Single local JSON checkpoint is the recovery source of truth for open-position/account continuity.
- Closed-trade CSV ledger remains the source of truth for finalized trades.
- No database infrastructure is introduced at this stage.

## Trade Ledger Fields

Single source-of-truth closed trade ledger fields:

- trade_id
- timestamp_utc
- symbol
- side
- entry_price
- exit_price
- position_size
- gross_pnl
- fees
- slippage
- net_pnl
- holding_time_seconds
- strategy
- signal
- confidence
- close_reason
- entry_timestamp_utc
- exit_timestamp_utc

## Configurable Inputs

Environment variables handled by [market_data_engine.py](market_data_engine.py):

- ACCOUNTING_ENGINE_ENABLED
- ACCOUNTING_TRADE_LEDGER_PATH
- ACCOUNTING_ACCOUNT_STATE_PATH
- ACCOUNTING_OPEN_POSITION_STATE_PATH
- ACCOUNTING_STRATEGY_NAME
- ACCOUNTING_STARTING_BALANCE
- ACCOUNTING_ORDER_NOTIONAL_EUR
- ACCOUNTING_FEE_RATE
- ACCOUNTING_SLIPPAGE_BPS

## Restart Recovery Behavior

On startup, accounting restores from checkpoint when present:

- open position state for one long position (if open)
- available balance
- realized and unrealized PnL
- cumulative fees and slippage
- equity and drawdown continuity values (peak/current/max)

After recovery:

- mark-to-market continues from live bid/ask updates
- unrealized PnL and equity continue without resetting
- drawdown continuity is preserved
- non-fill events still do not mutate open-position lifecycle

## Pricing and Execution Rules

Long-only simulation baseline:

- Entry BUY executes against ask.
- Exit SELL executes against bid.

Slippage model:

- slippage_rate = slippage_bps / 10000
- entry_execution_price = ask * (1 + slippage_rate)
- exit_execution_price = bid * (1 - slippage_rate)

## PnL Formulas

Let:

- q = position_size
- Pe = entry_execution_price
- Px = exit_execution_price
- Ne = q * Pe
- Nx = q * Px
- fee_rate = configured fee rate

Fees:

- entry_fee = Ne * fee_rate
- exit_fee = Nx * fee_rate
- total_fees = entry_fee + exit_fee

Slippage impact (explicit metric):

- entry_slippage = (entry_execution_price - ask_reference) * q
- exit_slippage = (bid_reference - exit_execution_price) * q
- total_slippage = entry_slippage + exit_slippage

Gross and net PnL:

- gross_pnl = (Px - Pe) * q
- net_pnl = gross_pnl - total_fees

Notes:

- Slippage affects PnL through execution prices in gross_pnl.
- Slippage is also reported explicitly as total_slippage for observability.

## Account and Equity Formulas

Account fields:

- starting_balance
- available_balance
- realized_pnl
- unrealized_pnl
- equity
- cumulative_fees
- cumulative_slippage
- peak_equity
- current_drawdown
- maximum_drawdown

Mark-to-market for long position:

- unrealized_pnl = (bid_mark - entry_price) * q
- equity = available_balance + (bid_mark * q)

After close:

- available_balance += exit_notional - exit_fee
- realized_pnl += net_pnl
- unrealized_pnl = 0

Drawdown:

- peak_equity = max(previous_peak_equity, equity)
- current_drawdown = max((peak_equity - equity) / peak_equity, 0)
- maximum_drawdown = max(previous_maximum_drawdown, current_drawdown)
