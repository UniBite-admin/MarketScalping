# STEP 7.3 — Raw, Validated, Canonical Historical Data Contract

## Status

Authoritative architecture contract for Step 7.3.

This contract is design-only and does not create runtime behavior. It defines the repository-grounded boundary for raw historical evidence, validated raw historical data, canonical replay data, and the non-authoritative role of historical datasets relative to financial state.

## 1. Purpose

This contract defines the exact lifecycle for historical dataset handling in the MarketScalping repository:

- raw Bitvavo exchange evidence is collected and preserved
- invalid and quarantined records are explicitly separated from valid data
- validated raw data is a distinct artifact
- canonical replay data is a separate artifact derived only from valid validated data
- replay eligibility is a strict, machine-checkable condition
- historical datasets remain non-authoritative for financial execution and accounting

This contract preserves all relevant decisions from STEP 7.1 and closes the remaining architecture gaps required for implementation readiness.

## 2. Scope

This contract applies to:

- Bitvavo historical trade collection
- raw data validation
- dataset quarantine and rejection handling
- canonical replay normalization
- replay boundary enforcement
- lineage and metadata tracking across raw, validated, canonical data

This contract does not change:

- execution authority
- accounting authority
- execution idempotency model
- live trading activation rules
- risk-engine authority

## 3. Authority boundaries

The repository already defines a strict separation of authority.

- Raw historical data is evidence-only.
- Validated raw data is evidence-only.
- Canonical replay data is deterministic simulation input.
- Accounting state is the authoritative financial ledger.
- Execution events are not redefined by raw trade identity.
- The canonical replay stream does not carry financial execution identity.

Normative rule:

- Historical data is non-authoritative.
- No financial engine may derive authoritative state from raw trade evidence.
- No canonical replay record may be treated as a financial execution record.
- No `execution_event_id` is created or required in the canonical replay schema.

## 4. Raw dataset definition

A raw dataset is the original source evidence returned by the exchange fetch layer and stored by the collector.

A raw record MUST retain the raw trade identity and evidence fields, including at minimum:

- `trade_id`
- `event_time_utc`
- `price`
- `amount`
- `side`
- `source`
- raw exchange payload metadata

Raw records are not canonical replay input.

### Raw value semantics

For raw `price` and raw `amount`:

- value MUST be supplied as a numeric value or decimal-string value that is parseable
- it MUST be finite
- it MUST be greater than zero
- `NaN`, `+Infinity`, `-Infinity`, zero, negatives, and non-numeric values are rejected

This preserves the STEP 7.1 rule that raw source values remain evidence and must be validated before accepted use.

### Raw time semantics

- timestamps MUST be timezone-aware UTC or normalized to UTC
- timestamps MUST be parseable and valid
- timestamp values are compared as UTC event time, not local wall-clock time

## 5. Validated dataset definition

A validated dataset is the accepted subset of raw records that pass validation and completeness checks.

A validated dataset MUST contain only valid raw rows and MUST preserve:

- raw identity fields
- raw evidence metadata
- validation status per record
- rejection/quarantine metadata for invalid records

A validated dataset is not yet canonical replay data.

### Validated dataset acceptance rule

A raw record becomes part of the validated dataset only if:

- timestamp is valid and in the permitted range
- `trade_id` is present and unique within the dataset window
- `price` is finite and greater than zero
- `amount` is finite and greater than zero
- `side` is valid
- record is not quarantined

A validated dataset is considered successful only if the dataset is complete for the requested window and the service has no unresolved integrity failure.

## 6. Canonical dataset definition

A canonical dataset is the deterministic, normalized replay stream used for market simulation and replay.

Canonical records MUST contain only runtime-relevant replay fields:

- `event_time_utc`
- `event_type`
- `market`
- `bid`
- `ask`
- `last`

Canonical replay records intentionally do not contain:

- `trade_id`
- `amount`
- `side`
- `execution_event_id`

This is required by STEP 7.1 and preserved here.

### Canonical trade semantics

Trade events are normalized using these rules:

- `last` is the execution price and MUST be finite and greater than zero
- `bid` and `ask` are compatibility placeholders when quote-side values are absent
- synthetic `bid` and `ask` values are defined as `last` if no quote-side values are present
- synthetic bid/ask values are not observed exchange quotes and MUST NOT be treated as real market quotes

## 7. Finite-number policy

This section is normative and machine-checkable.

### 7.1 Numeric validity rule

A numeric value is valid only if all of the following are true:

- it is numeric or parseable as a numeric string
- it is finite
- it is strictly greater than zero

A numeric value is invalid if any of the following are true:

- `NaN`
- `+Infinity`
- `-Infinity`
- non-numeric text
- zero
- negative value

### 7.2 Field-by-field decision table

| Field | NaN | +Infinity | -Infinity | Non-numeric | Zero | Negative | Accepted | Rejected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| raw `price` | reject | reject | reject | reject | reject | reject | finite > 0 | all invalid forms |
| raw `amount` | reject | reject | reject | reject | reject | reject | finite > 0 | all invalid forms |
| canonical `bid` | reject | reject | reject | reject | reject | reject | finite > 0 | all invalid forms |
| canonical `ask` | reject | reject | reject | reject | reject | reject | finite > 0 | all invalid forms |
| canonical `last` | reject | reject | reject | reject | reject | reject | finite > 0 | all invalid forms |

### 7.3 Canonical runtime semantics

- Canonical numeric values are runtime float semantics after successful parse and validation.
- Raw values may be stored as decimal strings or normalized numeric values as long as validation rejects non-finite or non-positive input.
- A synthetic trade `bid` or `ask` must remain finite and greater than zero even though it is a compatibility placeholder.

This preserves the STEP 7.1 contract: raw Decimal-string semantics and canonical runtime float semantics remain distinct, while both are finite and positive when accepted.

## 8. Dataset state model

The state model must remain explicit and non-ambiguous.

### 8.1 Required state values

- `COLLECTION_FAILED`
- `EMPTY_VALID_DATASET`
- `VALIDATED`
- `CANONICALIZED`
- `REJECTED`

### 8.2 Additional state rule

A dataset is never considered a successful canonical dataset if it is partial or incomplete.

The system MUST NOT represent partial successful canonicalization as `CANONICALIZED`.

Normative rule:

- `PARTIAL_DATASET` is not a terminal success state.
- `PARTIAL_DATASET` is represented as metadata on a dataset with status `REJECTED` when the dataset is incomplete or incomplete-with-valid-records.
- This preserves a strict rule: valid records alone do not imply canonical success.

### 8.3 Why this is required

A partial dataset may contain some valid records, but it is not safe to replay or treat as complete historical evidence. If the requested window is incomplete, the dataset is not a valid replay input.

Therefore:

- valid subset + incomplete window = `REJECTED` with `completeness_status=PARTIAL_WINDOW`
- empty set of valid records = `EMPTY_VALID_DATASET`
- full valid dataset = `VALIDATED`
- canonicalized dataset = `CANONICALIZED`

### 8.4 State definition examples

- `COLLECTION_FAILED`: source fetch or collection fails before validation begins
- `EMPTY_VALID_DATASET`: fetch succeeded, zero valid rows remain after validation
- `VALIDATED`: window complete, valid records accepted and stored
- `CANONICALIZED`: canonical records successfully produced from a complete validated dataset
- `REJECTED`: dataset is not acceptable for replay; includes partial/incomplete or invalid/failing datasets

## 9. Invalid record policy

This contract chooses a mixed policy that is safer than whole-dataset invalidation for raw data, while still requiring strict dataset-level completeness gating.

### 9.1 Policy decision

The architecture decision is:

- invalid raw records may be quarantined while valid records continue processing
- but the final dataset-level result is still governed by completeness and integrity rules
- canonicalization must never consume quarantined records

This is the safest choice because it preserves evidence and prevents silent data loss without permitting unvalidated or incomplete canonical data.

### 9.2 Quarantine semantics

Invalid records MUST be preserved in a quarantine artifact or quarantine metadata, including:

- raw record identity
- raw source evidence
- rejection reason
- validation stage
- whether the record was excluded from the validated dataset

Quarantined records MUST remain readable for audit and reconciliation.

### 9.3 Dataset-level rejection semantics

A dataset is rejected when any of the following are true:

- requested window cannot be satisfied
- validation fails for a required dataset-level integrity rule
- canonicalization fails
- incomplete dataset is not replay-eligible
- dataset completeness is ambiguous or partial

### 9.4 Why whole-dataset rejection is not the default

Whole-dataset rejection is not chosen as the universal rule because it would discard valid evidence unnecessarily and reduce auditability. However, a dataset may still be rejected at the final state if completeness or integrity is not satisfied.

In short:

- invalid record: quarantine, preserve evidence
- valid records continue
- final canonical output: only allowed if integrity and completeness are satisfied

