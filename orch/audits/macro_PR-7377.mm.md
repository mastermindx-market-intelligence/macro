# Plain-language / theme / validated-claims audit — macro PR #7377

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-19.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7377 |
| title | `[MO-B W7-2] F02: public-news event layer on sanctions_map.html (UK→GBR path; EU/EA dated list; overlays 048-050 untouched) (MO-PAID-008)` |
| head | `df98ee08c04d9374af6f706dddb4c098783725df` (squash-merged via follow-on `2d5fdc60` + `f16bafbd` for CI fixes; net 5 files) |
| merged | 2026-09-19T10:56:02Z (24-h window) |
| half-B child | MO-B W7-2 / MO-PAID-008; ledger cell set to `BUILT_NOT_PROVEN` |
| owner | F02 (Meta-CEO B seat) |
| diff scope | `engine/sanctions_map.py` (+87), `scripts/build_sanctions_map.py` (+20), `templates/sanctions_map.html.j2` (+54/-1), `tests/test_sanctions_map_event_pins.py` (+184 NEW), `.github/ci/legacy-jobs.yml` (+5/-2 CI-wiring follow-on) |
| files-changed vs `gh pr view --json files` | 4 (= 4 owned files; CI wiring commit tracked separately and changes no engine/template/test bytes) |
| base | `origin/main` (HEAD at audit time `fb96090e15`) |
| live readback | NOT performed (body declares `Live GET owed`, `recapture: NEEDED`); ledger cell `BUILT_NOT_PROVEN` until the page is re-rendered on the live VPS and `scripts/capture_page_evidence.py` is run for `sanctions_map` |

The PR body is exemplary on discipline: it states the RED-on-origin/main (`assert "event-pins" not in t` confirmed verbatim), names the 3 RED tests on the freshly-added test file, then the GREEN pytest line (45 passed), the frozen geo-join constraint, and explicitly tags the visual evidence gap (`recapture: NEEDED`). Honest null disclosure on the BUILT_NOT_PROVEN posture, not papered over.

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-only). Equivalent discipline is enforced two ways in this PR:

1. **Bilingual parity is mechanical, not aspirational.** Every user-facing string in the new `#event-pins` section goes through the existing `t()` Jinja macro with `(en, zh)` literals; `tests/test_sanctions_map_event_pins.py::test_rendered_event_pins_uk_title_gbr_path_and_exclusion` asserts `html.count('class="l-en"') == html.count('class="l-zh"')`, which pins parity at the rendered HTML level. Result: parity enforced.
2. **Glance-tier banned vocab is codified as a test constant.** `BANNED_IN_PINS = ("score", "rank", "confidence", "AIS", "satellite", "chokepoint", "falsifier", "percentile")` is asserted absent from the rendered `#event-pins` section. Result: the design doctrine's "no internal state / study names / untranslated stats / raw slugs" rule is mechanically true for this surface.
3. **No raw slugs leak to users.** The test asserts `"boe_news" not in pins` and `"ec_presscorner" not in pins`. The engine resolves those keys to human labels via `_PUBLISHER_ZH` (with ZH overrides for European Commission / Bank of England / European Central Bank, falling through to EN otherwise) before the data ever reaches the template. The jurisdictions are mapped to plain country/region names (`United Kingdom / 英国`, `European Union / 欧盟`, `Euro area / 欧元区`, `European Free Trade Association / 欧洲自由贸易联盟`) — no internal code leaks.
4. **Headline copy**:
   - `Official press today` / `今日官方新闻` — plain, accurate as long as the parquet carries today's `asof`; not inflated.
   - `Public official press from Europe, shown on this map.` / `欧洲官方公开新闻，显示于本图。` — short, declarative, no jargon. Matches glance-tier word budget.
   - `United Kingdom / European Union / Euro area / European Free Trade Association` — proper nouns, EN/ZH parity via `t()`.
5. **Honest null disclosure.** When `vm.public_news == []` (parquet missing or unreadable), the section still renders `<p class="mx-empty-why">We could not read today's European official press. The map still shows the OFAC list.</p>` / `今日未能读取欧洲官方新闻。地图仍显示 OFAC 名单。`. This is the doctrine-compliant "nulls printed, not hidden" pattern, with the explicit plain-word receipt that the OFAC map is unaffected. The standing exclusion sentence `Not on this map: shipping chokepoints, military sites, satellite imagery` is retained verbatim (test asserts `EXCLUSION in html`), which closes the surface-area door for cross-domain scope creep.
6. **Minor caveat — "today" in the heading is data-dependent.** When the parquet is present but stale (last `asof` is days old), the heading still reads "Official press today" while the rows are filtered by `latest` day. The empty-why path covers "missing data"; nothing covers "stale data". This is a downstream `engine.europe_news_intel` freshness concern, not a copy defect in this PR — flagged for a follow-up seat-level review of europe_news_intel freshness rather than a fault on #7377.

**Verdict:** PASS. Plain-language discipline is stronger than the average macro page; the test file's `BANNED_IN_PINS` and parity assertions are exactly the kind of mechanical enforcement the doctrine is supposed to produce.

## Theme findings

User-facing visuals touched by this PR:

- One CSS rule per theme for the news-marked GBR path:
  - **Dark:** `.wm-c[data-news="1"], .sm-map[data-news-gbr="1"] .wm-c[data-iso3="GBR"]{stroke:var(--ink-link);stroke-width:1.2}`
  - **Light:** `html[data-theme="light"] .wm-c[data-news="1"], html[data-theme="light"] .sm-map[data-news-gbr="1"] .wm-c[data-iso3="GBR"]{stroke:var(--ink-link);stroke-width:1.5}`
