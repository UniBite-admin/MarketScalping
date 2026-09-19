# Project Milestones

## Step 6 — Financial-State Architecture

This project milestone captures the required architecture and evidence for the financial state and recovery contract.

### 6A — Financial-State Architecture Investigation
- AccountingEngine is the authoritative ledger for financial state.
- ExecutionEngine is the immutable execution journal.
- PositionManager remains a derived projection, not a financial authority.
- The source-of-truth split is documented in ADR 0002.

### 6B — Financial-State Authority
- Recovery and reconciliation are governed by a fail-closed startup contract.
- The authoritative financial state must be recoverable and deterministic.
- Divergence between accounting state and derived projections blocks processing.
- The contract is documented in ADR 0003.

### Supporting architecture evidence
- .agent/adr/0002-financial-state-source-of-truth.md
- .agent/adr/0003-recovery-and-reconciliation.md
- .agent/roadmap/master_roadmap.json

## Scope note
This file exists as the repository-level milestone record referenced by the roadmap eligibility checks. It is planning evidence only and does not modify runtime workflow authority.
