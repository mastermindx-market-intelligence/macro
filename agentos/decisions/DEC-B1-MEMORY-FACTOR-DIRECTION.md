---
key: B1-MEMORY-FACTOR-DIRECTION
question: >
  In the B1 matched-memory event panel (grain vs memory test of the served RSI-MACD
  cascade), which direction does the exponent k in alpha_k = 1 - (1 - alpha)^k move the
  smoother's memory, and which constants make a 1D-grain smoother carry the same memory in
  sessions as a 3D-grain one?
answer: >
  k > 1 SHORTENS memory. The per-session decay of a 3D EMA is (1 - alpha)^(1/3), so the
  1D smoother matched to a 3D one uses k = 1/3, and the 3D smoother matched to 1D uses
  k = 3. Binding constants from 2026-10-04: 1D.M2 k = 1/2, 1D.M3 k = 1/3, 3D.K1 k = 3.
  The chapter-03 masterplan section 5.2 and packets/B1.spec.txt carried k = 2, 3, 1/3 (inverted);
  the round-0 panel was built under that spec and is superseded by the round-1 panel.
rationale: >
  The Opus review of B1 round 0 (finding D1) measured the EMA60 half-lives directly:
  1D 20.8 sessions, 3D 62.4 sessions, round-0 1D.M3 (k = 3) 6.9 sessions (anti-matched),
  round-0 3D.K1 (k = 1/3) about 187 sessions. The round-0 event counts prove the same
  thing without arithmetic: 1D.M3 fired 901,511 events against 1D's 338,340, and a
  longer-memory smoother fires LESS, not more. Under the inverted constants the
  "memory, not grain" arm of the hypothesis tests a different hypothesis (shorter
  memory on the 1D grain), which would make the section-7 product row uninterpretable.
alternatives:
  - option: "Keep the round-0 constants and relabel the variants as shorter-memory arms"
    why_not: >
      The pre-registered question is grain vs memory at MATCHED memory in sessions. A
      shorter-memory arm cannot answer it, and relabelling after seeing results is the
      rescue the evaluation contract forbids.
  - option: "Drop the two-session arm (1D.M2) and keep only the exact match (1D.M3)"
    why_not: >
      1D.M2 is the cheapest dose-response point between 1D and the matched memory; it
      costs one extra variant and keeps the kernel-memory curve readable.
evidence:
  - "results/B1/code/cascade_lib.py:18-21 implements alpha_k = 1 - (1 - alpha)^k (formula unchanged; constants amended)"
  - "Opus review of B1 round 0, finding D1: half-lives 20.8 / 62.4 / 6.9 / ~187 sessions; event counts 1D.M3 901,511 vs 1D 338,340"
  - "scratch packet pkts/B1_r1.txt lines 57-59 (amended VARIANTS block) plus the SPEC AMENDMENT paragraph of the repair block"
  - "packets/B1.spec.txt and 03_RESEARCH_AND_PRODUCT_MASTERPLAN.md section 5.2 amended with a dated note in the W1 results PR"
affects:
  - "WS:PROPHET-REGIME-TIMEFRAME-RESEARCH"
  - "research/prophet_v4/astra_regime_indicator_handoff_20261004/**"
confidence: high
reversibility: easy
decided_by: "coo-fable seat (Claude Code session f273dd7d), ruling on the Opus reviewer's D1 finding"
decided_at: 2026-10-04
---

# B1 memory factor: k > 1 shortens memory; matched constants are 1/2, 1/3, 3

The inverted constants were an authoring error in the frozen wave-1 design, caught by the
adversarial review of the round-0 panel before any number from it was read as evidence.
The round-1 panel regenerates every table under the amended constants; the round-0
verdict ("NOT SUPPORTED" on the 3D grain effect) is reported only as the round-0 result
and carries no weight in the C2 adjudication.
