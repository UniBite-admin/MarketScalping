# Phase 1 — Bar Contract Decision

## 1. Executive conclusion

ARCHITECT RESULT: HUMAN APPROVED / FROZEN

The repository provides strong evidence that the 15-minute reconstruction is deterministic and reproducible for the current canonical BTC-EUR dataset. It also provides evidence that the frozen Group A swing logic remains compatible with a bar-level high/low series. The human project authority has now approved the deterministic 15-minute operational bar contract as the authoritative Group B input contract.

This approval does not modify the frozen Group A swing rules, does not start Phase 2, and does not begin Zone Formation or tolerance calibration. It is a governing Phase 1 documentation decision only.

## 2. Evidence reviewed

- [REPO_MAP.md](../../REPO_MAP.md)
- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/BAR_CONTRACT_AUDIT.md](BAR_CONTRACT_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL.md](GROUP_B_PROPOSAL.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
- [data/canonical/tardis_btc_eur_20191201/metadata.json](../../data/canonical/tardis_btc_eur_20191201/metadata.json)
- [replay_runner.py](../../replay_runner.py)

## 3. Proposed authoritative 15m bar contract

This is the minimum deterministic contract proposal that is technically defensible from the repository evidence, while explicitly separating what is repo-grounded from what still requires human approval.

### A. TIME BUCKET

- Proposed timeframe: 15 minutes.
- Basis:
  - 2. Existing repository implementation behavior: the current research implementation defines `TIMEFRAME_MINUTES = 15` in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py).
  - 3. Existing repository data semantics: canonical events are timestamped and grouped by canonical time.
  - 4. Architectural necessity required for deterministic causal replay: a fixed interval is needed to avoid random bar formation.
  - 5. Human decision required: the project has not yet accepted 15-minute bars as the authoritative operational contract for Group B.
- Proposed bar_start: floor of the UTC timestamp to the 15-minute bucket boundary.
- Proposed bar_end: bar_start + 15 minutes.
- Timezone/alignment: UTC-based bucket alignment, matching the repository’s canonical dataset handling and the research script’s conversion to UTC.
- Interval rule: `[start, end)`
- Exact treatment of event at `bar_end`: belongs to the next bucket, not the current bucket.
- Basis: 2 + 4, with 5 required as final approval.

### B. EVENT → OHLC

- Source timestamp: `event_time_utc` from canonical event record.
- Source price field: `last` if present and valid; otherwise midpoint of `bid` and `ask` when both are present and valid; otherwise invalid and excluded.
- Basis:
  - 2. Existing repository implementation behavior: explicit in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py).
  - 3. Existing repository data semantics: canonical data contains `event_time_utc`, `market`, `bid`, `ask`, `last`, and `event_type`.
  - 5. Human decision required: whether this exact price source logic is accepted as the operational contract for Group B.
- Open: first valid price in the bucket in canonical order.
- High: maximum valid price in the bucket.
- Low: minimum valid price in the bucket.
- Close: last valid price in the bucket in canonical order.
- Missing or invalid price fields: excluded from pricing for that bucket; if a bucket has no valid prices, it is omitted.
- Empty bars: no empty bar rows are emitted; empty buckets are omitted.
- Basis: 2 + 3 + 4.

### C. CLOSED BAR

Proposed mechanical rule:

- A bar becomes CLOSED when the replay clock passes the bar’s `bar_end` boundary and the bar’s bucket is no longer the active bucket in canonical replay order.
- Closing does not require observing a later event in the next bucket; it is defined by time boundary progression under deterministic replay.
- A bar can never be reopened after it has closed.
- Once closed, no later event may change its OHLC under the authoritative replay contract.

Basis:
- 4. Architectural necessity required for deterministic causal replay: a closed-bar contract is required to prevent future events from changing a past bar.
- 5. Human decision required: the repository does not currently freeze a final closed-bar rule. The research implementation does not define a formal closed flag or explicit post-end immutability guard.

### D. INCOMPLETE BAR

Proposed rule:

- The current/trailing bucket is an INCOMPLETE BAR until replay reaches `bar_end` for that bucket.
- It is not eligible to be treated as a closed bar for Group A or Group B use.
- It may exist as a live/partial bucket only in the replay stream, but it must not be used as a finalized bar for confirmation or clustering.
- At dataset end, the trailing partial bucket is finalized as a terminal incomplete bar only if the project explicitly decides to include it; otherwise it is discarded as non-authoritative for downstream Group A and Group B use.

