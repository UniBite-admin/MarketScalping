# Phase 1 — Zone Formation Audit

## Status

FROZEN — HUMAN APPROVED

This audit records the approved frozen specification for Phase 1 Group A. It confirms that the Group A swing definition is complete, deterministic, causal, and internally consistent within the approved scope.

The Phase 1 operational 15-minute bar contract has also received explicit human approval as the authoritative Group B input contract. This approval is separate from the Group A freeze and does not reinterpret the frozen Group A swing definition.

## Final Human-Approved Freeze Record (2026-10-06)

This Phase 1 scope is now explicitly frozen under human approval as of 2026-10-06.

### Accepted frozen scope

The repository now records the following as the accepted Phase 1 governance scope:

- Group A swing definition remains frozen
- 15-minute UTC bar contract remains frozen as the authoritative Group B input contract
- narrow Group B tolerance-history rules remain frozen
- narrow Group B center statistic remains frozen
- narrow Group B membership rule remains frozen
- narrow Group B creation rule remains frozen

### Evidence boundary

The maximum lifecycle-independent evidence presently accepted is:

FIRST VALID ZONE → IMMEDIATE NEXT UNIQUE SAME-DIRECTION SWING → MATHEMATICAL MEMBER/NON_MEMBER/UNCLASSIFIABLE CLASSIFICATION

No broader lifecycle evidence is accepted within the Phase 1 freeze.

### Unresolved lifecycle boundary

The following remain explicitly outside the accepted Phase 1 freeze:

- active Zone identity
- multiple Zone behavior
- Zone persistence
- Zone retirement
- Zone replacement
- Zone overlap/merge
- member-set update semantics
- center update after a member
- tolerance update after a member
- non-member transition behavior
- candidate behavior after valid Zone creation
- candidate/Zone coexistence
- any later lifecycle behavior

### Rejected lifecycle-independent evidence

The prior counts:

- HIGH: 27 valid Zone creations
- LOW: 23 valid Zone creations

remain explicitly classified as:

REJECTED AS LIFECYCLE-INDEPENDENT EVIDENCE

They are not accepted as part of the frozen Phase 1 evidence set.

### Governance status

- Phase 1 status: FROZEN / HUMAN APPROVED
- Group B overall status: NOT FROZEN
- Phase 2 status: NOT STARTED
- production behavior: UNCHANGED
- human approval date: 2026-10-06

This is a governance freeze only. It does not broaden the accepted Phase 1 contract, does not implement lifecycle behavior, and does not start Phase 2.

## 1. Authoritative sources inspected

- [docs/ROADMAP.md](../../ROADMAP.md) — authoritative current roadmap
- [REPO_MAP.md](../../REPO_MAP.md) — authority and pipeline map
- [replay_runner.py](../../replay_runner.py) — deterministic replay ordering and canonical time processing
- [feature_signal_engine.py](../../feature_signal_engine.py) — validation of timestamp monotonicity and event ordering
- [historical_dataset.py](../../historical_dataset.py) — historical data validation and canonicalization behavior

## 2. Historical sources inspected

- [.agent/roadmap/master_roadmap.json](../../.agent/roadmap/master_roadmap.json) — historical roadmap artifact; not current authority

## 3. Review findings

### 3.1 Established repository facts

- The project’s replay layer is deterministic and timestamp-aware.
- The current repo does not define a normative Phase 1 swing rule, but the specification now closes that gap for Group A.
- Historical rules are traceability evidence only, not current authority.
- The system must not silently assume a technical rule without an explicit design decision.

### 3.2 Group A freeze audit

The Group A specification is complete and internally consistent for final human freeze review. The causal timing model is explicit, the boundary and equality behavior is deterministic, and the downstream contract is constrained to Group A outputs without prematurely designing later zone logic.

The specification satisfies the required conditions because:
- raw observation is defined exactly as the local candidate event at candle index i
- confirmation is defined as the moment the final required neighbor becomes observable in canonical order
- eligibility is defined as the moment the confirmed swing may affect downstream logic; it is the same event as confirmation for this rule
- boundary behavior is single-valued and deterministic
- equality is explicitly non-swing in all neighbor comparisons
- replay determinism is preserved by canonical ordering and strict equality semantics
- look-ahead is prevented because downstream logic cannot use the candidate before the required confirmation information exists
- downstream contract stays limited to the confirmed swing record and does not define later zone semantics

