# Group B Zone Creation Final Audit

## 1. Scope

This document is a governance/research audit only.

It addresses the unresolved Group B root decision:

> What is the simplest defensible rule for when a Zone first becomes a valid Zone?

This audit does not:

- freeze any creation rule
- modify production code
- modify tests
- modify datasets
- start Phase 2
- invent a creation threshold
- optimize parameters
- silently change any frozen decision

The purpose is to keep the distinction explicit between:

- minimum tolerance history = 1
- minimum number of members required to create a valid Zone

These are separate decisions. The repository evidence supports the first as a tolerance-history rule. It does not currently support the second as a frozen Zone-creation rule.

Classification: REPOSITORY FACT

## 2. Frozen inputs

The following remain authoritative and are preserved exactly:

- 15-minute UTC bar contract
- separate HIGH and LOW streams
- W = 5 prior legal same-direction gaps
- minimum tolerance history = 1
- causal prior same-direction absolute-gap tolerance
- current swing excluded from its own tolerance history
- zone center = median(member prices)
- membership = abs(incoming_price - current_zone_center) <= current_tolerance
- canonical replay ordering remains authoritative
- causal no-lookahead semantics remain authoritative

These are frozen decisions. They do not freeze a Zone creation rule or a minimum member threshold.

Classification: FROZEN

## 3. Candidate creation semantics

### A. First eligible swing immediately creates a valid Zone

Definition:

- the first eligible same-direction swing is itself a valid Zone

### B. First eligible swing is a seed/candidate; the next qualifying same-direction observation creates the valid Zone

Definition:

- first eligible swing is a seed/candidate only
- second qualifying same-direction swing establishes a valid Zone

### C. Require more than two qualifying observations

Definition:

- more than two same-direction qualifying observations are required before a Zone becomes valid

### D. Any other creation rule already supported by repository evidence

Definition:

- any other creation rule already described by the repo, if supported by the actual evidence and not invented ad hoc

## 4. Causal state requirements

### A. First eligible swing immediately creates a valid Zone

Required state before creation:

- a confirmed eligible swing exists
- direction is known
- canonical ordering is known
- no additional state is strictly required by its own logic

Causally computable?

- Yes, in a trivial mechanical sense, because the single observed swing is available.

Uses only already-known information?

- Yes, if the system is willing to treat a single member as a valid Zone.

Relies on arbitrary threshold?

- No additional threshold is required, but it does require the undocumented assumption that a single observed member is sufficient for a valid Zone.

Conflicts with frozen membership rule?

- It does not directly conflict with the frozen membership equation, but it does conflict with the repository’s caution that a Zone requires more than a single observation before it is treated as a stable object.

Conflicts with frozen tolerance-history semantics?

- It does not conflict with the tolerance-history rule directly, because the rule is about tolerance availability, not Zone creation.
- However, the first swing cannot rely on the frozen tolerance history if there are zero prior legal gaps.

Repository evidence supporting it?

- No direct authoritative evidence supports this as a final rule.

Only a proposal?

- Yes, as a semantic choice.

Classification: PROPOSAL ONLY

### B. First eligible swing is a seed/candidate; the next qualifying same-direction observation creates the valid Zone

Required state before creation:

- current direction stream
- current candidate/seed state
- a prior eligible swing exists
- a second qualifying same-direction swing is observed in canonical order
- the creation event occurs only when the second qualifying observation is known

Causally computable?

- Yes, because it uses already-observed data only.

Uses only already-known information?

- Yes.

Relies on arbitrary threshold?

- It introduces a simple structural threshold of two observations, but it is not a parameter optimization and it is not an arbitrary tolerance formula.
- It is a structural proposal for the creation boundary.

Conflicts with frozen membership rule?

- It does not conflict with the frozen membership rule; it only defines the earlier state boundary before membership becomes meaningful.

Conflicts with frozen tolerance-history semantics?

- It does not conflict directly. The tolerance-history rule remains about prior same-direction gaps, while the creation rule is about when a Zone becomes valid.

Repository evidence supporting it?

- The repository repeatedly documents a candidate/seed concept, a valid Zone concept, and a minimal cluster or member-set baseline that is structurally compatible with a two-observation starting point.
- This is evidence-supported as the least-assumption proposal, but not a frozen decision.

Only a proposal?

- Yes, as a final rule.

Classification: PROPOSAL ONLY

### C. Require more than two qualifying observations

Required state before creation:

- direction stream
- a candidate or seed state
- at least N qualifying same-direction observations, where N > 2
- a defined rule for what counts as qualifying

Causally computable?

- Yes, once N is defined.

Uses only already-known information?

- Yes.

Relies on arbitrary threshold?

- Yes, by definition. Any N > 2 introduces an arbitrary structural threshold without repo authority.

Conflicts with frozen membership rule?

- It is not a direct conflict but it does impose a stronger creation requirement than the repository has frozen.

Conflicts with frozen tolerance-history semantics?

- No direct conflict, but it adds a separate creation threshold not justified by the tolerance-history rule.

Repository evidence supporting it?

- No direct authoritative evidence supports a final N > 2 threshold.

Only a proposal?

- Yes.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### D. Any other creation rule already supported by repository evidence

Required state before creation:

- depends on the specific rule proposed

Causally computable?

- only if the rule is fully defined and uses already-known state

Uses only already-known information?

- only if the rule is defined without future lookahead or hidden state

Relies on arbitrary threshold?

- only if the rule introduces a new threshold not already frozen

Conflicts with frozen membership rule?

- depends on the exact rule

