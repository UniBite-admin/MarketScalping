# Group B Human Decision Request

## Status

FROZEN — HUMAN APPROVED

The two requested human decisions have now been resolved and recorded as human-approved Group B tolerance-history decisions.

## 1. Decision context

### Already supported

- Group A swing semantics are frozen.
- The 15-minute bar contract is frozen.
- HIGH and LOW swing streams are separate.
- Legal prior same-direction absolute gaps are the current supported tolerance input.
- The current swing is excluded from its own tolerance calculation.
- Median is the strongest supported statistic.
- Fixed-count rolling history is the strongest supported memory architecture.

### Not yet decided

- exact fixed-count rolling history length W
- minimum-history behavior

---

## 2. Decision 1 — W

The current supported mathematical architecture is:

`T_i(W) = median(last W legal prior same-direction absolute gaps)`

where:

- W is a count of prior legal gaps, not bars
- W is not elapsed time
- W is not a zone-count target
- the history used for evaluation contains only legal same-direction observations strictly prior to the current evaluation
- the current swing does not contribute to the tolerance used to evaluate itself

### HUMAN DECISION REQUIRED

Existing evidence does not uniquely determine a specific W.

The human must explicitly choose one of the following:

- approve a specific fixed W
- request a separately defined deterministic data-derived W rule
- request another explicitly scoped research task

This decision matters because W controls:

- adaptation speed
- tolerance stability
- outlier response
- structural memory
- reproducibility
- downstream zone membership behavior

A numeric W cannot be chosen merely because it produces a more attractive clustering result or better downstream metrics. That would be parameter selection by outcome, not evidence-based governance.

---

## 3. Decision 2 — minimum history

The unresolved question is precise:

At evaluation of a swing, there may be:

- 0 prior legal gaps
- 1 prior legal gap
- 2 prior legal gaps
- ...
- fewer than W prior gaps
- at least W prior gaps

The current evidence does not uniquely establish whether the rule should be:

### Option A

Use all available prior legal gaps until W is reached.

### Option B

Do not produce a tolerance until W prior legal gaps exist.

The existing research documents do not support a third policy without additional scoped research.

### Important distinction

`Mathematical definability does not establish statistical adequacy.`

A median of one value is mathematically defined, but that does not automatically mean that a one-gap tolerance is statistically adequate for a stable decision rule. Likewise, requiring W observations may be statistically conservative, but it may also impose an arbitrary gate if the evidence does not justify it.

The evidence supports the need for a rule, but not a uniquely justified threshold or policy.

---

## 4. What is not being decided

This human decision does NOT decide:

- zone membership distance
- cluster creation
- zone center
- zone geometry
- overlap handling
- zone identity
- zone lifecycle
- Phase 2
- strategy behavior
- trading profitability

Those remain separate decisions.

---

## 5. Governance effect

Once the human approves W and minimum-history behavior:

- the decision must be recorded in authoritative Phase 1 artifacts
- the decision becomes frozen for Group B unless explicitly changed through the project’s change-control process
- later backtest results must not silently change W
- later strategy performance must not be used to retroactively tune W
- any future change requires explicit human approval and appropriate validation

---

## 6. Human response format

### Decision 1 — W

`APPROVED W = ______`

or

`REQUEST DATA-DERIVED W RULE`

or

`REQUEST ADDITIONAL SCOPED RESEARCH`

### Decision 2 — Minimum History

`OPTION A — USE AVAILABLE HISTORY UNTIL W`

or

`OPTION B — REQUIRE W PRIOR GAPS`

or

`REQUEST ADDITIONAL SCOPED RESEARCH`

---

## 7. Required status

- Group A: FROZEN / HUMAN APPROVED
- 15-minute bar contract: FROZEN / HUMAN APPROVED
- Group B: NOT FROZEN
- W: HUMAN DECISION REQUIRED
- Minimum-history policy: HUMAN DECISION REQUIRED
- Production implementation: UNCHANGED
- Production tests: UNCHANGED
- Phase 2: NOT STARTED