## 10. Time-window and completeness semantics

A dataset has explicit time-window semantics.

### 10.1 Required metadata

- `requested_start_time_utc`
- `requested_end_time_utc`
- `actual_first_event_time_utc`
- `actual_last_event_time_utc`

### 10.2 Completeness rule

The dataset is considered complete if and only if:

- all raw rows in the requested time window are either accepted or explicitly rejected/quarantined
- no valid rows are silently omitted from the validated dataset
- a partial result is explicitly marked as incomplete

### 10.3 Incomplete requested window

If the request is for a window but the collected or validated data does not cover the entire requested interval, the result is:

- dataset status = `REJECTED`
- completeness status = `PARTIAL_WINDOW`
- canonicalization blocked

### 10.4 Empty but valid window

If the requested time range is valid and no records are returned because there are genuinely no events, the dataset status is:

- `EMPTY_VALID_DATASET`

This is not a canonicalized dataset and is not replay input.

## 11. Lineage model

The lineage model must connect each canonical record back to the valid row and original source evidence.

### 11.1 Required lineage path

`canonical_record -> validated_record -> raw_record -> original_source_evidence`

### 11.2 Identity placement

The raw source identity is the exchange identity:

- `trade_id` belongs to the raw and validated record lineage

The canonical replay schema intentionally does not add `trade_id` because it is not part of the runtime replay model and it would contradict the STEP 7.1 contract.

### 11.3 Minimal lineage metadata

Minimal lineage metadata MUST include:

- `canonical_record_id`
- `validated_record_id`
- `raw_record_id`
- `raw_trade_id`
- `source_dataset_id`
- `source`
- `market`
- `validation_reasons[]`
- `canonical_status`
- `replay_origin`

### 11.4 Implementation location

Lineage belongs in:

- validated dataset metadata for raw-to-validated traceability
- canonical dataset metadata for canonical-to-validated mapping
- sidecar lineage manifest for full record-level provenance

This avoids polluting the canonical schema with raw trade identity while preserving full historical traceability.

## 12. Dataset metadata

Dataset-level metadata is required for machine-checkable status and traceability.

### 12.1 Required metadata fields

- `dataset_status`
- `schema_version`
- `source`
- `market`
- `requested_start_time_utc`
- `requested_end_time_utc`
- `actual_first_event_time_utc`
- `actual_last_event_time_utc`
- `raw_record_count`
- `validated_record_count`
- `canonical_record_count`
- `rejected_record_count`
- `validation_result`
- `canonicalization_result`
- `lineage_reference`
- `rejection_summary[]`

### 12.2 Explicit processing metadata rule

Wall-clock processing timestamps are not part of event-time semantics and should not be mixed into the dataset event timeline.

If a generation timestamp is needed, it MUST be named explicitly as:

- `processing_generated_at_utc`

This field is metadata, not event time.

## 13. Immutability

Transformations produce new artifacts; they do not mutate earlier artifacts.

### 13.1 Required immutability rules

- raw dataset is immutable once written
- validated dataset is a derived artifact and must not mutate the raw dataset
- canonical dataset is a derived artifact and must not mutate the validated dataset
- rejected and quarantined records remain preserved and immutable as evidence

### 13.2 Minimal fingerprinting

A dataset fingerprint may be used only for artifact integrity tracking.

The preferred minimal mechanism is a deterministic content digest of the serialized artifact, for example a stable hash over normalized bytes. This is not a cryptographic security mechanism by itself; it is a deterministic artifact integrity aid.

## 14. Determinism

Deterministic transformation is required.

The same raw dataset plus the same contract/schema version and the same transformation rules MUST produce the same:

- validation result
- dataset state
- canonical records
- ordering
- rejection result
- lineage mapping

### Determinism requirements

- no network access during validation or canonicalization
- no current-time-dependent decisions
- no hidden state
- no nondeterministic ordering beyond the required `(event_time_dt, original_index)` canonical sort

### Canonical ordering rule

Canonical ordering MUST be:

- `(event_time_dt, original_index)`

This is the authoritative replay ordering contract.

## 15. Replay boundary

The replay boundary is machine-enforceable.

### 15.1 Allowed replay input

Replay may accept only a canonical dataset that satisfies all of the following:

- `dataset_status == CANONICALIZED`
- `canonicalization_result == SUCCESS`
- all canonical records are valid
- ordering is deterministic
- no quarantined or rejected records are included
- no partial dataset is allowed