### 3.3 Swing window size assessment

The 1-left / 1-right structure is the required V1 design because it is the smallest deterministic local-turn detector and it preserves clarity, testability, and causal behavior. Wider windows are intentionally not part of this specification because they are later-phase design questions, not Group A freeze items.

### 3.4 Causality and confirmation

The required distinction is explicit:
- swing candle time = time[i]
- confirmation time = time[i + 1] when the required right-side observation becomes visible in canonical stream order
- eligibility time = confirmation time for this specification because the same final observation begins downstream usability

This is not a violation of the no-look-ahead rule because the system does not use future information to decide at candle time i; it only confirms a prior candidate once the required information is observable.

### 3.5 Boundary behavior

The boundary rules are exact and deterministic:
- first candle: not eligible
- last candle: not eligible
- insufficient prior candles: not eligible
- insufficient confirmation candles: not eligible
- incomplete historical window: not eligible

There is no alternate boundary interpretation in Group A.

### 3.6 Equality analysis

The specification is explicit that equality never qualifies:
- high[i] == high[i - 1] => non-swing
- high[i] == high[i + 1] => non-swing
- low[i] == low[i - 1] => non-swing
- low[i] == low[i + 1] => non-swing

This removes plateau ambiguity and preserves deterministic behavior.

### 3.7 Data field analysis

High/Low alone are sufficient for Phase 1 pivot detection. Open, Close, and Volume remain excluded from the Group A pivot definition unless a later phase provides explicit justification.

### 3.8 Determinism review

The same candle sequence under the same canonical replay order produces the same swing sequence because:
- ordering is fixed by canonical timestamp and stable index
- equality is excluded from all valid swing cases
- no tolerance or fuzzy comparison is allowed
- incomplete windows are non-eligible
- no retroactive backfill occurs

There is no remaining Group A tie or ordering ambiguity in the approved scope.

### 3.9 Downstream compatibility

The design remains compatible with later Phase 1 work because it emits only confirmed swing candidates, not zone objects. It does not prematurely define:
- clustering tolerance
- zone center
- zone boundaries
- zone lifecycle
- touch rules
- reaction rules

These are intentionally deferred.

## 4. Audit result

PASS

Status:
- FROZEN — HUMAN APPROVED
- READY FOR HUMAN FREEZE: superseded by final approval

## 5. Group B tolerance-history audit

FROZEN — HUMAN APPROVED

The approved Group B tolerance-history semantics are consistent with the higher-authority frozen inputs:

- Group A swing semantics remain authoritative and are not changed.
- The 15-minute bar contract remains authoritative and is not changed.
- The causal/no-lookahead requirement remains in force.
- HIGH and LOW remain separate streams.
- The current swing is excluded from its own tolerance history.
- Prior observations are ordered by canonical replay / eligibility order.
- The tolerance is a median of legal prior same-direction absolute gaps.
- W = 5 is a count of prior legal same-direction gaps, not bars and not elapsed time.
- minimum history = 1 prior legal same-direction gap is explicitly approved.
- when 0 prior legal same-direction gaps exist, no tolerance is available and membership cannot be evaluated.

The approved semantics do not silently resolve the broader unresolved Group B root decisions. The following remain NOT FROZEN even after this approval:

- member-to-zone distance/reference rule
- zone geometry
- join/new-zone rule
- multiple-candidate zone handling
- overlap resolution
- zone center behavior
- historical snapshot/immutability details not already frozen
- deterministic zone identity/tie-break details not already frozen
- any other unresolved Group B root decision discovered during the audit

This approval therefore records a bounded human-approved tolerance-history decision without creating a broader Group B freeze.

## 6A. Candidate A center-statistic approval audit

FROZEN — HUMAN APPROVED

The human project authority has explicitly approved the center statistic for Candidate A — Point-Center Zone:

- CENTER STATISTIC: median(member prices)
- STATUS: FROZEN — HUMAN APPROVED

This approval is intentionally narrow. It freezes only the center statistic for Candidate A. It does not freeze the membership rule, zone creation rule, zone update timing, zone identity, multiple-zone handling, overlap, merge behavior, zone width, lifecycle semantics, or historical snapshot semantics. Those remain unresolved Group B decisions. Group B remains NOT FROZEN as a whole, and Phase 2 remains NOT STARTED.

