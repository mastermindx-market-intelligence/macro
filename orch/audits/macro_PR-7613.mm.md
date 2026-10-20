# Plain-language / theme / validated-claims audit — macro PR #7613

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7613 |
| title | `[MO-A heal] Re-mint p0b receipts (#7603 staled them) + closure GUARD so it cannot recur` |
| merged_at | 2026-09-21T12:43:32Z |
| head (semantic) | `b6c06d15bb909cd434bae8334299db23fb34f639` |
| merge_commit | `021d799a7af250da3d917dc72c260b7875d0feea` |
| branch | `claude/mo-a-heal-p0b-hk-tpl-and-closure-guard` |
| changed files | **26 files, +875 / −185.** New: `scripts/check_p0b_receipt_closure.py` (+414), `tests/test_check_p0b_receipt_closure.py` (+188). Modified: `.github/ci/legacy-jobs.yml` (+19 / −1), `config/house_law_checks.yml` (+48 / −0), `docs/HOUSE_LAW_CI_GUARD_SUITE.md` (+1 / −0), `templates/glossary.html.j2` (+1 / −0), `site/glossary.html` (+1 / −0), `mockups/evidence/prophet-p0b-zero-fouc/{manifest.json, mobile-layout.json, mobile-layout-canada.json, rendered-fixture.json}` (+177 / −180), 12 PNG receipts (all 0 / 0, sha-only), `tests/test_glossary_contract.py` (+13 / −0), `tests/test_bonds_glance_copy.py` (+6 / −3), `tests/test_check_ui_visual_evidence.py` (+7 / −6). |
| additions / deletions | 875 / 185 |
| labels | `merge-on-green`, `main-red-repair` |
| carriers / healing sequence | r1 (p0b receipts): re-mint mobile-layout*.json + manifest.json to bind `templates/hk.html.j2` `81c9a04a…` (the #7603 staling source). r2 (gate + glossary + bonds): add `ui.p0b_receipt_closure` law, wire it into `design-governance` as a base-dependent diff-scoped step, repair the `site/glossary.html` dropped `data-whb` banner tag, update the bonds stylesheet fingerprint test to the legitimate rename `f5ed7f7d → ebe31e14`. |
| parent / predecessor | heal closes the #7603 staling incident + the 2026-09-21 10:35Z public-render `data-whb` drop + the markets re-render bonds fingerprint rename; prior heal of the same class is #7597 / `site/navigation-refresh.css` (referenced verbatim by both the new law and the new check) |
| conflict / overlap | body declares explicit non-collision with `#7597` (healed lane) and the existing mobile-layout receipts (path-disjoint from #7603's HTML surface); the r1 receipts (`81c9a04a…`) are re-stamped from on-disk bytes, not re-edited |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --merged recent` against `git ls-tree origin/main -- orch/audits/` over the 24-h window starting 2026-09-21T06:30Z (the last 24 h at audit time, before the audit recording PR #7689 itself) shows the previously audited substantive merges are #7662 (brain Fast tool visibility), #7632 (risk replay), #7629 (China public live client + shared reason Lens), #7623 (purple composer notice), #7619 (Control Room sessionless continuity frontier), #7610 (help affordance keyboard + touch reachable), #7608 (research risk classify caution persistence), #7607 (China selective synthesis + reason Lens), plus the run of `orch(audit)` filing PRs #7671/#7659/#7651/#7644/#7636/#7627/#7612/#7606. The remaining 24-h unaudited substantive merges are **#7613** (this PR — half-B CI / receipt-closure guard + glossary banner + bonds fingerprint), #7679 (agentos SC1 release frontier — too small at +14 / −19), #7678 (CI contamination probe), #7666 (research risk replay rerun), #7628 (CI canary reachability), #7621 (CI bonds stylesheet fingerprint bind), #7614 (CI core engine outputs checkpoint), plus the audit-record runs. Of those, **#7613 is by far the largest single non-research, non-audit-record carrier (875 / 185 lines, 26 files) and the only one with both new user-facing template/site surface (glossary banner) AND new CI gate surface (the new `ui.p0b_receipt_closure` law and its checker).** That combination makes it the half-B pick with the most reviewer-relevant surface: a guard becomes a design-system-flavoured gate (so theme-doctrine relevance is non-zero), the glossary banner fix touches an operator-facing page (so plain-language relevance is non-zero), and the receipts are exactly the kind of claim-bearing artifacts (named SHAs, dates, sources) where validated-claims discipline applies. The CI-only peers (#7678/#7628/#7621/#7614) touch no user-visible surface; #7666 is a research rerun; #7679 is a +14-line agentos state update. #7613 is the only 24-h merge that touches user-visible HTML, has an explicit reviewable scope boundary, and is large enough that the audit has prose to read.

**Nature of change (half-B CI-gate + small user-visible patch, three-carrier heal).** Three sub-slices, each independently reviewable:

1. **r1 — Receipt remint (the heal itself).** `scripts/render_stock_dashboard_fixture.py` + `scripts/verify_stock_dashboard_mobile_layout.cjs` are re-run for HK and CA at then-current main. `templates/hk.html.j2`'s SHA advances from `1ae1c8edb8554b3fa3a64c02e326522c99c6649f0f7e7f48e62cecb8bda082c5` to `81c9a04a97008d1c82962227127a45de6137433872663dfbcefe6e73667213c2`; every receipt that pinned `1ae1c8ed…` is restamped. The historical baseline (`3fb76ea8…` / `b4dd8fd9…`) is preserved. Owner-empty PNGs and the `manifest.json` `repair_extension` hashes are restamped from on-disk bytes (no companion edit). Receipt file lists close correctly: each PNG's `path` is unchanged, only `sha256` rotates.
2. **r2 — Closure guard.** A new house law `ui.p0b_receipt_closure` is registered in `config/house_law_checks.yml` (severity: `hard`, selftest: `true`, owner_program: `prophet-us-eyes-open`) with three documented known_limits (`file-list closure only`, `derives pins from committed receipts at HEAD`, `REFUSES on a sparse checkout that omits mockups/`). A new `scripts/check_p0b_receipt_closure.py` (+414) is added that derives the pin set FROM the receipts (`mobile-layout*.json` → `construction_inputs` keys + `loaded_assets` keys + `verifier.path` + `fixture_receipt.path` + `rendered-fixture.json` recipe inputs) and refuses rather than passes vacuously on a sparse tree. Two new steps are wired into `.github/ci/legacy-jobs.yml` `design-governance`: a `--selftest` step and a `--diff-file` step that fetches `origin/${{ github.base_ref || 'main' }}`, computes `git merge-base`, and exits 1 with a `::error title=p0b-receipt-closure::` annotation if any pinned path moved without its receipts. Both new steps fail closed on missing base (the `if ! git fetch …; then exit 1` pattern matches the standing "an unresolvable base is an absent gate, not a degraded pass" doctrine).
3. **r2 — Glossary banner repair + bonds fingerprint update.** `templates/glossary.html.j2` is amended to emit `<script defer data-whb data-root="" src="wh_banner.js"></script>` (one line, +1), and `site/glossary.html` is re-baked through `build_public_pages` write + `inject_data_base` + `externalize_css` + `optimize_assets` so the committed page carries exactly one stamped tag (`wh_banner.js?v=b1207f44`). A new source-pinning test `test_glossary_template_emits_the_alert_banner_script` reads the template and asserts the tag is present (this is the source pin the body says was missing — the 10:35Z public-render re-bake dropped the tag because the template had never emitted it). The bonds test `test_committed_bonds_stylesheet_is_fingerprinted` is amended to expect `ebe31e14` (the legitimate markets re-render rename `f5ed7f7d → ebe31e14`, comment `LIVE / as-of` → `Snapshot / as-of`) and the assertion message is annotated with the cause-and-effect so a future PR knows why the fingerprint moved.

The PR does **not** introduce any new signal, score, ranking, sizing, trade, premium payload, public surface outside `templates/glossary.html.j2` + the matching site copy, or new authority. The gate refines a long-standing class of red (a template touched without the receipts that pin it being reminted) by adding a base-dependent diff-scoped step that names the remint recipe when it fires.

## Diff content (scoped to this audit)

The diff has four substantive code-bearing surfaces; the remaining 22 files are receipt manifests (sha-only edits), a one-line banner-tag emit, and the bonds test pin. The audit reads only the code-bearing surfaces.

### `scripts/check_p0b_receipt_closure.py` (NEW, +414)

A CLI checker with a docstring that names the class it closes (#7603 + #7500), the precedent heal (#7597), the schema-source (`mastermind.stock_dashboard_mobile_layout.v1` for receipts, `mastermind.stock_dashboard_rendered_fixture.v1` for the fixture), the exit-code contract (0 = closed / nothing pinned moved / selftest passed; 1 = pinned path moved without its receipts / selftest failed; 2 = cannot derive the pin set), and the refuse-on-sparse policy. Three CLI modes:

- `--selftest`: runs a synthetic receipt tree in `tempfile.mkdtemp`, asserts RED on a pinned-path-only diff, GREEN on a same-diff remint, GREEN on an unrelated-path diff.
- `--diff-file PATH`: reads `git diff --name-only` output (or a unified diff — `parse_changed_paths` auto-detects by sniffing for `diff --git `) and reports every pinned path that moved without the receipt that pins it.
- `--diff-file -`: reads stdin (the canonical CI form is `git diff --name-only "$mb" HEAD | python3 scripts/check_p0b_receipt_closure.py --diff-file -`).

Pin-set derivation reads `mobile-layout*.json` (filtered by `schema == RECEIPT_SCHEMA`) and unions: `construction_inputs` keys, `loaded_assets` keys, `verifier.path`, the path of the receipt's `fixture_receipt.path`, and (transitively) every `markets[*].inputs[*].path` from the fixture (which is what makes `templates/hk.html.j2` a pinned path even though it appears in the receipt via the fixture recipe, not the receipt's own `construction_inputs`). Template names appear in the docstring (as historical-incident mentions of #7603/#7500) but never as live pins in code — `test_checker_source_does_not_hardcode_template_pins` asserts this.

Three refused states are explicit: (1) no receipts under `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout*.json` AND no sparse-detect installed → "REFUSED: no `mastermind.stock_dashboard_mobile_layout.v1` receipts under …"; (2) no receipts AND sparse-detect reports `mockups/` absent → "REFUSED: cannot derive the P0B pin set (`python3 scripts/worktree_sparse.py full` for this worktree)"; (3) CI step can't resolve `origin/${{ github.base_ref || 'main' }}` or its merge-base → `::error title=design-governance::` annotation + exit 1 with prose "the p0b receipt-closure gate has NO canonical comparison base and cannot run. Failing closed — an unresolvable base is an absent gate, not a degraded pass."

When findings fire, the check emits one `::error title=p0b-receipt-closure::PINNED PATH CHANGED WITHOUT RECEIPT: <path> is pinned by <receipt>, which is not in the same diff` per finding, then a final `::error title=p0b-receipt-closure::re-mint with: python3 <recipe> --market all --out-dir DIR --receipt <fixture> && node <verifier> --html DIR/<market>.html --site-dir site --fixture-receipt <fixture> --fixture-assets-dir <assets> --screenshot-dir <evidence> …` line that names the actual verifier/fixture/asset paths derived from the receipts (not hardcoded) and respects the receipt's `historical_baseline.candidate_head` / `candidate_tree` if present (so the remint carries the historical `--historical-head` / `--historical-tree` flags). Both `::error` lines start with the bare annotation marker (no logger prefix), per the standing GitHub-annotation-line-start discipline.

### `tests/test_check_p0b_receipt_closure.py` (NEW, +188)

Eight red-first unit tests; every test plants a fresh receipt tree under `tmp_path` and asserts on the synthesized diff. Coverage: `test_hk_template_alone_fails` (RED: `templates/hk.html.j2` alone is enough to red), `test_hk_template_with_receipts_passes` (GREEN: same diff with both receipts present), `test_hk_template_with_canada_receipt_only_still_fails` (one-receipt closure doesn't close a path both receipts pin), `test_pin_set_is_derived_from_receipts_not_hardcoded` (a path the checker never names is still gated when a receipt pins it), `test_unrelated_path_passes`, `test_parse_name_only_and_unified_diff` (CLI accepts both `git diff --name-only` and unified-diff output), `test_cli_red_then_green` (CLI `main()` round-trip), `test_checker_source_does_not_hardcode_template_pins` (walks the source file, strips docstring + comments, asserts neither `templates/hk.html.j2` nor `templates/canada.html.j2` is mentioned in the live code body — only in the historical-incident docstring at module top), `test_selftest_passes` (the `--selftest` mode).

### `templates/glossary.html.j2` (+1) + `site/glossary.html` (+1)

The template emits one `<script defer data-whb data-root="" src="wh_banner.js"></script>` line at the same position the matching `templates/markets.html.j2` already emits its tag. The site copy is re-baked through the canonical render lane so the committed stamp is `wh_banner.js?v=b1207f44` (sha256 of `site/wh_banner.js` first 8 hex == `b1207f44`). No other template / site change.

### `tests/test_glossary_contract.py` (+13)

One new test `test_glossary_template_emits_the_alert_banner_script` reads `templates/glossary.html.j2` and asserts exactly one `data-whb` tag containing `wh_banner.js`. The existing test `test_committed_glossary_page_carries_the_alert_banner_script` (which reads `site/glossary.html`) is unchanged — it continues to assert the rendered site carries the tag; the new test pins the source so a future render that drops it during re-bake cannot re-stale the page.

### `tests/test_bonds_glance_copy.py` (+6 / −3)

`test_committed_bonds_stylesheet_is_fingerprinted` swaps `f5ed7f7d` → `ebe31e14` for both the `in refs` assertion and the `sha256(css)[:8]` self-check. The replacement is annotated with the cause (`Main's 2026-09-21 markets re-render moved the bonds sheet f5ed7f7d.css → ebe31e14.css (comment "LIVE / as-of" → "Snapshot / as-of")`) and the verification (`sha256(ebe31e14.css)[:8] == ebe31e14`). The chip-class assertions (`.dtp-chip--snapshot` present, `.dtp-chip--live` absent) are preserved. This is a fingerprint pin update, not a content change.

### `tests/test_check_ui_visual_evidence.py` (+7 / −6)

The `test_diff_scoped_steps_fail_closed_without_a_comparison_base` assertion `assert len(base_dependent) == 2` becomes `assert len(base_dependent) == 3` because the new `p0b-receipt-closure` step is also `merge-base`-dependent (it computes `git merge-base` against `origin/${{ github.base_ref || 'main' }}`). The assertion prose is updated to name the three base-dependent gates: "the forward-only design ratchet, the visual-evidence gate, and the p0b receipt-closure gate."

### `.github/ci/legacy-jobs.yml` (+19 / −1)

Two new steps on the `design-governance` job: a `--selftest` step and a `--diff-file` step. The `--diff-file` step runs `git fetch origin ${{ github.base_ref || 'main' }}` then `git merge-base`; either failing exits 1 with a `::error title=design-governance::` annotation. The existing design-governance unit suite is widened by one test: `tests/test_check_p0b_receipt_closure.py` is added to the `python3 -m pytest …` line.

### `config/house_law_checks.yml` (+48)

One new entry: `law_id: ui.p0b_receipt_closure`, severity `hard`, `selftest: true`, `allowlist: null`, `ratchet: null`, `owner_program: prophet-us-eyes-open`, `check_script: scripts/check_p0b_receipt_closure.py`. Three `known_limits` documented (file-list closure only / derives pins from committed receipts at HEAD / REFUSES on a sparse checkout that omits `mockups/`). The prose cites both precedents (#7597, #7603) by PR number. Severity is `hard` because the class reddens `tests/test_stock_dashboard_first_frame.py` on every fresh merge-ref until closure; no `allowlist` because the gate derives from receipts at runtime (no exemption class makes sense — either receipts pin the path or they don't).

### `docs/HOUSE_LAW_CI_GUARD_SUITE.md` (+1)

One row added to the table documenting `ui.p0b_receipt_closure`. The row mirrors the YAML's `summary` and `known_limits` blocks (same prose, same PR-number citations).

## Plain-language findings

### 1.1 Pass — `scripts/check_plain_language.mjs` does not exist in macro (terminal-side only); discipline is read against the design-doctrine banned-glance vocabulary + the standing bilingual-pair discipline, both of which apply narrowly

Macro enforces plain-language through (a) `tests/test_bilingual_ui.py` + `scripts/check_bilingual.py` for templates (EN/ZH paired discipline) and (b) the design-doctrine §Glance-tier banned-vocabulary list (`docs/DESIGN_DOCTRINE.md` §Glance tier). Both gate scopes target template/HTML/JS user-facing copy. This PR's user-visible copy surface is exactly one line in one template:

```html
<script defer data-whb data-root="" src="wh_banner.js"></script>
```

That line is structurally identical to the existing `templates/markets.html.j2` banner tag (same `defer`, same `data-whb`, same `data-root=""`, same `src="wh_banner.js"`) and carries no EN/ZH content (it's a script element with no inner text or aria-label). The bilingual-pair discipline is inapplicable to a script tag with no body text; `test_glossary_template_emits_the_alert_banner_script` asserts exactly one tag is present, which is the structurally-correct unit. **No banned-glance vocabulary is introduced.**

A plaintext scan of the diff for canonical banned tokens (`internal_state`, `study`, raw slug names, raw state names, `validated` as authority claim, internal product names like `RuntimeBinding`, `P0B` as user-facing label, `falsifier` as user-facing label, "thesis refuted" / "证伪" / "falsifier fired") returns:

- **`P0B`, `MO-A`, `HEAL-P0B-GUARD-R2`, `r1`, `r2`, `#7597`, `#7603`, `p0b-receipt-closure`, `data-whb`** — all are intentional, canonical internal identifiers. `data-whb` is a vendor-style data-attribute that the wh_banner script looks for; it has no user-facing rendering and is the standing convention for this banner. `P0B` / `MO-A` / `HEAL-P0B-GUARD-R2` appear only in operator-facing prose (PR body, house-law `summary:` field, known_limits, test docstrings, `docs/HOUSE_LAW_CI_GUARD_SUITE.md` table description). The banned-glance tier explicitly excludes operator memos / CI config / test docstrings.
- **`validated`** — does NOT appear in any PR-added content. The single grep hit is in the pre-existing `ui.runtime_style_injection` row of `docs/HOUSE_LAW_CI_GUARD_SUITE.md` ("`generated_from` is recorded, never validated against the PR head"); that row was already in the table before #7613 landed (this PR only adds a new `ui.p0b_receipt_closure` row). The new row contains zero occurrences of `validated`. Grep of the new files (`scripts/check_p0b_receipt_closure.py`, `tests/test_check_p0b_receipt_closure.py`, `tests/test_glossary_contract.py` new test, `tests/test_bonds_glance_copy.py` new prose, `tests/test_check_ui_visual_evidence.py` new prose, `templates/glossary.html.j2`, `site/glossary.html`, `config/house_law_checks.yml`, `.github/ci/legacy-jobs.yml`) for `validated` returns zero matches.

### 1.2 Pass — the new `ui.p0b_receipt_closure` house-law prose is plain-language operator prose, not user-facing copy

The new law's `summary:` field reads:

> *"A change to any path pinned by the Prophet P0B browser receipts (construction_inputs, loaded_assets, the verifier script, or rendered-fixture.json's recipe inputs) must remint those receipts in the same diff. #7603 changed templates/hk.html.j2 without reminting mobile-layout*.json (still pinning 1ae1c8ed…); #7500 did the same with site/navigation-refresh.css (healed by #7597). The class reddens test_stock_dashboard_first_frame.py on every fresh merge-ref until the closure is a GATE. The pin set is derived FROM the receipts at runtime and is never hardcoded."*

This is operator documentation: it names the exact technical class it closes, cites both precedents by PR number with their healing history, and states the design intent (derive pin set from receipts, never hardcode). It does not claim product capability, accuracy, or authority. The same plain-language reading applies to the checker's module docstring (paragraph 1: class statement + precedents; paragraph 2: pin-set-derivation design; paragraph 3: CLI usage; paragraph 4: exit-code contract) and to each test docstring (each names the specific RED/GREEN case it exercises).

### 1.3 Pass — the glossary banner fix uses the canonical pattern; no plain-language surface

The `templates/glossary.html.j2` change is one line. The matching `site/glossary.html` re-bake is identical structurally. Both are the standing `wh_banner.js` banner pattern (the same script is loaded by `markets.html.j2`, `risk-radar.html.j2`, etc. — the banner is site-wide). The new test `test_glossary_template_emits_the_alert_banner_script` reads the template and asserts exactly one tag is present. No user-facing copy is introduced; the banner script is loaded, not authored. No EN/ZH pair is broken because no EN/ZH content is touched.

### 1.4 Observation (non-blocking) — the bonds test pin update replaces one fingerprint with another; the comment is plain-language but uses operator shorthand

`tests/test_bonds_glance_copy.py` `test_committed_bonds_stylesheet_is_fingerprinted` swaps `f5ed7f7d → ebe31e14` and adds the comment:

> *"# Main's 2026-09-21 markets re-render moved the bonds sheet f5ed7f7d.css → ebe31e14.css (comment "LIVE / as-of" → "Snapshot / as-of"). sha256(ebe31e14.css)[:8] == ebe31e14; chip assertions unchanged."*

This is operator prose (commit-message style: cause, evidence, unchanged-assertion-list). It uses "LIVE" / "Snapshot" as the legitimate CSS-class rename context, not as market-state terminology (those tokens are CSS-class suffixes, not risk-on/risk-off labels). The assertion prose is plain-language: it names the cause ("markets re-render"), the artifact ("bonds sheet"), the rename direction (with the cause-comment text), and the self-check that the new fingerprint matches. **Not blocking** — flagged so a future audit pass on prose-language in test docstrings doesn't get mistaken for a regression.

## Theme findings

### 2.1 Pass — `scripts/check_theme_compliance.mjs` does not exist in macro (terminal-side only); discipline is read against `scripts/check_design_system.py` + `scripts/check_runtime_style_injection.py` + the standing dark/light two-art-directions law

The macro theme/visual-evidence gate scope is `templates/` + `site/` user-facing HTML/CSS/JS files plus the per-file style-injection allowlist. This PR's surface in those paths is:

- `templates/glossary.html.j2` (+1 line): a `<script>` element carrying a `defer`, a `data-whb`, a `data-root=""`, and a `src="wh_banner.js"` — no CSS, no color, no theme tokens, no dark/light branch, no rendered text. The element is loaded as a separate vendor/operator script (`site/wh_banner.js` is the alert-banner script, not a theme component).
- `site/glossary.html` (+1 line): the same script element, with a stamped `?v=b1207f44` query string. The fingerprint is the canonical `?v=<sha256[:8]>` cache-busting pattern (the Caddyfile's `immutable` list and the script-loading conventions require it).

Neither change introduces a dark/light decision, a new CSS variable, a new token, a new color, a new typography rule, a new motion rule, a new spacing rule, a new component, or any other visual surface. The PR does not touch `theme.css`, `theme.js`, `navigation-refresh.css`, `_public_chrome_css.html.j2`, `_site_nav.html.j2`, or any other theme owner. The Dark + Light art-direction law (TP-0 2026-08-27, the doctrine that "dark and light share information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behavior — they do not have to share material treatment") is structurally inapplicable: zero material decisions were touched.

The two CI gates that scope this concern (`scripts/check_design_system.py --mode enforce-added`, `scripts/check_runtime_style_injection.py`) both accept the change:
- `check_design_system.py --mode enforce-added` walks every PR that adds to `templates/` or `site/` and refuses a violation of the design system. Adding a `<script>` element that loads an existing vendor script does not add to the design system (no token, no rule, no class, no CSS variable). The one-line template edit and the one-line site edit both pass this gate.
- `check_runtime_style_injection.py` is the per-file signature counter; this PR does not touch any user-facing JS file (`site/theme.js` is not in the diff, no `templates/*.js` is in the diff). The new `scripts/check_p0b_receipt_closure.py` is a CI checker, not a user-facing JS file, so it is structurally out of scope for the runtime-style-injection allowlist.

### 2.2 Pass — the new gate's check-script is structurally out of theme scope

`scripts/check_p0b_receipt_closure.py` is a CI checker (Python 3, no template / no CSS / no JS). It emits `::error title=p0b-receipt-closure::…` annotations to the GitHub Actions log, not to a user-facing page. It is invoked from `.github/ci/legacy-jobs.yml` `design-governance` and from a possible local developer run (`python3 scripts/check_p0b_receipt_closure.py --selftest`). Its output style is operator-facing prose, not user-facing copy; its error annotations start with `::` (the bare annotation marker), per the standing GitHub-annotation-line-start discipline. There is no template / no JS / no CSS surface that could create a theme-discipline question.

### 2.3 Pass — the receipts are receipts, not theme artifacts

The 17 receipt files (`mockups/evidence/prophet-p0b-zero-fouc/*`) are evidence data: each is a JSON manifest with construction-input hashes, asset hashes, and screenshot hashes. None of them carries a CSS variable, a theme token, a color, a typography rule, or any other theme artifact. The PNG receipts are restamped from on-disk bytes (the diff shows 0 / 0 for every PNG because PNGs are binary — only the `sha256` in the surrounding JSON manifest rotates). The receipt test (`tests/test_stock_dashboard_first_frame.py`, not in this PR) is the binding test for theme correctness; this PR only heals the receipt-pin drift, it does not change the captured bytes themselves.

## Validated-claims findings

### 3.1 Pass — the PR body is operator-prose with no user-facing claim surface

The PR body is structured as `## Situation / ## What this PR does / ## Files-changed / ## Validation`. The "Situation" section names the incident (#7603 stale `templates/hk.html.j2` mobile-layout pins; 2026-09-21 10:35Z public-render `data-whb` drop on glossary; markets re-render bonds fingerprint rename) and the precedent heals. The "What this PR does" section enumerates four numbered actions with their exact outputs. The "Files-changed" section is a 26-row `git diff --name-only origin/main...HEAD` set. The "Validation" section lists pytest outputs (`22 passed in 2.46s`, `114 passed in 55.24s`, `136 passed in 56.60s`) and an explicit "Hosted CI is not claimed green."

Every claim in the body is either (a) a file path / SHA citation / pytest count (machine-verifiable), (b) a healing-history statement (#7597 healed #7500; #7603 staled the receipts), or (c) the explicit "CI is not claimed green" disclaimer. The body does not claim production acceptance, does not claim authority, does not claim a metric or ranking, does not claim a user-facing capability, and does not use the word `validated` as an authority claim.

### 3.2 Pass — the new `ui.p0b_receipt_closure` law entry has explicit `known_limits` prose

The YAML entry's `known_limits:` block carries three bullets, each one self-describing what the gate does and does not cover:

- *"File-list closure only: a receipt file present in the diff satisfies the gate even if its hashes were not actually reminted. The receipt tests in tests/test_stock_dashboard_first_frame.py still bind live bytes and catch a touch-only companion."*
- *"Derives pins from committed receipts at HEAD, not from the incoming diff's new receipt bytes. A PR that adds a newly pinned path and the receipts in the same diff is judged against the pre-change pin set for that path (the new pin takes effect on the next PR)."*
- *"REFUSES on a sparse checkout that omits mockups/ rather than reporting a vacuous pass over receipts it cannot see."*

These are not defenses ("we might miss this") — they are honest scope statements of what the gate covers and where the next reviewer must look. The receipt tests in `tests/test_stock_dashboard_first_frame.py` are the second line of defense (they bind live bytes). This is the standing "honest scope" pattern: a gate names what it covers, names what it does not, and points to the next reviewer (in this case the live-bytes tests).

The same self-disclosure pattern is in the checker's module docstring (the "REFUSES on a sparse checkout" sentence is the third paragraph; the exit-code-2 contract is the fourth paragraph). The checker's CI step also self-discloses in failure: when no receipts are found under `mockups/`, it returns exit-code 2 with a `REFUSED: …` message rather than exiting 0 ("vacuous pass"). The third refused state — CI step can't resolve the merge-base — exits 1 with `::error title=design-governance::` prose that says "the p0b receipt-closure gate has NO canonical comparison base and cannot run. Failing closed — an unresolvable base is an absent gate, not a degraded pass." This is the standing "an unresolvable base is an absent gate, not a degraded pass" doctrine, applied verbatim.

### 3.3 Pass — the glossary banner repair and bonds fingerprint update both cite verifiable evidence

- The glossary test `test_glossary_template_emits_the_alert_banner_script` is itself the evidence pin (it asserts the source emits the tag). The site re-bake is the evidence that the rendered page carries the stamped tag. The pre-existing `test_committed_glossary_page_carries_the_alert_banner_script` is the second-line test that asserts `site/glossary.html` carries the tag with the stamp. Both tests are present and unchanged/newly-added in this PR.
- The bonds test `test_committed_bonds_stylesheet_is_fingerprinted` cites `sha256(ebe31e14.css)[:8] == ebe31e14` and asserts `.dtp-chip--snapshot in text` and `.dtp-chip--live not in text`. The assertion message names the cause (markets re-render rename) and the cause-comment (`LIVE / as-of` → `Snapshot / as-of`). The CSS file is already on main (the rename happened in a previous render commit; this PR only updates the test pin). The chip assertions are preserved unchanged.

### 3.4 Pass — no user-facing claim-bearing prose is introduced

The diff does not introduce any of: a new score / ranking / sizing / trade / verdict; a new signal source / signal class; a new authority / entitlement / gate; a new product claim (capability, accuracy, performance); a new EN/ZH user-facing string. The only user-visible HTML change is the addition of one `<script>` element loading an existing operator script; the user-visible change is "the glossary page now shows the standing wh_banner alert banner that the rest of the site already shows." That is a parity restoration, not a capability claim.

The PR body, the law summary, and the test docstrings all use operator / engineering prose (PR numbers, SHA-256 prefixes, exit codes, gate-class names). None of that prose reaches the user; the `design-governance` CI lane is the only consumer.

## Overall verdict

**PASS — half-B scope, no plain-language / theme / validated-claims defects.**

The PR is a CI-gate + receipt-closure heal with three bounded sub-slices: (1) a receipt remint that restamps `mobile-layout*.json` from on-disk bytes with no companion content edit; (2) a new `ui.p0b_receipt_closure` house law + its checker + its selftest + its base-dependent CI wiring, all in the standing `::error title=…::` annotation shape with explicit "REFUSES on sparse / unresolvable base" refused states; (3) a one-line glossary banner emit (source + re-baked site copy) plus a bonds fingerprint test pin update with annotated cause. The plain-language scope is structurally narrow (one `<script>` element, no EN/ZH content), the theme scope is structurally zero (no CSS / no theme / no token / no dark/light decision), and the validated-claims scope is structurally zero (no user-facing claim surface introduced; all "claim-like" prose is operator/engineering prose citing verifiable SHAs and pytest counts). The two reviewer-relevant surfaces — the new gate's `known_limits` and the bonds test pin cause-comment — are both self-disclosing in the standing honest-scope style.

The merge labels (`merge-on-green`, `main-red-repair`) and the body's "CI is not claimed green" disclaimer correctly characterize this as a healing PR that depends on a green hosted CI baseline to land. No claim about the merge itself is being made; the audit reads the merge as already-landed (merge_commit `021d799a7af250da3d917dc72c260b7875d0feea` on `origin/main`).

| dimension | result | blocking? |
|---|---|---|
| plain-language | PASS (operator prose only; one `<script>` element; no banned vocab; no `validated` claim) | no |
| theme | PASS (zero CSS / theme / token / dark/light surface; new checker is structurally out of theme scope; receipts are evidence data not theme artifacts) | no |
| validated-claims | PASS (no user-facing claim; `known_limits` prose is honest-scope; bonds test pin cites verifiable SHA; glossary banner is a parity restoration) | no |
| overall | PASS | no |
