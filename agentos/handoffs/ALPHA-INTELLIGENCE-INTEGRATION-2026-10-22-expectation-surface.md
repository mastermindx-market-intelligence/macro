---
workstream: "WS:ALPHA-INTELLIGENCE-INTEGRATION"
session: "2fc05761-5cc2-4045-b383-56c4bb35ce2a (Information-to-Price Meta-CEO seat, Chairman directive 2026-10-21: site materialization via Fable seat + fabric lanes)"
model: fable
ended_because: ci_handoff
mission: >
  Materialize the Information-to-Price Expectation Surface as a site page: a descriptive, regenerated-per-render
  view of data/revisions/expectation_observations.parquet (687,456 rows, 64 sessions, 1,508 matched securities,
  2 metrics, 4 horizons) under the program brief research/INFORMATION_TO_PRICE_SITE_PROGRAM_BRIEF_2026-10-21.md,
  with design accepted before implementation and every lane's return judged by artifact.
state_before: >
  Brief #9958 MERGED (cd90f651). BUILD-DATA (fabric lane itp-es-build-data-20261021-r1) delivered the builder,
  JSON contract, tests and CI registration plus a semantic skeleton on draft #9969 head ff28fc1b. Design
  accepted by the seat (spec + boards in the seat scratchpad es_design/). ORCH-ITP-BUILD (Opus orchestrator
  a0642764002213cac) died on a provider 429 before consuming the BUILD-UI commission.
changed:
  - path: templates/expectation_surface.html.j2
    what: >
      Accepted design implemented by fabric lane itp-es-build-ui-20261021-r1 (glm-5.3-flash, ubuntu0): hero answer
      + descriptive/identity chips, census tiles, revision-breadth strip (newest 12 of 54 compared sessions) +
      session table, dual-sided largest consensus moves (25/side, 6 shown), consensus explorer (search combobox,
      metric/horizon radios, SVG band chart, covering-analyst bars, keyboard navigation, ?t= deep link), method
      and provenance with decisions on record. Tokens scoped to body.page-es; EN/ZH via #es-strings; no edge
      stripes; shared authenticated header family untouched.
  - path: tests/test_build_expectation_surface.py
    what: "4 UI-contract tests added (18 -> 22): style tokens/ids, strings JSON + language, horizon labels (G1), offline render of every section and band."
  - path: research/alpha_intelligence/expectation_market_dynamics/EXPECTATION_SURFACE_UI_EVIDENCE_2026-10-21.md
    what: Lane evidence record (build timing, test counts, §13 screenshot matrix, interaction proofs, a11y checklist, GAPS 1-4, DEVIATIONS D1-D9) + 19 PNGs under evidence/es_ui_2026-10-21/.
  - path: templates/theme.css
    what: >
      Seat repair r2 (commit 681f3dbf) after CI run 39712475941 reported 75 blocking design-ratchet findings on the
      lane template: the page's colour mixes, series colours and skeleton/flat greys now live in the sanctioned token
      root as the --esurf-* group (dark :root + light override); body.page-es only aliases them, every radius uses
      var(--r-*,<px>), hover mixes are tokens. Visual parity proven by pixel diff (<= 0.012 % on all 8 core shots).
  - path: mockups/evidence/expectation-surface/
    what: >
      Seat repair r3 (commit 4bdb0b14): page_evidence_receipt.v1 EVIDENCE.yml owning the page template and
      templates/theme.css, p0_evidence.v2 manifest + smells from scripts/capture_page_evidence.py, 24 PNGs
      (8 rest cells desktop/mobile x en/zh x dark/light + hover(.es-btn)/focus(.es-card-t) cells in both themes).
  - path: site/theme.css
    what: Derived copy re-synced with templates/theme.css (ci-pack-8 template<->site sync; 1 of 139 pairs had diverged).
  - path: mockups/evidence/prophet-p0b-zero-fouc/
    what: >
      Seat repair r4 (commit f7e8076c): mobile-layout.json + mobile-layout-canada.json re-minted against the
      re-copied site/theme.css (same Chromium 151.0.7922.34, only the theme.css digest moved, no new PNGs);
      manifest.json repair_extension.browser_receipts re-bound, prior extension archived in repair_extension_history.
  - path: site/research_screener.html
    what: >
      Seat repair r5 (merge commit 6de93f86): origin/main 8182ec04 merged into the branch after prophet #9954
      changed theme.css and re-minted the same P0B receipts; the four derived files were re-derived against the
      merged theme (receipts rc 0, manifest history 13, screener re-baked).
    what: Re-baked from the committed payload so the theme.css?v= stamp matches site/theme.css (ci-pack-7 parity).
  - path: .github/workflows/render.yml
    what: scripts/build_expectation_surface.py added to the push paths filter (render ownership test, pack-7).
