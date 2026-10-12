# Crypto T19 consumer evidence plan — 2026-10-12

Display-tier plan for the Crypto cockpit and Bitcoin Vector pages after candidate `#8050` R2 (`fd8095012e91026640ae07e092ae6272a2e7d30c`) is applied onto `origin/main` `e038bd40eee`. This lane does not promote a reading to authority, does not add a score, and does not size or execute.

Worktree templates are the R2 bytes. `git diff --stat ba258da9217c6fc905475511d5597be5d8f37af0 fd8095012e91` is empty for `templates/crypto.html.j2`, `templates/vector.html.j2`, `templates/_crypto_house_style.html.j2`, `scripts/build_crypto.py`, `scripts/build_vector.py`, and `scripts/capture_page_evidence.py`. `ba258da9` is an ancestor of `fd8095012e91`.

## Census

### `templates/crypto.html.j2` (515 lines)

Both languages are emitted by `t()` at lines 2–4. `data-theme` / `data-lang` are set from `localStorage` at line 13 (default theme `dark`). Hide/show is `templates/theme.css:513-514`.

Context the template reads, first use:

| Lines | Fields |
| --- | --- |
| 14, 468 | `as_of`, `built` |
| 298–312 | `market.stance/stance_zh/summary/summary_zh`, `market.total_tone`, `market_total`, `market_30d`, `market.dominance_tone/dominance_state`, `dominance`, `dominance_30d`, `market.fear_tone/fear_state`, `fear`, `market.history.dates`, `tape` |
| 319–330 | `allocation.available/budget_available/exposure/cash/decision_as_of` |
| 339–347 | `universe_snapshot.as_of/requested/excluded`, `universe_count`, `breadth.available/positive/eligible/required/excluded` |
| 371–383 | `top_assets[]` (`rank`, `symbol`, `name`, `tone`, `live_symbol`, `price_label`, `change_label`, `spark`, `history_chip`, `state`, `state_zh`), `more_assets`, `universe_sources` |
| 389–404 | `market.flows.etf/stablecoins/volume.*`, `market.heat.open_interest/volatility/altseason.*` |
| 407–416 | `btc_options.as_of`, `volatility.atm_iv_30d`, `gamma.flip/distance_pct/assumption_*`, `positioning.put_call_oi_ratio/max_pain`, `basis.annualized_pct`, `coverage.note_*` |
| 421–435 | `allocation.btc/eth/alts/split_context_available/regime/season/ethbtc/season_score/reason_en/reason_zh` |
| 452, 458, 465 | `lanes[]`, `equities[]`, `calendar[]` |

Line 400 hardcodes the funding reading as `—`. It does not interpolate `market.heat.funding.value`.

### `templates/vector.html.j2` (808 lines)

Same `t()` / `localStorage` pattern at lines 4–6 and 18. First use:

| Lines | Fields |
| --- | --- |
| 19, 360–361, 759 | `as_of`, `price`, `chg24`, `built` |
| 337–379, 456 | `decision.status`, `decision.integrity.ok`, `decision.final`, `master.ok/tone/band/band_zh/headline_en/headline_zh`, `timeline` |
| 402–448 | `chart_contract.valid/issues/performance_valid`, `chart_contract.meta.fields.{price,risk,allocation}.source_id`, `chart_contract.meta.observed_at` |
| 430–431, 471–485 | `risk_index`, `risk_label`, `risk_on`, `decision.schema/final.action_*/exposure_pct/change_pp`, `decision.advisory.levels` |
| 515–552, 571 | `presentation.axes/watch/complex`, `cycle_stage`, `cycle_pos` |
| 615–668 | `btc_options.*` (same nodes as Crypto), `options.dvol/gamma_flip`, `leverage.oi_total/okx_ls_ratio/okx_ls_pctile/okx_ls_z`, `derivatives_flow` as `flow.*`, `charts.etf_flow/momentum/structure/bfi`, `valuation.mvrv_z`, `bfi`, `newf.holders.state`, `newf.miner.state`, `onchain.premium_state`, `cycle_vintage.reserve_risk_asof/vdd_asof` |
| 678–750 | `strategy.as_of/strategies/hodl.*`, `cards`, `calib.meta/signals/risk_drawdown` |

`C` is passed at `scripts/build_vector.py:5057` and is not read by the template.

### Where a missing input becomes a template value

