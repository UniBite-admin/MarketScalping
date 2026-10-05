# Group B Zone Creation + First-Member Audit

## 1. Objective

This audit addresses one unresolved Group B root decision:

> What is the simplest defensible Zone Creation + First-Member semantic that is compatible with all frozen decisions and supported by repository evidence?

This is architecture research only. It does not implement a Zone, a membership engine, or a lifecycle state machine. It does not freeze any rule.

The question is not: "Which rule is personally preferred?"

The question is:

> Which rule can be responsibly proposed without inventing unsupported strategy behavior?

This document separates:

- REPOSITORY FACT
- ARCHITECTURAL PROPOSAL
- UNRESOLVED / HUMAN DECISION

and it keeps all proposals explicitly labeled PROPOSAL ONLY — NOT FROZEN.

## 2. Authoritative Inputs

Authoritative sources inspected:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ARCHITECT_PROPOSAL.md](GROUP_B_ARCHITECT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL_AUDIT.md](GROUP_B_PROPOSAL_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_SECOND_ROOT_DECISION_BATCH_ANALYSIS.md](GROUP_B_SECOND_ROOT_DECISION_BATCH_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_TOLERANCE_ARCHITECTURE_COMPARISON.md](GROUP_B_TOLERANCE_ARCHITECTURE_COMPARISON.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_TOLERANCE_FORMULA_ANALYSIS.md](GROUP_B_TOLERANCE_FORMULA_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_HISTORY_WINDOW_ANALYSIS.md](GROUP_B_HISTORY_WINDOW_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_WINDOW_CALIBRATION_ANALYSIS.md](GROUP_B_WINDOW_CALIBRATION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_W_MINIMUM_HISTORY_FINAL_ANALYSIS.md](GROUP_B_W_MINIMUM_HISTORY_FINAL_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md](GROUP_B_MEMBERSHIP_SEMANTICS_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md](GROUP_B_ZONE_STATE_CONTRACT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md](GROUP_B_ZONE_OBJECT_GEOMETRY_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_COMPARISON.md](GROUP_B_ZONE_GEOMETRY_COMPARISON.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_CENTER_CALIBRATION_ANALYSIS.md](GROUP_B_CENTER_CALIBRATION_ANALYSIS.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

Repository searches were also used for the terms:

- zone creation
- cluster creation
- first member
- minimum cluster size
- support/resistance level creation
- state transitions
- identity
- lifecycle
- replay reconstruction

No authoritative Zone production object or Zone state machine was found to define a final zone creation rule.

## 3. Frozen Decisions Used

The following remain frozen and authoritative:

### 3.1 Group A swing formation

REPOSITORY FACT

- Swing High = High[i] > High[i - 1] and High[i] > High[i + 1]
- Swing Low = Low[i] < Low[i - 1] and Low[i] < Low[i + 1]
- strict comparisons only
- complete required neighborhood
- confirmation precedes downstream eligibility
- no lookahead
- deterministic canonical replay

### 3.2 15-minute bar contract

REPOSITORY FACT

- UTC aligned
- half-open [bar_start, bar_end)
- event exactly at bar_end belongs to next bar
- closed bars are immutable
- incomplete trailing bar excluded
- Group A only operates on closed bars

### 3.3 Group B tolerance history

REPOSITORY FACT

- HIGH and LOW streams remain separate
- only prior legal same-direction gaps may enter tolerance history
- current swing is excluded from its own tolerance history
- W = 5
- minimum history = 1
- 0 prior legal gaps => no tolerance available
- 1–4 prior legal gaps => use all available
- 5+ => use the latest 5
- tolerance = median(selected prior legal absolute gaps)

### 3.4 Center statistic

REPOSITORY FACT

- Candidate A center statistic is frozen:
  - center = median(member prices)

This is frozen as a statistic. Its update timing is not frozen.

## 4. Repository Facts

### 4.1 REPOSITORY FACT

The canonical research code reconstructs the same-direction sequence and reproduces descriptive counts.

Evidence:

- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

The current code reconstructs 15-minute bars and identifies eligible swing highs and swing lows in canonical order. It does not implement a Zone object or Zone state machine.

### 4.2 REPOSITORY FACT

The repo documents repeatedly say the same-direction sequence must remain separated by direction.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md](GROUP_B_SEQUENCE_SEMANTICS_ANALYSIS.md)

