# Sector Intelligence — observed contracts of the four receivers (SIC-RCV)

Observed facts of the tree at `66bc4205abd06bdce30a24e45b88692d7ef977d1`. Every claim cites `path:line`; storage keys, endpoints and parameter names are quoted verbatim. Nothing here is a proposal. Convention as `INTEGRATION_CONTRACT.md`.

## Research receiver

Surfaces: `site/research_vault.html`, `site/research/index.html`, `site/research/<slug>.html`, `site/research_screener.html`; saved views `templates/fif_saved_briefcase.js`; nightly producer `engine/fif_saved_research_notifications.py`.

### Params

`grep -nE "URLSearchParams|location\.search|location\.hash|searchParams"` over the four research templates + `fif_saved_briefcase.js` → **0 hits**.

| parameter | reader | effect | ignored-if-unknown? |
|---|---|---|---|
| (none read) | — | URL never read | n/a |

Pre-fill per field: subject **NOT FOUND**; question **NOT FOUND**; source snapshot **NOT FOUND as a link-read** — `source_snapshot_at` exists only as a stored policy key (`templates/fif_saved_briefcase.js:42` `var POLICY_KEYS = ['selection', 'source_snapshot_at', 'recorded_at'];`); observation date **NOT FOUND**; evidence mode **NOT FOUND** (greps: the one above + `subject|question|observation|evidence_mode`).

### State

`localStorage['theme']`/`['lang']` pre-paint, device-scoped (`templates/research_vault.html.j2:12`, `research_index.html.j2:18`, `research_report.html.j2:25`, `research_screener.html.j2:21`). `templates/fif_saved_briefcase.js:27` — `var STORAGE_KEY = 'mastermind.filing_forensics.saved_research.v1';` — container `{contract:"fundamental_forensics.saved_research.v1", saved_views:[…]}`; stored-view key set `VIEW_KEYS` `:48-49` (schema, request_contract, id, name, created_at, updated_at, issuer, request, peers, view, pinned, saved_against, evidence_refs, watch). **Device-scoped** — no identity attach ("never fetches, polls, sends a notification, or talks to an account service" `:5-7`); browser network grep over all five files → 0 hits.

Server-side only (nightly): `engine/fif_saved_research_notifications.py` → Supabase REST `f"{SUPABASE_URL}/rest/v1/{path}"` (`:537`, default `https://fsldfzlxyavsuwqbceod.supabase.co` `:59-61`); paths `watchlists?name=eq.` + `DESIGNATED_LIST_NAME = "Filing Forensics"` (`:71`), `watchlist_symbols` (`:604`), POST `alert_outbox` (`:642`). **Account-scoped** by the designated list's `user_id` (`:456-474`); dedupe `f"fif:{kind}:{cik}:{event_ref}:{user_id}"` (`:226-229`). Delivery belongs to `scripts/drain_alert_outbox.py`, not this module.

### Return

**NOT FOUND** (`grep -nE "history\.back|window\.back|[?&](return|from|origin)=|referrer"` → 0 hits). Plain hrefs: screener rows → `stocks/{{ row.ticker }}.html` (`templates/research_screener.html.j2:74`, `:96`); vault cards → `research/<slug>.html` injected at build (`scripts/build_research_vault.py:306-314`).

### Builder

`scripts/build_research_vault.py` → `site/research_vault.html` (`:283`, `:320`); reads `data/research_vault/catalog.json` (`:54`, schema `research_vault.catalog.v1` `:57`); bakes preview island `#rv-catalog` (`templates/research_vault.html.j2:853`). `scripts/build_research_pages.py` → `site/research/<slug>.html` (`:393`) + `site/research/index.html` (`:411`); reads catalog + `data/research_vault/excerpts.json` (`:65`). `scripts/build_research_screener.py` → `site/research_screener.html` (`:185`) + `site/research_screener.json` (`:178-180`; names `:22-23`); reads `site/stockdata/*.json` (`security_state.v1`/`valuation_scenario.v1` `:36-86`); engine `compile_research_screener` (`:87-92`).

### Tests

Pages: `test_research_screener.py`, `test_research_pages.py`, `test_seo_meta_rollout.py`, `test_validated_claims_thirdparty.py`, `test_svg_wrapper_clipping.py`. Briefcase: `test_fundamental_forensics_saved_store_schema.py` + `fundamental_forensics_saved_research_roundtrip/saved_url_state/investigation_manifest_mapping/investigation_manifest_emitter/pf_health/pf_page` (`.mjs`). Notifications: `test_fif_saved_research_notifications.py`, `test_fif_x2_ownership_guards.py`.