### 15.2 Forbidden replay input

Replay MUST NOT directly consume:

- raw evidence
- rejected raw records
- quarantined records
- unvalidated records
- incomplete datasets
- empty-but-meaningful dataset states

### 15.3 Replay acceptance condition

A dataset is replay-eligible only if the canonical artifact exists and the dataset is complete, valid, and canonicalized. Anything else is blocked.

## 16. Failure semantics

This section defines exact machine-detectable outcomes.

| Failure type | State | Required action |
| --- | --- | --- |
| API or fetch failure | `COLLECTION_FAILED` | stop collection, preserve failure metadata |
| malformed raw record | `REJECTED` with quarantine entry | preserve raw evidence, do not include in validated data |
| invalid timestamp | `REJECTED` with quarantine entry | preserve raw evidence |
| invalid numeric value | `REJECTED` with quarantine entry | preserve raw evidence |
| duplicate `trade_id` | `REJECTED` or quarantined duplicate entry | preserve duplicate evidence and continue if policy allows |
| incomplete requested window | `REJECTED` with `completeness_status=PARTIAL_WINDOW` | block canonicalization |
| empty but valid window | `EMPTY_VALID_DATASET` | no canonicalization |
| validation failure | `REJECTED` | preserve rejected records and metadata |
| canonicalization failure | `REJECTED` | preserve failure metadata and block replay |
| serialization failure | `REJECTED` or stage-specific failure state | do not silently convert to empty dataset |

Normal rule:

- failure must never be silently converted into an empty successful dataset
- a failure is explicit in metadata and state

## 17. STEP 7.1 preservation rules

This Step 7.3 contract preserves all relevant STEP 7.1 decisions.

- raw Decimal string semantics remain valid for raw source evidence
- canonical runtime float semantics remain valid for normalized replay values
- finite positive numeric rules apply to raw and canonical numeric fields where applicable
- timestamps are timezone-aware and UTC-normalized
- deterministic ordering remains `(event_time_dt, original_index)`
- canonical event types remain `ticker` and `trade`
- synthetic trade bid/ask are compatibility placeholders only
- canonical replay has no financial `execution_event_id`
- historical data remains non-authoritative

## 18. QA test matrix

The implementation should satisfy the following acceptance checks.

### 18.1 Raw validation matrix

- valid raw dataset accepted
- invalid timestamp rejected
- non-finite value rejected
- zero or negative price rejected
- zero or negative amount rejected
- duplicate `trade_id` quarantined or rejected according to policy
- malformed record quarantined without breaking valid records
- empty valid window returns `EMPTY_VALID_DATASET`
- incomplete window returns `REJECTED` with partial-window metadata

### 18.2 Canonicalization matrix

- valid ticker canonicalized successfully
- valid trade canonicalized successfully
- trade with missing bid/ask falls back to synthetic last values
- invalid canonical numeric field rejected
- invalid market rejected
- invalid event type rejected
- canonical ordering matches `(event_time_dt, original_index)`

### 18.3 Replay eligibility matrix

- `CANONICALIZED` dataset accepted for replay
- `VALIDATED` dataset not replay-eligible
- `REJECTED` dataset not replay-eligible
- `EMPTY_VALID_DATASET` not replay-eligible
- raw dataset not replay-eligible

## 19. Safety guardrails

- Historical data is evidence-only and never execution-authoritative.
- Canonical trade bid/ask placeholders are not real quotes.
- Raw `trade_id` remains raw identity only.
- Canonical replay schema does not include raw identity fields that would create false execution semantics.
- Partial or incomplete data is never represented as successful canonical data.
- Invalid records remain preserved, not silently discarded.
- Replay only consumes canonicalized and complete datasets.

## 20. Final normative summary

The repository-grounded architecture is:

RAW
 ↓
VALIDATED
 ↓
CANONICAL
 ↓
REPLAY

The required contractual rules are:

1. raw evidence is preserved and immutable
2. invalid raw rows are quarantined and preserved
3. validated raw data is complete-only for valid accepted rows
4. canonical replay is derived only from valid complete validated data
5. replay does not consume raw, rejected, quarantined, or incomplete data
6. numeric values are finite and strictly positive when accepted
7. synthetic trade bid/ask are compatibility placeholders only
8. canonical replay has no execution identity
9. historical data is non-authoritative
10. dataset status is explicit; partial data is never treated as successful canonical data

This contract is the authoritative architecture definition for Step 7.3.