### 4.3 REPOSITORY FACT

The canonical research tooling reproduces:

- HIGH = 78 eligible swings
- LOW = 68 eligible swings

This is descriptive evidence only. It is not proof of a final zone-creation rule.

### 4.4 REPOSITORY FACT

The repo does not contain an authoritative Zone creation rule, a first-member rule, or a minimum-cluster-size rule that is frozen or implemented.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL_AUDIT.md](GROUP_B_PROPOSAL_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ROOT_DECISION_ANALYSIS.md](GROUP_B_ROOT_DECISION_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)

### 4.5 REPOSITORY FACT

The repository supports the distinction between:

- an observation
- a confirmed swing
- an eligible swing
- a tolerance history event
- a Zone candidate
- a Zone member

But it does not freeze the technical semantics that connect those states into a Zone lifecycle.

## 5. Creation Candidate Analysis

The following candidates were analyzed without assuming any one is correct.

### Candidate A — FIRST ELIGIBLE SWING CREATES A ZONE

UNRESOLVED / HUMAN DECISION

Reasoning:

- The repository does not define a formal Zone-creation event.
- The frozen tolerance rule says minimum history = 1, but that only says a tolerance may exist after one prior legal gap; it does not say a Zone must exist at the first eligible swing.
- The project documents repeatedly describe a minimum cluster size proposal of 2 as a reasonable structural starting point, but it remains a proposal and not a frozen rule.

Evidence for:

- simple, minimal creation semantics
- a first eligible swing is available and can be represented as an observed state
- it involves no extra parameters

Evidence against:

- risks treating a single observation as a fully valid Zone without enough evidence
- does not line up with the repo’s repeated minimum-cluster-size proposal as a research baseline
- would conflate historical observation with zone existence unless the repo explicitly defines the difference

Conclusion:

- not justified as a frozen rule
- remains a candidate only

### Candidate B — FIRST ELIGIBLE SWING IS ONLY AN OBSERVATION; ZONE EXISTS ONLY AFTER A SECOND QUALIFYING SAME-DIRECTION SWING

ARCHITECTURAL PROPOSAL

Reasoning:

- This is the strongest repository-aligned minimal design because it separates observation from zone existence.
- The project documents explicitly discuss a minimum cluster size of 2 as a reasonable structural proposal.
- This avoids creating a Zone from a single point without an evidentiary basis.

Evidence for:

- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md) explicitly discusses minimum cluster size and treats 2 swings as a reasonable proposal.
- [docs/phases/phase-01-zone-formation/GROUP_B_ARCHITECT_PROPOSAL.md](GROUP_B_ARCHITECT_PROPOSAL.md) recommends a minimum evidence threshold before a valid Zone is created.
- It keeps the first swing as a stateful observation and avoids conflating observation with a valid Zone.

Evidence against:

- the repo does not freeze a minimum cluster size of 2
- the repo does not define the exact creation event or trigger
- the repo does not define whether a first swing can seed a candidate Zone without full validity

Conclusion:

- this is the best minimal proposal supported by the current evidence
- still PROPOSAL ONLY — NOT FROZEN

### Candidate C — FIRST ELIGIBLE SWING WITH AVAILABLE TOLERANCE CREATES A ZONE

UNRESOLVED / HUMAN DECISION

Reasoning:

- This would connect tolerance-history availability to Zone creation.
- But the frozen tolerance rule and the zone-creation question are separate concerns unless the repo explicitly connects them.
- The repo never states that tolerance availability is equivalent to zone creation evidence.

Evidence for:

- there is a natural appeal to: no tolerance available = no zone evidence
- the tolerance rule already has minimum history = 1

Evidence against:

- the repo does not define that tolerance availability is a Zone creation trigger
- it does not define whether first valid tolerance means first zone member, seed, or valid Zone
- it risks conflating a tolerance rule with a Zone existence rule

Conclusion:

- not justified by current evidence
- this is an invalid shortcut unless explicitly approved later

### Candidate D — ZONE EXISTS ONLY AFTER A MULTI-MEMBER CLUSTER SATISFIES A MINIMUM EVIDENCE CONDITION

ARCHITECTURAL PROPOSAL

Reasoning:

- This is the most conservative version of the same underlying idea as Candidate B.
- It treats the minimal meaningful Zone as a cluster that has more than one same-direction observation.
- It avoids creating a full Zone from a single observation.

Evidence for:

- repo docs repeatedly state single-swing structures are weak and fragmented
- proposals discuss minimum cluster size and reject single-swing zones as structurally weak

Evidence against:

- no final minimum size is frozen
- no exact trigger semantics are frozen
- current evidence is descriptive, not a proof of the best threshold

Conclusion:

- a reasonable design baseline
- still PROPOSAL ONLY — NOT FROZEN

### Candidate E — OTHER RULE SUPPORTED BY REPO EVIDENCE

REPOSITORY FACT

No alternative rule is explicitly supported by authoritative repo evidence. The project has a clear pattern of leaving Zone creation unresolved and of treating 2-member minimum evidence as a reasonable but not frozen proposal.

## 6. First-Member Analysis

### 6.1 What “first member” means

UNRESOLVED / HUMAN DECISION

The repository does not define a final semantic for the first member. The term can mean several different things:

- a valid Zone may start from a single observed swing
- a single swing may be a seed or candidate before it becomes a Zone
- a single swing may be a historical member without constituting a valid Zone
- a single swing may be an observation that awaits a second same-direction swing to become a cluster

The repo evidence supports a distinction between observation and Zone, but it does not freeze which of those states is the first Zone member.

### 6.2 Can a zone have exactly one member?

UNRESOLVED / HUMAN DECISION

The project docs repeatedly suggest that single-swing clusters are structurally weak and highly fragmented. That is evidence against treating a one-member Zone as a robust Zone, but it is not a final rule.

### 6.3 Is minimum member count of 2 required?

ARCHITECTURAL PROPOSAL

The current evidence supports a weak but legitimate proposal that a minimum zone evidence of 2 same-direction eligible swings is a reasonable starting point.

Evidence:

- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ARCHITECT_PROPOSAL.md](GROUP_B_ARCHITECT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL.md](GROUP_B_PROPOSAL.md)

But the repo does not freeze this as a final rule.

### 6.4 Seed semantics

ARCHITECTURAL PROPOSAL

A minimal and conceptually clean interpretation is:

- the first same-direction eligible swing may exist as a historical observation and as a candidate seed
- a Zone does not become a valid Zone until a second qualifying same-direction swing exists or another explicit creation condition is met

This does not require a final technical rule; it is a structural distinction between seed and Zone.

### 6.5 Does a seed have identity, center, or geometry?

UNRESOLVED / HUMAN DECISION

The repo does not define that a seed must have a stable identity, a center, or a geometry. Those are state-model choices, not facts.

### 6.6 Can a seed later become a zone?

ARCHITECTURAL PROPOSAL

This is a reasonable design possibility, but it is not a frozen rule.

The project evidence supports an explicit distinction between:

- seed observation
- candidate Zone
- valid Zone

without requiring a final implementation decision.

## 7. Causal Timeline

This section is a conceptual timeline using only frozen facts and clearly labeled proposals.

### 7.1 First eligible HIGH

REPOSITORY FACT + PROPOSAL ONLY

At H1:

1. H1 is observed as a candidate swing
2. H1 is confirmed when the required right-side evidence is available
3. H1 becomes eligible as a confirmed swing
4. No prior same-direction legal gap exists
5. Tolerance is unavailable under the frozen rule
6. The current evidence does not support a final statement that a Zone must or must not exist at H1
7. H1 may be treated as a historical observation or as a candidate seed
8. A valid Zone is not justified merely because a single swing exists