## Watch/save owner

Surface: `site/watchlist.html` (`watchlist.html.j2` + `watchlist.js` + `watchstore.js` + `watchlist_risk.js` + `account.js`); nightly `scripts/run_watchlist_sentinel.py` over `engine/watchlist_sentinel.py` / `engine/watchlist_alerts.py`.

### Params

No `URLSearchParams` in the five files. One hash family is read:

| parameter | reader | effect | ignored-if-unknown? |
|---|---|---|---|
| `#wl=<b64>` / `#wl.<name>=<b64>` | `templates/watchlist.js:2093-2104` (`consumeShareHash`, booted `:2422`) | imports a shared list blob (`importCode` `:2104`; scoped form only for the list of that name `:2099`); fragment then stripped `history.replaceState(null, '', location.pathname + location.search)` (`:2103`) | yes — non-`wl` hashes left alone; query never read |

Outbound only: `https://app.mastermind-x.com/terminal?sym=<t>&from=macro` (`templates/watchlist.js:1104`); writer `b64enc(JSON.stringify(blob))` (`:2071`).

### State

localStorage (device): `templates/watchlist.js:25` `var KEY = 'mdash.watchlist.v1';`; `:37` `'mdash.wl.' + listId + '.v1'`; `:756` `var MODE_KEY = 'mdash.ws.mode.v1';`; `:1344` `localStorage.setItem('mdash.ws.entry.v1', JSON.stringify({ mode: wmode, text: box.value }))` (entry draft, restored `:1351`); sessionStorage `'mm.pact.watchlist_add'` (`:250-251`). `templates/watchstore.js`: `CACHE_PREFIX = 'mdash.wl.'`/`CACHE_SUFFIX = '.v1'` (`:102-103`); `'mdash.watchstore.folded.v1'` (`:94`); `PF_KEY = 'mdash.pf.v1'` (`:1320`); `'mdash.watchstore.pf_folded.v1'` (`:1321`); sessionStorage `'wl_auth_reloaded'` (`:2137`).

Cloud (account-scoped): browser→Supabase direct via `window.getSupabaseClient()` from `window.SUPABASE_CFG` baked at `templates/watchlist.html.j2:23` (`// null => local-only build`). Tables: `watchlists` (`id, user_id, name, position, created_at`; insert `{user_id, name, position}` `watchstore.js:525-584`), `watchlist_symbols` (insert `{watchlist_id, symbol, section, position}` `:755-756`), `portfolio_positions` (select `'id, user_id, ticker, shares, entry_price, entry_date, notes, status'` `:1722-1723`). Local blobs are device caches; the mirror is scoped by the Supabase session (browser key `'sb-' + SUPA.ref + '-auth-token'`, `templates/account.js:266`).

`/api/account*` identity (account.js `api()`): `Authorization: Bearer <token>` + `credentials: 'include'` (`templates/account.js:309-329`); base same-origin on mastermind-x.com else `window.MM_API` (`:40`); endpoints `/api/account` (`:344`), `/api/account/prefs` GET `:367`/POST `:419`, `/api/account/email` `:800`, `/api/account/password` `:813`, `/api/account/delete` `:825`, `/api/account/signout-everywhere` `:895`. No-identity fetches: `fetch('factor_betas.json')`/`fetch('transmission_chains.json')` (`templates/watchlist_risk.js:2336`, `:2347`).

Saved-item schema: local item `{ t: <symbol>, added, note }` (`watchlist.js:171-176`); blob `{v:1, updated, items, order, settings:{sort, buySoonOnly}}`; sector/name derived at render (`:329`), never persisted. Cloud row = the 5 columns above. **Non-symbol subject NOT FOUND**: `grep -nE "type|kind|subject|sector|theme|subindustry"` over the two stores hits only sync-result kinds + render strings; `watchstore.js:1972` — cloud table has "no kind/system/metadata column (Terminal 0001_init.sql:29-36)".

