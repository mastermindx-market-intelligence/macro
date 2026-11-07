---
workstream: "WS:CHINA-ALPHA-INTELLIGENCE"
session: "sol/web-cn-prophet-peer-context-20261102-c3"
model: sol
ended_because: ci_handoff
mission: >-
  Link A-share Prophet setups with China Sector Central, measure broad participation and
  independent leadership, and qualify any future change in ordering.
state_before: >-
  The November 2 V4 publication used the V3 score for all 1,644 candidates. Two unmeasured
  raw-ineligible stocks disabled intelligence ordering. The published score included 15
  points of theme timing; its tooltip omitted this term.
changed:
  - path: research/cn_prophet_v4/SECTOR_PEER_CONTEXT.md
    what: "Scoped task tree, frozen replay design, US comparison, four input revisions and evidence gates."
  - path: engine/china_prophet_peer_context.py
    what: "Industry and curated-theme measurements, stock exclusion, dated cycle and risk context, distinct leader and decline interpretations."
  - path: scripts/build_china_library.py
    what: "Compute context for the complete scored population before board caps."
  - path: engine/china_prophet_shadow.py
    what: "Capture the observed receipt in the original candidate ledger under its keep-first rule."
  - path: templates/_cn_prophet_peer_context.html.j2
    what: "Featured-stock drilldown with denominators, benchmark, cycle, breadth change and coverage refusal."
prs: []
decisions: []
verified:
  - claim: "The exact incumbent featured set is reproducible across all four diagnostic publications."
    command: "python -m research.cn_prophet_v4.replay_sector_peers <commit from task tree>"
    result: "All 24 matched on October 9, 16, 23 and November 2. The fixed-cap variants replaced 1, 0, 0 and 2 slots."
  - claim: "The local candidate stock evidence is usable with a keyboard at phone and desktop widths."
    command: "Render the candidate board block using the pinned November 2 source and open with Playwright in clean headless Chrome."
    result: "At 390 and 1440 px, Enter opened the evidence, 24 rows were present, the first opened with 138/378 industry coverage, and the return link targeted Sector Central."
unverified:
  - claim: "Better net selection outcomes and production acceptance."
    what_would_verify: "Independent exact-head review, green hosted gates, released natural Asia close, served round trip and the prospective P5 comparison."
unresolved:
  - "Only ten of 24 featured names had sufficient peer breadth on November 2. The two missing original intelligence inputs are on the separate #6992 carrier."
next_actions:
  - "Complete independent source and CI review; verify the naturally published stock and sector pages and the first candidate-ledger receipt after deployment."
  - "Grade the frozen challenger against the same original cohorts at lawful entry and exit clocks through #8714 P5."
do_not_redo:
  - "Preserve R0 #6871, input parity #6992, the current order/gates, the immutable original ledger and earlier China Alpha milestones."
danger_areas:
  - "An ETF entry pulse, a curated theme score and a stock entry differ. A market-risk tone can coexist with a calm drawdown radar."
---
