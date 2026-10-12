---
workstream: WS:PROPHET-US-V4-RECOVERY
session: 01a11e89-b35d-7a81-9404-5fce2c6170cb
model: sol
ended_because: ci_handoff
prs:
- 8444
mission: Integrate original P1a with current main and repair actual public identity boundaries while preserving
  the four-market Daily Desk delivery chain.
state_before: The human explicitly reopened original P1a current-main integration. The original carrier
  contained accepted candidate-pool and cached-render repairs, but committed public bytes were stale and
  integration had not occurred.
changed:
- path: scripts/build_site.py
  what: Compose the existing board boundary with both candidate-pool and leader-observation previews.
    Each public projection remains a source-ordered prefix; protected hydration retains every withheld
    row. Preserve the existing protected company-label tail when only the identity boundary is active,
    even with panel caps disabled.
- path: templates/_prophet_coverage.html.j2
  what: Keep the imported bilingual macro and escape owner text before it creates markup, covering both
    autoescape modes without rendering literal span tags.
- path: tests/test_us_board_gate.py
  what: Retain original regressions, add production-call-path observation boundary cases and autoescape-on/off
    markup and hostile-text proof.
- path: .github/ci/legacy-jobs.yml
  what: Keep the P1a non-US compatibility suite on its existing code-gate job; declare seven concrete
    dependencies exposed by the unchanged import-closure check. Declare exact-tree ancestry for this
    owner job and bind the unchanged parity suite to the plan-pinned Git base before it runs.
- path: tests/test_ci_pack.py
  what: Exercise the actual owner setup and child environment against shallow Git fixtures, including
    isolated base replay and missing, malformed, absent-object and non-ancestor rejection.
- path: mockups/evidence/prophet-p0b-zero-fouc
  what: Regenerate actual composed fixtures and browser receipts, preserving historical baseline identity
    and refreshing only the repair extension.
- path: site/us_stocks.html
  what: Render from a fresh native builder VM through canonical access helpers. Pair with the actual protected
    us_stocks payload; keep unrelated generated outputs unstaged.
- path: mockups/evidence/prophet-p1a-coverage-20261012
  what: Bind the changed coverage partial to 16 existing actual dual-theme bilingual browser captures
    through the canonical evidence schema; no new pixels or production claim.
verified:
- claim: The initial fresh build completed and restored its original config bytes.
  command: python3 -m scripts.build_site (original execution 82738; p1a-fresh-build-terminal-20261012.json)
  result: Native assembly completed with rc=0 at 03:09:20 UTC. Original config SHA21390831fc7bba585a6393862bfbed934c1755efabb701f5dd2dd59d888eb3e3
    restored. Four optional ingestion/AI settings were disabled only during this local build.
- claim: The new generation exposed a real cross-panel protected identity disclosure.
  command: python3 -m pytest tests/test_us_board_gate.py -k shipped -q (fresh native output)
  result: Unchanged public-shell check failed on ABBV; initial targeted group had 19 passing and one failing
    test. The separate new production-call-path boundary tests failed eight cases before repair.
- claim: Observation repair preserves access boundaries, source order and immutable input.
  command: python3 -m pytest tests/test_us_board_gate.py tests/test_prophet_leader_observation_shelf.py
    -q -k 'not shipped'
  result: 94 passed, five shipped-artifact tests intentionally deselected pending regeneration. After
    canonical retained-VM rendering the five unchanged shipped checks passed.
- claim: Coverage text renders proper bilingual elements without unescaping hostile owner input.
  command: python3 -m pytest tests/test_us_board_gate.py -k candidate_coverage_renders -q
  result: 'Before repair: one failed and one passed for the two autoescape modes; after repair: both passed.
    Actual Canada screenshot exposed the literal tags before this repair.'
- claim: The composed source and browser receipt checks passed before the final label-tail change.
  command: python3 -m pytest tests/test_us_board_gate.py tests/test_prophet_card_shared.py tests/test_prophet_plan_relation.py
    tests/test_stock_dashboard_first_frame.py tests/test_p_mp1_shell_nonus_byte_parity.py -q
  result: 318 passed, no skip/deselect, 290.23 seconds; exact snapshot remains separate from the subsequent
    label-tail delta.