Crypto builder `scripts/build_crypto.build` (`:464-613`) renders `crypto.html.j2` at `:603` and writes through `write_page`. Context keys are the `vm` dict at `:561-591`.

- Missing `crypto_cockpit.json`: `_load_e0` `:120-142` sets `decision.status=unavailable`, `final_exposure_pct=None`, errors `COCKPIT_DECISION_UNAVAILABLE`, hero stance `Unavailable`.
- `_money` `:54-56` and `_pct` `:72-74` return `—` for None. A real `0.0` stays `0.0%`. A price with `abs < 1` becomes `$0.0000` (`:65-66`), so a missing price must stay None.
- `_allocation` `:256-287`: failed canonical checks → `CANONICAL_DECISION_UNAVAILABLE`; empty signals → `CANONICAL_SNAPSHOT_UNAVAILABLE`; `as_of` mismatch → `CANONICAL_DECISION_AS_OF_MISMATCH` (old target not shown). After those checks, exposure `0` returns `available` with `btc=eth=alts=0`, `cash=100`, empty reason (`:280-285`) and does not read `close`. Exposure `> 0` with no `close` column returns `CLASS_SPLIT_INPUT_UNAVAILABLE` with the budget kept and `cash=100-budget` (`:286-287`). Copy is `:199-218`. Template branches: history `:312-315`, desk budget `:319-328`, H5 `:421-444`, spark vs `Building history` `:376`.
- `regime_tape` returns a truthy hairline (`ilx-null`, "No history yet") when fewer than 4 points exist (`lib/illus.py:463-464`, `_null_fragment` `:241-253`). The template treats `dates|length >= 2 and tape` as available (`crypto.html.j2:312`). Empty dates take the else branch and the hairline is not inserted. Two or three dates would mark history available and paint the hairline. Patch below raises the gate to 4. Not applied.
- Altseason meter `:404` sets `--v:0%` when `market.heat.altseason.value` is none, while the score text is `—`. Patch below omits the style. Not applied.
- Empty ETH history is not a safe partial. With a close column and a non-zero budget, `btc_mtf.mtf_ladder` on a 3-row close returns regime None, `alt_cycle.ethbtc_signal` of an empty series returns `{}`, `alt_season_score` returns score None / bucket `—`, and `alloc_grid(None, "—")` returns `{btc: 45, eth: 20, alts: 5, cash: 30, regime_key: neutral, season_key: mixed}` (probe this session, no network). The four fixtures never enter that path: zero returns at `:280`, stale fails at `:275`, partial has no `close` column at `:286`. Do not patch the allocation engine from this lane.

Vector chart contract is `_risk_strategy_payload` (`scripts/build_vector.py:196-333`). A real `0` allocation stays a number. A missing allocation stays null. `valid` is variants present and no NaN close (`:284`). `performance_valid` also requires the equity path not broken by a prior gap (`:288-290`). Issue codes: `NO_ALLOCATION_VARIANTS`, `PRICE_UNAVAILABLE`, `ALLOCATION_GAPS` (`:266-283`). The template emits `#vec-risk-chart` only when `valid` (`:408-409`); otherwise "Interactive replay unavailable" plus `issue.message_en` (`:415-420`). When `valid` is true and issues remain, only the static sentence "the chart preserves them as unknown" is emitted (`:412`), not the issue code. `performance_valid` false while `valid` shows "Allocation simulation unavailable" (`:730-733`).

`_derivatives_flow_view` (`:4354-4422`) states: `available`, `stale` (share forced None, `:4403-4405`), `coverage_gap` (`:4406-4408`), `no_activity` (share None, net 0), else `unavailable`. Template `:627-636`.

`vector.html.j2:360-361` formats `price` and `chg24` with no None guard, so a missing quote cannot render. `:494` prints `risk_index/100` and Chinese `低风险`/`高风险` from `risk_on` even when the index is missing. The overview side already shows `—` and "Unavailable" when `risk_index is none` (`:430-431`). Patches below. Not applied.

`build_vector.main` (`:4425`) writes `vector/signals.parquet`, spawns sibling builders, and publishes the configured site dir (`:5062`). The render test repeats only `:5045-5061` (Environment, `money`/`money1`, `td`/`tr`, `render(**vm, C=C)`, the same `re.sub`) and returns the string. It does not call `main`.

### Tests and harness already in tree

