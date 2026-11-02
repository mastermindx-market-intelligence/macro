---
workstream: WS:RATES-INFLATION-COMMAND
session: sol/web-macro-fed-forward-board-20261102-c3
model: sol
ended_because: ci_handoff
mission: Deliver the Chairman's Fed Path detail upgrade on the existing registered Macro route, with understandable drivers and contract-specific policy comparisons.
state_before: The deployed dialog drew a 12-month line and placed the current-year SEP dot in its final slot even when Rates Command withheld a policy comparison. Rates Command looked for D1 at a flat path while the bond producer wrote the monthly results under implied_source_meta.
changed:
  - path: engine/rates_inflation_command.py
    what: Use the native D1 pointer and the older flat format, carrying contract identity and its reference interval with each existing B0 result.
  - path: lib/fed_forward_board.py
    what: Select per-month evidence by source, cutoff, interval and units. An archived missing-D1 board can recover its original rows only from the exact pinned bond bytes.
  - path: templates/_fed_forward_board.html.j2
    what: Bilingual monthly pricing, weighted pressure, driver disclosures, source dates, prediction-market benchmarks and historical policy context in the existing dialog.
  - path: tests/fed_forward_board_browser.py
    what: Test the actual registered launcher using a local entitlement fixture in both themes, languages and viewport sizes.
verified:
  - claim: The October 20 committed artifact can recover fourteen monthly comparisons without rewriting that artifact.
    command: "git show HEAD:data/rates_command/latest.json, then fed_forward_board(saved_board, bond_file=Path('data/bonds/bond_health.json'))"
    result: "14 contracts, October 2026 to November 2027. Source cutoff October 21. A changed digest withholds the recovered rows."
  - claim: The render projection refuses unusable comparisons and preserves independent benchmarks.
    command: python3 -m pytest -q tests/test_fed_forward_board.py
    result: "18 focused cases cover rejected status, wrong component/rule/unit/pointer/cutoff, quotes after cutoff, non-finite values, duplicated months and an altered archived source."
  - claim: Browser checks on the real Macro template with the archived board exercise the sign-in boundary and the keyboard workflow.
    command: "tests.fed_forward_board_browser.check on the rendered dashboard.html.j2 using the archived board and pinned bond file"
    result: "8 of 8 desktop/mobile, light/dark and EN/ZH combinations passed. Each inspection table contained 14 contracts. Escape restored focus."
  - claim: The site builder produced macro.html and the registered launcher exposed the fully labelled per-month table.
    command: "scripts.build_site.main with optional edgar.enabled=false, then python3 tests/fed_forward_board_browser.py OUTPUT_DIR"
    result: "8 built-page browser checks and 8 degraded fixture checks passed. Captures and per-case evidence are in research/rates_inflation_command/forward_board_20261102."
  - claim: Fed Path, Rates Command, full dashboard template regressions and the new consumer checks pass.
    command: python3 -m pytest -q tests/test_fed_path.py tests/test_rates_command.py tests/test_dashboard_template_render.py tests/test_fed_forward_board.py
    result: "283 passed. The render ownership suite also passed all seven tests. The design-system added-line ratchet reported zero blocking findings."
unverified:
  - claim: Release approval and the deployed authenticated board.
    what_would_verify: Independent formal review of the exact candidate, required CI, a covering main render and a signed-in production check.
  - claim: Editable Paper artboards for this revision.
    what_would_verify: The enrolled Mastermind Paper app must accept its live schema, then allow guarded edit and screenshot readback of the intended target.
unresolved:
  - "Paper read MASTERMIND PAGES 01M2WGNCX9475G79JRKJTCM08P. The write schema was rejected: observed 16e6b93f, expected 1b9afff4. No Paper mutation was dispatched."
  - "The read-only Fabric contract audit macro-fed-forward-board-20261102-c3-contract-audit returned EFFECT_UNKNOWN on controller 82366, with unverified root. No result was consumed, no retry and no source custody for that worker."
next_actions:
  - Review the exact branch and the captured browser evidence. Reconcile any overlap with the separately owned Macro overview PR 10060 before release.
  - After independent review and required checks, the separate release owner verifies the served registered dialog and its actual data cutoffs.
do_not_redo:
  - Reuse D1/B0 monthly averages and matched differences. Never infer rate decisions from the 12m legacy headline or substitute SEP year-end for a rolling horizon.
  - Keep the existing dialog launcher, entitlement gate, pressure model and nightly ledger owners.
danger_areas:
  - A comparison for one ZQ contract supplies no SEP gap, meeting probability, or permission to connect another horizon.
  - The board as-of, source cutoff, prediction-market observation and policy briefing can have different dates.
---

The current session took responsibility for the Fed detail slice of the Rates & Inflation Command workstream. The October 14 program handoff continues to govern the wider program. The adjacent overview redesign and unrelated dashboard work retain their own branches.
