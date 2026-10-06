# 1. Audit Objective

This document audits the methodology behind the existing research artifact [docs/phases/phase-01-zone-formation/GROUP_B_NON_MEMBER_TRANSITION_ANALYSIS.md](GROUP_B_NON_MEMBER_TRANSITION_ANALYSIS.md).

The audit is limited to methodology and evidence quality. It does not modify production code, executable tests, frozen decisions, or any authoritative Phase 1 specification. It does not start Phase 2, freeze any lifecycle behavior, or invent new strategy semantics.

The primary question is the one raised by the artifact itself:

- Why do the member + non-member totals exceed the number of eligible swings in each direction?

The short answer is that the reported numbers are not counts of unique swings. They are counts of repeated evaluations of later swings against multiple Zone creation events. The same downstream swing is evaluated many times, once per Zone-creation context in which it falls after the creation event.

# 2. Source Artifacts

The following artifacts were reviewed for this audit:

- [docs/phases/phase-01-zone-formation/GROUP_B_NON_MEMBER_TRANSITION_ANALYSIS.md](GROUP_B_NON_MEMBER_TRANSITION_ANALYSIS.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
- [tmp_diag/non_member_transition_metrics.py](../../tmp_diag/non_member_transition_metrics.py)
- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/BAR_CONTRACT_DECISION.md](BAR_CONTRACT_DECISION.md)

The audit also relies on the repository’s frozen documentation status:

- Group B remains NOT FROZEN.
- Single-active-zone remains RESEARCH CANDIDATE ONLY.
- Non-member lifecycle remains UNRESOLVED.
- Phase 2 remains NOT STARTED.
- Production behavior remains unchanged.

# 3. Reported Metrics Under Audit

The artifact reports the following descriptive totals:

- HIGH: 78 eligible swings; 27 valid Zone creation events; 46 subsequent members; 968 subsequent non-members
- LOW: 68 eligible swings; 23 valid Zone creation events; 23 subsequent members; 767 subsequent non-members

These totals are not a unique-swing count. They are a repeated-evaluation count under a per-Zone-creation loop.

The critical issue is that:

- 46 + 968 = 1014 for HIGH
- 23 + 767 = 790 for LOW

and both exceed the eligible-swing counts of 78 and 68.

That is impossible under a true unique-swing accounting model, but it is entirely possible under a repeated-application model where each later swing is evaluated again for each creation event.

# 4. Exact Metric Reconstruction

The relevant logic in the surviving temporal analysis script in [tmp_diag/non_member_transition_metrics.py](../../tmp_diag/non_member_transition_metrics.py) is the following pattern:

1. Build the eligible same-direction sequence for HIGH or LOW.
2. Identify valid Zone creation starts.
3. For each valid Zone creation event, iterate all later eligible swings after the creation swing.
4. For each later swing:
   - compute the tolerance at that later point using prior legal same-direction gaps
   - compare the swing price to the current Zone center
   - classify as member or non-member
5. Add the result into the running total for that Zone creation event.

This yields totals by Zone-observation pair, not by unique swing.

The exact calculation structure is:

- For each start event k with creation index s_k:
  - for each later eligible swing j > s_k:
    - evaluation_count += 1
    - if abs(price_j - center_k) <= tolerance_j:
      member_evaluations += 1
    - else:
      nonmember_evaluations += 1

That means:

- the same swing j may contribute to many Zone creation events
- the same future swing can be counted repeatedly
- the reporting unit is therefore “evaluation of a later swing against a specific Zone creation event,” not “one unique historical swing.”

The actual surviving script shows the state-reset pattern that produces the same structure:

- when a valid creation is found, the script resets the candidate state and keeps scanning
- this allows additional Zone creation events to be found later in the same stream
- each later observation is then evaluated against each creation event in turn

The key result is that the reported totals are per Zone-observation pair, not per unique swing.

# 5. HIGH Accounting

The high-direction reconstruction, using the same logic as the artifact and the repository’s canonical 15-minute data, yields the following accounting:

- total eligible swings: 78
- Zone creation events: 27
- unique swing timestamps/prices in the eligible stream: 78
- subsequent observation evaluations after all creation events: 1014
- member evaluations: 46
- non-member evaluations: 968
- duplicated or repeated swing evaluations: 1014 - 78 = 936 extra evaluations beyond the unique-swing base
- maximum number of times one swing was evaluated: 27
- counting unit: per Zone-observation pair, not per unique swing

Summary table for HIGH:

| Metric | Value |
| --- | ---: |
| Total eligible swings | 78 |
| Number of Zone creation events | 27 |
| Unique swing timestamps/prices in stream | 78 |
| Observation evaluations | 1014 |
| Member evaluations | 46 |
| Non-member evaluations | 968 |
| Repeated/duplicated evaluations | 936 |
| Maximum repeats for one swing | 27 |
| Counting unit | Zone-observation pair |