Condition alerts: (a) **persisted — server-side only**: `data/alerts/watchlist_alerts.jsonl` (`scripts/run_watchlist_sentinel.py:84`, `_append_alert_jsonl` `:364-401`) + `watchlist_sentinel_states.json` (`:82`) + `watchlist_sentinel_cooldown.json` (`:83`); client-persisted condition NOT FOUND (alert grep over `watchlist.js`/`watchstore.js` → CTA copy + `role="alert"` only). (b) **evaluated**: `engine/watchlist_sentinel.py::run_sentinel` (`:153`; enter-only `:197-203`) over `site/factordata/signal_gate.json` (`:203`) + `site/factordata/us_standouts.json` (`:215`); watched set from Supabase REST `GET /rest/v1/watchlists?select=id,user_id,watchlist_symbols(symbol)&user_id=eq.{uid}` (`:134`, `:140-143`). (c) **delivered**: Discord webhook `requests.post(config.secret("DISCORD_WEBHOOK_WATCHLIST") or …DISCORD_WEBHOOK_URL, …)` (`:409-438`; message `engine/watchlist_sentinel.py::format_discord_message` `:309`). No email/UI-badge path in these files.

### Return

**NOT FOUND** (same grep → only outbound `from=macro` `:1104` and the fragment strip `:2103`; no `history.back`, no inbound return/from/origin param).

### Builder

`scripts/build_site.py:8237-8243` → `site/watchlist.html`; render args `generated_utc`, `state_display_json`, `supabase_cfg_json=site_assets.supabase_cfg_json()`, `wri_regime_json` (from `data/regime/latest.json`), `sector_zh_json`, `starters_json` (config `watchlist.suggested`); gated by config `watchlist.enabled` (`:8210-8211`); copies `watchlist.js`/`watchlist_risk.js` (`:8256-8258`).

### Tests

Core: `test_watchlist_sector_i18n.py`, `test_watchlist_drawer_js.py`, `test_watchlist_workspace_js.py`, `test_watchstore_multilist_js.py`, `test_watchlist_books_js.py`, `test_unsubscribe_page.py`; portfolio: `test_portfolio_truth_a1a_js.py`, `test_portfolio_import_a1b_js.py`, `test_portfolio_auth_transition_js.py`, `test_portfolio_state_js.py`; fif/watchstore: `test_fif_watchstore_designated_list_js.py`, `test_fif_x2_ownership_guards.py`, `test_stockdata_consumer_recovery_js.py`; misc: `test_flow_observatory_workflow.py`, `test_ca1a_producers_contract.py`; sentinel: `test_watchlist_sentinel.py`, `test_recurring_briefs.py`; account: `test_account_actions.py`, `test_alert_prefs.py`, `test_shared_pref_atomics.py`, `test_supabase_browser_proxy.py` (+ more); `engine/watchlist_alerts.py`: none.

## Prophet/Screener destination

**Premise correction (observed)**: `/us_stocks.html` is NOT served from `templates/us_stocks_v2.html.j2`. It renders from `templates/dashboard.html.j2` in `mode="stocks"` — `scripts/build_site.py:8165-8175` (`_dash = env.get_template("dashboard.html.j2")`; `write_page(site / "us_stocks.html", _dash.render(…, mode="stocks"))`). `us_stocks_v2.html.j2` is a deliberately UNLINKED shadow → `site/us_stocks_v2.html` (`scripts/build_stock_board_v2.py:607-612`; self-description `templates/us_stocks_v2.html.j2:2-3`; `lib/seo.py:103`). Lab: `site/us_stocks_lab.html` from `engine/pick_lab/render.py:558-559` over `site/labdata/pick_lab.json` + `pick_lab_longhold.json`.

### Params (served page = dashboard.html.j2, mode=stocks)

Prophet partial included only in stocks mode: `templates/dashboard.html.j2:16380` `{% if mode == "stocks" %}{% include "_sector_prophet_context.html.j2" %}{% endif %}`.

| parameter | reader | effect | ignored-if-unknown? |
|---|---|---|---|
| `si_sector` (11 SPDR ids) | `templates/_sector_prophet_context.js.j2:22` `params.getAll('si_sector')` in `sectorProphetSelection(search)` (`:20-28`) | **identity only**: banner `#si-prophet-subject` + enables `#si-prophet-screener` (`:39-49`, `:63-77`). NO filter on arrival (`:2-3` "URL context supplies identity only; the native Screener owner applies its filter after an explicit click"); filter runs on click (`:70-76`) → `window.USStockTable._selectSector` → `selectSector` (`templates/dashboard.html.j2:20630-20648`) | invalid/dup → `{status:'invalid'}` (`:24-25`) → "Selected sector unavailable" + return link (`:56-61`); absent → hidden (`:46`). Other params never read; Clear preserves them (`:51-55`) |
| `life` (lifecycle ladder) | `templates/dashboard.html.j2:17864-17867` (`qp.has('life')`/`qp.get('life')`; legacy `#life=` same lines) | applies the ladder filter AT ARRIVAL (`if (initial) setLife(initial, { writeUrl: true })` `:17869`); valid set `VALID_LIFE` `:17768`; query-only `history.replaceState` write-back (`:17805-17813`) | invalid → `life = null` (`:17770-17771`) |

