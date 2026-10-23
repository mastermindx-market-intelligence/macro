---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: "01a11e89-b35d-7a81-9404-5fce2c6170cb / claude/ssd-prophet-plan-filter-return-1dd890c1c8dd5b14"
model: codex
ended_because: ci_handoff
mission: >-
  Finish the four-market Daily Desk, advancing the Paper-assessed candidate to
  native Plan return and truthful initial-failure behavior while prior releases publish.
state_before: >-
  On the authenticated production board, a PG candidate linked to the native
  PG-BULL-20260914 record while the Plans filter remained resolved. The entered
  target stayed display:none, focus was empty, but the handler reported ok.
  Protected board transport and malformed-payload errors also retained the
  preview silently. Work begins from main 3c9dcfcfd0224c56e564110be44853f92e9cb1e1.
changed:
  - path: templates/dashboard.html.j2
    what: Selects the exact native Plan record's published lifecycle through the existing lifecycle owner before scrolling and focusing; adds a bilingual polite unavailable notice for non-access protected-load failures.
  - path: tests/test_prophet_plan_relation.py
    what: Executes actual lifecycle/navigation scripts to prove exact target, current grid, URL and focus behavior with rejection controls.
  - path: tests/test_us_board_hydration_merge.py
    what: Executes the actual protected loader for 14 failure/access/success scenarios; repairs an inherited brittle shipped-grid selector while retaining population/order assertions and adding three isolation/refusal cases.
prs: [8798, 8762, 8444]
verified:
  - claim: The navigation defect was reproduced on the actual authenticated production page.
    command: IAB Plans resolved filter to Screener PG setup detail to Evidence and source details to View in Plans using Enter; inspect the target DOM and URL.
    result: PG-BULL-20260914 entered target remained hidden, focus empty, life=resolved and result=ok. Evidence plan-filter-live-red-20261011.json is retained outside Git; this is production RED, not repair GREEN.
  - claim: The Plan delta corrects the exact-target behavior locally without ticker substitution.
    command: Run retained plan-filter-return-20261011/browser-proof.py and pytest tests/test_prophet_plan_relation.py -k view_in_plans; independent hydrated-grid Node probe.
    result: Original browser RED followed by repaired Chromium visibility/focus/keyboard return GREEN; six independent tests pass. Five invalid/missing/withheld controls refuse; unrelated URL query and same-ticker sibling are preserved.
  - claim: The actual protected loader distinguishes unavailable service from access denial.
    command: python -m pytest tests/test_us_board_hydration_merge.py -k availability -q; independent Chromium controlled HTTP 500 matrix.
    result: Ten RED failures before repair, then fourteen behavior scenarios pass. Network, 500, malformed JSON and invalid envelope disclose missing full data; 401/403 retain access behavior; successful hydration clears only its own notice. EN/ZH, dark/light, desktop1440/mobile390 and all source tabs remain visible without overflow.
  - claim: The inherited shipped-grid selector is corrected without weakening the original merge assertions.
    command: python -m pytest tests/test_us_board_hydration_merge.py -k grid_inner -q before repair; python -m pytest tests/test_us_board_hydration_merge.py -q after repair.
    result: Three exact-grid/nested-card/decoy/missing/incomplete cases fail before repair; all 28 hydration tests pass afterwards, including the original shipped shell plus protected payload count and ordered-heading assertions.
  - claim: The nearby source checks passed apart from the selector subsequently repaired.
    command: python -m pytest tests/test_us_board_hydration_merge.py tests/test_prophet_plan_relation.py tests/test_dashboard_template_render.py tests/test_p_mp1_shell_ladder_filter_css.py -q after canonical mockups/site hydration.
    result: 115 passed, zero skipped and one inherited selector failure; the full affected 28-test hydration suite then passed after the selector repair. Counts overlap.
  - claim: The source changes pass mechanical presentation controls.
    command: python scripts/check_design_system.py --mode enforce-added --diff-file /private/tmp/prophet-consumer-final.diff; python scripts/check_ui_visual_evidence.py --diff-file /private/tmp/prophet-consumer-final.diff; python scripts/check_runtime_style_injection.py; git diff --check.
    result: Zero added design blocking findings; visual evidence guard passes; runtime allowance remains 212 JavaScript files, 44 injecting files and 89 hits. No added style system.
  - claim: Separate completed native reviewers accepted the Plan and availability source deltas within their scopes.
    command: Existing original-parent native returns from p1a_access_delta_review and p1a_rebuild_path; match full source and isolated script hashes.
    result: Both scoped accepts. The initial missing Plotly concern was withdrawn because the pre-existing helper already imports the same environment. These are native return acceptances, not fabricated Fabric process/usage/lease receipts.
unverified:
  - claim: This change has passed hosted CI or shipped.
    what_would_verify: Publish the exact source head, consume normal current-head semantic evidence, merge through protected checks, verify generated-site commit and authenticated served behavior.
  - claim: B03 and entry-copy are now visible on production.
    what_would_verify: Existing automatic render38137488198 at entry-copy merge866bb4987d2a0b60af5312fef591052323cfdf3b must produce and serve a generation, then complete the authenticated B03 and bilingual mixed Buy/Near checks.
unresolved:
  - B03 source8762 and entry-copy8798 are normally merged; production evidence remains open. GitHub normal pending-render replacement cancelled38133349439 in favor of38137488198; no manual cancellation or duplicate dispatch.
  - The unrelated HK byte-pin test remains inherited at this base; both its template and assertion are unchanged by this work. Evidence hk-inherited-pin-proof.json is retained.
  - P1a8444 integration refusal6029541334 and DailyBrief8249 source-edit refusal5924461491 remain binding. This current-main consumer change does not adopt or transfer either effect.
next_actions:
  - Publish this reviewed consumer repair, consume its actual hosted CI, and complete normal expected-head release plus authenticated target/failure-path proof.
  - Continue the one existing observer for the current combined renderer and B03/entry-copy production acceptance; do not poll consumed CI or mint another observer.
  - Preserve source populations, exact Plan identity, separate source clocks, and held regional/scientific dependencies while progressing permitted product work.
do_not_redo:
  - Human B03 visual approval and the Studio Paper assessment are consumed; do not request them again.
  - B04/B06 releases, old M2 failures, accepted P1a scoped reviews and missing historical cache diagnosis are closed.
  - Do not treat fixture/local browser proof or a source merge as authenticated production GREEN.
danger_areas:
  - Model Plans are not holdings or fills. A same-security relation is not an exact candidate Plan relation.
  - Preserve the existing entitlement wall and generated-artifact security assertion; the P1a public identity leak is a separate open obligation.
  - The unavailable notice reports missing full data while preserving the dated preview. It does not assert current market freshness or manufacture a replacement payload.
---

Paper reference: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-1-0.
The existing programme checkpoint remains Macro6817 comment6107291350. All local
proof is under /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89.
The source status paragraph uses the existing muted material and bilingual helper;
no new design language, rank, producer, clock, Plan identity or authority is added.