verified:
  - claim: The lane return matches the commission by composition and count.
    command: "git diff --stat origin/main...5858a3c260c9041aab1843fe9958fd8ac757cfb8"
    result: "26 files, +3708: the six wave-1 paths + evidence md + 19 PNGs (all < 600 KB); nothing else"
  - claim: The repaired head passes the design ratchet and the render-ownership test with no visual change.
    command: "python3 scripts/check_design_system.py --mode enforce-added --diff-file <exact PR-vs-main template diff>; python3 -m pytest -q tests/test_build_expectation_surface.py tests/test_render_builder_ownership.py tests/test_render_run_size_cap.py tests/test_check_design_system.py; scratchpad/es_shots_diff.py es_shots_5858 es_shots_r2"
    result: "0 blocking; 131 passed; pixel diff <= 0.012 % per core shot (timestamp region only)"
  - claim: The r3 head satisfies the visual-evidence gate on the exact PR-vs-main template diff.
    command: "python3 scripts/check_ui_visual_evidence.py --diff-file <git diff --unified=0 <merge-base> HEAD -- templates site>; cmp templates/theme.css site/theme.css"
    result: "rc 0 (receipt mockups/evidence/expectation-surface/EVIDENCE.yml, 24/24 cells captured); cmp identical"
  - claim: The r4 head closes the P0B receipt pins on site/theme.css.
    command: "python3 scripts/check_p0b_receipt_closure.py --diff-file <PR-vs-main + working-tree file list>; python3 -m pytest -q tests/test_stock_dashboard_first_frame.py -k 'self_binding or visual_manifest or receipt'; python3 -m pytest -q tests/test_research_screener.py -k 'fresh_bake or committed'"
    result: "closure rc 0; 6 passed; 2 passed"
  - claim: The page builds LIVE and its suite passes on the head.
    command: "python3 -m pytest -q tests/test_build_expectation_surface.py (seat es_local root at head 5858a3c2)"
    result: "22 passed in 5.20 s; build(write=True) LIVE in 2.98 s, reasons []"
  - claim: No horizontal overflow and theme/lang honoured at both breakpoints.
    command: "python3 scratchpad/es_shots.py es_local/site es_shots_5858 (playwright chromium 151.0.7922.34)"
    result: "8 core shots 1440/390 x dark/light x en/zh: scrollWidth == clientWidth (390/390, 1440/1440); data-theme/data-lang attrs as set"
  - claim: The rendered page matches the accepted design boards.
    command: "seat visual inspection of 11 viewport crops (es_crops/) against es_design/ boards"
    result: "ACCEPT recorded in handoff_kits/meta-ceo-b-2026-09-08/orch/fabric/reviews/ITP_ES_BUILD_DATA_20261021.md"
  - claim: PR #9969 merged at its exact judged head.
    command: "gh pr merge 9969 --squash --match-head-commit 6de93f86fbd8555b9125182dc68820e975387b15"
    result: "6a4c0079 on main; required checks ci-plan, contract-delta, ci-authority/main SUCCESS; legacy packs green after repairs r2, r3, r4 and the r5 merge of main"
unverified:
  - claim: site/expectation_surface.html is live and registered.
    what_would_verify: "First nightly render after 6a4c0079: git ls-tree origin/main -- site/expectation_surface.html; registry row generated by scripts/build_product_page_registry.py; HTTP 200 on the production URL with body.page-es and the latest-session date."
  - claim: research/index.html link target (G3) resolves on the rendered site.
    what_would_verify: "curl the production research/index.html after the nightly; the sparse branch tree never materializes it."
unresolved:
  - "GLM vision delegation is refused for fabric lanes (controller_minimax_lease_required), so a lane cannot judge its own screenshots; the seat inspects. Fabric owner item."
  - "Fabric admission race: host_pick thermal gate vs lane_runtime admission can burn a run-id (observed on ubuntu1). Fabric owner item."
next_actions:
  - "PRODUCTION_PROOF after the nightly render; then Wave 2: Research mega-menu item for the page (design-tier: the menu is a curated icon system; 38 suites parity-check _navlinks.html.j2 via tests/test_chat_nav_sync.py), per-security link-out, CPL-1 coupling panel. The page does NOT join the Intelligence Hub desk rail (that rail carries live lamps and qledger track records; the surface is descriptive by DEC:ITP-R5-NO-DURABLE-APPEND-2026-10-07)."
do_not_redo:
  - "The page build, tokens, strings and UI tests on #9969 (ACCEPTED by artifact); lane itp-es-build-ui-20261021-r1 is spent."
  - "Seat rulings G1-G6 (horizon labels, UTC-only session clock, research/index.html link, no unit claims, 25/side, identity labels)."
danger_areas:
  - "financial_influence and k3e_admissible stay false on every emitted record; the page is a view, never a ledger."
  - "Never commit site/ or data/ on a branch; the nightly is the sole renderer and registry regenerator."
decisions:
  - "DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07"
  - "DEC:ITP-R5-NO-DURABLE-APPEND-2026-10-07"
---

# Expectation Surface page materialized (2026-10-22)

PR #9969 merged as `6a4c0079d1aec13b08cb554f6f7424b775165d09` (2026-10-22T08:42:34Z) from exact head `b4d942d87ed7c239ff12b73ca6e2f5f4639b7fba`. Rung reached: MERGED. PRODUCTION_PROOF waits on the first nightly render; see research/INFORMATION_TO_PRICE_CONTINUATION_HANDOFF_2026-10-06.md sections 41-43 for the ledger, the repair r2 lesson and the Wave 2 list.
