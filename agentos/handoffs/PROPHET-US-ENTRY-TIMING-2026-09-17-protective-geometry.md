---
workstream: WS:PROPHET-US-ENTRY-TIMING
session: claude/prophet-protective-geometry-20260917
model: sol
ended_because: ci_handoff
mission: >
  Refuse newly originated plans whose existing protective invalidation contradicts
  their entry or explicit waiting band, while retaining valid geometry, identities,
  unavailable-data semantics and complete candidate accounting.
state_before: >
  The real recovery build produced three bullish plans immediately marked invalidated.
  Its schema and intake checks passed because abs(entry-stop) concealed the wrong side.
  The original reserved checkout was incomplete and had not produced a commit or PR.
changed:
  - path: engine/prophet_bridge.py
    what: Validate consumed numeric inputs, signed risk, published rounded levels and the existing waiting zone; use the existing geometry refusal path.
  - path: tests/test_prophet_bridge.py
    what: Add loss-side, numeric, rounding, zone and actual-shape accounting regressions; preserve the registered suite.
verified:
  - claim: Existing consumers and the new geometry cases pass.
    command: python -m pytest -q tests/test_prophet_bridge.py tests/test_prophet_arena.py tests/test_prophet_integrity.py tests/test_prophet_arena_clock_parity.py
    result: 279 passed after 36 initial intended failures; three forbidden boundaries have discriminating mutation coverage.
  - claim: The full saved real board loses only the three contradictory plans.
    command: python -c "import json; print(json.load(open('research/us_prophet_availability/2026-09-17-protective-geometry/actual-board-receipt.json')))"
    result: 42 input rows, 26 survivors, 23 preimage versus 20 repaired plan objects; exactly HON/RBA/TRN refused, all20 shared objects unchanged, lossless and zero unaccounted.
unverified:
  - claim: The new protection is deployed and the public US board is current.
    what_would_verify: Exact-head independent review and CI, accepted integration, one canonical publication, and real candidate/plan/history/premium/browser proof.
unresolved:
  - Geometry source review and full release checks remain required; source-author verification is not independent approval.
  - The separate T2/section7 chronology relation must be reconciled across origination and correction readers, not waived by this patch.
  - Other recovery branches retain their incumbent writers and review/adoption gates.
next_actions:
  - Review the exact same-carrier geometry source and current integration; release its hold only after all blockers and binding checks conclude.
  - Coordinate the shared bridge file with the separate chronology owner, then prove the integrated production journey through one publisher.
do_not_redo:
  - Do not create another geometry operation or repeat the repaired checkout recovery.
  - Do not refetch the preserved full archive or rerun the entire stock-library build just to test these exact rows.
  - Do not clamp dates, substitute stops, rewrite old plans, widen trade policy or impersonate an independent reviewer.
danger_areas:
  - abs(entry-stop) is not a signed safety check; hidden precision is not published precision.
  - A stop valid at spot may already invalidate a lower waiting fill.
  - A schema/accounting pass cannot replace a usable-plan proof.
prs: [7180, 7200, 7206, 7187]
discoveries: [DSC:PROPHET-ABS-RISK-CAN-HIDE-BREACHED-PROTECTION]
---

Operation `prophet-protective-geometry-20260917-sol-001` continues the original Sol-owned direct carrier announced in #7180 comment5709761833; resumed under live Chairman continuation at comment5710669894. Procedure pin `Mastermind@42d210bc07a75234092ff5be71f6038ccacaa884`; base `8b688809239d760be0cdcf8cd64f0d6f7ee05316`; semantic repair `6af030bdd7777901b00c170d4014a168cf787731`. Reason: CRITICAL_PATH_SHORTCUT / PRINCIPAL_JUDGMENT. No separately admitted worker was replaced and no lifecycle plane was invented.

The zero-byte orphaned lock and final incomplete source file were preserved as local proof before the original index/missing-file preparation was repaired. The checkout was clean before feature edits. This supersedes the old "no index / no published repair" state, not other workers' source custody. Private proof files are under Studio `~/.cache/mastermind-proof/prophet-protective-geometry-20260917-sol-001/`.

This handoff has no merge, provider activation, worker binding, protocol activation or production authority. Runtime lifecycle remains Executive OS-owned; organizational continuity lives here; GitHub is the source/review carrier. Source custody stays with this direct operation until an explicit accepted handback. Capability is BUILT_NOT_PROVEN, parent availability remains active.


Final consumer verification adds the existing stretched-reset tests: 282 passed. Two intended-valid test fixtures now place their artificial stop below the waiting band; a new negative case retains the old contradictory geometry and requires refusal. The broader eight-suite diagnostic had four failures also reproduced with the exact preimage bridge (two missing sparse artifacts, earnings horizon expectation, management wording expectation) and 27 existing artifact-dependent skips. No full-repository green claim is made. Exact scopes/results are committed with the evidence.
