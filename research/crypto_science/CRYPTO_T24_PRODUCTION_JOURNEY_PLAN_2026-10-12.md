# Crypto T24 — production journey plan and capability ledger

Date of census: 2026-10-12 05:20–05:21Z. This file is the observation plan and the ledger template. It is not production proof, not a Job, and not a release.

Worktree base: `origin/main` `e038bd40eee52388c7944edede4ec24e5857bbc7` (commit subject `render-public: public pages + asset stamps`, committer time `2026-10-12 05:05:03 +0000`). Candidate read-only: draft PR #8050 head `fd8095012e91026640ae07e092ae6272a2e7d30c`, inspected as `origin/claude/cx-t01b-20261012` `0dc4915da247cd7b939c46c35ce578757d2518da` (that branch’s commit message is the R2 source delta on main). Masterplan read-only: draft PR #8880 head `035994bfddd9b54735a6902ec90a0df8b0b138d9`, file `research/CRYPTO_INTELLIGENCE_FABLE_MASTERPLAN_2026-10-11.md`. #7645 is OPEN, not draft, head `74298e32bbbbc7f00884ece259455b9bbe46fd6f` (`gh pr view` 2026-10-12).

Public origin is `https://www.mastermind-x.com`, Caddy static root `/opt/macro/site.served` (`app/deploy/Caddyfile:1`, `:88`). Product HTML for Crypto and Vector is the open-html family: readable after the IP/country gate, `X-Robots-Tag: noindex, noarchive` (`app/deploy/Caddyfile:423-438`). `start.html` is on the public-funnel list (`app/deploy/Caddyfile:381-383`). Marketing `index.html` is a different surface.

## 1. Journey

Read-only commands only. No login, no POST, no form. A pass is the command result below. Browser execution of the nav rewrite and of the assistant pill was not done in this census; those steps name the runtime selector and the GET that proves the owner script is on the page.

### Step 1 — Public nav

- URL: `https://www.mastermind-x.com/start.html`
- Selector: `a.card.btc.crypto[href="crypto.html"]` (Crypto Cockpit card) and `a.card.btc[href="vector.html"]` (Bitcoin Vector card). After `theme.js` loads `account.js`, which loads `nav_market.js`, the Other Assets dropdown is `[data-nav-market-key="assets"]` and contains `a.nav-market-item[href="crypto.html"]` and `a.nav-market-item[href="vector.html"]`.
- Command: `curl -sSI -A 'MastermindCensus/1.0' --max-time 25 https://www.mastermind-x.com/start.html` then `curl -sS -A 'MastermindCensus/1.0' --max-time 25 https://www.mastermind-x.com/start.html | rg -o 'href="crypto.html"|href="vector.html"|Other Assets' | sort | uniq -c`
- Pass at 05:20Z: HTTP 200, `last-modified: Mon, 12 Oct 2026 05:06:31 GMT`, `cache-control: public, must-revalidate, max-age=60`, no `x-robots-tag` on that response. Body contains `Other Assets`, two `crypto.html` hrefs, and `vector.html` hrefs, including the card classes above. `theme.js` is referenced. `nav_market.js` is not baked; it is injected by `templates/account.js:1244-1254`, and `account.js` is injected by `templates/theme.js:474-491`.
- Static Other Assets markup in `templates/_navlinks.html.j2:198-211` lists Commodities, Forex, and Bonds. Crypto and Bitcoin Vector are inserted by `templates/nav_market.js:441-453` inside `enhanceMarketMenus`, called for every visitor from `boot()` at `templates/nav_market.js:1317-1321`. A no-JS client still has the start.html cards.
- `https://www.mastermind-x.com/index.html` is not this door. At 05:20Z it was HTTP 200, `last-modified: Sun, 11 Oct 2026 15:27:04 GMT`, and the body contained zero `crypto.html` and zero `vector.html` hrefs.

### Step 2 — Asset class (Crypto Cockpit)

