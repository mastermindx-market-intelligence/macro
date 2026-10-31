# ES_LINKOUT_RECORD — ITP-ES-LINKOUT Wave 3a (run itp-es-linkout-20261022-r1)

- **Commission id**: itp-es-linkout-20261022-r1
- **Base sha**: ce93903889ea50056e9f4890422dad044c31c65a (origin/main at commission time)
- **Branch**: lane/itp-es-linkout-20261022-r1 (fabric-minted worktree)
- **Seat**: 2fc05761 (Information→Price Meta-CEO) judges the return by artifact
- **VERDICT**: DONE

## Mission

Add a `company_page` field to the Expectation Surface builder output and render a
"Company page" link beside the explorer card heading (`#es-card-t`) only when that
security ships a `stocks/<T>.html` page. Additive, EN/ZH, no new theme tokens, no
new strings-table keys.

## Step checklist

- [x] STEP 0: this record created (VERDICT: PENDING → DONE below)
- [x] BASELINE: HEAD == ce93903889ea50056e9f4890422dad044c31c65a; module suite **22 passed in 4.90s**
- [x] BUILDER (R1): additive `company_page` on index entries + ticker docs; `rendered_ticker_pages` called once per build through the module attribute (monkeypatchable); summary.json key set untouched; offline path unchanged (index empty)
- [x] TEMPLATE (R2): `#es-card-link` anchor after the h3, before the pill; CSS line `.es-card-link{ margin-right:auto; }` next to `.es-card-h`; `updateCard()` wiring with the mandatory `^stocks\/[A-Z0-9.\-]{1,12}\.html$` guard; no other JS/CSS change; h3 untouched
- [x] TESTS (R3): both expected key sets in `test_index_and_ticker_file_contract_keys` extended with `company_page`; 3 new tests added; module suite **25 passed in 4.88s**
- [x] Extra suites: `test_render_builder_ownership.py` **7 passed**; `test_public_chrome.py` 5 passed / 2 failed (both failures = sparse worktree lacks generated `site/*.html`, e.g. `site/about-research.html`; environmental, this diff touches nothing under site/)
- [x] DESIGN RATCHET: `check_design_system.py --mode enforce-added` → **blocking=0** (`estate pre-existing, non-blocking: 25372`)
- [x] EVIDENCE RECEIPT: `capture_page_evidence.py` → `outcome: captured, pages: 1, states: 8/8 captured`; `EVIDENCE.yml` written (receipt schema v1, changed_paths=[templates/expectation_surface.html.j2]); `check_ui_visual_evidence.py --diff-file` → **rc 0**
- [x] SCREENSHOTS: 8 open-state PNGs + `es_linkout_card_2x.png` + `es_linkout_hidden_1440.png` under `research/alpha_intelligence/expectation_market_dynamics/evidence/es_linkout_2026-10-22/`; hidden case proven programmatically (`{'hidden': True, 'href': None}` for `?t=BBB`); `scrollWidth === clientWidth` asserted at 390 in all four theme/lang passes
- [x] COMPOSITION: 3 commits, diff limited to owned files (a)–(f)
- [x] PUSH: refs/heads/claude/itp-es-linkout-2026-10-22 verified by ls-remote
- [x] SENTINEL: emitted on stdout

## Builder value rule (verified end-to-end on the evidence site)

`tickers/index.json`: AAA→`"stocks/AAA.html"`, BBB/CCC/DDD/EEE→`null`;
`AAA.json["company_page"] == "stocks/AAA.html"`. The value is only ever
`stocks/<T>.html` with T already gated by `_TICKER_SAFE_RE`, or null.

## EVIDENCE

- Visual record: `EXPECTATION_SURFACE_LINKOUT_EVIDENCE_2026-10-22.md` (same dir)
- Receipt: `mockups/evidence/expectation-surface-linkout/{EVIDENCE.yml, manifest.json, smells.json}` + capture PNGs
- Screenshots: `research/alpha_intelligence/expectation_market_dynamics/evidence/es_linkout_2026-10-22/*.png` (10 files)

## GAPS

- GAP (visual semantic confirmation): the guarded visual-judgment helper refused —
  `GLM_VISION_DELEGATION_REFUSED reason=controller_minimax_lease_required`
  (preserved verbatim; not retried around). Standing in: 8/8 browser state
  matrix, programmatic hidden/href/overflow assertions, ratchet blocking=0,
  receipt rc 0. No independent model-based visual judgment of the PNGs in-lane.
- GAP (minor, environmental): evidence capture ran on a scratch evidence site
  (synthetic fixture + chrome extracted from the committed base tree) because the
  sparse lane worktree omits site/; the repo working tree was never modified
  under site/. The production page re-renders on the next nightly.

## DEVIATIONS

- Screenshot server moved 8765 → 8791: port 8765 is held by a foreign process
  (pid 3123541, not this lane) serving a stale page without `es-card-link`;
  the lane did not touch that process. Spec's intent (serve the scratch site on
  localhost) preserved.
- `worktree_sparse.py add mockups` was run (the documented, config-named remedy)
  because `check_ui_visual_evidence.py` refuses sparse worktrees with mockups
  omitted; only the mockups/ directory was materialized — data/ and site/ stayed
  sparse, and the command is the tool's own printed opt-in.
- Commit trailer per the commission's explicit instruction: `Co-Authored-By:
  Claude Fable 5.1 <noreply@anthropic.com>`.

## RETURN

- **STATUS**: DONE
- **RESULT**: three commits on `claude/itp-es-linkout-2026-10-22` (pushed,
  verified by `git ls-remote origin refs/heads/claude/itp-es-linkout-2026-10-22`;
  the pushed 40-char head sha is emitted in the stdout sentinel — a commit
  cannot contain its own sha). Files: `scripts/build_expectation_surface.py`,
  `templates/expectation_surface.html.j2`,
  `tests/test_build_expectation_surface.py`,
  `mockups/evidence/expectation-surface-linkout/` (EVIDENCE.yml, manifest.json,
  smells.json + captured states), `research/alpha_intelligence/
  expectation_market_dynamics/{ES_LINKOUT_RECORD.md,
  EXPECTATION_SURFACE_LINKOUT_EVIDENCE_2026-10-22.md, evidence/es_linkout_2026-10-22/*.png}`.
  Tests: module 25 passed (baseline 22), ownership 7 passed, public_chrome
  5 passed / 2 failed (sparse-env only). Ratchet blocking=0; receipt rc 0.
- **EVIDENCE**: see EVIDENCE section above.
- **GAPS / DEVIATIONS**: as listed above.