Producer: `sectorProphetHref` builds `us_stocks.html?si_sector=<ID>#sector-prophet-context` (`templates/_sector_prophet_context.js.j2:15-19`). Shell-level (not receiver logic): `templates/theme.js:394` `u.searchParams.get('symbol') || u.searchParams.get('sym')` feeds the global search; `theme.js:212-215` `hashchange` ticker deep-link.

### State

`localStorage['mdx_stocktable_us']` (`templates/dashboard.html.j2:20557` `var LS_VIEW = 'mdx_stocktable_us';`) — grid/table view pref, **device-scoped** ("no second table owner, store or localStorage key is introduced" `:20651-20653`). `theme`/`lang` pre-paint (dashboard `:302`, v2 `:110`, lab `:16`); `sessionStorage`/`document.cookie`: 0 hits in all in-scope templates. Tier payload `site/premiumdata/us_stocks.json` by `_write_us_payload` (`scripts/build_site.py:5659`; `US_PAYLOAD_DIR = "premiumdata"`/`US_PAYLOAD_NAME = "us_stocks.json"` `:4907-4909`; write `:5716`; schema `tier_payload.v1`, always written, empty when ungated `:5672-5675`); hydrated same-origin (`credentials: 'same-origin'` `:21541`, merge `:21480-21483`). Population: the scored standout board — `us_standouts.buy` rows embedded server-side in `<script type="application/json" id="us-stocktable-data">` (`templates/dashboard.html.j2:16828-16845`), NOT all US stocks. Lab = pick-engine evaluation; v2 = dual-lane shadow board (`templates/us_stocks_v2.html.j2:189-233`).

Screener pages: `confluence_screener.html.j2` → `site/confluence_screener.html` (`scripts/build_confluence_screener.py:229`, `:276`), reads `site/factordata/tech_confluence.json` (`:242`) + `site/marketdata/sp500_heatmap.json` (`:257-269`), writes `site/premiumdata/confluence_screener.json` (`:283-286`); client hydrates `credentials: 'same-origin'` (`templates/…:591-598`); NO url params (grep → 0). `research_screener.html.j2` fully server-rendered (no fetch, no params; greps → 0).

### Return

Fixed links, no `history.back` (grep over dashboard/lab/confluence/research screener → 0): `#si-prophet-return` static `href="sector_central.html#map"` (`templates/_sector_prophet_context.html.j2:11`), dynamic `'sector_central.html?g=' + <id> + '#map'` (`…js.j2:27`); Clear → `us_stocks.html` preserving other params (`…js.j2:51-55`). Partial re-renders on `popstate` (`…js.j2:83`).

### Tests

`test_sector_central_paper.py`, `test_sector_central_measured_panel.py` (si_sector), `test_stock_board_v2.py`, `test_pick_lab_render.py`, `test_confluence_screener_page.py`, `test_research_screener.py`, `test_seo_meta_rollout.py`, `test_reflexivity_overlay.py`, `test_sa_w5_v2_grader_hook.py`.

## Sector Dossier page

Surface: `site/sectors/<TICKER>.html` from `templates/sector.html.j2`.

### Params

`grep -nE "URLSearchParams|location\.search|location\.hash|searchParams"` over `templates/sector.html.j2` + `templates/mtf.js` → **0 hits**.

| parameter | reader | effect | ignored-if-unknown? |
|---|---|---|---|
| (none read) | — | URL never read | n/a |

### State

`localStorage['theme']`/`['lang']` pre-paint only (`templates/sector.html.j2:13`; TradingView theme `:306`). **No dossier-specific key**; the wider localStorage/cookie census (`'theme'`, `'themeAuto'`, `'lang'`, `'liveOff'`, `'mm.pendingPrefs'`) is shared shell chrome. Device-scoped.

### Entity identifier + membership

