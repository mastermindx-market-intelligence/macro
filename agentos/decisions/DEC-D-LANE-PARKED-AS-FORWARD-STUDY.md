---
key: D-LANE-PARKED-AS-FORWARD-STUDY
question: >
  Can lane D (theme-conditioned Prophet analysis: does leading-theme membership change
  the entry or management edge of the served signals) run as a retrospective study on the
  2014-2026 event panel, or must it be parked?
answer: >
  PARKED as a retrospective study; converted to a pre-registered FORWARD study. Lane D0's
  point-in-time census (accepted at round 1 on its numbers, token PIT_PARTIAL) shows that
  honest leading-theme membership exists only from 2026-08-13 (any-theme membership from
  2026-07-05), that honest coverage for 2014-2025 is zero, and that the pre-declared Q5
  floor (membership coverage >= 50% of the universe from D* onward) is never reached:
  any-theme coverage peaks at 35.95% and leading-restricted (dominant + emerging)
  coverage ranges 1.12%-11.83%. No authority override can cure a data-availability
  blocker, and no backfilled source may be graded as honest. The forward study
  pre-registers now: conditioning variable = leading-restricted membership as recorded at
  belief_time (never snapshot_date or asof alone); outcomes = the B1 event panel's
  excess_h10_net and excess_h21 for served Prophet events; verdict only after >= 26
  honest ISO weeks, >= 300 in-theme events, and membership KNOWN (in or out) for >= 50%
  of events in the window. That last clause is a seat amendment of the Q5 floor that
  applies to the forward study only: the original floor conflated "membership known"
  with "member", which a sparse conditioning variable can never satisfy. D0's verdict is
  not re-graded by this amendment.
rationale: >
  The honest window is 51-90 days (7.3-12.9 weeks) with five distinct honest membership
  dates in four ISO weeks and 29 honest leading-label dates across eight ISO weeks; no
  retrospective conditioning result on that window could satisfy the program's
  honest-N floors or the adjudication coverage gate (motivating exemplars span 2014-2026).
  Write-time honesty of the sources is proven by commit history (tree_history first
  committed 2026-07-05T06:50:58Z; membership_history committed on each snapshot date).
  Parking with a registered forward log keeps the question gradeable without fabricating
  history.
alternatives:
  - option: "Run lane D on the 2026-08-13 onward window now"
    why_not: "7-13 weeks and <= 12% in-theme coverage cannot clear any honest-N floor; a verdict would be noise with a label."
  - option: "Reconstruct 2014-2025 membership from the current theme tree (backfill)"
    why_not: "Survivor-selected and final-vintage by construction; the census classifies every such source BACKFILLED and the program forbids grading backfilled rows as honest."
  - option: "Lower the Q5 floor retroactively so D0 reads PIT_AVAILABLE"
    why_not: "Post-hoc gate editing; the amendment here is scoped to the forward study and leaves D0's token unchanged."
evidence:
  - "results/D0/RESULT.md and result.json (round 1, sha256 6ed2c879...): D* 2026-07-05, E* 2026-10-03, min 660/2595 on 07-05, max 933/2595 on 08-13, leading-restricted 29-307 names"
  - "Opus review of D0 round 1: all numbers reproduced; PIT_PARTIAL confirmed against spec Q5; commit SHAs b35bac058e, 00c7154781, 44c90f8f54, f960202b48, 297b3e6f16"
  - "scratch packet pkts/D0_r1.txt lines 1-73 (frozen D0 spec, Q5 floor)"
affects:
  - "WS:PROPHET-REGIME-TIMEFRAME-RESEARCH"
  - "research/prophet_v4/astra_regime_indicator_handoff_20261004/05_ACCEPTANCE_AND_CONTINUATION.md"
confidence: high
reversibility: easy
decided_by: "coo-fable seat (Claude Code session f273dd7d), ruling on the accepted D0 census numbers"
decided_at: 2026-10-04
---

# Lane D is parked as a retrospective study and registered as a forward study

The theme question stays open and gradeable. Nothing in this record builds a theme
score, promotes a theme signal, or alters the served product; it records that the
retrospective construction cannot be run honestly and names the exact conditions under
which the forward construction earns a verdict.