- URL: `https://www.mastermind-x.com/crypto.html`
- Selectors: `[data-shelf="H1"]#crypto-overview .hero-meta` (class as-of), `#market-board` (board), `#market-board .source-line` (universe source), `#allocation` (H5 budget), `#asset-lanes a.asset-lane[href="vector.html"]` (Bitcoin lane), `.page-foot` (built and data-through).
- Command: `curl -sSI -A 'MastermindCensus/1.0' --max-time 25 https://www.mastermind-x.com/crypto.html` and a body GET saved locally, then search for the selectors.
- Pass at 05:20Z: HTTP 200, `content-type: text/html; charset=utf-8`, `x-robots-tag: noindex, noarchive`, `last-modified: Mon, 12 Oct 2026 05:06:29 GMT`, `cache-control: public, max-age=60, must-revalidate`. Body has H1–H8, `#market-board`, `#allocation`, one `href="vector.html"` on an asset lane, 30 `nb-px` and 30 `nb-chg` nodes, and two `.source-line` nodes. Visible stamps: class as-of `2026-10-09`; foot `built 2026-10-12 02:50 UTC` and `data through 2026-10-09`. H5 text is the main-template copy “the migrated four-way budget” with total crypto `100%`, Bitcoin `64%`, Ethereum `29%`, altcoins `7%`, cash `0%`. `data-allocation-state` is absent, so the served page is not the #8050 H5 markup.
- Universe source line on the served page: “Universe data: CoinGecko primary, CoinGecko / CoinPaprika observed; CoinPaprika is the disclosed availability fallback.” Equities source line: curated Crypto & Digital Rails basket, regime sensor.
- Same stamps are in the committed blob `origin/main:site/crypto.html` (`2026-10-09` and `As of`).

### Step 3 — Bitcoin Vector

- URL: `https://www.mastermind-x.com/vector.html`
- Selectors: `#overview .asof-chip` (daily close), `.live-price[data-sym="BTC-USD"]` (baked close), `[data-shelf="S2"][data-decision-schema][data-decision-status]` (decision), `.decision-action`, `.page-foot`.
- Command: `curl -sSI -A 'MastermindCensus/1.0' --max-time 25 https://www.mastermind-x.com/vector.html` plus a body GET.
- Pass at 05:20Z: HTTP 200, `x-robots-tag: noindex, noarchive`, `last-modified: Mon, 12 Oct 2026 05:06:35 GMT`, same cache policy as crypto.html. Visible: `Daily close · Oct 10, 2026`; `.live-price` text `$82,482`; `data-decision-schema="btc.decision/v1"`; `data-decision-status="ok"`; `data-decision-exposure="100"`; action text `HOLD 100% BTC` / `持有 100% BTC`; foot `built 2026-10-12 02:47 UTC`, `data through Oct 10, 2026`. `nb-px` count is 0. `details.overview-source` and `signals.close` are absent.
- Committed blob `origin/main:site/vector.html` matches those stamps (`Oct 10, 2026`, `data-decision-status="ok"`, `2026-10-12 02:47 UTC`).

### Step 4 — Source identity

Two clocks are already on the served pages. A third clock is the public quote file. The #8050 source table is the candidate contract and is not on the served HTML.