Keyed by **SPDR ETF ticker** (XLK, XLF, …), not a GICS code or slug: `for fund in config.load()["sponsors"]["sector_funds"]:` → `write_page(outdir / f"{fund}.html", html)`, `outdir = site / "sectors"` (`scripts/build_site.py:4158`, `:4283`, `:4142-4143`); template labels `{{ s.name }} ({{ s.fund }})` (`templates/sector.html.j2:12`, `:133`). Membership: `store.read("sector_holdings", fund)` → `data/sector_holdings/<FUND>.parquet` via `latest_top10` (`collectors/sector_holdings.py:159-162`; writer `:66-73`); row fields `ticker, name, weight_pct, rank` (`:134-137`). **Dated field = observation as-of only**: DataFrame index is the SPDR "As of" date (`:113-121`, `:138`); PIT archive `data/sector_holdings/history.parquet` column `as_of` (`:77`, `:92`). Membership-effective/reconstitution date **NOT FOUND** (`grep -n "effective" collectors/sector_holdings.py` → prose only). Member → stock link: `../stock.html#{{ a.ticker }}` (`templates/sector.html.j2:327`, `:356`, `:376`) — hash form. (Observed inconsistency: research screener links members as `stocks/<ticker>.html`.)

### Link producers

`templates/sector_cycles.js::sectorPageHref` (`:1222-1234`, caller `:1381`, button `:1383`): intl → null; china → `sector_central_china.html#<id>` (null inside the hub); basket → `basket/<id>.html`; nasdaq/russell → null; US sector → `US_SECTOR_PAGE[s.id]` (lowercase-id map `:1203-1214`, e.g. `xlk: "basket/us_sector_tech.html"`) else `stock.html#<ticker>`. Builder twin `US_SECTOR_PAGE` (`scripts/build_site.py:1890-1902`) with href fallback `"sectors/" + fund + ".html"` (`:2032`, `:2284`). The Sector Central hub has no `sectors/` hrefs of its own (`grep -n "sectors/" templates/sector_central.html.j2` → 0) — its links come from embedded `sector_cycles.js`.

### Return

**NOT FOUND** (grep → 0 hits). Return is the global nav, subdirectory-aware: `{% set nav_prefix = '../' %}` + `{% include "_site_nav.html.j2" %}` (`templates/sector.html.j2:125-126`).

### Builder

`scripts/build_site.py::build_sector_pages` (`:4075-4289`, called `:6168`). Inputs: `config["sponsors"]["sector_funds"]` `:4158`; `store.read("yahoo", fund)`/`("yahoo", "SPY")` `:4159`,`:4141`; membership + fundamentals (`collectors/sector_holdings.py`, `latest_fundamentals` `:487`); `site/factordata/insider_signals.json` `:4107`; `site/factordata/factors.json` `:4114`; `data/regime/ladder_calibration.json` `:4133`; `site/live/shock_state.json` `:4164`; engine ladder/technicals/sector_signals + `alpha["by_sector"]` `:4250-4255`. Output: one page per fund `:4283` + heat-board summaries. Fail-soft per fund (`:4160`, `:4164`); additive enrichments in try/except (`:4124`, `:4167-4172`, `:4268-4272`).

### Tests

`test_sector_nav_links.py`, `test_subdir_nav_prefix.py`, `test_seo_meta_rollout.py`, `test_validated_claims_surfaces.py`, `test_w03_basis_match.py`, `test_cycle_ontology.py`, `test_board_copy_and_controls_guard.py`; `sectors/` href pins: `test_ts_u3_dashboard_surfaces.py:437`, `test_us_stocks_s2_compression.py:58`, `test_act_now_board_icons.py:67`. `sectorPageHref`: **none** (grep → 0 hits).

## Cross-receiver facts

