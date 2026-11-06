# Sector Central — shell/router/builder contract (observed)

Observed facts of the tree at `3d8d14acdc8de99fa2c17316aa22de6177364dbc`. Packet SIC-I01.
Every claim cites `path:line` in this tree. Nothing here is a proposal.

## Routes

The in-template router is `templates/si_workspace.js` (loaded by the shell at
`templates/sector_central.html.j2:4058`). It is hash-based: `route()` reads
`location.hash` (`templates/si_workspace.js:348-350`), is bound to `hashchange`
(`templates/si_workspace.js:361`) and runs once at boot (`templates/si_workspace.js:365`).
View switching is `activate()` (`templates/si_workspace.js:297-347`): it toggles `.on` on
`section.si-view[data-view]` and on `.si-view-btn`, sets `aria-current`, updates
`document.title`, lazy-mounts the view's organ scripts (LAZY table
`templates/si_workspace.js:100-110`) and dispatches `si:view` (`templates/si_workspace.js:340`).

Observed route set (== expected set; no differences): **overview, map, moving, money,
explore, confluence** (`var VIEWS` `templates/si_workspace.js:17`; rail buttons
`templates/sector_central.html.j2:1495-1506`; view sections at 1509 / 2149 / 2284 / 2312 /
2348 / 2404).

| route id | hash/history form observed | mount element | populating function | tests that cover it today |
|---|---|---|---|---|
| overview | `#overview`; empty hash → `activate('overview')` + `replaceState` to `#overview` (`si_workspace.js:355-356`) | `section.si-view[data-view="overview"]` (`sector_central.html.j2:1509`) | server-rendered + inline rvx scripts (`sector_central.html.j2:1605+`); `activate()` `si_workspace.js:297` | `tests/test_si_workspace_shell.py:78,86,91`; `tests/test_sector_intelligence_page.py` |
| map | `#map`; valid `?g=` deep link with empty hash lands here via `replaceState '#map'` (`sector_central.html.j2:4043-4044`) | `section.si-view[data-view="map"]` (`sector_central.html.j2:2149`) | LAZY `@cycles` → `loadCycles()` injects `sector_cycles_data.js`,`mm_charts.js`,`sector_cycles.js` (`si_workspace.js:101,126-135`); mr-panel inline script (`sector_central.html.j2:3460-4051`) | `tests/test_si_workspace_shell.py`; `tests/test_sector_central_measured_panel.py` |
| moving | `#moving` | `section.si-view[data-view="moving"]` (`sector_central.html.j2:2284`) | LAZY `subsector_rotation.js`,`rotation_events.js`,`desk_watch.js` (`si_workspace.js:102`); accumulation panel server-side (see Mount points) | `tests/test_si_workspace_shell.py` |
| money | `#money` | `section.si-view[data-view="money"]` (`sector_central.html.j2:2312`) | LAZY `heatmap.js` (`si_workspace.js:103`); internals cards inline (`sector_central.html.j2:2318-2332`) | `tests/test_si_workspace_shell.py` |
| explore | `#explore` | `section.si-view[data-view="explore"]` (`sector_central.html.j2:2348`) | LAZY `subsector_rotation.js`,`time_machine.js` (`si_workspace.js:104`); table/chart inline (`sector_central.html.j2:2357-2383`) | `tests/test_si_workspace_shell.py`; `tests/test_xpv2_sector_r3_fixture.py` (`tm-mount` anchor) |
| confluence | `#confluence` | `section.si-view[data-view="confluence"]#si-confluence` (`sector_central.html.j2:2404`) | LAZY `subsectors.js` self-boots into `#sc-app` (`si_workspace.js:105-109`) | `tests/test_si_workspace_shell.py:99-103` |

Non-view hash families the router handles:
- `#theme-<id>` — router short-circuits to overview (`si_workspace.js:351`); the page's
  `resolveThemeHash()` then `location.replace`s away to `basket/<id>.html`
  (`sector_central.html.j2:2739-2745`, called once at boot `:2998`).
- `#read-<id>` — overview + held trace-expand of that board row (`si_workspace.js:284-292,352`).
- 24 legacy anchors: 21-key `LEGACY_ANCHORS` (`si_workspace.js:52-76`) merged with 3-key
  `LEGACY_ANCHORS_S2` (`si_workspace.js:83-88`) → `[view, intra-view scroll target]`
  (`si_workspace.js:354`). Pinned by `tests/test_si_workspace_shell.py` and
  `tests/test_xpv2_sector_r3_fixture.py::TestLegacyAnchors`.
- unknown hash → overview (`si_workspace.js:355`).
- history (non-hash) entries: mr-panel group selection pushes/replaces `?g=<id>`
  (`sector_central.html.j2:3912-3915`, `3932-3934`).