- Class clock. Field `as_of` written by `scripts/build_crypto.py` view-model (`"as_of": market["as_of"]`, `scripts/build_crypto.py:446` on main and the same key at `scripts/build_crypto.py:562` on the candidate). `market["as_of"]` is the max date among total market cap, BTC dominance, fear-and-greed, stablecoin supply, and BTC close (`engine/crypto_market_state.py:282-290`). ETF 5-day flow keeps its own `flows.etf.as_of` (`engine/crypto_market_state.py:190-197`) and the served H3 shelf does not print that date. Foot `built` is `datetime.now(timezone.utc)` at render (`scripts/build_crypto.py:447` main, `:563` candidate).
- Vector clock. `as_of` is `sig.index.max()` formatted `%b %d, %Y` (`scripts/build_vector.py:4599` main, `:4792` candidate). `built` is UTC now at the same render (`:4600` main, `:4793` candidate). Decision date inside `btc.decision/v1` is `base["as_of"]` from the signals index (`engine/btc_decision.py:250`).
- Quote clock. URL `https://www.mastermind-x.com/live/quotes.json`. Selector in JSON: `asof`, `ts`, `source`, `quotes["BTC-USD"].price`, `.ts`, `.source`, `.changePct`, `.delayMin`. Browser binder is `templates/live.js:63-65`, which paints `.nb-px[data-sym]` and `.nb-chg[data-sym]` only. Crypto board qualifies. Vector `.live-price` does not.
- Command: `curl -sSI` and `curl -sS` of `/live/quotes.json`, then read only those keys.
- Pass at 05:21Z: HTTP 200, `content-type: application/json`, `cache-control: no-store`, `last-modified: Mon, 12 Oct 2026 05:20:05 GMT`. Top-level `asof=2026-10-12T05:21:02.791556+00:00`, `source=snapshot`, `ts=1791782462791`. `quotes["BTC-USD"]` is `price=84064.99`, `changePct=0.47`, `source=yahoo`, `ts=1791782462000`, `delayMin=0.1`, `currency=USD`, `basis=regular`. Top-level `meta.delayed_min=15`, `meta.realtime=false`, `meta.feed="≈15-min delayed (Polygon Standard / Yahoo)"`, `meta.resolved=362` of `meta.requested=364`. The row `delayMin` and the file-level delay label are both present; this census does not collapse them into one freshness claim.
- Candidate source table, not served: `templates/vector.html.j2` `details.overview-source` renders `chart_contract.meta.fields.{price,risk,allocation}.source_id` and `chart_contract.meta.observed_at`, with the sentence that the availability clock is not asserted. The payload is `scripts/build_vector.py:291-320` on the candidate: schema `mastermind.vector_risk_strategy.v2`, `availability_clock: "NOT_ASSERTED"`, `source_id` values `signals.close`, `signals.risk_index`, `signals.alloc_optimal`, and `available_at: None` on each field. `observed_at` is the last signals date (`scripts/build_vector.py:255`).
- Sidecar JSON is not a public source read. Anonymous `GET /crypto_cockpit.json` and `GET /crypto_class_state.json` both returned HTTP 401, `content-type: application/json`, `cache-control: no-store`, `x-robots-tag: noindex, noarchive` at 05:21Z. Those paths fall through `@reg_asset` (`app/deploy/Caddyfile:344-377`).

### Step 5 — Assistant

- URL of the page: `https://www.mastermind-x.com/crypto.html` or `vector.html`. API: `https://app.mastermind-x.com/api/brain/me`.
- Selector: none in the static HTML (`#mmb-boot` count 0 on both saved bodies). Runtime owner is `templates/theme.js` `initChatLauncher` (`templates/theme.js:5167` calls it; the stub is `#mmb-boot` at `templates/theme.js:5242-5246`). First activation loads `mm_brain.js` from the shared asset root (`templates/theme.js:5214-5239`). The client send is `POST /api/brain/stream` (`templates/mm_brain.js:2788`). This plan’s read-only command does not send that POST.
- Command: confirm `theme.js` is in the page body, then `curl -sS -D - -o /tmp/brain-me.json -A 'MastermindCensus/1.0' --max-time 20 https://app.mastermind-x.com/api/brain/me` and read the JSON keys `tier` and `quotas` only.
- Pass at 05:21Z: both product pages reference `theme.js`. `GET /api/brain/me` returned HTTP 200, `content-type: application/json`, body `{"tier":"guest","quotas":{"fast":{"remaining":30,"limit":30,"period":"day"},"pro":{"remaining":0,"limit":0,"period":"day"}}}`. Handler is `app/main.py:1638` `brain_me`, dependency `_brain_user_or_guest` (`app/main.py:1366-1392`). A verified Supabase bearer wins; a missing token becomes a guest only when guest config is enabled, otherwise 401.
- Candidate note, not served: `tests/test_vector_r2_frontdoor.py` `test_vector_uses_in_page_brain_entry_and_suppresses_floating_launcher` expects Vector to use an in-page entry and suppress the floating pill. The served Vector HTML still includes `theme.js` and has no `overview-source` block.

## 2. Authenticated versus public, and the owner

