---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: sector-focus-preserve-dossiers-20260923
model: sol
ended_because: ci_handoff
prs: []
mission: >
  Stop the focused Sector Intelligence publisher from erasing stock assessments
  on detail pages when it has not rebuilt their gitignored dossier inputs.
state_before: >
  Full-engine commit e77ddcedfe9f preserved eleven semiconductor assessments on
  the Sep21 detail; focused publish f8bc00fe1532 replaced them with zero while
  retaining the Sep21 date. The focused builder unconditionally ran stock detail
  generation and its workflow staged site/basket.
changed:
  - path: scripts/build_baskets.py
    what: Run the existing stock-detail pass only outside sector_intelligence_only mode.
  - path: .github/workflows/sector-intelligence.yml
    what: Remove only stock-detail pages from this focused lane's staged outputs; retain core sector outputs and freshness validation.
  - path: tests/test_sector_intelligence_page.py
    what: Add five native-boundary cases; retain broad behavior and strengthen exact publication ownership.
verified:
  - claim: New tests distinguish both dossier absence and stale host residue from legitimate detail-build authority.
    command: python3 -m pytest -q tests/test_sector_intelligence_page.py -k 'stock_detail or incidental_stale or stages_sector or broad_detail'
    result: Before correction three failed and two passed; after correction all five pass.
  - claim: Existing sector, gating and watchdog contracts remain intact.
    command: python3 -m pytest -q tests/test_sector_intelligence_page.py tests/test_sector_central_gate.py tests/test_nightly_liveness.py
    result: 150 passed on Python3.14; the 48-test sector-page suite also passes on Python3.12.
unverified:
  - claim: Hosted CI, independent review and deployed focused-run preservation.
    what_would_verify: Concluded source checks/review plus the existing publisher's next lawful run preserving full stock-detail inputs.
unresolved:
  - Already-erased assessments require a successor from the existing full stock-aware producer, not isolated old-score grafting or a private-data bypass.
next_actions:
  - Complete exact-head review and CI on this bounded source branch and release through the existing merge/publication owner.
  - Keep #7669 explanation/compiled-page repair separate; its source is untouched by this guard.
do_not_redo:
  - Do not redo the accepted #7211 merge or its successful Sector Central production proof.
  - Do not rerun, cancel or replace the currently queued engine-render owner merely to fill this gap.
  - Do not fetch protected stock intelligence through an unauthenticated alternate alias.
danger_areas:
  - Source-date equality alone did not detect loss of the stock-assessment population.
  - This prevents future overreach; it does not claim current missing assessments have been recovered.
---

Protected Skillpack: Mastermind@c18ea2ca779f042702a63a78bf1f10f5a1e0c0f6.
Source base: macro@d34993def9fa00e88c930f39a498b6ecad97455b.
Branch: sol/sector-focus-preserve-dossiers-20260923.
Current Chairman continuation covers the recommendation/source-quality mission.
Direct execution reason: CRITICAL_PATH_SHORTCUT; bounded producer ownership bug.
No score, rank, entry condition, private-data route, runner, queue or publisher is added.
Source finding returned to incumbent #7211 in comment5789637591.
MISSION_COMPLETE: false. Production acceptance is outstanding.
