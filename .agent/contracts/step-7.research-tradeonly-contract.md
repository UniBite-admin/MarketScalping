---
contract_id: step-7.research-tradeonly
contract_version: 1.0.0
schema_version: 1
title: Trade-Only Research Profile Contract
format: yaml-in-markdown
created_by: architect
created_utc: 2026-09-19T00:00:00Z

# Machine-policy references
canonical_quote_policy_reference: .agent/contracts/step-7.3-raw-validated-canonical-contract.md
research_forbidden_override: true

# Machine-readable sections
input_contract:
  description: "Canonicalized trade-only input record schema. Records MUST be UTC timestamped and finite numeric values where required."
  fields:
    source_trade_id:
      type: string
      required: false
      description: "Original exchange identifier when present. Must be preserved in raw-layer provenance."
    record_id:
      type: string
      required: true
      description: "Deterministic internal record id. Not an exchange-native trade id; must be generated deterministically when source id missing."
    event_time_utc:
      type: string
      format: iso-8601
      required: true
      description: "UTC event timestamp; millisecond precision recommended. Must be parseable and timezone-aware."
    market:
      type: string
      required: true
      description: "Canonical market identifier (e.g. BTC-USDT)."
    price:
      type: number
      required: true
      constraints:
        finite: true
        gt: 0
      description: "Trade execution price; required and strictly positive."
    quantity:
      type: number
      required: true
      constraints:
        finite: true
        gt: 0
      description: "Trade quantity/amount; required and strictly positive."
    side:
      type: string
      required: false
      description: "Exchange side if provided. If absent, features requiring side must be marked unavailable."
    source:
      type: string
      required: true
      description: "Provider id or dataset origin."
    raw_lineage:
      type: object
      required: true
      description: "Opaque provenance object with source path/URL, compression, retrieval timestamp, and per-file hash when available."

record_id_scheme:
  description: "Deterministic record_id generation scheme. Implementations MUST produce identical record_id given the same inputs."
  algorithm: "sha256_hex"
  inputs_order:
    - dataset_id
    - event_time_utc
    - source
    - source_trade_id
    - original_index
  separator: "|"
  note: "If `source_trade_id` is absent, include an explicit empty token in its position so generation remains deterministic. Implementations MUST NEVER surface `record_id` as an exchange/native id."
  original_index_semantics:
    description: "Zero-based deterministic integer index assigned to the record within the canonicalization window."
    zero_based: true
    source: "Index in the canonicalized event ordering after deterministic sorting (see 'index_and_timestamp_semantics')."
    stability: "Implementations that use chunked or parallel ingestion MUST perform a deterministic global ordering pass before assigning `original_index`. If such a pass is impossible, canonicalization MUST fail."
  timestamp_normalization:
    description: "Exact event_time normalization before hashing."
    parse: "RFC3339 / ISO-8601"
    utc_normalize: true
    precision: "millisecond"
    canonical_format: "YYYY-MM-DDTHH:MM:SS.sssZ"
  string_normalization:
    description: "Per-field normalization applied before hashing."
    rules:
      - trim_whitespace: true
      - unicode_normalization: "NFKC"
      - source_lowercase: true
      - market_canonical_format: true
      - source_trade_id_normalization: "trim + NFKC + preserve-case-unless-blank"
  hash_input_example: "sha256_hex(join('|', dataset_id, normalized_event_time_utc, normalized_source, normalized_source_trade_id_or_empty, original_index))"

output_contract:
  description: "Research-only outputs. All derived fields must be namespaced with 'research_' prefix. None may pretend to be quote-derived."
  categories:
    raw_observations:
      allowed: true
      description: "Canonicalized trade-only rows preserved under data/research/raw/."
    derived_features:
      allowed: true
      prefix: research_
      examples:
        - research_trade_return_t2t: "(price_i / price_{i-1} - 1)"
        - research_trade_return_tN: "N-trade returns"
        - research_time_delta_ms
        - research_trade_volume
        - research_rolling_volume_{window}
        - research_trade_rate_{per_sec}
        - research_signed_flow (only if `side` reliable)
        - research_trade_volume_imbalance (only if `side` reliable)
    research_signals:
      allowed: true
      prefix: research_signal_
      description: "Heuristic or derived numeric/boolean signals for research only."
    research_decisions:
      allowed: true
      prefix: research_decision_
      description: "Research-only decision records (not execution events)."

forbidden_fields:
  - bid
  - ask
  - mid_price
  - spread_abs
  - spread_pct
  - bestBid
  - bestAsk
  - order_book
  - L1
  - L2
  description: "These fields MUST NOT be produced or published by trade-only profile artifacts."

artifact_namespace:
  root: data/research/
  rules:
    - "All research artifacts MUST be written under `data/research/` and never to production artifact paths."
    - "File naming must include dataset_id, profile_id, run_id and contract_version."

provenance_required:
  - contract_version
  - dataset_id
  - source
  - source_dataset_hash
  - collection_period:
      - start_utc
      - end_utc
  - canonicalization_version
  - feature_profile_version
  - transform_version
  - run_id
  - created_utc
  - timestamp_semantics
  - ordering_rules
  - side_mapping
  - limitations
  - synthesis_status

reproducibility_requirements:
  - exact_input_dataset_identity
  - input_file_hashes_when_available
  - config_file_included (config_<run_id>.yaml)
  - deterministic_ordering_by_event_time_then_record_id
  - transform_version_pinned
  - environment_versions (python, deps hash)

status_model:
  VALID: "Run completed, provenance present, no forbidden synthesis, dataset completeness and validation passed."
  PROVISIONAL: "Run completed but requires downstream quote-complete validation before any production consideration."
  INCOMPLETE: "Run lacked required inputs or failed completeness checks (not replayable)."
  INVALID: "Run failed data validation (bad timestamps, invalid prices/quantity, etc.)."
  REJECTED: "Run rejected by QA/Safety due to policy violation or synthesis attempt."