| Step | Anonymous result on 2026-10-12 | What a signed-in session changes | Owner that gates it |
|---|---|---|---|
| 1 start.html nav and cards | HTTP 200, funnel page, cards in the HTML | `nav_market.js` `apply()` folds country menus from `MDXAuth.onChange` (`templates/nav_market.js:1327-1335`). The assets menu rewrite already runs before that return. | Caddy `@gate_html` then `GET /api/gate/check`. Gate errors allow (`app/gate.py:343`). Account identity: `templates/account.js`, cookie on `.mastermind-x.com` (`templates/theme.js:469-472`). |
| 2 crypto.html shell | HTTP 200, `noindex` | Same HTML. Paid rows elsewhere use `tier_preview.js`; this cockpit is server-rendered. | `@open_html` (`app/deploy/Caddyfile:423-438`). Not in the `@reg_asset` exclusion as a special case; `*.html` is excluded from the asset wall (`app/deploy/Caddyfile:345`). |
| 2 H5 numbers | Shown from `signals.alloc_optimal` | Same bytes. No account-holding field. | Builder `scripts/build_crypto.py:207-214` on main. Candidate replacement is `_allocation` plus `engine/btc_decision.py:396` `project_budget` (not served). |
| 3 vector.html shell and decision attrs | HTTP 200, decision `ok` / `100` | Same bytes. | `@open_html`. Decision writer `engine/btc_decision.py:202` `build_decision`. P0A acceptance is PR #6294, recorded in `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md:20-28`. |
| 4 board prices | Baked text, then `live.js` may replace `.nb-px` / `.nb-chg` from the public snapshot | Same public file. | `templates/_navlinks.html.j2:341-348` loads `live_config.js` and `live.js`. Snapshot is on the public not-path list (`app/deploy/Caddyfile:345` includes `/live/quotes.json`). |
| 4 sidecar JSON | HTTP 401 | Needs `GET /api/regwall/check` (Supabase account) and, when `PAYWALL_ENABLED=1`, `GET /api/paywall/check` for feature `site_full` (`app/deploy/Caddyfile:292-295`, `app/paywall.py:392-406`). | `app/regwall.py` and `app/paywall.py`. Entitlement row is `user_entitlements` via `engine/neuralweb/brain_gateway.py:4857-4915` `_resolve_tier`. Writer is `app/billing.py`. |
| 5 assistant quota | Guest fast 30/30, pro 0/0 | A valid bearer replaces the guest. Tier cache TTL defaults to 60s (`engine/neuralweb/brain_gateway.py:4868-4869`). Pro and research require the resolved tier. | `app/main.py` `/api/brain/me`, `/api/brain/chat` (`:1419`), `/api/brain/stream` (`:1483`). Guest switch is brain guest config, fail-closed (`app/main.py:1358-1363`). Burst throttle is 10 requests / 60s before quota (`app/main.py:1264-1293`). |

`PAYWALL_ENABLED` on the production host was not read. The 401 on the sidecars shows the asset wall is in front of those JSON files for an anonymous client. It does not by itself show whether a free signed-in account would pass the paywall.

## 3. Natural source update versus synthetic failure states

A natural update is a movement of a source date or a quote timestamp produced by the existing publisher. A synthetic state is a fixture or an integrity branch used to prove fail-closed behavior. The synthetic state is not a description of the live book.

### Clocks that move, and the lane that moves them