- **Language switch is in-page, never a reload.** `window.toggleLang` → `setLang` (`templates/theme.js:680`, `:661-674`): sets `data-lang`, syncs `documentElement.lang`, persists `localStorage.setItem('lang', lg)` (`:665`, device-scoped), dispatches `langchange` (`:673`). `location.reload` in theme.js: 0 hits.
- **Unsaved input across a language switch.** `langchange` listeners exist only in the watch family + the Prophet partial: `templates/watchlist.js:522`, `:2333` (`paintPlaceholders(); paintChip(); render();`), `:2447-2449` (`q.placeholder = L('lgPh'); lgRender();`); `templates/watchstore.js:2330` (`relabel`); `templates/account.js:1050-1053` (`persistPref('lang', …); render();`); `templates/_sector_prophet_context.js.j2:82` (banner `render()`). None clears an input value — they repaint labels/placeholders/rows; the watchlist workspace also persists its entry draft `{mode, text}` to `'mdash.ws.entry.v1'` (`templates/watchlist.js:1344`, restored `:1351`). Research/dossier/confluence have no `langchange` listener → their DOM, including unsaved input, is untouched. `account.js` mirrors the pref account-side (`POST /api/account/prefs` `:419`).
- **Account identity source (shared).** `templates/account.js` is the only credentialed browser path: `api()` = `Authorization: Bearer <Supabase token>` + `credentials: 'include'` (`:309-329`) to `<MM_API>/api/account/*` (same-origin on mastermind-x.com, else `window.MM_API` `:40`); server side outside this repo. Watchlist cloud sync bypasses it (direct Supabase client from `SUPABASE_CFG`, browser key `'sb-' + ref + '-auth-token'` `:266`). Server sentinels use service-role secrets (`config.secret(...)`) — server only.
- **Return conventions seen.** NO receiver reads an inbound `return`/`from`/`origin` param (grep across all four → 0 hits). Outbound shell convention: `terminalUrl` appends `from=macro&ret=<encodeURIComponent(location.href)>` (`templates/theme.js:269-273`); watchlist's Terminal link `from=macro` (`templates/watchlist.js:1104`). Fixed-link returns: the Prophet partial's Return/Clear anchors. Everything else: plain site nav.
- **In-page navigation.** `us_stocks` `life` writes back with `replaceState` only (no pushes — Back exits the page; `templates/dashboard.html.j2:17805-17813`); the watchlist share hash is consumed once then stripped with `replaceState` (`templates/watchlist.js:2103`); the dossier and research pages have no in-page router at all.

## Gaps

1. No receiver accepts a link-carried research subject / question / observation date / evidence mode — all NOT FOUND with greps (Research §Params). The only persisted subject state is the device-local briefcase, which round-trips via export manifests, never URLs.
2. A saved watchlist item cannot carry a non-symbol subject (sector/theme/subindustry): NOT FOUND in schema and cloud columns (`watchstore.js:1972`).
3. Client-side condition alerts NOT FOUND; persist→evaluate→deliver exists only as the nightly server sentinel (Discord webhook — operator channel, not per-user; per-user delivery belongs to the `alert_outbox` drain outside these receivers).
4. `site/research_vault_app.js` is not in this sparse checkout; the live vault app's URL behaviour beyond the baked `#rv-catalog` island is unverified (builder docstring claims it paints from `GET /api/research/catalog`, `scripts/build_research_vault.py:13`).
5. Dossier membership carries an observation as-of date only — no membership-effective/reconstitution date in the store (`collectors/sector_holdings.py`).
6. `sectorPageHref` and the dossier link-producer surface are unpinned by tests (grep → 0 hits).
7. `/us_stocks.html` is served from `dashboard.html.j2` (mode=stocks), not `us_stocks_v2.html.j2` (unlinked shadow) — later packets must re-freeze against this section, not the v2 name.

## Evidence

- Prophet param read — `templates/_sector_prophet_context.js.j2:21-23`: `var params = new URLSearchParams(search);` / `var values = params.getAll('si_sector');` / `if (!values.length) return {status:'absent'};`
- Served page — `scripts/build_site.py:8165-8168`: `_dash = env.get_template("dashboard.html.j2")` / `write_page(site / "us_stocks.html", _dash.render(…, mode="stocks"))`.
- Watchlist share hash — `templates/watchlist.js:2094` `var m = h.match(/^#wl=(.+)$/);` and `:2103` `history.replaceState(null, '', location.pathname + location.search);`.
- Keys — `templates/watchlist.js:25` `var KEY = 'mdash.watchlist.v1';`; `templates/fif_saved_briefcase.js:27` `var STORAGE_KEY = 'mastermind.filing_forensics.saved_research.v1';`; `templates/dashboard.html.j2:20557` `var LS_VIEW = 'mdx_stocktable_us';`.
- Identity — `templates/account.js:317-319` `if (token) headers['Authorization'] = 'Bearer ' + token;` … `credentials: 'include'`.
- Dossier — `scripts/build_site.py:4283` `write_page(outdir / f"{fund}.html", html)` (`outdir = site / "sectors"` `:4143`); member link `templates/sector.html.j2:327` `<a href="../stock.html#{{ a.ticker }}">`; dating `collectors/sector_holdings.py:138` `out.index = pd.to_datetime([asof] * len(out))`.
- Language toggle — `templates/theme.js:665` `try { localStorage.setItem('lang', lg); } catch (e) {}`; `:673` `document.dispatchEvent(new CustomEvent('langchange', …))`.
