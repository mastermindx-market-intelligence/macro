---
workstream: "WS:GREY-DEER-RISK-INTELLIGENCE"
session: "claude/risk-radar-parity-rerun-20260921"
model: sol
ended_because: context_budget
mission: >-
  Recover truthful US Risk Radar research after the historical replay was proven
  not to match the shipped live escalation state machine, and preserve the
  corrected scientific frontier without changing live model authority.
state_before: >-
  PR #7632 had proven and repaired replay/live transition parity. Pre-parity
  warning-path, gate-latency, caution-persistence, and state-ladder evidence was
  materially invalidated for state/probability/gate decisions.
changed:
  - path: research/grey_deer/RISK_RADAR_REPLAY_PARITY_RERUN_PREREG_2026-09-21.md
    what: Froze a no-retune rerun protocol before corrected outcome inspection.
  - path: reports/risk_radar_episode_atlas.json
    what: Regenerated fixed historical warning paths with exact live transition semantics.
  - path: research/grey_deer/evidence/gate-latency-20260921/result.json
    what: Regenerated gate selectivity/latency on the corrected raw state path.
  - path: research/grey_deer/evidence/caution-persistence-20260921/result.json
    what: Regenerated five-session persistence from corrected gated states.
  - path: research/grey_deer/evidence/state-ladder-calibration-20260921/result.json
    what: Regenerated H5/H10/H21 state buckets and uncertainty from corrected replay.
verified:
  - claim: Rerun targets/settings were frozen before corrected outcomes.
    command: "git show e9ff3d234df1f50137bfa38a50995a70f06c1164"
    result: "Protocol commit precedes corrected study execution."
  - claim: Corrected modern state ladder is point-monotonic at H5/H10/H21.
    command: "Read state-ladder result.json y2020 cells."
    result: "H21 calm/watch/caution/elevated/risk-off = 0.0/4.6/16.5/30.3/43.8%; elevated n=33 remains thin."
  - claim: Broad-market gate conclusion survives corrected replay.
    command: "Read gate-latency result.json since_2020."
    result: "Gated H21 precision 42.0%, recall 36.7%, fire-rate 15.4%; median latency 3 sessions."
  - claim: Five-session caution persistence is not a sparse alert.
    command: "Read caution-persistence result.json since_2020."
    result: "Event rate 24.0%, lift 1.36x, recall 93.5%, fire-rate 68.8%."
unverified:
  - claim: The complete displayed probability surface is calibrated.
    what_would_verify: >-
      Separately preregister state-plus-conjunction probability bins under the
      corrected replay, report calibration/error and uncertainty, and keep issued
      forecast evidence distinct.
  - claim: Any reconstructed result authorizes a live probability retune.
    what_would_verify: >-
      Accepted candidate study plus promotion evidence and applicable authority gates.
unresolved:
  - "Modern elevated is directionally restored but thin (n=33); precise probability confidence remains low."
  - "Full-history calm/watch and elevated/risk-off adjacent cells are not cleanly separated."
  - "SVB fixed-episode persistence weakened materially; prior 10-session into-T0 caution streak was stale replay evidence."
next_actions:
  - "Finish corrected receipts/tests/Agent OS validation and publish the parity-rerun evidence PR."
  - "Then preregister and evaluate the complete displayed probability surface: state + existing conjunction count; no fitting in the diagnostic wave."
  - "Only after corrected evidence should any Risk Radar UI evidence-depth cue be built; do not create another prominent warning badge."
do_not_redo:
  - "PR #7632 replay/live parity repair is accepted and merged."
  - "PR #7608 pre-parity persistence result is superseded, not a live alert license."
  - "Closed #7611 pre-parity state-ladder result must not be revived or merged."
  - "Recorded issued-probability audit remains a separate evidence class and is not invalidated by replay parity."
danger_areas:
  - "Daily forward windows overlap; do not call them independent events."
  - "Thin elevated cells cannot support precise probability claims."
  - "Do not mix reconstructed historical states with genuinely issued forecast history."
prs: [7586, 7599, 7608, 7611, 7632]
---

# Post-parity Risk Radar research continuation

Protected source at rerun start: Mastermind `4ca1b97e65de9d4ba8c868b9d708fb7620a8a76f`,
Skillpack 1.0.1/bootstrap1. Corrected evaluator source base:
`7c6e35163c9f67087ffe174a7ab3810f47ce6a45`.

The corrected rerun changes research truth, not live market/risk authority. The next
scientific frontier is the full displayed probability surface under exact production
state semantics.