| Field | Where a reader sees it | Lane | Cadence |
|---|---|---|---|
| Crypto class `as_of` (`2026-10-09` at this census) | `.hero-meta`, `.page-foot` “data through” | `daily.yml` step `build crypto intelligence cockpit` after collectors (` .github/workflows/daily.yml:3627-3631`). Input dates: `engine/crypto_market_state.py:282-287`. | Authoritative nightly 18:30 America/New_York. Crons `30 22 * * *` (EDT) and `30 23 * * *` (EST); `et_gate` keeps one (`.github/workflows/daily.yml:36-37`). |
| Vector `as_of` (`Oct 10, 2026` at this census) and decision `as_of` | `.asof-chip`, `.page-foot`, `[data-decision-*]` if the decision changes | Same nightly, step `build bitcoin vector + landing hub` (`.github/workflows/daily.yml:3620-3626`), which recomputes signals. `as_of` is the signals index max. | Same nightly. Asia-close does not call `build_crypto` or `build_vector` (search of `.github/workflows/asia-close.yml` finds only comments that the nightly owns the vector hook). |
| `built` on both foots (`2026-10-12 02:47 UTC` vector, `02:50 UTC` crypto) | `.page-foot` | Any run of those two builders, including `render.yml` `crypto()` and `hub()` (`.github/workflows/render.yml:838-839`, scope list `:1041`). A render from already committed data can move `built` while the source dates stay put. | Not a source advance by itself. |
| HTTP `Last-Modified` | response header | VPS cron `*/3 * * * * /usr/local/bin/macro-update` (`app/deploy/setup.sh:69-75`, `app/deploy/update.sh:1-6`) after a commit to main. | This census: commit `e038bd40eee` at `05:05:03Z` and Last-Modified `05:06Z`, while in-page data-through stayed 9 Oct / 10 Oct. Last-Modified is the publish clock of that commit, which is an asset-stamp commit, not a new source date. |
| `quotes.json` `asof`, `ts`, `quotes["BTC-USD"].price`, `.ts`, `.changePct` | public JSON; crypto `.nb-px` / `.nb-chg` after `live.js` | VPS `macro-live-fast.timer` about every 60 seconds and `macro-live-snapshot.timer` about every 5 minutes (`docs/VPS_LIVE_ORCHESTRATION.md:135-139`). GitHub `btc-live.yml` cron `0 * * * *` writes the same file only when `vars.VPS_LIVE_PRIMARY` is not `true` (`.github/workflows/btc-live.yml:41-44`). Which writer produced the `05:20:05Z` Last-Modified is UNVERIFIED; the age versus the `05:21:03Z` GET fits the ~60s lane better than the hourly cron. | Quote leaf. It does not rewrite `.asof-chip`, `.hero-meta`, `.page-foot`, or `[data-decision-*]`. |
| Vector `.live-price` `$82,482` | hero | Nightly `build_vector` from `close.iloc[-1]` (`scripts/build_vector.py:4601` main). | Does not follow `quotes.json`. At 05:21Z the public quote was `84064.99` while the hero still showed the baked close. |

Observation procedure for one natural advance, without dispatching a workflow and without editing HTML:

1. Record the five reads in section 1: start.html headers, crypto.html as-of and foot, vector.html as-of, decision attributes, and action text, quotes.json `asof` plus `quotes["BTC-USD"].price` and `.ts`.
2. Quote leaf: repeat the quotes.json GET after at least one `macro-live-fast` interval. Pass: `asof` or `quotes["BTC-USD"].ts` is later, and the crypto/vector data-through strings are unchanged.
3. Nightly leaf: after the next 18:30 America/New_York `daily` run has committed, wait one `*/3` pull plus the 60-second HTML cache, then repeat the HTML GETs. Pass: vector data-through or crypto data-through is a later civil date than the baseline, the foot `built` is later than `2026-10-12 02:50 UTC`, and the new bytes arrived as a main commit served by `macro-update`. A later Last-Modified with the same data-through strings is an asset-stamp or render-public commit, the pattern already observed at `05:05Z`, and is not a source advance.
4. `render.yml` `workflow_dispatch` is a rebake of committed data (`.github/workflows/render.yml:1-27`). It is not the natural collector path. This plan does not ask anyone to dispatch it.

### Synthetic states — controlled tests only

These strings are integrity and fixture outcomes. Seeing one of them in a unit test is the pass for that test. Seeing one of them on `www.mastermind-x.com` would be a fail-closed render, not a market fact, and it is not what the 05:20Z pages showed.

- `engine/btc_decision.py` returns `status: "unavailable"` with `integrity.ok` false for `EMPTY_SIGNALS`, `MISSING_FINAL_ALLOCATION`, `FINAL_ALLOCATION_OUT_OF_RANGE`, `RAW_ALLOCATION_OUT_OF_RANGE`, `OVERRIDE_RELEASE_FRAC_OUT_OF_RANGE`, `ACTIVE_OVERRIDE_WITHOUT_ID`, `RAW_FINAL_MISMATCH_WITHOUT_NAMED_OVERRIDE`, and an invalid prior allocation (`engine/btc_decision.py:216-247`, `:289-303`, `:364-374`). A valid decision is `status: "ok"` (`:390-392`). The served page is the latter (`data-decision-status="ok"`).
- Candidate `project_budget` forces `status: "unavailable"` and `final_exposure_pct: None` unless schema, `status=="ok"`, `integrity.ok`, and an exposure percentage in `[0, 100]` all hold (`engine/btc_decision.py:396-434` on `origin/claude/cx-t01b-20261012`). Diagnostic final fields on an invalid decision are not a budget.
- Candidate `scripts/build_crypto.py:193-242` `_allocation_unavailable` reasons: `CANONICAL_DECISION_UNAVAILABLE`, `CANONICAL_DECISION_AS_OF_MISMATCH`, `CANONICAL_SNAPSHOT_UNAVAILABLE`, `CLASS_SPLIT_INPUT_UNAVAILABLE`, `CLASS_SPLIT_UNAVAILABLE`. The H5 element would carry `data-allocation-state` of `available`, `breakdown-unavailable`, or `unavailable` (`templates/crypto.html.j2` on the candidate, the `data-allocation-state` attribute). The served page has no such attribute.
- Candidate chart issues `NO_ALLOCATION_VARIANTS`, `PRICE_UNAVAILABLE`, `ALLOCATION_GAPS` (`scripts/build_vector.py:265-283` on the candidate) keep a missing allocation null. Tests `tests/test_vector_r2_data_boundary.py` pin that a missing allocation is not rendered as 0% Bitcoin. Those tests were not run in this lane.
- `scripts/build_live_quotes.py:481-486` can attach `quote_ts_synthetic` when the engine marks the quote timestamp synthetic. A synthetic quote clock is not the natural `asof` advance in the table above.