- `tests/test_crypto_house_style.py:8-23`: three source checks (include, SF/Inter, tokens). No render.
- `tests/test_crypto_wave2.py:27-49`: `build_crypto.build` plus `store.read("vector","signals")`. Needs `data/`. Not run here.
- `scripts/check_ui_visual_evidence.py` is a receipt gate. `VIEWPORT_WIDTHS` is desktop `1440` and mobile `390` only (`:101-102`). It does not import Playwright. `--selftest` is documented at `:64`. It cannot certify 320 or 768.
- `scripts/capture_page_evidence.py:122-126` viewports: desktop `(1440, 900)`, tablet `(820, 1180)`, mobile `(390, 844)`. CLI `:2122-2132`: `--site-dir`, `--routes`, `--output-dir`, `--manifest`, `--smells`, `--viewports` default `desktop,tablet,mobile`, `--locales` default `en,zh`, `--themes` default `light,dark`, `--max-pages`. `page.goto` at `:1625`. Named viewports do not include 320 or 768. `tests/test_capture_page_evidence.py:738` requires `by_viewport == {desktop, tablet, mobile}`. Do not add widths to that default.
- A repo search for `playwright|page.goto` also hits unrelated capturers (`scripts/capture_aibrief_band_evidence.py`, `scripts/capture_macro_command_p3.py`, `scripts/capture_am_edition_evidence.py`, `scripts/fetch_ishares_validation_sample.py`, and test modules). The Crypto/Vector pixel owner in this tree is `scripts/capture_page_evidence.py`. The 112-cell owner is R2-only `research/crypto_science/r15/render_and_check.py` (not on `origin/main`, not in this worktree).

### `#7645`

`git fetch origin claude/uiux-crypto-market-board-20260921` → `74298e32bbbbc7f00884ece259455b9bbe46fd6f`. Merge-base with `origin/main` is `2b62f496`. Own delta vs that base: `templates/crypto.html.j2 | 38 ++++++++++++++++++++++++++------------`. `templates/_navlinks.html.j2` has no hunks vs that base. `git merge-file` of navlinks (base `2b62f496`, ours `HEAD`, theirs `74298e32`) exits 0 with 0 conflict markers and keeps Morning Edition (merged line 285) and `ontology.html` (merged line 305). A two-dot diff against today's `origin/main` is the wrong object: main added those links after the branch point.

## 1. Evidence matrix

One cell is `{scenario}_{width}_{theme}_{lang}`. Scenarios: `known`, `zero`, `unavailable`, `stale`, `breakdown`, `history_missing`, `combined`. Widths: `320×850`, `390×844`, `768×1024`, `1440×1000`. Themes: `dark`, `light`. Languages: `en`, `zh`. Count: 7 × 4 × 2 × 2 = 112.

Language and theme are runtime, not separate templates. The harness sets them before navigation:

`localStorage.setItem('theme', …); localStorage.setItem('lang', …)` then `page.goto` (`render_and_check.py:99-100` at `fd8095012e91`). CSS then hides `.l-zh` or `.l-en` (`templates/theme.css:513-514`).

Producer for every semantic cell, including 320 and 768, on a checkout that contains the R2 script (this worktree does not):

```text
python3 research/crypto_science/r15/render_and_check.py --completion
```

Matrix literal: `render_and_check.py:90`. The script raises if `browser_proof.json` exists (`:74`), hashes `data/` inputs (`:75-79`), and reads stored `vector/signals` inside `render()`. Browser launch is pinned to `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` (`:89`). Loopback only; other HTTP is aborted (`:98`). Not re-executed here (`data/` is sparse-omitted; no Chrome at that path).

`--smoke` is the same script and only scenario `known`, three cells: `1440/dark/en`, `390/light/zh`, `320/dark/en` (`:90-92`). 768 is absent from smoke.

Canonical rest pixels, 390 (named `mobile`) and 1440 (named `desktop`) only, both themes and both locales (8 rest cells), plus the force-state argv inside `research/crypto_science/r15/capture_canonical.py` at `fd8095012e91`:

```text
python3 scripts/capture_page_evidence.py \
  --site-dir <loopback site> --routes /crypto.html \
  --output-dir <receipt dir> --manifest <receipt>/manifest.json \
  --smells <receipt>/smells.json \
  --viewports desktop,mobile --locales en,zh --themes dark,light --max-pages 1
```