Conflicts with frozen tolerance history?

- depends on the exact rule

Repository evidence supporting it?

- none as a final rule

Only a proposal?

- yes

Classification: UNRESOLVED

## 5. Evidence from repository

### 5.1 Repository fact: the canonical stream and eligible swings are real

The repository research code reconstructs the canonical 15-minute bars and identifies eligible direction-specific swings in time order.

Evidence:

- tools/research/research_15m_groupb.py

Observed canonical counts:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

This is descriptive historical evidence. It is not proof of a final Zone-creation rule.

Classification: REPOSITORY FACT

### 5.2 Repository fact: a candidate/seed concept is repeatedly discussed

The earlier Group B audits repeatedly distinguish between:

- eligible swing
- seed/candidate state
- valid Zone
- member set
- membership evaluation

That distinction is real and supported by the current repo documentation.

Classification: REPOSITORY FACT

### 5.3 Repository fact: the repo does not freeze a creation threshold

The repository does not contain a final frozen rule saying:

- one swing creates a Zone
- two swings create a Zone
- three or more swings create a Zone

This is the central unresolved governance fact.

Classification: REPOSITORY FACT

### 5.4 Repository fact: the minimum-history rule is not the creation-rule

The frozen tolerance-history rule says:

- minimum history = 1 prior legal same-direction gap

This is a rule about tolerance availability.

It is not a rule about the minimum number of members required before a Zone is valid.

This distinction is critical and is supported by the repo’s governance wording.

Classification: REPOSITORY FACT

## 6. Relationship to membership and tolerance history

The tolerance-history rule and the Zone-creation rule are not interchangeable.

### 6.1 The tolerance-history rule

The repo explicitly froze:

- W = 5
- minimum history = 1
- tolerance computed as the median of the selected prior legal same-direction absolute gaps

This is a bound on the historical tolerance used in membership evaluation.

Classification: FROZEN

### 6.2 The creation rule

A Zone can only exist if some creation semantics define when the Zone becomes valid.

The repository has not frozen that semantics.

Therefore:

- tolerance availability is not sufficient evidence for Zone creation
- the first eligible swing is not automatically a valid Zone merely because no prior legal gaps exist
- even a seed/candidate state does not equal a valid Zone by default

Classification: REPOSITORY FACT

### 6.3 Why a two-observation baseline is only a proposal

The idea that the first swing is a seed and the second same-direction qualifying swing creates a valid Zone is the simplest defensible structural proposal because it:

- separates observation from validity
- avoids a one-move leap to a finished Zone
- respects the repo’s direction-specific causal structure

However, this remains a proposal only. It is not a frozen fact, and it is not the same as saying that two members are objectively required as a permanent design rule.

Classification: PROPOSAL ONLY

## 7. Comparison of candidates

| Candidate | Is creation causally computable? | Uses only already-known data? | Requires arbitrary threshold? | Conflicts with frozen membership rule? | Conflicts with frozen tolerance history? | Repository support | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. First swing = valid Zone | Yes | Yes | No extra threshold, but yes hidden assumption | Not directly | Not directly, but semantically weak | No direct support | PROPOSAL ONLY |
| B. First swing = seed; second qualifying observation = valid Zone | Yes | Yes | Structurally yes, but not a parameter optimization | No | No | Strongest minimal proposal in repo docs | PROPOSAL ONLY |
| C. More than two observations | Yes | Yes | Yes | No direct conflict | No direct conflict | No authoritative support | BLOCKED BY UNRESOLVED ROOT DECISION |
| D. Other existing creation rule | Depends | Depends | Depends | Depends | Depends | No final authority | UNRESOLVED |

## 8. Simplest defensible proposal

The simplest defensible proposal is:

- the first eligible same-direction swing is a candidate/seed state
- the Zone becomes valid only after a second qualifying same-direction observation in the same direction stream
- this maintains a causal distinction between observation and valid Zone
- it does not invent a broader lifecycle or a parameterized creation rule
- it does not conflate tolerance history availability with Zone validity

This is the least-assumption proposal supported by the repo’s direction-specific and state-separation language.

It is still not frozen and not authoritative.

Classification: PROPOSAL ONLY

## 9. Decision readiness

Status: NOT READY TO FREEZE

The current repository evidence is sufficient to distinguish the semantic candidates and to identify the simplest minimal proposal, but it is not sufficient to freeze a final Zone creation rule because:

- the Zone object itself is not final
- member-set semantics are not final
- geometry and lifecycle remain unresolved
- the repo does not define the final creation threshold as authoritative

Therefore, the evidence supports a proposal, not a freeze.

Classification: UNRESOLVED

## 10. Remaining blockers

The blockers are:

- no final Zone object definition
- no final member-set semantics
- no final geometry semantics
- no final lifecycle semantics
- no human decision on whether the first observation is a seed or a valid Zone
- no authoritative minimum member count for valid Zone creation

These blockers prevent a final freeze without silently inventing missing rules.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 11. Required human decision

The required human decision is:

> Should a valid Zone be created only after the second qualifying same-direction observation, or should the first eligible swing itself be treated as a valid Zone candidate/seed or a valid Zone?

Until that choice is made, the repo must keep Zone creation in the following status:

- Group B remains NOT FROZEN
- Phase 2 remains NOT STARTED
- Zone creation remains PROPOSAL ONLY / UNRESOLVED / BLOCKED BY UNRESOLVED ROOT DECISION

This audit is research-only and does not authorize implementation or downstream Phase 2 work.

Classification: REQUIRED HUMAN DECISION