promotion_requirements:
  - "translation of candidate logic into quote-compatible representation"
  - "quote-complete historical validation run evidence"
  - "paper-session validation evidence"
  - "Architect + QA + Safety approval record"

fail_closed_rules:
  - id: invalid_event_time
    condition: "missing or non-parseable event_time_utc"
    action: INVALID
  - id: non_finite_price_quantity
    condition: "non-finite or non-positive price/quantity"
    action: INVALID
  - id: duplicate_record_id
    condition: "duplicate record_id conflicts"
    action: INVALID
  - id: missing_provenance
    condition: "missing provenance"
    action: REJECTED
  - id: attempted_quote_synthesis
    condition: "any attempt to synthesize bid/ask/mid/spread or L1/L2"
    action: REJECTED
  - id: invalid_market
    condition: "market not in canonical market list or malformed"
    action: INVALID
  - id: dataset_incomplete
    condition: "dataset completeness check failed"
    action: REJECTED
  - id: record_id_exposed_as_source
    condition: "record_id is presented as trade_id, source_trade_id, exchange_id, or provider/native trade identifier in any downstream research artifact"
    action: REJECTED

market_list_reference: null
market_list_note: "No repository-wide canonical market-list exists; invalid_market remains fail-closed and requires external manifest for automated validation."

governance:
  owner: architect
  reviewers: [qa, safety]
  required_approvals: [architect, qa, safety]

# Duplicate handling policy (machine-readable)
duplicate_policy:
  description: "Enumerates deterministic handling for duplicate identities and conflicting records. Fail-closed semantics preferred."
  rules:
    - case: identical_source_records
      match: "same source_trade_id and identical content"
      action: "keep_one_deterministic"
      selection_rule:
        keep: 1
        selector: "min by (event_time_utc, original_index)"
        preserve_provenance: true
    - case: source_trade_id_conflict
      match: "same source_trade_id but differing content"
      action: "FAIL_CLOSED"
      rationale: "Conflicting source-trade identity must not be silently deduplicated."
    - case: duplicate_record_id
      match: "same record_id appears with conflicting inputs"
      action: "INVALID"
      rationale: "Record_id collision indicates generation flaw or data corruption; fail the run."

# Side mapping schema (provenance.side_mapping)
side_mapping_schema:
  description: "Defines vendor-specific side values mapping to canonical BUY/SELL/UNKNOWN and ambiguity policy."
  mapping_example:
    vendor_values: ["b", "s", "buy", "sell", "taker_buy_buy", "unknown"]
    canonical_map:
      b: BUY
      buy: BUY
      s: SELL
      sell: SELL
      unknown: UNKNOWN
  ambiguity_policy: REJECT
  note: "Ambiguous or unmapped vendor side values MUST cause the dataset or run to be rejected unless explicit mapping is provided in provenance."

# Production boundary enforcement
do_not_use_as_replay_input: true
artifact_namespace_enforcement: true

# Versioning policy
versioning_policy:
  breaking_change_definition: "Any change that alters forbidden fields, core enforcement rules, duplicate policy, or record_id scheme."
  major_version_required_for_incompatible_changes: true
  consumer_behavior_on_unsupported_version: "FAIL_CLOSED"
  note: "Consumers must fail closed when encountering an unsupported or incompatible contract_version."

# Synthetic quote policy (machine-readable)
synthetic_quote_policy:
  research_profile_allows_synthesis: false
  canonical_replay_reference: .agent/contracts/step-7.3-raw-validated-canonical-contract.md

# Dataset completeness policy
dataset_completeness_policy:
  required_fields_for_completeness: [requested_start_time_utc, requested_end_time_utc, actual_first_event_time_utc, actual_last_event_time_utc, raw_record_count, validated_record_count]
  incomplete_action: REJECTED

# Provisional usage clarification
provisional_usage: promotion-stage-only

---

# Trade-Only Research Profile Contract (human-readable)

## Purpose
This contract defines the machine-readable rules for an offline, research-only profile that consumes trade-only historical data and produces trade-derived research artifacts. These artifacts are explicitly NOT production-compatible and MUST NOT be used as inputs to the canonical replay or live/paper pipeline.

## Main invariants
- NO FABRICATED QUOTE STATE: the profile MUST NOT produce any of `bid`, `ask`, `mid_price`, `spread_abs`, `spread_pct`, or order-book fields.
- SOURCE vs RECORD ID: `source_trade_id` (when present) is distinct from `record_id`; the latter is a deterministic internal id.
- ARTIFACT ISOLATION: all outputs live under `data/research/` and must include required provenance.

## Input fields (summary)
- `source_trade_id` (optional)
- `record_id` (required)
- `event_time_utc` (required, ISO-8601)
- `market` (required)
- `price` (required, finite > 0)
- `quantity` (required, finite > 0)
- `side` (optional)
- `source` (required)
- `raw_lineage` (required)

## Output categories (summary)
- Raw observations (preserved canonicalized trades)
- Derived features (namespaced `research_`)
- Research signals (namespaced `research_signal_`)
- Research decisions (namespaced `research_decision_`)

## Promotion boundary
Trade-only research artifacts may produce hypotheses, candidate strategy specifications, and research evidence, but promotion to production requires quote-complete validation and paper validation and formal approvals.

## Machine-readable format
This file contains a YAML machine-readable contract in the frontmatter, followed by a concise human-readable explanation. Consumers may parse the YAML block for validation and tooling.

## Notes
- This contract intentionally omits any synthetic mid/approximation in v1. Any future extension that permits labelled synthesis must create a new contract version and include explicit synthesis metadata and QA requirements.