- claim: Identity-only gating had lost three authorized company labels; the repaired path retains them.
  command: python3 -m pytest tests/test_us_board_gate.py tests/test_prophet_leader_observation_shelf.py
    -q
  result: 'Discriminating real fast-render regression: one failed/two controls before repair; final affected
    group 100 passed in 128.17 seconds. Canonical cached render retains the exact native VM and restored
    config.'
- claim: Current HK and Canada fixture construction receipts and images were generated by the actual browser
    tool.
  command: node scripts/verify_stock_dashboard_mobile_layout.cjs --html <actual composed market fixture>
    --site-dir site --fixture-assets-dir mockups/evidence/prophet-p0b-zero-fouc/inputs/browser-data
  result: Each market completed 96 cases including 48 primary and 16 owner-degraded cases, with eight
    watch-only captures per market. Historical manifest target, pages and baseline are preserved; repair_extension
    binds current results. Visual schema guard passes; visual taste and production remain separate.
- claim: The unchanged import-closure checks accept the seven newly declared concrete dependencies.
  command: python3 -m pytest tests/test_ci_pack.py::test_real_manifest_has_non_vacuous_derived_scopes
    tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure -q
  result: 2 passed in 278.13 seconds following one actual closure failure. No checker or allowlist changed.
- claim: Normal Plan-relation cards and coverage surfaces have actual dark/light bilingual desktop/mobile
    images.
  command: NODE_PATH=<installed Playwright> node p1a-normal-surface-capture-20261012.cjs
  result: 32 viewport crops with applied axes verified, zero page exceptions and no page overflow. Local
    protected routes explicitly unavailable; no deployed authorization or visual-taste claim. The earlier
    unprotected local-route capture was rejected and retained separately.
- claim: Regenerated shipped US artifacts retain the existing public identity boundary.
  command: python3 -m pytest tests/test_us_board_gate.py -k shipped -q
  result: 5 passed, 87 intentional deselections, after final label-tail retained-VM rendering. Original
    configuration and actual native cache hashes unchanged.
- claim: Current-main composition preserves every reviewed application source, test and capture byte.
  command: Compare original owned publication paths between fb366eba9a9e7423d2df097ac27b9898486cf1e7 and
    the 17afadc7ed8ab82ec3b49f8d88ffd3a193bee58c merge index/worktree.
  result: Only the CI manifest, its upstream test_ci_pack.py and the combined workstream narrative changed
    among owned paths. Premium conflict was only upstream built time; exact newer canonical native payload
    retained. All 1096 unrelated build outputs archived and byte-verified before narrow restoration; no
    reset or stash.
- claim: The third composition retains the upstream table-filter fix and refreshes its actual browser evidence.
  command: Canonical retained-VM stocks renderer; actual HK/Canada browser verifier; normal-surface
    capture; pytest receipt and shipped checks; node --test tests/js/tablesort_browser.test.cjs.
  result: Composed with main 99b8a6e107d82d8178db67a4b5d0b85888d9c95e. Forty-eight real images rebound
    to loaded tablesort SHA dc424cb1c002a92c4e2e0b38771ef501960040fc372daeaf6777142f0013f8e0.
    Nine affected receipt/artifact checks passed (87 deselected); table-sort browser suite 30 passed,
    two explicit composed-only skips. Both planner checks passed in 202.34 seconds. Historical
    evidence and reviewed application-source bytes are retained.
- claim: The hosted compatibility error was a missing Git ref at collection, not a failed byte-parity assertion.
  command: gh run view 38205318192 --job 114668170060 --log; git show -s --format=%H:%T:%P
    4fca7501291f42b6b38b622d6620f1cf99e3a3ec
  result: Exact failed log reports fatal Not a valid object name origin/main at the eager merge-base
    lookup. Actual fetched merge parents and tree equal the canonical plan and prior local composition.
    Final semantic evidence remains failed with one blocking proof; all old run evidence is consumed.
- claim: The owner-job setup preserves a fixed base and fails closed without one.
  command: python3 -m pytest tests/test_ci_pack.py -k stock_dashboard_parity_baseline_in_shallow_pack -q
  result: Six real-Git cases failed before repair and passed after repair (168 other tests deselected).
    The PR fixture has different current/base content and a newer remote main, so a moving or self
    comparison cannot pass. Base replay uses its isolated base-only origin. No parity assertion changed.