This is the cleanest statement supported by the evidence.

### 7.2 Second eligible HIGH

REPOSITORY FACT + PROPOSAL ONLY

At H2:

1. H2 is confirmed and eligible
2. H1 is a prior legal same-direction observation
3. one prior legal same-direction gap now exists
4. tolerance may become available under the frozen minimum-history = 1 rule
5. whether H2 triggers Zone creation remains unresolved
6. whether H1 and H2 form a valid 2-member cluster remains unresolved
7. whether this is a seed-to-zone transition or a zone creation trigger remains unresolved

### 7.3 First eligible LOW

REPOSITORY FACT + PROPOSAL ONLY

At L1:

1. L1 is observed and confirmed
2. no prior same-direction legal low gap exists
3. tolerance is unavailable
4. no final zone-existence rule is justified
5. L1 may be a candidate seed or a single historical observation

### 7.4 Second eligible LOW

REPOSITORY FACT + PROPOSAL ONLY

At L2:

1. L2 is confirmed and eligible
2. one prior legal low gap exists
3. tolerance may become available under the frozen rule
4. same unresolved questions as for H2
5. no final creation semantics are justified by the repo alone

### 7.5 Important conclusion

The frozen tolerance rule supports the existence of a legal prior-gap stream after the second same-direction swing, but it does not tell us whether that point is the first valid Zone or merely the first time a zone candidate can be evaluated.

This is exactly why zone creation must remain separate from tolerance-history availability.

## 8. Tolerance-History vs Zone-Evidence Separation

This distinction is critical.

### 8.1 REPOSITORY FACT

The frozen rule says:

- minimum history = 1 prior legal same-direction gap
- zero prior gaps => no tolerance available

This tells us that a tolerance may be unavailable for the first swing.

### 8.2 REPOSITORY FACT

It does not say:

- a Zone cannot exist at the first swing
- a Zone must not exist before tolerance is available
- a Zone creation trigger is equivalent to tolerance availability
- the first swing must be discarded
- the first swing is automatically invalid as a Zone seed

### 8.3 ARCHITECTURAL PROPOSAL

The cleanest minimal separation is:

- tolerance history is an input to membership evaluation
- Zone existence is a distinct state decision
- a single swing can be an observation or candidate seed
- a valid Zone should require stronger evidence than a single observation unless a later design explicitly chooses otherwise

This is a proposal only, not a frozen decision.

## 9. Data-Based Descriptive Evidence

### 9.1 REPOSITORY FACT

The canonical research tooling reproduces the following same-direction counts:

- HIGH = 78 eligible swings
- LOW = 68 eligible swings

### 9.2 ARCHITECTURAL PROPOSAL

A minimal creation rule based on 2-member evidence is not unsupported by the repo, but it is not proven by the data alone.

The descriptive evidence that matters here is not profitability or optimum behavior. It is the presence of a distinct same-direction stream and the project’s repeated suggestion that a single swing is too weak to be considered a robust Zone.

### 9.3 What the data does not support

The repository does not support the following claims:

- the first swing must create a Zone
- the second swing must always create a Zone
- the project has measured a true zone lifecycle
- a minimum evidence threshold of 2 is empirically proven optimal
- the first-swing or second-swing case is an empirically superior trading rule

These would require a true sequential Zone-state simulation, which the current repo does not have.

## 10. Phase Boundary

This section uses [docs/ROADMAP.md](../../ROADMAP.md) as authoritative.

### 10.1 Phase 1 — Zone Formation

REPOSITORY FACT

Phase 1 may legitimately define first-member semantics only if those semantics are the minimum necessary structure for Zone formation and remain within the current Phase 1 scope.

The following belong in Phase 1 research at most:

- the distinction between observation, seed, and valid Zone
- the minimum evidence required to define a Zone as a causal object
- the minimum member-set contract needed to make membership semantics meaningful

### 10.2 Phase 4 — Zone Lifecycle