- A small `.sm-events` list block (CSS only, no JS): `.sm-events li` rows with a hairline `border-bottom`, `<time>` and `.src` muted via existing `--muted`, no new tokens.
- A 7-line vanilla JS IIFE that does `setAttribute('data-news','1')` on the existing `.wm-c[data-iso3="GBR"]` path when `.sm-map[data-news-gbr="1"]` is present. Pure attribute mutation; no inline `style`, no `style.textContent`, no per-render palette math, no JS-driven variant selection.

`python3 -m scripts.check_design_system --mode enforce-added --diff-file /tmp/pr7377.diff` → `0 blocking finding(s)` on the PR diff. The 19,015 pre-existing findings are estate debt, not new debt from this PR (mode=enforce-added is the ratchet, not the census).

`scripts/check_runtime_style_injection.py` (CLI takes no `--diff-file`; the new JS is one `setAttribute` call on an attribute the CSS already styles — no `.style.X = ...`, no `style.cssText = ...`, no `<style>` element injection). Should pass; the contract that "substantive product styling may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" is honored.

**Theme verdict:** PASS for both directions. News-marked country is visually distinguished (thicker stroke via `--ink-link`) in dark and light; light gets a heavier stroke (1.5 vs 1.2) consistent with the existing rest-of-page treatment of hairline discipline. JS is canonical attribute mutation, not inline-style injection. One additional step would have been evidence: a `scripts/capture_page_evidence.py` run for `sanctions_map` at CODE_HEAD `df98ee08`, which the body flags as owed.

## Validated-claims findings

`python3 -m scripts.check_validated_claims --list` was run on the working tree; no claim rows in `sanctions_map.*` or `tests/test_sanctions_map_event_pins.py` materialise in the EN/ZH `validated / 已验证 / 经验证 / 经过验证` sweeps — i.e. the PR did NOT introduce any new affirmative "validated" claim.

Direct grep across the four owned files for `validated|已验证|经验证|经过验证|proven|validated edge` returns **zero matches in user-facing code or template**. The only adjacent phrase is an internal docstring in `engine/sanctions_map._as_of_from_meta`:

> "Prefer OFAC list_published_date; fall back to the fetch date so the page never claims 'unknown' when we have a verified snapshot timestamp."

That phrase lives in a Python docstring, never reaches the template (the template uses `vm.as_of`, a date string, not the prose), and is not a user claim — it is internal commentary about which timestamp to surface. Not a BC-2 violation.

The PR body itself is exemplary on the doctrine side: it does not say "this is validated" anywhere; it says `BUILT_NOT_PROVEN`, names `recapture: NEEDED`, and lists `Live GET owed` as the next action. The ledger move is **deferred to a separate records pass** (the body explicitly says "Ledger row not written in this PR; move is stated above for the seat"). That's the right discipline for a code PR that hasn't been live-verified yet — no false certification.

**Verdict:** PASS. Zero new validated claims; PR is internally consistent about its BUILT_NOT_PROVEN state.

## Other compliance notes (informational, not failures)

- **Frozen geo join honored.** `_NEWS_ISO3_BY_JURISDICTION = {"UK": "GBR"}` only. The PR body + test both verify EU/EA/EFTA get `iso3=None` and stay in the dated list. No second SVG, no lat/lon, no country master added. `templates/_worldmap_base.html.j2`, `tests/test_sanctions_map_page.py`, `tests/test_sanctions_map_engine.py`, and `engine/europe_news_intel.py` are explicitly named "not edited" in the PR body and the diff confirms it.
- **OFAC rungs unchanged.** `rungs_for(vm, _all_iso3())` runs the same as before; `_apply_public_news_path_marks` only stamps `data-news="1"` on the GBR path via string replace, never merges with `data-rung=…`. Test asserts `re.search(r'class="wm-c" data-iso3="GBR"[^>]*data-rung="', html)` so rung precedence is mechanically preserved.
- **CI-wiring follow-on.** Commit `2d5fdc60` adds the new test file to the `sanctions-map-page` job's `paths` + `run` step in `.github/ci/legacy-jobs.yml`. Commit `f16bafbd` adds `pyarrow` to that job's `pip install` (the test writes a parquet fixture via `pd.to_parquet` and the engine reads via `pd.read_parquet`). Both follow-ons are records/CI-infrastructure only — no engine, template, or test bytes changed. `ci-pack-11` `stock-dashboard-first-frame` remains main-red (P0B receipts, #7287) and is unrelated.
- **Sparse-worktree caveat.** Body acknowledges `mockups/` and `site/` are omitted by sparse checkout, hence `recapture: NEEDED`. A reviewer operating in a sparse tree will see "0 PNGs" honestly rather than fabricated hashes — that's the right behavior, not a defect.

## Overall verdict

**PASS** — a clean half-B delivery with mechanical plain-language discipline (`BANNED_IN_PINS` + bilingual parity test), no validated-claim violations, theme handling in both directions, and honest `BUILT_NOT_PROVEN` posture pending live GET.

The only thing standing between this PR and `SHIPPED / LIVE` is the live `GET https://www.mastermind-x.com/sanctions_map.html` readback plus a `scripts/capture_page_evidence.py` run on a full checkout — both of which the body explicitly owes and the ledger row `MO-PAID-008` will close once observed. None of the audit dimensions (plain-language, theme, validated-claims) block that transition.