Main H5 still does `round(100 * latest["alloc_optimal"])` and substitutes `0` when that cell is null (`scripts/build_crypto.py:207-214`). That is the live builder. It is the bypass recorded in `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md:182-188`. Today’s served H5 printed `100%`, and the Vector decision attribute was also `100`, so this snapshot does not demonstrate the bypass numerically. The code path is still the direct cell read.

## 4. Capability ledger

States: LIVE means a recorded anonymous GET only. The evidence cell names the command, the UTC time, the HTTP status, and the matched selector or string with a count. A source citation alone is not LIVE. A match count of zero is not LIVE. SOURCE-CITED means the merged main source is cited and the served bytes were not checked. ACCRUING means the work exists on an open carrier and is not what the origin served. REJECTED means the masterplan or a recorded decision closed that promotion. BLOCKED means a named gate still stops it. “Unavailable” is the word for missing inputs. A null is not zero.

Repair GETs, two requests total, both anonymous and read-only. Crypto command `curl -sS -A 'MastermindCensus/1.0' --max-time 25 https://www.mastermind-x.com/crypto.html` issued 2026-10-12T05:52:57Z, HTTP 200 (`content-type: text/html; charset=utf-8`, `last-modified: Mon, 12 Oct 2026 05:06:29 GMT`). Vector command `curl -sS -A 'MastermindCensus/1.0' --max-time 25 https://www.mastermind-x.com/vector.html` issued 2026-10-12T05:53:00Z, HTTP 200 (`last-modified: Mon, 12 Oct 2026 05:06:35 GMT`). Counts in the table are local matches on those two bodies, not further requests. `gh pr view 8935 -R mastermindx-market-intelligence/macro --json isDraft,headRefOid` during this repair, before the commit that contains this sentence, returned `isDraft` true and `headRefOid` `f82dbaa52426325722eb21184c20bd45cf9820c5`.