`check_ui_visual_evidence.py --selftest` checks a planted receipt. It does not produce a cell and cannot certify 320 or 768.

Vector has no cell in this matrix. Its first proof is the HTML render test below, then a browser pass that does not exist yet.

## 2. Four controlled states

Fixtures live in `tests/test_crypto_consumer_states.py`. No live provider call. `store.read` is replaced so `lib/store._path` cannot mkdir `data/`. `build_asset_states` / `build_btc_options` run with a reader that returns None. `event_calendar._fetch_upcoming_auctions` is replaced with `[]` because `us_macro_events(use_fred=False)` still calls it (`engine/event_calendar.py:433`, mkdir + TreasuryDirect at `:297-317`). A first unpatched run did create `data/macro/auction_cache`; that directory was removed. After the patch, `data/` stayed absent.

| State | Crypto fixture | Vector fixture | Visible result |
| --- | --- | --- | --- |
| Missing history | Cockpit `btc.decision/v1`, status `ok`, `integrity_ok`, exposure `0`, `as_of` `2026-09-26` matching the signals index. `market.history` dates/vals empty. Universe row price None, change None. | Four NaN closes, `alloc_optimal` `0.0`. Decision ok, exposure `0`. Flow regime None. Hero `price=100`, `chg24=0.0` because `:360-361` cannot render None (patch, not applied). | Crypto: `data-market-history-state="unavailable"`, "Market history unavailable", no `ilx-path`, no `ilx-null`, no `<svg` in `#crypto-overview` or `#market-board`. Spark cell "Building history", price/change `—`. Budget stays the real zero: "The recorded target is cash—not missing data." Vector: `data-vector-replay-state="unavailable"`, "Interactive replay unavailable", "Price history is incomplete", no `#vec-risk-chart`, no `polyline points=`, `data-flow-state="unavailable"`, "Activity unavailable". |
| Valid zero | Same decision with exposure `0`. Six market-cap dates `2026-09-21..26`. Row price `100`, `change_24h` `0.0`. | Four finite closes, `alloc_optimal` all `0.0`. Decision ok, exposure `0`, action `STAY_OUT`. Flow `no_activity` (share None, net `0`). | Crypto tape `data-market-history-state="available"` and `ilx-path`. Desk budget `0%` / `100%`, not "Budget unavailable". H5 "Model holds cash." and "A valid 0% crypto target means 100% cash." Board `$100` and `0.0%`. Vector: replay `valid`, `#vec-risk-chart` present, no "Decision unavailable", `data-decision-exposure="0"`, flow "No activity observed" and "not 0%". |
| Stale / unknown budget | Status `ok`, `integrity_ok`, exposure `60`, `as_of` `2026-09-25` against signals date `2026-09-26` (`CANONICAL_DECISION_AS_OF_MISMATCH`). History present. `CANONICAL_DECISION_UNAVAILABLE` hits the same template else branch (`:326-328`, `:439-444`); this fixture is the dated one. | Finite prices and alloc `0.4`. Decision `status=unavailable`, `integrity.ok` false, `final` None. Flow `stale=True`. `risk_index` None. | Crypto: `data-desk-budget-state="unavailable"`, "Budget unavailable", "An unavailable target is not a cash recommendation.", decision date `2026-09-25`, reason "The decision belongs to a different snapshot…". `60%` absent from the budget and H5 slices. Vector: "DECISION TEMPORARILY UNAVAILABLE", `data-decision-status="unavailable"`, no `data-decision-exposure`, "Stale observations", share `—`. Overview risk copy is "Unavailable" (`:430-431`). Shelf S2 still prints a Chinese high/low word from `risk_on` (`:494`) until the patch lands. |
| Partial | Exposure `40`, matching `as_of`, signals column `open` only (no `close`). History present. | Finite closes, `alloc_optimal` `[0.4, NaN, 0.4, 0.4]` so `valid` stays true and `performance_valid` is false. Decision exposure `40`. Flow `n_hours=23`. | Crypto: both state attributes `breakdown-unavailable`, "Breakdown unavailable", "Total budget known; asset breakdown unavailable.", `40%` and `60%`, no `alloc-seg`, "No asset percentages are inferred." Vector: `#vec-risk-chart` present, "the chart preserves them as unknown", "Allocation simulation unavailable", `data-flow-state="coverage_gap"`, "Incomplete 24-hour window", "Missing observations are not zero", `data-decision-exposure="40"`. The valid-branch template does not print `issue.message_en`; the test does not require it. |