**Back/Forward verdict: RESTORES_VIEW.** The only `popstate` listener in the shell is the
mr-panel's (`sector_central.html.j2:4028-4030`); it restores ONLY the measured-read group
selection from `?g=`. The view itself is restored because history traversal across hash
entries fires `hashchange` → `route()` → `activate(view, null)` (`si_workspace.js:361`,
`353`); no scroll target is reapplied on that path (`activate` scrolls only when a target
is passed, `si_workspace.js:342-346`), no filter state is saved/restored, and
`history.scrollRestoration` is never touched (grep: 0 hits in `si_workspace.js`,
`sector_central.html.j2`, `sector_cycles.js`).

## Mount points

- `#tm-mount` — empty div at `templates/sector_central.html.j2:2389` (explore view).
  Populated by `templates/time_machine.js::mount()` (`templates/time_machine.js:189-200`),
  injected on first explore activation (`si_workspace.js:104`).
- `#accumulation-section` — bare anchor span at `templates/sector_central.html.j2:2306`
  (moving view); the panel is server-rendered immediately after it by
  `{% include "_accumulation_watch.html.j2" %}` (`sector_central.html.j2:2307`), which
  consumes the `accumulation` / `accumulation_universe_n` render args
  (`templates/_accumulation_watch.html.j2:11,13`) built by
  `scripts/build_sector_central.py::_accumulation_rows` (`scripts/build_sector_central.py:106-135`,
  called `:555`). Nothing populates the span itself at runtime.
- `#si-measured` — `<section id="si-measured">` at `templates/sector_central.html.j2:2196`
  (map view). Populated by the inline mr-panel IIFE `templates/sector_central.html.j2:3460-4051`
  (`root` binding `:3469`; `render()` `:3556`; `renderDetail()` `:3688`; `renderHist()` `:3724`),
  reading `window.SECTOR_CENTRAL.measured_read`.

Each of the three ids appears exactly once in the template (grep `id="..."`: 1 hit each).

## Builder inputs/outputs

`scripts/build_sector_central.py::main` (`scripts/build_sector_central.py:412-620`). Fail-soft
by contract; `strict=True` fails closed (`:427-429`, `:552-553`, `:580-585`).

Inputs read:
- `config.load()`: `storage.site_dir` (`:421`), `sector_central_gate.gated|preview_rows`
  (`:78-89`), `holdings_signals.panel_top_n` (`:115`).
- `engine.sector_central.compute()` (`:425-426`; engine entry `engine/sector_central.py:851`).
  One level in, the engine reads `data/regime/latest.json` (`engine/sector_central.py:89`,
  keys `quad`,`quad_name` `:94`), `site/marketdata/sp500_heatmap.json` (`:183`, key
  `size_basis` `:186`), `data/us_sector_rotation/latest.json` (`:662`), site
  `marketdata/rotation_events.json` (`:695-698`, keys `ts`,`asof`), and
  `data/baskets/membership.json` (`:884-885`, key `baskets`→`members[].symbol`). The builder
  consumes from the result: `sectors` (`:430`,`:617`), `as_of` (`:530`,`:536`,`:572`),
  `baskets` (`:617`), `grader` (`:438-442`).
- `engine.sector_central_grader` `append_central_log`/`grade` (`:436-438`).
- `site/basketdata/si_handoff.json` (`:468-470`) — keys consumed: `theme_context` (`:561`),
  `factor_season` (`:562`), `flow` (`:563`), `basket_member_syms` (`:564`),
  `generated_utc` (`:530`,`:572`).
- `site/basketdata/action_board.json` (`:481-486`) — keys: `action_board` (`:485`), `as_of`
  (`:533`); raw bytes hashed (`:486`).
- `site/basketdata/baskets.json` (`:499-506`) — keys: `theme_intel.act_now` (+`theme_intel.as_of`
  `:533-534`), `as_of` (`:535`); raw bytes hashed (`:503`).
- via `_theme_tape_view` (`:138-165`, called `:571`): `site/marketdata/subsector_rotation.json`
  (`:142`,`:161`), `site/factordata/us_standouts.json` (`:143`,`:150`),
  `site/basketdata/foresight_cascade.json` (`:154`,`:157`) → `engine.theme_tape.build_theme_tape`
  (`:160`).
- via `_accumulation_rows` (`:555`): `engine.holdings_signals.sector_residual_panel` (`:111`),
  `engine.playbook.SECTOR_NAMES` (`:112`).
- via `_flows_section_html` (`:460`): `collectors.sponsors.sector_flow_periods` (`:349`),
  `engine.i18n.t` (`:350`), `engine.playbook.SECTOR_NAMES` (`:351`).
