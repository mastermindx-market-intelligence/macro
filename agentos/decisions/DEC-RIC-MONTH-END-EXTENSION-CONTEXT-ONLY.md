---
key: RIC-MONTH-END-EXTENSION-CONTEXT-ONLY
question: Does the confirmed month-end duration-extension family justify live rates-direction authority?
answer: No. Retain the effect as source-backed display/context and prospective-validation input only; do not add it to the RIC directional score.
rationale: >
  The predeclared direct-yield translation passed across DGS2/5/10/30 on 236
  complete 2007-Aug2026 month-ends. Headline DGS10 averaged -1.186bp
  (HAC t=-3.267, p=.0011, BH q=.0015), excess -1.242bp (t=-3.276), and both
  chronological halves were negative. Pre-ETF DGS10 context was also negative.
  However post-result current-relevance diagnostics show quarter-end months at
  +0.295bp (t=.502) and 2022-2026 at only -0.250bp (t=-.387). Those slices are
  post-selection and cannot become new rules, but they prevent treating the
  aggregate historical effect as a reliable current directional leg.
alternatives:
  - option: Add a generic month-end easing leg to the RIC hawk/ease score.
    why_not: Recent-era strength is weak and quarter-end months do not share the aggregate sign; forecast authority is unproven.
  - option: Promote only non-quarter month-ends.
    why_not: That subgroup was inspected after the primary result. Selecting it now would be post-result rule creation.
  - option: Discard the effect entirely because 2022-2026 is weak.
    why_not: The preregistered aggregate translated cleanly across all four Treasury tenors, matched the prior TLT/IEF/LQD price evidence, survived both chronological halves, and appears in pre-ETF DGS10 history.
  - option: Build a separate calendar/signal engine.
    why_not: engine.rebalance_calendar already owns the month-end session clock and the Rates & Inflation Command owns display context; a duplicate plane is unnecessary.
evidence:
  - research/rates_direction/MONTH_END_YIELD_EXTENSION_REPLICATION_V1.md
  - research/rates_direction/MONTH_END_YIELD_EXTENSION_REPLICATION_RESULTS_2026-09-24.md
  - research/rates_direction/month_end_yield_extension_replication_results_v1.json
  - research/rates_direction/month_end_yield_extension_replication_integrity_v1.json
  - research/rates_direction/month_end_yield_extension_replication_diagnostics_v1.json
  - "Freeze cfef07d2424a27604698c65eed03df3e0fe8c747; exactly 8 amendment configs appended to existing d2_rates_calendar_flows family."
affects: ["WS:RATES-INFLATION-COMMAND", "research/rates_direction/", "engine/rebalance_calendar.py"]
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-24
---

The product may show that month-end duration/rebalancing flow is a historical Treasury
context when the existing calendar owner says the session is month-end, provided the
copy remains display-only and preserves the current-regime/quarter-end uncertainty.
Prospective evidence is required before directional-score or equity-risk authority.