| Capability the masterplan names | State | Evidence |
|---|---|---|
| Open Crypto and read the class | LIVE | Crypto command above, 2026-10-12T05:52:57Z, HTTP 200. `data-shelf="H1"` count 1. `As of` count 1, civil date `2026-10-09`. Masterplan §2. |
| See whether participation is broadening | LIVE as display | Crypto command above, 2026-10-12T05:52:57Z, HTTP 200. `BTC share` count 1. `Spot participation proxy` count 1. The capitalization-versus-flow wording review is T08, ACCRUING (masterplan §5, §8). |
| Comparable asset board | LIVE as today’s top-N | Crypto command above, 2026-10-12T05:52:57Z, HTTP 200. `id="market-board"` count 1. Board price cells `class="market-value nb-px"` count 20. Page-wide `nb-px` count is 30 and also includes asset-lane and equity cells, so 30 is not the board count. Dated historical membership is T07, ACCRUING. |
| Price evidence | LIVE | Crypto command above, 2026-10-12T05:52:57Z, HTTP 200, `class="market-value nb-px"` count 20. Vector command above, 2026-10-12T05:53:00Z, HTTP 200, `class="live-price"` count 1, text `$82,482`. `/live/quotes.json` was not re-read; the previous quote comparison is not this LIVE record. |
| Stablecoin supply display | LIVE as the H3 shelf | Crypto command above, 2026-10-12T05:52:57Z, HTTP 200. `Stablecoin tide` count 1. Receipt `Aggregate circulating supply from DefiLlama.` count 1. Issuance-versus-cap separation is T08, ACCRUING. |
| ETF subscription display | LIVE as the H3 Farside shelf | Crypto command above, 2026-10-12T05:52:57Z, HTTP 200. `US spot-BTC ETFs` count 1. `Farside fund-level net flows` count 1. That sensor’s text has no as-of date. `templates/crypto.html.j2:206` does not print `flows.etf.as_of` (`engine/crypto_market_state.py:317`). |
| Venue-flow interval, unit, and finality | ACCRUING | Masterplan §5 R10. Candidate tests in `tests/test_vector_r2_frontdoor.py` (`test_r13_*`) are on #8050, not on the served page. |
| On-chain valuation family on Vector | LIVE as existing panels | Vector command above, 2026-10-12T05:53:00Z, HTTP 200. `Reserve Risk and VDD use backfill vintages only` count 1. Matched text includes `Reserve Risk through 2026-06-13; VDD through 2026-06-13`. Dependence map (MVRV and NUPL are not independent votes) is T11, ACCRUING (masterplan §5). |
| Short-horizon close versus cycle read | LIVE | Vector command above, 2026-10-12T05:53:00Z, HTTP 200. `Daily close` count 1, text `Oct 10, 2026`. `data-shelf="S2"` count 1. The chip and the decision shelf are separate nodes. |
| Canonical Bitcoin decision on Vector | LIVE | Vector command above, 2026-10-12T05:53:00Z, HTTP 200. `data-decision-status="ok"` count 1. `data-decision-exposure="100"` count 1. `HOLD 100% BTC` count 1. `engine/btc_decision.py` and P0A PR #6294 name the authority and are not the LIVE basis. |
| H5 uses that decision and fails closed | ACCRUING | #8050 `project_budget` and `_allocation`. Served H5 is still `scripts/build_crypto.py:207-214`. WS P0B is `in_progress` and the workstream status is `blocked` (`agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md:13`, `:31-48`). |
| Source line a reader can check | LIVE for the class board | Crypto command above, 2026-10-12T05:52:57Z, HTTP 200. `Universe data: CoinGecko primary` count 1. |
| Source table with source_id and a non-asserted availability clock | ACCRUING | Candidate `scripts/build_vector.py:300-320`. Absent from the served vector body. |
| Public quote snapshot | SOURCE-CITED | Not LIVE. §1 Step 4 recorded GET `/live/quotes.json` at 05:21Z, HTTP 200. This repair did not repeat that path, and this cell has no selector match count. Served quote bytes were not re-checked. |
| Ask Mastermind on the product pages | LIVE as the launcher script on the page | Crypto command above, 2026-10-12T05:52:57Z, HTTP 200, `src="theme.js` count 1 (`theme.js?v=17255989`). Vector command above, 2026-10-12T05:53:00Z, HTTP 200, `src="theme.js` count 1. The guest-quota GET was not repeated and is not this LIVE record. POST was not sent. Failure and privacy behavior is T20, ACCRUING (masterplan §8). |
| Chart-led Vector frontdoor from #8050 | ACCRUING | PR #8050 OPEN draft, head still `fd8095012e91`. Served page has no `overview-source`. |
| Accessible market rows from #7645 | ACCRUING | PR #7645 OPEN, head `74298e32bb`. Shared path is `templates/crypto.html.j2` (masterplan §3). Not merged. |
| Valid 0% distinct from a missing decision, and a known total with an unavailable sleeve | ACCRUING | Candidate `_allocation_unavailable` and `tests/test_vector_r2_data_boundary.py`. Not on the served H5. |
| Model budget kept distinct from an account holding | ACCRUING as copy | Candidate allocation note says the percentages are the model, not account holdings. Served H5 says “Risk budget receipt” and does not carry that sentence. |
| R9 live warning or protective-allocation promotion | REJECTED | Masterplan §5: no such promotion was accepted. |
| New options engine, Grey Deer, Market OS, ontology, Prophet, GMI, single-name equity work, a new aggregate risk or flow score, trade sizing, execution authority, LLM-originated signals | REJECTED | Program exclusions and masterplan §1 and §6. |
| Retired midterm calendar veto | REJECTED | `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md` `do_not_redo`, and `DEC:BTC-MIDTERM-BLACKOUT-AUTHORITY-RETIRED`. |
| Newly promoted forecast on the site | BLOCKED | Requires T17 and T22 evidence first. Section 6. |
| Prospective capture | BLOCKED | Masterplan §8: T03, T04, and T12 gate T22. |
| P0B Executive admission | BLOCKED | Workstream `blocked_by` Personal-Pro path. This plan does not clear it. |
| Anonymous read of `crypto_cockpit.json` and `crypto_class_state.json` | BLOCKED | HTTP 401 at 05:21Z. |
| T24 executed production proof | BLOCKED | This document is the plan. Section 1 has not been re-run after a later nightly. T23 independent exact-head review has not been recorded here. |
| Measured pages already on main | SOURCE-CITED | Not LIVE. The previous cell named Steps 2 and 3 and the main tree, not a shelf selector with a count. HTTP 200 on the two repair GETs does not prove the “already on main” claim. A measured-only release of further candidate work is a separate gate (section 6) and is not this row. |

