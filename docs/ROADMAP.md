# MarketScalping Authoritative Roadmap

This document is the authoritative current roadmap for the MarketScalping Candlestick + Zone Strategy project.

## HUMAN DECISION
The following 12-phase roadmap was explicitly approved by the human and is the current authoritative roadmap for MarketScalping.

- `docs/ROADMAP.md` = AUTHORITATIVE CURRENT ROADMAP
- `.agent/roadmap/master_roadmap.json` = LEGACY/HISTORICAL ROADMAP
- Historical labels such as Phase 5A, Phase 5B, and Phase 5C remain historical evidence only and must not be silently mapped onto the current 12-phase numbering.

## CURRENT STATUS
- Phase 1–5 specification work has previously been performed, but the authoritative roadmap/checkpoint is now being consolidated.
- Phase 6 implementation work must NOT begin until the current roadmap/specification governance is accepted.
- A phase is not complete merely because historical conversation history, code, or earlier artifacts said so.
- This governance checkpoint is a documentation and decision gate. No code or tests are modified by this task.

## CORE GOVERNANCE RULES
1. Complete phases sequentially.
2. Do not skip ahead.
3. Do not implement the trading strategy while its specification is still being defined.
4. Each phase must produce:
   - specification
   - test requirements
   - internal-consistency validation
   - explicit phase status
5. A phase is not complete merely because code exists.
6. No implementation may silently redefine a frozen specification.
7. If authoritative sources conflict, STOP and request human resolution.
8. Existing MarketScalping infrastructure must be preserved:
   Replay → Backtest → Risk → Execution → Accounting → Position Management → Logging
9. The new Zone/Candlestick/Strategy layers must be implemented on top of the existing infrastructure rather than replacing it.
10. V1 must be deterministic.
11. AI/LLM must NOT be inserted into the latency-sensitive trading decision chain.
12. Do not advance to the next phase until the current phase is explicitly accepted.

## PROJECT-WIDE PRINCIPLES
- DATA → TEST → VALIDATE → AUTOMATE → CONTROL → SCALE
- No assumptions:
  - If something is unknown, ambiguous, contradictory, or unsupported by authoritative evidence:
  - STOP → identify the uncertainty → request human decision → record the decision → continue.
- Implementation rule:
  - Specification first → Architect validation → Implementation → QA/Safety validation.

## AUTHORITATIVE 12-PHASE ROADMAP
1. PHASE 1 — Zone Formation
2. PHASE 2 — Touch Detection
3. PHASE 3 — Reaction Validation
4. PHASE 4 — Zone Lifecycle
5. PHASE 5 — Confluence
6. PHASE 6 — Candlestick Pattern Engine
7. PHASE 7 — Strategy Decision Engine
8. PHASE 8 — Multi-Asset Architecture
9. PHASE 9 — Backtest Integration
10. PHASE 10 — Testing & Anti-Lookahead
11. PHASE 11 — Architect Validation
12. PHASE 12 — Final Independent Validation

## LEGACY ROADMAP HANDLING
- `.agent/roadmap/master_roadmap.json` remains in the repository as a historical artifact and must not be treated as the current roadmap authority.
- Historical roadmap content is preserved for evidence and traceability.
- Historical numbering must not be silently remapped onto the current 12-phase order.
- Future work must follow the authoritative 12-phase ordering defined above.
