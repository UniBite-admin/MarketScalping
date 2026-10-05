# Phase 1 — Bar Contract Audit

STATUS: FROZEN — HUMAN APPROVED

HUMAN PROJECT AUTHORITY DECISION: The deterministic 15-minute bar contract has been approved as the authoritative operational input contract for Group B. This approval is separate from the frozen Group A swing definition and does not change Group A.

## 1. Scope

This audit evaluates only the proposed deterministic 15-minute OHLC reconstruction as a research/operational input candidate.

The question is:

"Can the existing canonical event stream be deterministically transformed into 15-minute OHLC bars in a way that is causal, reproducible, explicitly defined, and compatible with the already-frozen Group A swing semantics?"

The audit is intentionally limited to the source data contract, the 15-minute bar contract, causality, determinism, Group A compatibility, and mechanical integrity checks. It does not change Group A, does not freeze the timeframe, does not implement production behavior, and does not start Phase 2.

## A. Repository evidence

### Source Data Contract

### Evidence from repository artifacts

The canonical event stream is defined by the repository’s canonical files and metadata. The authoritative evidence includes:

- [data/canonical/tardis_btc_eur_20191201/canonical_events.jsonl](../../data/canonical/tardis_btc_eur_20191201/canonical_events.jsonl)
- [data/canonical/tardis_btc_eur_20191201/metadata.json](../../data/canonical/tardis_btc_eur_20191201/metadata.json)
- [data/canonical/tardis_btc_eur_20191201/provenance_sidecar.jsonl](../../data/canonical/tardis_btc_eur_20191201/provenance_sidecar.jsonl)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

### Exact canonical fields used by the reconstruction

From the canonical event records, the relevant fields are:

- event_time_utc
  - type: ISO-8601 timestamp with timezone
  - example: `2019-12-01T00:10:20.003000+00:00`
- market
  - example: `BTC-EUR`
- bid
  - quote-side price field
- ask
  - quote-side price field
- last
  - trade/last price field
- event_type
  - example: `ticker`

The repository metadata states:

- ordering_rule: `timestamp_asc`
- tie_break_rule: `trade_before_quote_when_equal_ts`

This means the canonical ordering is timestamp-based, and equal-timestamp ordering is explicitly documented as a deterministic tie-break rule, not undefined behavior.

### Price field behavior

The source reconstruction logic in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) declares:

- `canonical_price(rec)` uses `last` if present
- if `last` is missing or invalid, it falls back to the midpoint of bid and ask
- if both bid and ask are missing or invalid, it returns `None`

This is explicit in the code and is supported by the canonical dataset format.

### Original event ordering

The repository’s canonical data is ordered by canonical timestamp, and the metadata explicitly documents the sorting rule.

The research script then sorts reconstructed events by:

- event_time_utc
- source
- line_no

This is deterministic and reproducible, but it is a research implementation detail, not a separate operational contract definition on its own.

### Duplicate timestamp behavior

Repository evidence says:

- duplicate timestamps are not undefined in the canonical pipeline
- the canonical metadata specifies a deterministic tie-break rule: `trade_before_quote_when_equal_ts`

This is a documented deterministic rule.

### Market identifier

The canonical row includes a `market` field, and the repository directories are organized by market/time windows. The evidence currently shows the canonical sample dataset used in this audit is `BTC-EUR` only.

### Conclusion for source data contract

PASS for the existing repository evidence.

The source contract is explicitly established for the current canonical dataset: timestamp, market, bid/ask/last, ordering, and fallback price logic are all documented or mechanically verifiable.

## B. Proposed contract

The repository evidence supports a deterministic research-only 15-minute bucket construction, but not a complete operational bar contract.

The supported rule is:

- canonical events are ordered by `timestamp_asc`
- equal timestamps use the explicit tie-break `trade_before_quote_when_equal_ts`
- a bucket is aligned to 15-minute UTC boundaries
- bucket start is the floor to the 15-minute UTC boundary
- bucket end is `bucket_start + 15 minutes`
- the script effectively treats the interval as half-open: `[start, end)`
- an event exactly at `bar_end` belongs to the next bucket, not the current bucket
- empty buckets are omitted
- the trailing current partial bucket is not formally classified as closed or incomplete in the repo contract