## 5. Proposed text for `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md`

`agentos/` is seat-owned. The block below is proposed text. It was not written into the workstream.

```
## T24 production journey obligations (proposed 2026-10-12)

The observation plan and ledger live at
research/crypto_science/CRYPTO_T24_PRODUCTION_JOURNEY_PLAN_2026-10-12.md.
That file is a plan. It does not record a completed production journey.

Observe Crypto and Vector with anonymous GET against
https://www.mastermind-x.com/start.html, /crypto.html, /vector.html,
and /live/quotes.json. Read source advance from the in-page class as-of,
the vector daily-close as-of, and the decision attributes. HTTP
Last-Modified moves on every main commit the VPS */3 macro-update pulls,
including asset-stamp commits, and is not itself a source date.

A quote tick (public /live/quotes.json asof and quotes["BTC-USD"].ts)
may change .nb-px and .nb-chg on the Crypto board. It does not change
the vector daily-close chip, the page-foot data-through, or
data-decision-*. The vector hero .live-price is the nightly close, not
the quote file.

Synthetic integrity statuses (btc.decision unavailable, H5
CANONICAL_* and CLASS_SPLIT_* reasons, chart ALLOCATION_GAPS,
quote_ts_synthetic) are controlled failure fixtures. They are not live
market readings and are not a substitute for a nightly source advance.

Served H5 still reads signals.alloc_optimal in scripts/build_crypto.py.
#8050 carries the fail-closed project_budget path and is unmerged.
Do not describe today’s H5 percentage as that path.

Do not serve a newly promoted forecast until T17 (independently
challenged forecast qualification or abstention) and T22 (admitted
prospective evidence through the existing owners) are both recorded.
A measured-only release does not wait on those two. T03, T04, and T12
still gate prospective capture. P0B admission is unchanged and remains
blocked on its existing Personal-Pro gate.

Preserve #7645 row and disclosure semantics when crypto.html.j2 is
integrated. Keep instrument verdicts off the class verdict. Keep the
standing exclusions: no new options engine, no Grey Deer, no Market OS
or ontology, no Prophet, no GMI, no single-name equity work, no new
aggregate risk or flow score, no trade sizing or execution authority,
no LLM-originated signals. Research R1–R9 negative results stay
unpromoted. Missing inputs stay unavailable and are not rendered as zero.
```

## 6. Conditional boundary

T17 in the masterplan docket is “Independently challenged forecast qualification or abstention,” lead O4 (masterplan §8). T22 is “Admitted prospective evidence through existing owners,” lead O1. The same section says measured-product delivery and the science track run in parallel, T13–T16 follow qualified inputs, T17 adjudicates, and T03/T04/T12 gate new prospective capture T22.

A measured-only release of already measured class and Vector surfaces does not wait for a successful new forecast. Serving a newly promoted forecast does wait. The required pack is T17’s qualification or an explicit abstention, plus T22’s prospective evidence collected through the existing collector and publication owners, plus the source and release evidence the masterplan names in that same paragraph (“New predictive serving additionally needs its exact T17/source/prospective/release evidence”). R9’s negative result stays unpromoted either way.

This lane did not run that pack, did not run the nightly, and did not run the candidate tests.