This means the headline ratio is not a direct historical dominance ratio across unique swings. It is a repeated count ratio across many Zone contexts.

# 6. LOW Accounting

The low-direction reconstruction yields the following accounting:

- total eligible swings: 68
- Zone creation events: 23
- unique swing timestamps/prices in the eligible stream: 68
- subsequent observation evaluations after all creation events: 790
- member evaluations: 23
- non-member evaluations: 767
- duplicated or repeated swing evaluations: 790 - 68 = 722 extra evaluations beyond the unique-swing base
- maximum number of times one swing was evaluated: 22
- counting unit: per Zone-observation pair, not per unique swing

Summary table for LOW:

| Metric | Value |
| --- | ---: |
| Total eligible swings | 68 |
| Number of Zone creation events | 23 |
| Unique swing timestamps/prices in stream | 68 |
| Observation evaluations | 790 |
| Member evaluations | 23 |
| Non-member evaluations | 767 |
| Repeated/duplicated evaluations | 722 |
| Maximum repeats for one swing | 22 |
| Counting unit | Zone-observation pair |

Again, the total exceeds the unique-swing count because the same later swings are counted repeatedly against multiple creation events.

# 7. Duplicate / Repeated Evaluation Analysis

This is the central methodology issue.

The artifact is not measuring a single historical sequence in a single Zone lifecycle. It is measuring the same downstream sequence repeatedly, once for each valid Zone creation event that was found earlier in the stream.

This produces repeated evaluations of the later swing set, including the same later swing price at the same later timestamp being evaluated again and again against different Zone centers, each from a different creation event.

The surviving repo evidence shows the pattern clearly:

- In HIGH, one swing can be evaluated as many as 27 times.
- In LOW, one swing can be evaluated as many as 22 times.
- The same later swing is therefore not a single historical observation in the final count.

This is why the sum of member and non-member evaluations exceeds the number of eligible swings.

The report is therefore not a count of unique swing outcomes. It is a per-Zone-observation multiplication of the same historical stream.

In other words:

- unique swing count: one historical swing, one identity
- repeated evaluation count: one historical swing, many evaluation contexts

The artifact uses the second counting unit, but it does not say so explicitly.

# 8. State Reset / State-Machine Analysis

The surviving script in [tmp_diag/non_member_transition_metrics.py](../../tmp_diag/non_member_transition_metrics.py) is the important constraint check for method validity.

It does this:

- maintains a candidate state and a zone-members state
- identifies whether a valid Zone is created
- counts later observations after each creation event
- but it does not prove a state-machine lifecycle rule for model transitions

The artifact’s numbers are therefore not a valid simulation of a single active Zone lifecycle. They are descriptive repeated counts under a repeated-start loop.

Specifically:

- a single historical swing can be counted multiple times
- the same swing can be evaluated against multiple Zone creation events
- Zone state is not treated as a single persistent lifecycle object for all later events
- candidate state is restarted across valid creation events in the repeated counting loop
- observations are counted independently per creation event, not by unique swing identity
- future information is not introduced, but the loop does implicitly create repeated observation contexts from the same historical stream
- state transition semantics are silently assumed only by the repeated counting structure itself, not by the frozen rules

The current repository evidence does not contain a legitimate lifecycle state-machine specification for the following:

- one active Zone vs multiple active Zones
- creation while a prior valid Zone remains active
- invalidation or replacement semantics
- candidate + valid Zone coexistence
- stale Zone handling

Therefore the counts are descriptive but not valid as lifecycle evidence.

# 9. Causality / No-Lookahead Audit

The calculation is causally bounded with respect to the frozen Phase 1 inputs, but that does not make it a state-machine simulation.

The following causal conditions are satisfied in the research construction:

- swing confirmation precedes use: yes, the sequence is ordered by canonical replay and only eligible swings are used
- swing eligibility precedes use: yes, only eligible swings are considered after creation
- only prior information is used: yes, the tolerance and center are computed from already-known prior observations in the sequence
- current swing is excluded from its own tolerance history: yes, this matches the frozen rule in [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- no future swing is used: yes, the sequential loop only uses later swings after the creation event and never uses the future to retroactively redefine the current Zone
- canonical ordering is preserved: yes, the historical sequence is processed in canonical replay order

However, this causal validity does not establish the correctness of the lifecycle policy. It only establishes that the repeated counting pass is consistent with the frozen historical ordering rule.

The audit conclusion is therefore:

- the repeated-evaluation logic is causally valid
- the repeated-evaluation logic is not a valid lifecycle simulation
- the counts are not suitable as direct evidence for Model A vs Model B vs Model C decision-making

# 10. Model A Simulation Status

Model A: Persist + Ignore

Classification: DESCRIPTIVE ONLY

Why:

- The analysis counts non-member outcomes after Zone creation, but it does not simulate a state machine in which a valid Zone persists while later swings are ignored.
- There is no explicit rule in the repo saying that the Zone remains active and future non-members are silently ignored.
- The repeated count does not implement a stateful “persist until replaced or invalidated” rule.
- It merely observes that many later swings would be non-member if re-evaluated repeatedly against each Zone creation event.

This is a descriptive outcome count, not a state-machine simulation.

# 11. Model B Simulation Status

Model B: Persist + New Candidate

Classification: NOT SIMULATED

Why:

- The repo does not define the coexistence of a valid Zone and a pending candidate in the same direction.
- There is no explicit rule for candidate lifetime, candidate priority, or multiple pending candidates.
- The analysis does not implement that behavior.
- It only reuses the same later swings against multiple creation events, which is not the same as a candidate state machine.

This model is not currently simulated by the research artifact.

# 12. Model C Simulation Status

Model C: Retire + New Candidate

Classification: NOT SIMULATED

Why:

- The repo does not define retirement, invalidation, or replacement semantics for a valid Zone.
- The analysis does not implement a retire-and-reset transition.
- It does not create a lawful state transition from “valid Zone” to “retired Zone” and then to “new candidate.”
- It only repeatedly evaluates later swings against earlier valid Zone creation events.

This model is not currently simulated by the research artifact.

# 13. Evidence Classification

The following statuses are supported by the repo evidence:

- Group B remains NOT FROZEN.
- Single-active-zone remains RESEARCH CANDIDATE ONLY.
- Non-member lifecycle remains UNRESOLVED.
- Phase 2 remains NOT STARTED.
- Production behavior remains unchanged.

The following evidence conclusions are valid:

- The reported counts are repeated evaluations per Zone-observation pair.
- A single historical swing can appear in the totals more than once.
- The current numbers are descriptive, not a lifecycle simulation.
- The artifact cannot legitimately support a direct lifecycle comparison across Model A, Model B, and Model C without an explicit and approved state-machine definition.

The following evidence conclusions are not valid:

- “dominated by non-member outcomes” as a direct lifecycle statement under a single defined counting unit
- “the historical sequence proves Model A/B/C superiority”
- any freeze of single-active-zone semantics or non-member lifecycle behavior

# 14. Corrections Required

The current research artifact needs the following corrections before any lifecycle comparison can be considered defensible:

1. State the counting unit explicitly.
   - The current counts are not unique-swing counts.
   - They are per Zone-observation pair counts.

2. Disclose repeated evaluation explicitly.
   - The same later swing is evaluated again for each valid Zone creation event.
   - This is the reason the totals exceed the number of eligible swings.

3. Remove any implication that the descriptive totals are a state-machine simulation.
   - They are not.

4. Replace any direct lifecycle conclusion with a guarded statement.
   - The current numbers are descriptive but not suitable for direct lifecycle comparison.

5. Preserve the governance boundary.
   - Group B remains NOT FROZEN.
   - Single-active-zone remains RESEARCH CANDIDATE ONLY.
   - Non-member lifecycle remains UNRESOLVED.

# 15. Governance Impact

The audited methodology does not support the following claims:

- that a single lifecycle pattern has been proven
- that any model is already equivalent to an approved behavior
- that the historical non-member fractions are a direct proxy for lifecycle correctness
- that a frozen state machine exists for the valid Zone after creation

The governance implication is narrow and explicit:

- Group B remains NOT FROZEN.
- Single-active-zone remains RESEARCH CANDIDATE ONLY.
- Non-member lifecycle remains UNRESOLVED.
- Phase 2 remains NOT STARTED.
- Production behavior remains unchanged.

This is not a repair of the original methodology. It is a statement of the actual evidence limits.

# 16. Final Audit Conclusion

The reported member/non-member totals exceed the number of eligible swings because the methodology counts the same later historical swings multiple times across multiple Zone creation events.

This is not a unique-swing count and not a valid state-machine simulation. It is a repeated-evaluation count over a per-Zone-creation loop.

The exact reason is:

- one historical swing can be evaluated again and again as a downstream observation against different Zone creation events
- one swing may be counted 27 times in HIGH and 22 times in LOW
- the totals therefore exceed the eligible-swing count by construction

The audit therefore concludes:

- the current numbers are descriptive but not suitable for direct lifecycle comparison
- the methodology does not simulate Model A, B, or C as an actual state machine
- the counts are per Zone-observation pair, not per unique historical swing
- the research asks a real governance question but does not answer it by counting repeated evaluations
- Group B remains NOT FROZEN, single-active-zone remains RESEARCH CANDIDATE ONLY, non-member lifecycle remains UNRESOLVED, Phase 2 remains NOT STARTED, and production behavior remains unchanged.