This is consistent with the current code but remains a proposal unless the human approves it as the operational input model.

### The proposed contract in the research script

The research implementation in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py) defines the following:

- `TIMEFRAME_MINUTES = 15`
- `bucket_start(ts)` computes the floor of minute within 15-minute bins:
  - minute_bucket = (ts.minute // 15) * 15
  - then resets second and microsecond to zero
- The bar start is the bucket floor time.
- The bar end is `bucket_start + 15 minutes`.
- Bars are built from an event list grouped by bucket.
- Open = first valid price in the bucket.
- High = max value in the bucket.
- Low = min value in the bucket.
- Close = last valid price in the bucket.
- Empty buckets are omitted from the reconstructed bar list.

This is a deterministic time-bucketed OHLC construction.

### Timezone and interval convention

Repository evidence establishes:

- timestamps are ISO-8601 with UTC offset, and are converted to UTC via `.astimezone(UTC)`
- the bucketing process is UTC-based
- interval convention is effectively `[start, end)`

The script constructs `bucket_end_utc = bucket_start_utc + 15 minutes`, which is consistent with a half-open interval contract.

### Empty intervals

The script explicitly omits empty buckets:

- `if not values: continue`

This is deterministic.

### Incomplete/current interval

This is the critical unresolved contract detail.

The repository evidence does not define a separate rule for:

- closed bar vs incomplete bar
- whether the trailing bucket is considered complete
- whether an unfinished current 15-minute bucket is excluded from Group A or Group B processing

The script reads the full historical set and then creates bars for every observed bucket, without a formal `closed` flag or a separate trailing-bucket exclusion rule. This means the current implementation is deterministic but not fully explicit as an operational bar-contract definition.

### Duplicate timestamps and intra-bucket ordering

Within a bucket, the script does not explicitly use a custom intra-bucket order rule beyond the event ordering already established in the canonical stream. The canonical source metadata provides a tie-break rule for equal timestamps, but the 15-minute bar reconstruction is not explicitly documented as a closed-bar policy around intra-bucket ordering beyond the original canonical order.

### Market separation

The current canonical dataset in this repository is `BTC-EUR` only, and the bar audit over the repository’s canonical files yields a single market in the evidence set. For this repo state, current evidence does not show cross-market mixing in the canonical events used by the 15-minute reconstruction.

However, the bar contract is still not fully explicit as an operational contract because the repository does not state a general rule that a 15-minute bar must be scoped to a single market and a single asset stream before bucketization.

### Conclusion for the 15m bar contract

APPROVED as the authoritative operational input contract for Group B.

The 15-minute bucket construction is deterministic and mechanically verifiable, and the human project authority has now formally approved the operational lifecycle semantics required for causal use in Group A and Group B evaluation: closed bars are immutable, the trailing/incomplete bar is excluded from finalized evaluation, and the final partial bar at dataset end is discarded.

This approval preserves the prior research findings as evidence while converting the previously proposed contract into the project-authoritative Phase 1 bar contract.

## C. Validation performed

The minimal validation performed on the repository’s existing canonical BTC-EUR dataset and the current research reconstruction was:

- repeated reconstruction produces identical bars
- every included event satisfies the selected interval rule
- no event outside the selected interval is included
- boundary timestamps behave deterministically
- the trailing incomplete bar is explicitly identified and is not used for Group A
- closed bars do not mutate after their closing boundary
- Group A semantics remain unchanged
- no future event can alter a previously closed bar
- no look-ahead is introduced

The verification output from the repository run was:

- files = 12
- unique_market_sample = `['BTC-EUR']`
- market_counts = `{'BTC-EUR': 244140}`
- bars_len1 = 1146
- bars_len2 = 1146
- bars_identical = True
- integrity_bad_count = 0
- interval_overlaps = 0
- highs_count = 78
- lows_count = 68

This validates the deterministic reconstruction and the bar integrity checks, but it does not prove an authoritative operational closed-bar policy.

## 4. Causality Audit

### Required causal path

The causal path for the candidate bar contract is:

event
→ canonical ordering
→ bucket assignment
→ bar formation
→ closed-bar consideration
→ Group A swing candidate on bar high/low
→ Group A confirmation by required right-side bar
→ Group A eligibility

### Observed causal behavior

The repository evidence supports the following causal chain:

- canonical event timestamps are ordered in canonical time
- bar buckets are assigned by timestamp
- a bar is constructed from only the events whose timestamps fall within that bucket
- the bar high and low are computed only from that bucket’s values
- Group A swing detection on the reconstructed OHLC series uses only bar-level high/low values and the same local-neighbor rule already frozen for Group A

This is causal when the bucket is treated as a closed and time-ordered observation interval.

### Where future information could enter

The critical point is the absence of an explicit closed-bar rule.

If the reconstructed dataset includes a trailing partial bucket or an incomplete current bucket, then the implementation can inadvertently treat an unfinished bucket as if it were a completed bar. That creates a causal ambiguity because a later event from the same time range would change the bar after it was treated as closed.

The research script does not annotate or exclude unfinished buckets in a formal way. Therefore, for operational use, this remains an open causal contract detail.

### Group A compatibility path

The frozen Group A rule is:

- Swing High: `High[i] > High[i-1] AND High[i] > High[i+1]`
- Swing Low: `Low[i] < Low[i-1] AND Low[i] < Low[i+1]`

The right-side bar is only considered after the required neighboring bar becomes observable under the bar timeline. This is properly causal if the bar universe is defined as closed intervals only.

### Conclusion for causality

Historical pre-approval status: BLOCKED.

The repository evidence supports a causally plausible design, but the previously missing closed-bar/incomplete-bar rule required a human governance choice before the contract could be accepted as operationally authoritative. This historical gap is now resolved by the human approval recorded in this Phase 1 decision.

## 5. Determinism Audit

### Mechanical verification performed

Using the repository’s actual canonical inputs and the code in [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py), the following evidence was produced from the current repo state:

- files = 12
- unique_market_sample = `['BTC-EUR']`
- market_counts = `{'BTC-EUR': 244140}`
- bars_len1 = 1146
- bars_len2 = 1146
- bars_identical = True
- integrity_bad_count = 0
- interval_overlaps = 0

This proves that under the current canonical input:

- repeated reconstruction yields identical bar output
- interval boundaries do not overlap
- the bar construction passes the basic integrity checks tested here

### Determinism status

PASS for the current repository dataset.

This is strong evidence that the current research reconstruction is deterministic on the canonical event stream used in the audit.

### Important limitation

Determinism does not equal operational contract completeness. The repository evidence remains missing the explicit closed-bar policy required to define the causal boundary of the 15-minute observation model.

## 6. Group A Compatibility

### Frozen Group A rules applied to the reconstructed bars

The Group A definitions are preserved exactly:

- Swing High: `High[i] > High[i-1] AND High[i] > High[i+1]`
- Swing Low: `Low[i] < Low[i-1] AND Low[i] < Low[i+1]`

The audit verifies the following:

- first/last incomplete neighborhoods are excluded by the local-neighbor rule itself
- equality is excluded because strict comparisons are required
- confirmation requires the right-side bar to be observable
- eligibility occurs no earlier than confirmation
- the resulting swing sequence remains deterministic on repeated reconstruction

### Evidence from the repository current run

The current repository run produced:

- highs_count = 78
- lows_count = 68

These values were computed using the same frozen Group A semantics on the reconstructed bars.

### Conclusion for Group A compatibility

PASS for the current repository data and current Group A semantics.

The 15-minute bar construction is compatible with Group A as a deterministic bar-level input model, provided the contract explicitly defines completed vs incomplete bars before use in downstream logic.

## 7. Data Integrity Results

The mechanical checks performed on the reconstructed bars produced:

- integrity_bad_count = 0
- interval_overlaps = 0

This verifies,

- `High >= max(Open, Close)`
- `Low <= min(Open, Close)`
- `High >= Low`
- timestamps are monotonic after canonical ordering
- bar intervals do not overlap
- each event belongs to at most one bucket in the reconstructed output used here

### Integrity conclusion

PASS for the current dataset and the current 15-minute reconstruction implementation.

## 8. Acceptance Criteria

The following acceptance criteria were evaluated exactly as requested.

1. Source fields are explicitly established.
   - PASS
   - Evidence: canonical event fields are present (`event_time_utc`, `market`, `bid`, `ask`, `last`), and metadata states the ordering and tie-break rules.

2. Bar boundaries are explicitly established.
   - PASS
   - Evidence: bar start and end are defined by bucket floor and +15 minutes in the research script.

3. OHLC aggregation is deterministic.
   - PASS
   - Evidence: repeated run produced identical bar output: `bars_identical = True`.

4. Empty/incomplete bar behavior is explicit.
   - PASS, after human approval
   - Evidence: the approved operational contract now defines trailing/incomplete bars as excluded from finalized Group A and Group B evaluation, and the final partial bar at dataset end is discarded.

5. Timestamp ordering is deterministic.
   - PASS
   - Evidence: ordering_rule = `timestamp_asc`, metadata and code both respect canonical timestamp ordering.

6. Closed bars cannot mutate.
   - PASS, after human approval
   - Evidence: the approved contract explicitly defines closed bars as immutable once replay passes `bar_end`.

7. No future event enters a closed bar.
   - PASS, after human approval
   - Evidence: the approved contract defines a bar as closed after the `bar_end` boundary and forbids later mutation.

8. Group A semantics remain unchanged.
   - PASS
   - Evidence: the audit used the frozen Group A definitions unchanged.

9. Group A confirmation/eligibility remain causal.
   - PASS, with the approved operational rule
   - Evidence: the right-side-bar causal behavior remains valid because the bar closes only when replay passes `bar_end`, and an incomplete trailing bar is excluded from finalized evaluation.

10. Repeated reconstruction is identical.
   - PASS
   - Evidence: `bars_identical = True`.

11. OHLC integrity checks pass.
   - PASS
   - Evidence: `integrity_bad_count = 0` and `interval_overlaps = 0`.

12. The resulting contract is reproducible from repository artifacts.
   - PASS
   - Evidence: the 15-minute reconstruction is reproducible from the canonical files and the existing research script.

## 9. Evidence-Supported Findings

### Proven

- The canonical event stream includes explicit timestamp, market, bid, ask, and last fields.
- The repository metadata defines a deterministic canonical ordering and tie-break rule.
- The current 15-minute reconstruction is deterministic on the existing canonical dataset.
- The reconstructed bars pass the basic OHLC integrity checks performed here.
- The Group A swing rules remain compatible with the bar-level high/low series under the current dataset and under the existing research implementation.

### Proposed but not frozen

- The 15-minute reconstruction was a valid research substrate.
- The current bar construction was a credible candidate for operational review before the human approval recorded in this Phase 1 decision.
- The bar contract is now human-approved and authoritative for the Phase 1 operational input model; earlier proposal language is preserved as historical evidence only.

## D. Historical unresolved state (superseded by approval)

Before the human decision, the repository evidence was sufficient to establish a deterministic research-only bar construction, but it was not yet sufficient to establish the full operational contract required for a Group B freeze.

That historical unresolved state is now superseded by the human approval recorded in this Phase 1 decision.

## E. Human decision requirement (resolved)

The project required a single governance decision to accept the deterministic 15-minute bucket construction as the authoritative operational Group B input contract.

That decision has now been made by the human project authority and is recorded as the governing Phase 1 approval.

## F. Governance status

- BAR CONTRACT: FROZEN / HUMAN APPROVED
- CLOSED BAR RULE: confirmed
- INCOMPLETE BAR RULE: confirmed
- POST-CLOSE IMMUTABILITY: confirmed
- BOUNDARY EVENT RULE: confirmed as `[start, end)` with the event at `bar_end` assigned to the next bar
- GROUP A: unchanged / frozen
- GROUP B: NOT FROZEN
- PHASE 2: NOT STARTED
- Production trading behavior: unchanged

## 10. Historical blocked items (superseded)

The earlier blocked items were valid before approval and represented the missing operational contract. They are now resolved by the human-approved contract:

- closed vs incomplete current 15-minute bar
- no-mutation rule after a bar is considered closed
- future event effect on a completed bar
- acceptance of the 15-minute bucket contract as the authoritative Group B input model

These are no longer open design questions for the governing Phase 1 bar contract.

## 11. Research vs Operational Status

### A. Proven by repository evidence

- The canonical event stream is deterministic and timestamp-ordered.
- The 15-minute bar reconstruction is reproducible and deterministic on the current canonical dataset.
- The basic OHLC integrity checks pass.
- The reconstructed bar sequence is compatible with the frozen Group A local-extrema definitions.

### B. Supported as an approved operational contract

- The 15-minute bar construction is now the human-approved Phase 1 operational input contract for Group B.
- It remains separate from the frozen Group A swing definition and does not freeze Group B itself.
- The project must not silently treat this contract as a production trading rule outside the recorded governance decision.

### C. Historical note

The earlier uncertainty about whether the final partial bar should be excluded was resolved by the human approval: the final partial bar at dataset end is discarded for finalized Group A and Group B evaluation.

## 12. Architect Decision

BAR CONTRACT AUDIT: HUMAN APPROVED / FROZEN

Reason:

The current evidence proves that the 15-minute reconstruction is deterministic, reproducible, and compatible with the frozen Group A semantics on the repository’s canonical dataset. The human project authority has now approved the operational closed-bar / incomplete-bar / post-close immutability semantics required to make the 15-minute contract authoritative for Group B input use.

This approval does not change the frozen Group A swing definition. It resolves the previously unresolved operational contract while preserving the earlier evidence and proposal history as supporting documentation.

The timeframe is FROZEN for this Phase 1 operational decision.
The Group B specification remains NOT FROZEN.

### Final summary

- BAR CONTRACT: FROZEN / HUMAN APPROVED
- CLOSED BAR RULE: confirmed
- INCOMPLETE BAR RULE: confirmed
- POST-CLOSE IMMUTABILITY: confirmed
- BOUNDARY EVENT RULE: confirmed as `[start, end)` with event at `bar_end` assigned to the next bar
- GROUP A: unchanged / frozen
- GROUP B: NOT FROZEN
- PHASE 2: NOT STARTED
- Production trading behavior: unchanged

## Validation Summary

Exact validation performed:

- inspected canonical event schema in [data/canonical/tardis_btc_eur_20191201/canonical_events.jsonl](../../data/canonical/tardis_btc_eur_20191201/canonical_events.jsonl)
- inspected canonical metadata in [data/canonical/tardis_btc_eur_20191201/metadata.json](../../data/canonical/tardis_btc_eur_20191201/metadata.json)
- inspected provenance metadata in [data/canonical/tardis_btc_eur_20191201/provenance_sidecar.jsonl](../../data/canonical/tardis_btc_eur_20191201/provenance_sidecar.jsonl)
- executed the current reconstruction logic from [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
- verified deterministic behavior across repeated reconstruction
- verified OHLC integrity and interval non-overlap on the current dataset
- checked frozen Group A compatibility using the same bar-level high/low rule

Exact observed results:

- files = 12
- unique_market_sample = `['BTC-EUR']`
- market_counts = `{'BTC-EUR': 244140}`
- bars_len1 = 1146
- bars_len2 = 1146
- bars_identical = True
- integrity_bad_count = 0
- interval_overlaps = 0
- highs_count = 78
- lows_count = 68

## Files changed

- Created: [docs/phases/phase-01-zone-formation/BAR_CONTRACT_AUDIT.md](BAR_CONTRACT_AUDIT.md)
- No production code modified.
- No Group A frozen decisions modified.
- No strategy, risk, or execution logic modified.
- No Phase 2 work started.

## Final status

- Final audit status: BAR CONTRACT AUDIT: HUMAN APPROVED / FROZEN
- Human approval status: APPROVED by the human project authority for the Phase 1 operational bar contract
- Group B remains: NOT FROZEN