Basis:
- 4. Architectural necessity required for deterministic causal replay: the system must distinguish open/partial and closed bars.
- 5. Human decision required: the repository does not currently state whether the final partial bucket should be excluded or retained.

### E. IMMUTABILITY

Proposed rule:

- Once a bar is closed, its OHLC is immutable.
- Historical closed bars may not be recalculated or mutated in replay.
- Only a new canonical dataset or a fresh replay with a different canonical source may produce a new bar definition.
- Late or out-of-order events are not allowed to revise prior closed bars under the canonical replay contract.
- Canonical replay ordering means: sort by `timestamp_asc`, then deterministic tie-break `trade_before_quote_when_equal_ts` when the timestamp is identical.

Basis:
- 1. Existing authoritative project decision: the repository’s canonical metadata is authoritative on ordering and tie-break semantics.
- 3. Existing repository data semantics: canonical dataset ordering is deterministic.
- 4. Architectural necessity required for deterministic causal replay.
- 5. Human decision required: the operational contract for boundary closure and post-close immutability remains unapproved.

### F. GROUP A CAUSALITY

The frozen Group A rule is:

- Swing High: `High[i] > High[i-1] AND High[i] > High[i+1]`
- Swing Low: `Low[i] < Low[i-1] AND Low[i] < Low[i+1]`

Under the proposed bar contract:

- candle/bar i becomes observable when the bar for bucket i is closed and available to downstream logic.
- candle/bar i+1 becomes observable when the next bucket has closed.
- a swing candidate at bar i is confirmed only when the required right-side bar i+1 is observable in canonical time order.
- the candidate becomes eligible at confirmation time; for the frozen Group A rule, eligibility and confirmation are semantically the same moment because the final required neighbor is the right-side observation.
- no future information beyond the frozen confirmation rule is introduced because the system does not treat an unclosed trailing bucket as a valid prior state for a completed swing.

Basis:
- 1. Existing authoritative project decision: the Group A swing definition is frozen and approved.
- 2. Existing repository implementation behavior: the research script evaluates highs and lows on bar-level OHLC and applies the local-extrema logic in sequence.
- 4. Architectural necessity required for deterministic causal replay: this is the exact causal contract required to preserve the no-look-ahead rule.

### G. DATASET END

Proposed rule:

- At dataset end, the trailing partial/current bar is not permitted to validate or confirm Group A or Group B decisions unless the project explicitly approves a terminal partial-bar policy.
- Default conservative rule: discard the trailing partial bucket from downstream Group A and Group B calculations.
- This preserves causality and prevents a final partial bucket from being treated as a complete bar simply because the dataset ended.

Basis:
- 4. Architectural necessity required for deterministic causal replay.
- 5. Human decision required: the repository does not define whether the final partial bucket is retained or discarded.

### H. DETERMINISM

Two replays of identical canonical input must produce the same bars and timestamps because:

- canonical ordering is fixed by `timestamp_asc`
- equal timestamps are resolved by `trade_before_quote_when_equal_ts`
- bucket alignment is fixed to 15-minute UTC boundaries
- the half-open interval rule is fixed
- missing price fields are excluded deterministically
- empty buckets are omitted deterministically
- a bar is closed only by time boundary progression, not by later event mutation

Basis:
- 1 + 3 + 4, with 5 still required for final operational acceptance.

### I. RESEARCH IMPLEMENTATION COMPATIBILITY

Comparison to [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py):

What already matches the proposed contract:
- 15-minute bucket size
- UTC-based alignment
- bucket floor to the bucket start
- `[start, end)` style semantics in practice
- deterministic sorting by timestamp and source/line number
- omission of empty buckets
- use of `last` if present, else midpoint of `bid` and `ask`
- compatibility with the frozen Group A high/low local-extrema logic

What is only research behavior, not final contract authority:
- the code does not define a formal closed-bar state
- the code does not define an incomplete-trailing-bar policy
- the code does not define post-close immutability semantics
- the code does not designate the 15-minute bars as the authoritative operational Group B input contract
- the trailing bucket is not explicitly classified as complete/incomplete in the repo contract

What would need to be documented later:
- exact closed vs incomplete lifecycle semantics
- end-of-dataset handling
- replay-time immutability contract
- authoritative operational approval of the 15-minute bucket as Group B input