REPOSITORY FACT

The following belong to later lifecycle work and should not be imported into Phase 1 without explicit roadmap approval:

- expiry
- inactivity
- invalidation
- retirement
- merging
- splitting
- overlap resolution
- lifecycle state transitions

Those are not “small details”; they are Phase 4 concerns unless the roadmap explicitly says otherwise.

## 11. Recommended Architectural Proposal — PROPOSAL ONLY

### Proposal

PROPOSAL ONLY — NOT FROZEN

The minimal supportable architectural proposal is:

1. A confirmed, eligible swing may exist as a historical observation.
2. A historical observation is not automatically a final Zone.
3. A Zone should require stronger evidence than a single observation.
4. A minimal and conservative proposal is that a valid Zone requires at least two eligible same-direction observations before it is treated as a Zone in a causal sequential model.
5. The first eligible swing is treated as a seed or candidate observation until a second qualifying same-direction observation exists or another explicit creation rule is approved.
6. The creation trigger is a design-level question, not a frozen fact.
7. The minimum-history = 1 tolerance rule applies to tolerance calculation; it does not automatically define Zone creation.
8. Center = median(member prices) remains the frozen center statistic once a Zone exists, but the update timing of the center remains unresolved.

### Evidence supporting the proposal

- repeated repo comments that a single-swing structure is weak and fragmented
- minimum cluster size proposal appears in repo docs as a reasonable structural baseline
- tolerance availability and Zone creation are separate concepts
- the repo does not support creating a final Zone from a single swing without a separate, explicit rule

### Evidence against it

- not frozen
- not proven as the empirically best or only rule
- no final minimum cluster size is defined
- no final creation-event semantics are defined

## 12. Alternatives

### Alternative 1 — single eligible swing creates a Zone

UNRESOLVED / HUMAN DECISION

This is the simplest semantics but it is not justified by the repo’s repeated warnings about single-swing weakness and the lack of a final Zone-creation rule.

### Alternative 2 — tolerance availability defines Zone creation

UNRESOLVED / HUMAN DECISION

This is a tempting shortcut but it is not supported by repo evidence. It would silently conflate tolerance history and Zone existence.

### Alternative 3 — no creation rule yet; keep all observations in a pending set

ARCHITECTURAL PROPOSAL

This is a conservative option that keeps the state model minimal until the project chooses the exact creation rule.

It avoids premature abstraction and unsupported strategy behavior.

## 13. Unresolved Root Decisions

The following remain UNRESOLVED / HUMAN DECISION:

- exact Zone creation trigger
- minimum member count for a valid Zone
- first-member semantics
- whether the first swing is a seed, candidate, or fully valid Zone
- whether tolerance availability implies Zone creation
- exact Zone object minimum fields
- center update timing
- exact membership evaluation order
- exact multiple-zone selection semantics
- exact overlap / merge semantics
- zone identity semantics
- historical mutation semantics
- lifecycle semantics

## 14. Human Approval Gate

A human approval gate is now appropriate only for deciding whether to formalize one of the candidate creation semantics as a future Group B rule.

The current repository evidence supports a research proposal but does not support a final creation decision.

Therefore:

- a proposal is supportable
- a freeze is not supportable yet
- explicit human approval is required before converting the proposal into a formal rule

## 15. Governance Status

Status: PROPOSAL ONLY — NOT FROZEN

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- No production code was changed.
- No executable tests were changed.
- No canonical data was changed.
- Existing frozen decisions remain intact.
- This document does not create a new freeze.

## Final conclusion

The repository evidence does not justify freezing a Zone Creation rule. It does, however, support a minimal architecture-only proposal:

- separate an observation from a valid Zone
- treat the first eligible swing as a candidate seed or observation, not automatically a full Zone
- require stronger evidence before a Zone is treated as valid
- default to a conservative 2-member minimum evidence threshold as a research baseline only

This is the strongest defensible interpretation consistent with the current repo evidence, but it remains PROPOSAL ONLY — NOT FROZEN.