Altseason state word "Unavailable" is in the leverage slice. The test does not lock `--v:0%`, so the meter patch does not turn the test red.

`python -m pytest tests/test_crypto_consumer_states.py -q -p no:cacheprovider -x` → `4 passed in 1.37s`. No case is marked `needs_full_checkout`. Rendered HTML is asserted free of the promotion word.

## 3. Concrete assertions

These are the browser checks inside `render_and_check.py` at `fd8095012e91` (path endpoints `:122-126`, geometry `:128-137`, keyboard `:155-164` of that file). Selectors below are the current R2 template.

- Visible path endpoint, only when `data-market-history-state="available"`: `#crypto-overview .desk-tape .ilx-path`. Computed `strokeDasharray == "none"` (rule at `crypto.html.j2:106`), `strokeDashoffset` within `0.1` of 0 after `ilx-in`, and `isPointInStroke(getPointAtLength(getTotalLength() - 0.5))` true for every such path. Missing history: zero `.ilx-path` and zero `.ilx-null` under `#crypto-overview`. Vector missing history: no `#vec-risk-chart` and no `polyline points=` (axes SVG is `vector.html.j2:519` and stays absent while `presentation.axes` is empty).
- Row/cell geometry: `#crypto-overview` `scrollWidth` overflow flags, every `p` font-size `>= 12.5`, every overview link box height `>= 44`. Market-board row is `.market-row` (`crypto.html.j2:160-165`): five columns, `.asset` grid `30px 48px minmax(0,1fr)` on the R2 file. After the clean `#7645` merge that column is `30px minmax(64px,max-content) minmax(0,1fr)` (merged line 165) and, at `max-width: 720px`, `#market-board .market-row` becomes `minmax(0,1fr) 100px 66px` with `.asset` `20px minmax(0,1fr)` (merged lines 286–292). Re-measure at 320 and 390; both rule sets are in the merged file.
- Keyboard, in order: `.desk-nav a[href="#money-flows"]`, then `#leverage-heat`, then `#allocation`, Enter, URL hash matches. Then `.desk-chart-foot a` click, `#universe-snapshot .universe-coverage > summary` focus, Enter, `details.open`. Brain: `[data-crypto-brain]` focus, Enter, focus inside `#mmb-panel`, Escape returns focus to the entry. Focus rings: `crypto.html.j2:69` and `:79`, `vector.html.j2:55-56`, `:234`, `:288`, house style `:153-156`. `#7645` adds `#market-board .more-market summary:focus-visible` (merged line 284) and `role="table"` / `role="row"` / `role="cell"` (merged line 383). Preserve those semantics.
- Reduced motion: `templates/_crypto_house_style.html.j2:389-396` sets `transition: none` on `.crypto-shelf`, `.shelf`, `.market-row`, `.sensor`, `.asset-lane`, `.equity`, `.event`, `.axis-row`, `.watch-item`, `.complex-card`, `.study-fold` under `prefers-reduced-motion: reduce`. `vector.html.j2:323` sets `.ilx-path,.ilx-bar { animation: none !important }` under the same media query. Assert `getComputedStyle` transition/animation is `none` for those selectors when the media query matches. The endpoint rule `stroke-dasharray: none` (`crypto.html.j2:106`) is what makes the path visible without waiting on the dash reveal.

## 4. Three-way merge risk — `templates/crypto.html.j2`

Base for `#7645` is `2b62f496` (its merge-base with `origin/main`). `templates/crypto.html.j2` is identical from merge-base `7150f29a` through `origin/main` (empty diff), so the R2 file in this worktree is "ours". Theirs is `74298e32`.

`git merge-file -p` (ours = worktree, base = `2b62f496`, theirs = `74298e32`) exits 0, 0 conflict markers, 529 lines. It is not a conflict stop. It is a silent semantic replacement on lines R2 left equal to the base.

`#7645` hunks vs `2b62f496` (old line numbers):

- `:70` `.asset` `30px 48px` → `30px minmax(64px,max-content)`.
- Insert after the house-style include (`:157`): `#market-board .more-market summary` min-height 40px, `touch-action`, `focus-visible`, and `@media (max-width: 720px)` board grid.
- `:170` "Daily class read" → "Daily snapshot".
- `:185-199` Market Board: `id="crypto-market-title"`, "assets tracked", `role="table"` / `aria-labelledby`, `role="row"` / `columnheader` / `rowheader` / `cell`, "24h change", `title="{{ a.name }}"`, summary "More assets" instead of "Expand ranks 21–50".