Does any current research behavior conflict with the proposed contract?
- Not in the deterministic statistical sense.
- The conflict is not mathematical; it is governance and contract completeness. The research implementation is deterministic, but it is incomplete as an authoritative operational contract because it does not define closed/incomplete lifecycle semantics.

## 4. Closed-bar rule

Proposed rule:

- A bar is CLOSED as soon as the replay time advances beyond the bar’s `bar_end` boundary.
- The bar is not reopened.
- Once closed, the bar’s OHLC is immutable.
- No future event may alter its Open / High / Low / Close.

This is the minimum operational rule needed for causal Group A confirmation to be valid in a deterministic replay system.

## 5. Incomplete-bar rule

Proposed rule:

- A trailing bucket whose `bar_end` has not yet been reached is INCOMPLETE.
- Incomplete bars are excluded from finalized Group A and Group B evaluation.
- The final partial bucket at dataset end is discarded unless an explicit human-approved exception is made.

## 6. Boundary event rule

Proposed rule:

- Event timestamps exactly equal to `bar_end` belong to the next bucket.
- This is the strict half-open interval rule: `[bar_start, bar_end)`.
- The current research implementation matches this behavior in principle and is therefore compatible with the proposal.

## 7. Empty-bar rule

Proposed rule:

- Empty buckets are omitted.
- They do not create a zero-value bar.
- This is consistent with the existing research implementation and with a deterministic replay model.

## 8. Post-close immutability rule

Proposed rule:

- Once a bar is closed, its data cannot be revised during replay.
- Historical closed bars remain append-only and immutable.
- Canonical ordering and tie-break rules are authoritative for any event ordering before closure.

## 9. Dataset-end rule

Proposed rule:

- The final trailing partial bucket is not considered a finalized bar for downstream Group A or Group B logic.
- A dataset-end partial bucket may be retained only under an explicit human-approved operational policy.
- In the absence of such approval, it is discarded.

## 10. Group A causal compatibility

The proposed bar contract is compatible with the frozen Group A semantics because:

- a finished bar becomes observable only after its close boundary passes
- the right-side neighboring bar is available only after the next bucket is complete
- the Group A confirmation rule remains causal and does not depend on future information beyond the required adjacent bar
- no earlier bar is mutated after closure, so no later event can retroactively alter a candidate swing after it was confirmed

## 11. Determinism requirements

The bar contract supporting Group B must satisfy these requirements:

- same canonical dataset + same replay ordering => same OHLC series
- same bar alignment and interval semantics => same bar boundaries
- same event inclusion/exclusion rules => same bars
- same strict Group A confirmation semantics => same swing stream
- no mutation of closed bars during replay => same future evaluations from the same historical state

## 12. Research implementation comparison

The existing research code is a strong starting point, but it is still a research artifact. It supports the proposal with one important caveat: it does not explicitly define the operational lifecycle of a bar. The decision remains human-governed.

## 13. Remaining uncertainties

The following items remain human decisions and are not yet accepted as authoritative project policy:

1. Whether the 15-minute bucket is the operational Group B input contract or only a research artifact.
2. Whether the trailing partial bar is excluded or retained at dataset end.
3. Whether a bar is considered CLOSED only at `bar_end` or by a separate event-based marker.
4. Whether the project accepts the research script’s price-source logic as the official operational source rule.
5. Whether the final Group B input contract should be limited to a single market and single asset stream.

## 14. Exact human approval required

The human must decide one governance question only:

“Do you approve the deterministic 15-minute `[start, end)` bucket contract, using the current canonical ordering and the rule that incomplete trailing bars are excluded from finalized Group A and Group B evaluation, as the authoritative operational input contract for Group B?”

If yes, the proposal becomes the authoritative operational Group B input contract. If no, the project remains at: research substrate only, Group B not frozen, no Phase 2, no production behavior change.

## 15. Explicit governance status

- Group A: frozen and unchanged
- Group B: not frozen
- 15-minute bar timeframe: not frozen
- Phase 2: not started
- Production trading behavior: unchanged
- Decision gate: human approval required
- Outer governance rule: no assumptions, no silent reinterpretation of Group A, no implementation during this decision stage

## Final decision

HUMAN APPROVED / FROZEN

This contract is now the authoritative Phase 1 operational bar contract for Group B input use. The earlier research findings remain intact as evidence, but the project-authoritative decision has been approved and recorded.