- asset copies from `templates/` (`:593-606`).

Outputs written:
- `site/sector_central_data.js` — `window.SECTOR_CENTRAL=` (`:444-445`).
- `site/sectordata/sector_central.json` (`:446-449`).
- `site/premiumdata/sector_central.json` — ALWAYS written, gated or not (`:228`,
  `write_payload` `:213-248`).
- `site/sector_central.html` (`:573` via `lib.pages.write_page`).

China/zh variant: `main()` writes none. `site/sector_central_china.html` is built by a
separate builder, `scripts/build_china_sector_central.py` (page `:138`, data JS `:67`,
`chinasectordata/sector_central.json` `:70`; reads `basketdata/theme_context_cn.json` `:90`,
`factordata/cn_reversal_sleeve.json` `:100`, `chinabasketdata/act_now_cn.json` `:123`).

## Generation/session fields

Render kwargs (`scripts/build_sector_central.py:557-572`): `flows_html`, `pgate`,
`bottoming`, `theme_context`, `factor_season`, `flow`, `basket_member_syms`,
`action_board`, `source_as_of`, `baskets_sha256`, `action_board_sha256`, `accumulation`,
`accumulation_universe_n`, `theme_tape`, `generated_utc`.

- `generated_utc` = `si_handoff.generated_utc` or engine `as_of` (`:530`, passed `:572`);
  rendered as "Built"/"Generated" stamps (`templates/sector_central.html.j2:2439`, `:2447`).
- `source_as_of` cascade: `action_board.as_of` → `baskets.theme_intel.as_of` →
  `baskets.as_of` → engine `as_of` (`:531-538`).
- session/provenance attrs on the hero: `data-si-as-of`, `data-si-baskets-sha256`,
  `data-si-action-board-sha256` (`templates/sector_central.html.j2:1513-1515`).
- `pgate` gates the Act-Now board; the gated branch hydrates from
  `premiumdata/sector_central.json` (`templates/sector_central.html.j2:4059-4160`).

## Navigation family + render lane

- Family: authenticated/product — `{% include "_site_nav.html.j2" %}`
  (`templates/sector_central.html.j2:1431`; china `:791`; cycles `:32`). No
  `_public_nav.html.j2` anywhere in these templates (grep: 0 hits).
- `public-render-fastlane` (`.github/ci/legacy-jobs.yml:22245`) is runner-free
  (`if: ${{ false }}` `:22246`, "executed inside ci-pack"). Its single run line (`:22288`)
  includes `tests/test_si_workspace_shell.py`, `tests/test_sector_central_paper.py` and
  `tests/test_sector_central_data_is_sync.py` — so the fastlane covers the Central shell's
  router/paper/data-sync contracts, but NOT `tests/test_sector_central.py` (runs in
  `unrun-scoring-engine`, `.github/ci/legacy-jobs.yml:29777`) and NOT the gate suite
  (`tier-gate`, `.github/ci/legacy-jobs.yml:6289`).

## Sector Cycles counterpart

- Routes: `/sector_cycles.html` has NO hash router. Single view; family tabs `#sc-tabs`
  (`data-fam` sectors/baskets/nasdaq/russell, `templates/sector_cycles.html.j2:49-54`).
  Hash form is a focus deep link `#<series-id>` consumed once at boot
  (`templates/sector_cycles.js:2033-2038`); focus changes call `replaceState`
  (`templates/sector_cycles.js:1018`) — no history entries are pushed. No `hashchange` or
  `popstate` listener exists in `sector_cycles.js` (grep: 0 hits) → Back/Forward verdict
  for this page: DOES_NOT_RESTORE (focus state).
- Mount points: `#sc-chart` (`templates/sector_cycles.html.j2:88`), `#sc-groups`/`#sc-chips`/
  `#sc-baskets` (`:83-85`), detail panels `#sc-panel-default`/`#sc-panel-focus` (`:96-97`),
  `#sc-cards` (`:106`) — all populated by `templates/sector_cycles.js` (boot at `:2028+`,
  `renderPanel` `:1021+`). CSS: `templates/sector_cycles.css` (page) + shared `cycle.css`.