- claim: Existing non-US byte-parity assertions still pass on the actual original carrier.
  command: python3 -m pytest tests/test_p_mp1_shell_nonus_byte_parity.py -q
  result: 29 passed, zero skip/deselect, 2.97 seconds after the owner-job setup repair.
- claim: The corrected owner setup is independently reviewed and selected by the existing planner.
  command: fabric_task.py result/accept/status prophet-p1a-ci-baseline-corrected-review-01a11e89;
    python3 -m pytest tests/test_ci_pack.py -k 'stock_dashboard_first_frame_contract_is_executed_by_pr_code_gate or stock_dashboard_parity_baseline_in_shallow_pack or curated_exclusive_scopes_cover_their_own_import_closure' -q;
    python3 -m pytest tests/test_ci_pack.py::test_real_manifest_has_non_vacuous_derived_scopes -q
  result: Exact-delta static review approved; canonical original-root/parent reviewer acceptance verified.
    Eight targeted tests passed (166 deselected, 143.04 seconds); the separate non-vacuous scope test
    passed in 105.49 seconds. No full-repository or independent pytest execution claim by the reviewer.
    AgentOS validation passes with zero errors and 103 existing warnings after correcting one local
    narrative indentation error; owned whitespace is clean.
unverified:
- claim: Qualified visual adjudication, hosted exact-head CI, source release and authenticated four-market
    production acceptance.
  what_would_verify: Human visual approval of the actual committed matrix, or a separately admitted
    qualified Opus reviewer, followed by exact-head semantic CI/gates, normal merge, publication/adoption
    and required live journeys.
unresolved:
- Pre-fix composition reviews remain consumed scoped evidence; later findings are preserved and repaired.
  Coverage markup and final label-tail reviews are accepted for their exact source/DOM deltas. The latter
  independently verified excerpts and narrow dependency files, with full build/test file hashes retained
  as parent bindings. Parent exact-source test execution remains separate. No source review proves visual
  taste or production.
- Original integration was published at 2196da598cb74b89a4a8d9157fc432b3b8029260 and then composed
  with the newly released Daily Brief main 99b8a6e107d82d8178db67a4b5d0b85888d9c95e. Seven concrete
  CI dependencies remain on existing jobs; both affected planner checks passed. Qualified visual
  judgment and hosted exact-head release gates remain.
- The existing claude-native Opus review route returned no eligible host before launch. The incumbent
  Fabric owner confirmed that none is admitted. Do not retry, enroll a host or substitute an unqualified
  worker. The human/Opus visual requirement remains; no visual approval has been inferred.
- HK/China adoption depends on actual accepted shared P1a release; Canada native Plan remains unavailable
  until its real owner exists.
next_actions:
- Publish the independently reviewed CI prerequisite repair on original PR8444 after current-main
  compatibility adjudication, then consume new exact-head semantic CI. Do not reread failed run38205318192.
- Obtain qualified visual judgment over the concrete published screenshots; retain the completed
  scoped source acceptance, current planner checks and exact parent test evidence.
- Finish original current-main integration and normal exact-head source release, then continue dependent
  owner-native integration and authenticated journeys.
do_not_redo:
- Do not duplicate P1a or Daily Brief carriers; human approvals already received and must not be requested
  again.
- Do not reset retained worktrees or stage unrelated native-build outputs. Historical captures and failed
  probes remain evidence.
- Do not manufacture native object/selection provenance, add a second selector, join Plan authority by
  ticker or replay any closed B03/Return evidence.
danger_areas:
- The native build disabled only macro_news.enabled, news_vector.enabled, news_translation.enabled and
  engine.conditions.regime_snap.veto.enabled. It is scoped native assembly evidence, not full-config or
  production proof.
- Current VM hash3e5cda1af580f81eb5c456a82e33d253244b4fdc90e36e04db3e3933cc591f07 retains its own source
  generation. A later cached render does not make its facts freshly observed.
---

This continuation uses the original carrier and the explicit human reopen decisions. The prior integration refusal is superseded only for that approved effect. The old failed merge was narrowly recovered before ordinary conflict resolution; no destructive Git recovery was used. Detailed raw logs, input/output hashes and review receipts remain in `/Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89`. Full Daily Desk acceptance remains open.