This decision is a governance-approved center-definition record. It is not an evidence claim that median is experimentally proven optimal, more profitable, or fully validated across a complete sequential zone lifecycle. The repository evidence remains descriptive cluster analysis only; it does not prove full sequential zone-state superiority.

## 6B. Candidate A / D membership-rule approval audit

FROZEN — HUMAN APPROVED

The human project authority has explicitly approved the following membership rule for a valid Zone:

- incoming eligible swing is a member when abs(incoming_swing_price - current_zone_center) <= current_tolerance
- current_zone_center = median(member prices)
- current_tolerance = causal tolerance from the frozen HIGH/LOW-specific tolerance history
- HIGH and LOW remain separate
- the current incoming swing is not included in the tolerance used to evaluate itself
- strict causal ordering is preserved
- membership is evaluated only from already-known state

This approval is intentionally narrow. It freezes only the membership rule for a valid Zone under the current frozen center-statistic and tolerance-history semantics. It does not freeze zone creation, member-set update semantics, zone geometry, overlap, merge, lifecycle, identity, or any other unresolved Group B root decision. Candidate B (nearest-member distance) is explicitly not the membership rule. Candidate C remains unresolved/blocked. Group B remains NOT FROZEN as a whole, and Phase 2 remains NOT STARTED.

The recorded governance rationale is:
- A/D is the simplest defensible membership rule under the current frozen center semantics.
- The 86 A-vs-B disagreements demonstrate materially different geometry, not evidence that A/D is invalid.
- Repository evidence does not require nearest-member semantics.

## 6C. Zone Creation approval audit

FROZEN — HUMAN APPROVED

The human project authority has explicitly approved the following Zone Creation rule:

- the first eligible same-direction swing is a SEED / CANDIDATE
- the first eligible same-direction swing does NOT create a valid Zone
- a valid Zone is created when a second same-direction swing qualifies as a member under the already-frozen Group B membership rule
- "qualifies as a member" means abs(incoming_swing_price - current_zone_center) <= current_tolerance
- current_zone_center is the median of the current member prices
- current_tolerance is the already-frozen causal HIGH/LOW-specific tolerance history, with:
  - W = 5
  - minimum tolerance history = 1
  - current swing excluded from its own tolerance history
  - HIGH and LOW histories remain separate
- no additional numerical threshold is introduced
- minimum tolerance history = 1 is not reinterpreted as the minimum Zone member count; these are separate decisions
- the two-member requirement applies only to Zone creation:
  - member #1 = seed/candidate
  - member #2 = valid Zone creation trigger

This approval is intentionally narrow. It freezes only the creation semantics for when a valid Zone first becomes valid under the already-frozen center and membership rules. It does not freeze member-set update semantics beyond the approved creation rule, final Zone geometry/boundaries, zone expansion/broadening behavior, multiple simultaneous zones, overlap handling, merge behavior, zone identity, lifecycle/state transitions, historical snapshot semantics, or any other Group B decision not explicitly approved by the human.

The following remain unresolved / NOT FROZEN unless already independently frozen by prior human approval:
- member-set update semantics beyond the approved creation rule
- final Zone geometry / boundaries
- zone expansion / broadening behavior
- multiple simultaneous zones
- overlap handling
- merge behavior
- zone identity
- lifecycle / state transitions
- historical snapshot semantics
- any other Group B decision not explicitly approved by the human

Group B remains NOT FROZEN overall, and Phase 2 remains NOT STARTED.

## 6. Final conclusion

The Phase 1 Group A specification is complete, deterministic, causal, and internally consistent as the approved frozen swing definition. No unresolved contradiction remains within the approved Group A scope.

## 6. Frozen decisions

A1 — Swing High:
- High[i] > High[i - 1]
- High[i] > High[i + 1]

A2 — Swing Low:
- Low[i] < Low[i - 1]
- Low[i] < Low[i + 1]

A3 — Required Data:
- Swing High detection uses High only.
- Swing Low detection uses Low only.
- Open, Close, and Volume are not inputs to the Phase 1 swing definition.

A4 — Comparison:
- All comparisons are strict.
- Equality never qualifies as a swing.

A5 — Boundary:
- A swing requires the complete required neighborhood.
- The first/last candle and any candle without the required neighboring observations cannot qualify.

## 7. Freeze invariants

These decisions must not be silently changed or reinterpreted. The distinction between swing observation, confirmation, and eligibility remains explicit and binding for Group A. The no-look-ahead requirement remains in force for all downstream logic.