R2's own inserts (desk CSS, history gate, budget aside, H5 copy, brain script) do not edit those base lines, so the merge keeps both the R2 desk and the `#7645` board. Needle counts in `/tmp/cx-merged-crypto.j2`: "Daily snapshot" 1, "Daily class read" 0, "assets tracked" 1, "assets accruing daily" 0, `role="table"` 1, "More assets" 1, "Expand ranks" 0, "24h change" 1, `>24H<` 0, `minmax(64px,max-content)` 1, `30px 48px` 0, "Market history unavailable" 1, `stroke-dasharray:none` 1, `focus-visible` 3, `touch-action` 1. Merged line map: desk CSS 65, endpoint rule 106, `.asset` is the `#7645` grid at 165, mobile board rules 283–292, "Daily snapshot" 314 inside the R2 hero, `role="table"` 383.

Risk: a reviewer can miss that R2 board copy and the 48px column were replaced, and that the `#7645` `@media (max-width: 720px)` block now sits beside the R2 `.market-row` grid (`crypto.html.j2:160`). Re-proof 320 and 390. Do not drop `#7645` roles or the summary focus ring. `_navlinks.html.j2` is not part of `#7645`'s own delta.

## 5. What R15 still covers

`research/CRYPTO_R15_DESK_INTEGRATION_RESULTS.md` and `research/crypto_science/r15/completion/browser_proof.json` exist only at `fd8095012e91` (read with `git show`; not in this worktree). The JSON has 112 cases, 0 failures, `source_head` `ba258da9217c6fc905475511d5597be5d8f37af0`, the seven scenarios, widths 320/390/768/1440, both themes, both languages.

Still a true statement about the R2 template blob (byte-identical to `ba258da9` for the files listed at the top):

- Budget, history, funding-dash, and eight-shelf assertions on the 96 non-`combined` cells.
- The endpoint rule `stroke-dasharray: none` and the repaired `isPointInStroke` check.
- `combined` is a different template: `render()` swaps in `combined_crypto.html.j2` only for that scenario, and the script then requires `#market-board [role=table]` and "Daily snapshot". Those 16 cells are the `#7645` overlay, not the R2 file alone.

Not still a proof of current pixels or of the merge:

- `templates/theme.css` differs from `fd8095012e91` to `HEAD` by 13 lines (`11 insertions, 2 deletions`). Full-page shots include nav and theme. Whether those 13 lines move a pixel was not opened here. UNVERIFIED as a visual delta; the diff stat is verified.
- After the three-way, market-board copy, roles, the `.asset` column, and the 720px grid change. Every cell that shows the board needs re-proof. 320 and 768 are produced only by `render_and_check.py`, not by `capture_page_evidence.py` or `check_ui_visual_evidence.py`.
- Canonical capture is desktop/mobile only.
- Vector was never in the 112. All Vector cells need a first browser proof. `tests/test_crypto_consumer_states.py` is HTML, not pixels.
- This lane did not re-run the browser matrix, did not open the PNG hashes, and did not run `research/crypto_science/r15/verify_final.py` (script not in the worktree; it also hashes `data/` inputs).

## Patches for the integration writer

Not applied. `git apply --check` succeeded for both.

- `research/crypto_science/patches/cx-t19p-20261012__crypto.html.j2.patch`
  - `crypto.html.j2:312`: history gate `>= 2` → `>= 4`, matching `regime_tape`'s floor so a 2–3 point series shows "Market history unavailable" instead of the hairline.
  - `crypto.html.j2:404`: omit `style="--v:…"` when `market.heat.altseason.value` is none. A missing score must not paint a 0% rail.
- `research/crypto_science/patches/cx-t19p-20261012__vector.html.j2.patch`
  - `vector.html.j2:360-361`: `price` or `chg24` none renders `—` and skips the pos/neg class.
  - `vector.html.j2:494`: `risk_index` none renders `—` and "Unavailable" / "暂无", matching the overview guard at `:430-431`.

No patch to `scripts/build_crypto.py`, `scripts/build_vector.py`, `scripts/capture_page_evidence.py`, or the allocation engine.
