# Phase 1 — Zone Formation Group B Calibration Audit

## 1. Objective

PROVEN

This audit tests the smallest meaningful architectural question for Group B: whether the mixed tolerance family

    distance <= max(A, r * reference_price)

can be calibrated in a structurally meaningful way without adding unnecessary complexity.

This is not a parameter-picking exercise. It is a calibration audit for the abstraction itself.

The central issue is not whether the family is invalid. The issue is whether the calibration method is informative or whether static A/r values are often merely inactive because A dominates the max() expression across the observed price range.

## 2. Authoritative Inputs

PROVEN

The following are treated as the authoritative inputs for this audit:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_PROPOSAL.md](GROUP_B_PROPOSAL.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
- [tools/research/research_15m_groupb_output.json](../../tools/research/research_15m_groupb_output.json)

This audit preserves all of the following:

- Group A remains frozen and human-approved.
- Group B remains not frozen.
- The 15-minute bar reconstruction remains a research proposal.
- The OHLC reconstruction contract remains a research proposal.
- No exact tolerance value is frozen.
- No production strategy behavior is changed.
- No Phase 2 work starts.

## 3. Reproduced Evidence

PROVEN

The research implementation reconstructs 15-minute bars from the canonical event stream and then identifies same-direction swing highs and swing lows. The same dataset and same researched semantic assumptions were reused for this audit.

The observed swing-price distribution in the current research data is:

- swing highs price range: approximately 5,749 to 11,892
- swing lows price range: approximately 5,681 to 11,803
- combined swings price range: approximately 5,681 to 11,892

This matters because the effective tolerance under the mixed family is:

    effective_tolerance = max(A, r * price)

so the observed price scale determines whether A or r controls the rule.

The existing research already established that the family is structurally workable but does not yet demonstrate a strongly stable static parameter region.

## 4. A-Dominant / Transition / r-Dominant Analysis

PROVEN

For the mixed family, the relevant question is whether the max() expression is dominated by A or by r * price over the observed swing-price range.

For representative candidate pairs already used in the existing research, the effective tolerance behaves as follows:

- A = 20, r = 1e-4
  - relative component is 5.68 to 11.89
  - absolute component is 20
  - A dominates over the full observed price range
  - effective tolerance is constant at 20
  - result: A-dominant, not meaningfully r-controlled

- A = 20, r = 2e-3
  - relative component is 11.36 to 23.78
  - A dominates for most of the range, but r begins to contribute near the upper end of the observed price range
  - result: mixed A-dominant / transition behavior

- A = 50, r = 1e-4
  - relative component is 5.68 to 11.89
  - A dominates completely
  - effective tolerance is constant at 50
  - result: A-dominant

- A = 50, r = 2e-3
  - relative component is 11.36 to 23.78
  - A dominates completely over the observed range
  - result: A-dominant

- A = 100, r = 1e-4
  - A dominates completely
  - effective tolerance is constant at 100
  - result: A-dominant

This is the crucial evidence: many of the tested mixed-family points are not meaningfully varying in their effective tolerance. They appear stable only because the absolute floor is active and the relative term is being ignored.

The observed dominance pattern for the actual swing-price data is:

- For A = 20 and r = 1e-4, 100% of observed prices are A-dominant.
- For A = 20 and r = 2e-3, approximately 82.9% of combined swings are A-dominant, 15.1% are r-dominant, and 2.1% sit at the transition equality boundary.
- For A = 50 and r = 2e-3, the effective tolerance remains A-dominant across the full observed swing range.
- For A = 100 and r = 5e-4, the effective tolerance remains A-dominant across the full observed price range.

This means the previous 100% agreement results are not true stability evidence. They are often parameter inactivity evidence.

Descriptive reporting convention used here:

- A-dominant: A > r * price
- transition: A = r * price
- r-dominant: r * price > A

This is a reporting convention only, not a project rule.

## 5. Chronological Stability Analysis

EXPERIMENTAL EVIDENCE

A simple chronological check was performed by splitting the observed swing sequence into first-half and second-half segments without assigning any market regime labels.

The dominance structure remained broadly similar across both halves, but it was not identical:

- For A = 20 and r = 2e-3,
  - first-half combined swings: about 82.2% A-dominant, 15.1% r-dominant, 2.7% transition
  - second-half combined swings: about 83.6% A-dominant, 15.1% r-dominant, 1.4% transition

- For A = 20 and r = 1e-4,
  - both halves remain 100% A-dominant, meaning r is inactive throughout

This does not show a market regime effect. It shows that the same structural issue persists across time: A often dominates, and the effective tolerance is mostly a fixed floor rather than an informative dynamic scaling parameter.

The absence of a clear chronological drift in the dominance pattern is useful, but it does not prove that a static A/r pair is the right abstraction.

## 6. Structural Interpretation of A and r

PROVEN

The actual data suggests the following interpretation:

- A behaves primarily as a floor.
- r behaves primarily as a price-scaling component.
- The max() construction creates a useful guardrail against vanishing tolerance at low price levels.
- But over the observed BTC-EUR price range, A often dominates, so r contributes little or nothing to effective tolerance.

In practical terms, the mixed family often behaves like a fixed absolute tolerance with occasional transitions rather than a genuinely two-parameter calibration surface.

This is a strong reason to separate two questions:

- Is the family structurally sensible on paper?
- Is a static A/r calibration meaningfully informative in the actual market scale?

The answer to the second question is weaker than the first.

## 7. Simple Calibration Candidates

PROPOSED

The project should not jump to adaptive or learning-based methods. The current evidence supports only simple, deterministic, replayable alternatives that are structurally explainable.

Candidate 1: distribution-derived distance statistic
- deterministic: yes
- causal: yes
- replayable: yes
- easy to test: yes
- additional state: no
- risk of overfitting: moderate if derived from a narrow sample
- compatibility with Phase 1 simplicity principle: strong

Candidate 2: percentile-derived distance statistic
- deterministic: yes
- causal: yes
- replayable: yes
- easy to test: yes
- additional state: no
- risk of overfitting: moderate but lower than an adaptive method
- compatibility with Phase 1 simplicity principle: strong

Candidate 3: median or robust spread-derived distance
- deterministic: yes
- causal: yes
- replayable: yes
- easy to test: yes
- additional state: no
- risk of overfitting: low if robust and market-local
- compatibility with Phase 1 simplicity principle: strong

Candidate 4: simple price-normalized statistic
- deterministic: yes
- causal: yes
- replayable: yes
- easy to test: yes
- additional state: no
- risk of overfitting: low if bounded and explicit
- compatibility with Phase 1 simplicity principle: moderate to strong

These are all more structurally meaningful than arbitrary fixed A/r values when the current evidence shows that A is often dominating the rule.

## 8. Causality / Anti-Lookahead Assessment

PROVEN

Any calibration method must be evaluated on whether the required information is available at the time the zone is created.

The following distinction is required:

- research-only descriptive calibration: uses the full sample to understand the distribution and may be useful for research but not for production implementation
- causal production calibration: must use only information available as of the current replay point

The mixed family itself is replayable and causal if the parameters are chosen before runtime and fixed. However, a full-sample percentile or distribution-derived statistic is not causal if it is computed from the entire dataset before the zone is created.

Therefore:

- arbitrary fixed A/r values are replayable and causal
- full-sample research stats are useful for research but not a production calibration method unless they are re-expressed as a causal, time-local rule

This distinction is essential.

## 9. Evidence Classification

PROVEN / EXPERIMENTAL EVIDENCE / PROPOSED / UNKNOWN

PROVEN
- The mixed family is structurally sensible and deterministic.
- A often dominates the observed price range, creating parameter inactivity.
- The static A/r surface does not reliably produce independent control over clustering.

EXPERIMENTAL EVIDENCE
- The transition boundary is real and appears in the mixed surface.
- The family behaves like a floor-driven system more often than a two-parameter scaling system.

PROPOSED
- A structural calibration method derived from robust market-local statistics is a reasonable next-step research direction.
- A simple deterministic rule based on observed swing spacing remains more defensible than a fixed static A/r pair if the pair is often inactive.

UNKNOWN
- Whether a simple robust calibration statistic can be made causal and replayable without hidden complexity.
- Whether the same calibration rule generalizes cleanly across other assets.

REQUIRES HUMAN APPROVAL
- Any decision to move from fixed A/r toward a more structural calibration abstraction should be explicitly reviewed by the human before it becomes a frozen Phase 1 decision.

## 10. Architectural Decision

PROPOSED

B. KEEP MIXED FAMILY WITH STRUCTURAL CALIBRATION

This is the best-supported architectural decision from the current evidence.

Reasoning:

- The mixed family remains a sensible structural abstraction for Zone Formation.
- The evidence does not support trusting a static A/r pair as the final calibration abstraction.
- The present issue is not that the family is invalid, but that its calibration method is too blunt and often inactive.
- A more structurally derived calibration rule remains more consistent with the project’s principle of simple before complex.

This is not evidence for moving to a complex adaptive method. It is evidence for changing the calibration method while keeping the family.

## 11. Remaining Unknowns

UNKNOWN

The remaining unknowns are narrow and specific:

- whether a simple robust statistic can be expressed as a causal,replayable tolerance rule without future data
- whether the resulting rule is stable across chronological segments without being overfit
- whether the rule remains practical when the asset price scale changes materially
- whether a market-local or market-agnostic formulation is preferable

These are the only questions that remain open at this stage.

## 12. Governance Status

PROVEN

- Group A remains FROZEN.
- Group B remains NOT FROZEN.
- No exact tolerance was frozen.
- No timeframe was frozen.
- No OHLC contract was frozen.
- No new clustering rule was frozen.
- No Phase 2 work started.
- No production strategy behavior changed.
- No profitability optimization was used.
- No look-ahead was introduced.

This audit is an architectural calibration review only.

## 13. Safety Check

PROVEN

The following safety conditions remain satisfied:

- Group A remains FROZEN.
- Group B remains NOT FROZEN.
- No exact tolerance was frozen.
- No timeframe was frozen.
- No OHLC contract was frozen.
- No production strategy behavior changed.
- No Phase 2 work started.
- No profitability optimization was used.
- No look-ahead was introduced.

No production modules were modified. No executable trading logic was changed. No freezing of any new decision was performed.