- Builder `scripts/build_sector_cycles.py::main` (`:71-162`). Inputs: `engine.sector_cycles.compute()`
  (`:80-81`; entry `engine/sector_cycles.py:1302`), `data/sector_cycles/narratives(.<epoch>).json`
  (`:51`, `_load_narratives` `:43-55`), `data/sector_cycles/cycle_dna(.<epoch>).json` (`:64`,
  `:58-68`), `engine.cycle_forward_log.append_forward_log` (`:91-92`),
  `scripts._narrative_ttl.enrich_narr_ttl` (`:102-103`), `scripts._cycles_payload.split_cycles_payload`
  (`:116-117`), `config storage.site_dir` (`:74`). Outputs: `site/sector_cycles_data.js` (`:118`),
  `sector_cycles_series_data.js` (`:121`), `sector_cycles_narr_data.js` (`:124`),
  `sector_cycles_dna_data.js` (`:127`), `site/sectordata/sector_cycles.json` (`:134`),
  `site/sector_cycles.html` (`:146`); copies `sector_cycles.css`/`sector_cycles.js` (`:148-151`)
  and shared `mm_charts.js`/`cycle.css` if absent (`:152-158`). No template render args —
  `render()` is called with none (`:145`); the page reads everything from the data JS.
- China variant: separate builder `scripts/build_china_sector_cycles.py` →
  `site/sector_cycles_china.html` (`:170`), `sector_cycles_china_{data,series_data,narr_data,dna_data}.js`
  (`:139-148`), `chinasectordata/sector_cycles.json` (`:155`), `chinasectordata/sector_cycles_basket_map.json`
  (`:157`).
- Nav family: `_site_nav.html.j2` (`templates/sector_cycles.html.j2:32`). Render lane:
  `tests/test_sector_cycles.py` runs in `lr-rotation-evidence-modes`
  (`.github/ci/legacy-jobs.yml:17620`), not in the fastlane run line (`:22288`).

## Gaps

1. No test pins the shell's Back/Forward behaviour — grep of `tests/` for `popstate` +
   sector_central/si_workspace finds nothing (0 hits); the `popstate` handler at
   `templates/sector_central.html.j2:4028` and the `hashchange` binding at
   `templates/si_workspace.js:361` are unpinned.
2. Scroll origin is not restored on Back/Forward by shell code: `activate(view, null)` on
   the hashchange path reapplies no scroll target (`templates/si_workspace.js:342-346`);
   `history.scrollRestoration` is never set (0 hits). Native browser restoration is the
   only mechanism.
3. `#accumulation-section` is an empty anchor span (`templates/sector_central.html.j2:2306`);
   the panel beside it is server-rendered (`:2307`) — the span itself has no runtime
   populator (harmless; the id exists for the LEGACY_ANCHORS jump).
4. `templates/sector_cycles.js` keeps no `hashchange`/`popstate` handler, so a Back from an
   in-page focus deep link restores nothing (`templates/sector_cycles.js:1018`, `:2033-2038`).
5. The fastlane job is runner-free (`if: ${{ false }}`, `.github/ci/legacy-jobs.yml:22246`) —
   its sector_central suites reach CI only through the ci-pack execution path, so a broken
   run line there surfaces in ci-pack, not as a standalone red job.

## Evidence

- Router: `templates/si_workspace.js:17` (VIEWS), `:52-88` (anchors), `:100-110` (LAZY),
  `:297-347` (activate), `:348-357` (route), `:361` (hashchange binding), `:365` (boot call).
- popstate (mr-panel `?g=` restore), quoted:
  `templates/sector_central.html.j2:4028-4030` —
  `window.addEventListener('popstate', function () {`
  `  select(new URLSearchParams(location.search).get('g'), { user: false, push: false });`
  `});`
- Empty/unknown hash: `templates/si_workspace.js:355-356` — `activate('overview',null);` /
  `if(!h&&history.replaceState) history.replaceState(null,'','#overview');`; `?g=` empty-hash
  landing `templates/sector_central.html.j2:4043-4044`.
- Mounts: `templates/sector_central.html.j2:2389` (`#tm-mount` div), `:2306-2307`
  (`#accumulation-section` + include), `:2196` (`#si-measured`); `templates/time_machine.js:189-190`;
  `templates/_accumulation_watch.html.j2:11,13`; mr-panel `templates/sector_central.html.j2:3460-3469`.
- Builder: `scripts/build_sector_central.py:412-620` (reads cited inline above), render kwargs
  `:557-572`, outputs `:445`, `:448`, `:228`, `:573`.
- Nav/lane: `templates/sector_central.html.j2:1431`; `.github/ci/legacy-jobs.yml:22245-22288`
  (fastlane), `:6289` (tier-gate), `:29777` (unrun-scoring-engine), `:17620` (cycles suite).
- Cycles: `templates/sector_cycles.html.j2:32,49-54,88,96-97,106`;
  `templates/sector_cycles.js:1018`, `:2033-2038`; `scripts/build_sector_cycles.py:71-162`;
  `scripts/build_china_sector_cycles.py:139-170`; `engine/sector_cycles.py:1302`.
