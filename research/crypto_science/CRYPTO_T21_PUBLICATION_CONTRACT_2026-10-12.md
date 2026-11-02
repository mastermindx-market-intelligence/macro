# Crypto + Vector publication, freshness, and recovery contract

Census date: 2026-10-12. Tree: `origin/main` `33f96b9d95b749af5d7ac0d2b98ab1848dceb277`.
Scope: `site/crypto.html` and `site/vector.html`, the JSON they bake or fetch, and the live-quote overlay. Candidate PR #8050 was not applied (this lane was told not to take the candidate-base step).

Acceptance labels `A31` and `A14` are not defined for this program inside the searched tree. Bound: `rg '\bA31\b' --glob '*.md'` hit only `research/healthcare/hc_program/reviews/HC_INDEPENDENT_REVIEW_R1_2026-09-24.md:67` (an unrelated R8 item). `rg 'A31|A14'` under `research/crypto_science`, `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md`, and `agentos/decisions/DEC-CRYPTO*` returned no hits. The four sections below are the acceptance this lane was given.

No page text in this contract uses the word "validated". A missing figure is unavailable, not zero.

## 1. Source → generated → served

Deploy is git `main` → VPS, not object storage. `pages.yml` is absent (`ls .github/workflows/pages.yml` → no file). Comments in `daily.yml` that still say "pages.yml deploys" are stale. The box runs `/usr/local/bin/macro-update` every 3 minutes (`app/deploy/setup.sh:74-75`), which is `app/deploy/update.sh`.

Pull: `git fetch --depth 1 origin main`, then `git reset --hard FETCH_HEAD` only when `HEAD != FETCH_HEAD` (`app/deploy/update.sh:263-289`). Publish: `rsync -a --delete --min-size=1 site/ site.served/` (`update.sh:295-296`). Caddy's root is `/opt/macro/site.served`, not the git work tree (`app/deploy/Caddyfile:82-88`). A `flock -n` on the updater exits 0 if a tick is already running (`update.sh:10-17`), so a long nightly rsync is not interrupted by the next cron.

R2 is not on this path. Bound: `rg 'crypto_cockpit|vector_risk|site/crypto|site/vector'` joined to `r2|boto|s3` under `scripts/` and `.github/` returned no hits. `daily.yml:4863-4876` publishes `ohlc`, `stockdata`, `feeds`, and similar dirs via `scripts.publish_r2`. `crypto.html` and `vector.html` are not in that list. `scripts/freshness_sentinel.py` watches an R2 massive-stock-day manifest and Prophet packs (`id` values at lines 375-705). It does not name `crypto.html` or `vector.html` (`rg 'crypto\.html|vector\.html|btc' scripts/freshness_sentinel.py` → no hits).

### HTML shells (anonymous, 60s)

Both pages match `@open_html` `path *.html` (`Caddyfile:423-437`). After the IP gate (fail-open), the header is `Cache-Control: public, max-age=60, must-revalidate` plus `X-Robots-Tag: noindex, noarchive`. They are not in `@gate_html`'s funnel list (`Caddyfile:381-384`).

| Artifact | Generator | Inputs | Generation stamp | Served | Cache |
|---|---|---|---|---|---|
| `site/crypto.html` | `scripts/build_crypto.py:368-489` from `templates/crypto.html.j2` via `lib/pages.py:740-745` `write_page` | `engine/crypto_market_state.py` store reads; `data/crypto_universe/market_*.parquet` (`engine/crypto_universe.py:51-53`); `store.read("vector","signals")` (`build_crypto.py:377`); `site/crypto_cockpit.json` if present (`:117-138`); `data/baskets/membership.json` (`:297-298`); `engine/btc_options.py` | `as_of` = `market["as_of"]` (`build_crypto.py:446`). `built` = `datetime.now(timezone.utc)` (`:447`). Footer prints both (`crypto.html.j2:269`) | `/crypto.html` | 60s must-revalidate |
| `site/vector.html` | `scripts/build_vector.py` `main`, write at `:4868` from `templates/vector.html.j2` | `engine/btc_signals.compute_all()` (`build_vector.py:4240-4241`) over committed stores (coinmetrics, bgeo, okx, coinbase, farside, and the rest the signal frame joins) | `as_of` = `sig.index.max()` formatted `%b %d, %Y` (`:4599`). `built` = wall clock (`:4600`). Footer (`vector.html.j2:577`). Chip says "Daily close" (`:276`) | `/vector.html` | 60s must-revalidate |

`write_page` is a single `Path.write_text` (`lib/pages.py:745`). It is not a temp-file rename.

`market["as_of"]` is the max date among non-empty total-cap, dominance, fear-greed, stablecoin, and BTC series (`engine/crypto_market_state.py:282-287`), or `"—"` when none exist. It is not the wall clock. `btc_signals.py` contains no `datetime.now` / `date.today` (grep of that file). A rebuild does not invent a source bar.

### Baked JSON (registration-gated, `private, no-store`)

`config/site_access.yml:1-25` is default-deny for non-HTML. `@reg_asset` (`Caddyfile:344-368`) sends anything not on the public exclusion list through `/api/regwall/check` then `/api/paywall/check`, then `Cache-Control: private, no-store`. None of the files below appear in `public.exact` or in the Caddy public matchers (grep of `vector_chart|vector_timemachine|vector_risk|crypto_cockpit|crypto_class|crypto_asset|vector_timeline|btc_options` in `config/site_access.yml` and `app/deploy/Caddyfile` → no hits).

| Artifact | Generator | Stamp | Who fetches it |
|---|---|---|---|
| `site/crypto_cockpit.json` | `scripts/build_vector.py:661-716` `emit_crypto_cockpit_json` | `as_of` = `sig.index[-1]` (`:682`). `generated_at` = UTC now, seconds (`:683`). Schema `crypto.cockpit/v1`, `display_only: true` | Not fetched by `crypto.html.j2`. `build_crypto.py:117-138` reads it at bake time for the H6 BTC lane. Missing file → hero `as_of: "—"`, stance `Unavailable` (`:120-128`) |
| `site/crypto_class_state.json` | `build_crypto.py:386-417` | `as_of` = `market["as_of"]` (`:390`). `tier: display`, `display_only: true` | No `fetch(` in `crypto.html.j2` |
| `site/crypto_asset_states.json` | `build_crypto.py:382-385` | Inner `as_of` of `engine.eth_state` was not line-cited in this pass | No runtime fetch in the template |
| `site/btc_options.json` | `engine/btc_options.py:140-147` `write_contract`. Called from `build_crypto.py:380-381` and again inside `build_vector` | Page prints `btc_options.as_of` or "Awaiting data" (`crypto.html.j2:224`). The assignment of that field inside `build_contract` was not line-cited here | No runtime fetch; the derivatives desk is server-rendered |
| `site/vector_risk_strategy.json` | `build_vector.py:196-228` | No `as_of`. No `generated_at`. Columns: dates, price, risk, alloc, equity, markers, hodl | `site/vector_chart.js:252` `fetch(jsonUrl)` from the inline mount `vector.html.j2:603` (`vector_risk_strategy.json`) |
| `site/vector_timeline.json` | `build_vector.py:4224-4230`, called at `:4903` inside a try that logs and continues (`:4902-4905`) | `dates` from the signal index (`:4207`). No `generated_at` | `site/vector_timemachine.js:88` `fetch(... \|\| 'vector_timeline.json')`. The template node `#vtm` (`vector.html.j2:419`) does not set `data-timeline` |

`vector_chart.js` and `vector_timemachine.js` are committed static files under `site/` (`git ls-tree origin/main`). The template loads them at `vector.html.j2:582-584`. `?v=2` on `vector_timemachine.js` is hand-written. `lib/pages.py:212-216` leaves any query that is not `?v=` plus 8 lowercase hex untouched, so `scripts/optimize_assets.py` will not move that stamp.

Public shell assets that do get a content hash: `theme.js`, `illus.js`, `live.js`, `lightweight-charts-v5.js`. They are on `@public_static` (`Caddyfile:535-539`, `not query v=*`, `max-age=300`) and `@public_versioned` (`:570-574`, `query v=*`, `max-age=31536000, immutable`). `daily.yml:4504-4511`, `render.yml:1281`, and `engine-render.yml:880` run `python -m scripts.optimize_assets` before the site commit. A swallowed failure leaves the previous stamp, and an immutable URL then pins the old bytes for a year (`daily.yml:4507-4510`).

### Live quotes (separate plane, not the daily as-of)

`templates/_navlinks.html.j2:341-348` loads `live.js` on every page that includes `_site_nav.html.j2` (both cockpits do: `crypto.html.j2:161`, `vector.html.j2:265`). `live.js` patches `.nb-px[data-sym]` / `.nb-chg[data-sym]` only (`templates/live.js:63-65`). Crypto market rows and H6 lanes use those classes (`crypto.html.j2:191-192`, `:253`). The Vector hero uses `.live-price` / `.live-change` (`vector.html.j2:272-274`), which this patcher does not select. The Vector "Daily close" chip is the baked signal date, not the live tick.

`/live/quotes.json` is public and `Cache-Control: no-store` when the file exists under `/var/lib/macro-live/public` (`Caddyfile:193-202`). The git-tree fallback is `max-age=60, must-revalidate` (`:205-207`). Producer when `vars.VPS_LIVE_PRIMARY != 'true'`: `btc-live.yml` cron `0 * * * *` (`:30`), `python -m scripts.build_live_quotes --display` (`:58`), force-add of `site/live/quotes.json` only (`:67`). When `VPS_LIVE_PRIMARY=true`, that scheduled job does not run (`btc-live.yml:41-44`); the VPS live lane owns the file. `live.js:87-93` marks a crypto quote stale after `LIVE_CRYPTO_STALE_MIN` (default 65) minutes and leaves the baked text in place on a stale or missing snapshot (`live.js:36`).

### What `fetch(` / `?v=` the templates actually contain

`templates/crypto.html.j2`: no `fetch(`. Scripts: `illus.js`, `theme.js` (`:271-272`). No `?v=`.
`templates/vector.html.j2`: `vector_timemachine.js?v=2` (`:582`); `VectorChart.mount(..., 'vector_risk_strategy.json')` (`:603`). The fetch itself is in `site/vector_chart.js:252` and `site/vector_timemachine.js:88`.

## 2. Freshness rules

### Who builds, and how often

Collectors `coinmetrics`, `bgeo`, `okx`, `coinbase`, `deribit`, `feargreed`, `coingecko`, `crypto_universe`, `defillama`, `mempool`, `wikipedia_btc`, `farside` are registered in `scripts/collect.py:309-320` and grouped as `_CRYPTO` (`:384-386`). The comment at `:382-383` says that group is inert until a workflow passes `--group crypto`. No workflow does (`rg '--group crypto'` under `.github` → no hits). They run because the nightly collect is everything except Asia:

`daily.yml:384` `python -m scripts.collect --exclude-group asia --exclude sam_gov_opportunities --skip-shadow-importance`.

Cadence: Build B, 18:30 America/New_York. Crons `30 22 * * *` (EDT) and `30 23 * * *` (EST) (`daily.yml:36-37`). `et_gate` keeps one of them. This is once per successful night, not 24/7. `btc-live.yml` does not run these collectors.

`stale_after_days` on the adapters (consumed by `collectors/base.py:671-675`: status `"stale"` when the wall-clock age of the last bar exceeds that number; empty frames are not upserted, `:641-649`):

| Family | Adapter | `stale_after_days` | What the page does with a gap |
|---|---|---|---|
| CoinMetrics community | `collectors/coinmetrics.py:26` | 4 (comment: lands T-1/T-2) | Feeds the signal frame. No separate date on the Vector chip |
| BGeometrics | `collectors/bgeo.py:37` | 4 | Quota stop is partial success (`bgeo.py:14-16`). Dominance series is one input to the crypto page max-date |
| OKX | `collectors/okx.py:34` | 3 | Vector leverage block is display context (`build_vector.py:4699`) |
| Coinbase BTC daily | `collectors/coinbase.py:35` | 2 | Vector `as_of` and the crypto BTC series |
| Fear & Greed, CoinGecko global, universe, mempool | `collectors/crypto_misc.py:24, 47, 78, 294` | 3 | Universe short history is "Building" (`engine/crypto_universe.py:43-48`). Empty dir → `[]` (`:54-55`) and the board says the snapshot is awaiting the next CoinGecko collection (`crypto.html.j2:197`) |
| DefiLlama stables, Wikipedia | `crypto_misc.py:196, 262` | 4 | Stablecoin 30d prints `—` via `_money` when the value is missing (`build_crypto.py:53-55`) |
| Farside ETF flows | `collectors/farside.py:77` | 4 | H3 prints the 5-day sum or `—` (`crypto.html.j2:206`). `etf_asof` is computed (`crypto_market_state.py:191-196`) and stored on the flow dict (`:317`) but the H3 cell does not print it |

There is no page state named "pending". The words in the templates are `Unavailable`, `—`, `Building`, `Building history`, `Awaiting data`, `Coverage unavailable`.

Collector `"stale"` is a run-health status (`collectors/base.py:671`). It is not copied onto `crypto.html` or `vector.html`. A stale store still renders its last bar. The page date does not flip to today to hide that.

### Rebuild must not renew a source date

It does not, for the source bar:

- Crypto `as_of` is `max` of existing series indexes (`crypto_market_state.py:282-287`). `build_market_state` only reads.
- Vector `as_of` and cockpit `as_of` are the signal index (`build_vector.py:4599`, `:682`). `btc_signals.py` has no wall-clock stamp.
- `engine/btc_decision.py:87-90` `_as_of` formats the signal index. `generated_at` is the bake clock (`:78-84`, `:219`). `status` starts `"unavailable"` (`:220`) and becomes `"ok"` only after the integrity checks (`:390`).
- If `compute_all` throws, `build_vector.main` logs and `return 0` without writing `vector.html` (`build_vector.py:4240-4244`). The previous page stays.

What a rebuild does renew: `built` (`build_crypto.py:447`, `build_vector.py:4600`) and cockpit `generated_at` (`:683`). The footers show "built" and "data through" as two fields. A render from unchanged stores produces a new `built` and the same `as_of`.

Composition gap, not a write-back: crypto `as_of` is the newest of five series. A fresh fear-greed bar can make the page "data through" newer than the BTC daily bar those H5 and H6 numbers came from. Smallest fix is in section 4.

### Zero versus unavailable

Missing money and percents format as `—` (`build_crypto.py:53-55`, `:71-73`). Fear prints `—` when null (`:453-455`). Empty universe prints the awaiting-collection line, not a zero book (`crypto.html.j2:197`). Breadth stays "Building history" until 10 names have 30 days (`engine/crypto_universe.py:104-112`).

Two paths print a number for missing data:

- H5, empty or column-less signals: `btc/eth/alts = 0`, `cash = 100`, `exposure = 0` (`build_crypto.py:177-189`). That is a zero book. The same function, when signals exist, reads `signals.alloc_optimal` directly (`:209-214`) and does not read `btc_decision` `status`. `agentos/discoveries/DSC-CRYPTO-H5-BYPASSES-BTC-DECISION.md` and `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md:183-188` record that bypass. An integrity-unavailable decision can still show a percent.
- Altseason meter width is `0%` when `altseason.value` is none (`crypto.html.j2:221`), while the printed score is `—`. The bar looks like a zero reading.

Vector time-machine `alloc` is scaled by 100 inside `vector_timeline` (`build_vector.py:4219`). A failed fetch hides the widget (`site/vector_timemachine.js:97`) rather than painting zero. The risk chart's fetch failure does not: `site/vector_chart.js:252-255` only `console.error`s, so the SSR line "Loading interactive chart…" (`vector.html.j2:547`) stays. Because that JSON and `vector_chart.js` are behind `@reg_asset`, an anonymous visitor hits this path on every load. The score cards beside the chart are inlined (`vector.html.j2:548`, `data-cards`) and do not need the fetch.

## 3. Recovery

Nobody hand-runs a writer. The next owning workflow is the recovery.

### Cached or out-of-order generation

HTML can be wrong at the edge for at most 60 seconds (`max-age=60, must-revalidate`). Public hashed JS/CSS can stay immutable for a year under the old `?v=` if `optimize_assets` fails (`daily.yml:4507-4510`). `vector_timemachine.js?v=2` is not in that immutable set today, because the file is not public. If it is later added only to `@public_static`, `not query v=*` (`Caddyfile:537`) skips it, it is not on `@public_versioned`, and EdgeOne's default long TTL applies. That is the 2026-07-03 class the Caddy comment at `:519-523` describes. Smallest fix: drop the hand `?v=2` so the 8-hex stamp can apply, and add the path to both public lists in one change — or leave it gated and accept `no-store`.

`render.yml:1388-1393`: the render push is the only way that lane reaches the VPS, and `git pull --rebase -X theirs` keeps the commit being replayed. A render that started on older stores can replace a newer nightly `vector.html` / `crypto.html` and stamp a new `built` on an older `as_of`. `engine-render.yml` uses the same site-only rebase pattern (`:924`, `:1030`). `docs/HOUSE_LAW_CI_GUARD_SUITE.md` records the 2026-07-07 sibling incident (stale render replayed over a newer market-state board). There is no crypto/vector equivalent of `scripts/check_ms_board_coherence.py`.

Vector-only lanes rewrite `vector.html` and do not call `build_crypto` (`rg build_crypto` in `closing-bell.yml`, `earlyclose.yml`, `weekly.yml`, `sentinel.yml` → no hits):

- `closing-bell.yml:431-433` then `git add site/` (`:558`). Also refreshes `crypto_cockpit.json` because that write sits inside `build_vector` (`:4874-4878`). `crypto.html` stays at the checkout copy. JSON can be newer than the crypto page.
- `earlyclose.yml` is `workflow_dispatch` only. The 17:20 ET crons are retired (`earlyclose.yml:47-56`, comment dated 2026-07-16: closing-bell is the superset). A dispatch still runs `build_vector` (`:255`) and `git add site/` (`:360`) and does not call `build_crypto`. It discards data writes except two regime pointers. It is not a qualified cadence.
- `weekly.yml:4` Saturday 14:00 UTC, `build_vector` at `:190`, `git add data/ reports/ site/` at `:278`.
- `sentinel.yml:4` every 30 minutes. Rebuilds only when `scripts.vector_sentinel` exits 10 (`:38-47`) and commits `site/vector.html` plus `site/index.html`, `data/vector`, and `data/coinbase/btc_hourly.parquet` (`:59`). It does not stage `crypto_cockpit.json` or `crypto.html`.

User-visible result of a vector-only bake: Vector shows the new bake; Crypto H6 still shows the previous cockpit until `build_crypto` runs. The live quote overlay can move on its own clock and must not be read as the daily decision date.

### Failed render

`render.yml` sets `RENDER_OK` only after the scoped builders finish (`:1092-1096`). The commit step requires `success()` and `complete == true` (`:1295-1296`). A failed render does not push. `main` and therefore `site.served` stay on the last good commit. The visitor keeps the previous HTML, delayed at most one 60s edge TTL after the next good pull.

`daily.yml:4853-4854` commits with `if: always()` through `scripts/ci/daily_engine_commit_outputs.sh:64` (`git add data/ site/ reports/`). The comment says each builder leaves the prior page on its own error. That holds for `build_vector` when `compute_all` throws (`return 0` before the write). It does not hold if `build_crypto.build` raises after `write_page` has started: `write_text` is not atomic (`lib/pages.py:745`), and the always-commit can stage a truncated file. `rsync --min-size=1` blocks a 0-byte publish only (`update.sh:301-302`).

Owner of a failed nightly bake: the `daily` workflow's next 18:30 ET run, or a `workflow_dispatch` of `render.yml` (scope `all` or `macro`, both call `hub` then `crypto` — `render.yml:1040-1043`) by the render lane. Not a laptop rebuild.

Owner of a failed express rebake: the next push-triggered `render.yml` / `engine-render.yml` run. `render.yml` `on.push.paths` includes `scripts/build_crypto.py` (`:132`) and `scripts/build_vector.py` (`:223`) and `templates/**` (`:63`), and it does not run collectors (`render.yml:8-16`). `engine-render.yml` fires on `engine/**` (`:55-61`), recomputes, commits `site/` only, and discards `data/` (`engine-render.yml:12-17`). A render must not be treated as a new source date.

### Failed VPS pull

If `fetch` or `reset` fails, `set -e` stops the script before `rsync`. `site.served` is unchanged. If the lock is held, the tick exits 0 and the next `*/3` cron retries (`setup.sh:75`, `update.sh:17`). The visitor keeps the last rsynced tree. Caddy does not read the half-reset git work tree (`Caddyfile:82-86`).

There is no crypto/vector row in `freshness_sentinel`. The unit `app/deploy/macro-sentinel.service:45` runs that script; `app/deploy/macro-sentinel.timer:13` fires at `:12` and `:42` each hour. It will not page because these two pages froze. `nightly-liveness` proves the Prophet store advanced in git, not that the VPS served Crypto or Vector (`docs/HOUSE_LAW_CI_GUARD_SUITE.md` row `ops.nightly_liveness`).

Owner of the pull: the VPS `macro-update` cron. Owner of the dead-man switch for the pages it does watch: `macro-sentinel.timer`. Adding a Crypto/Vector surface belongs to that sentinel, not to a hand SSH.

### What the user sees

| Failure | Crypto page | Vector page |
|---|---|---|
| Collect missed, previous bake still on `main` | Last good shell. `as_of` stays the old bar. Live tiles go stale after 65 min and keep baked text | Same for the daily chip. Live hero is not patched by `live.js` |
| `build_crypto` never ran after a vector-only lane | Previous H6 text. Cockpit JSON may already be newer (closing-bell, earlyclose) | New `vector.html` |
| Chart or timeline asset 401 / network fail | n/a (no runtime fetch) | Chart stays "Loading interactive chart…". Timeline node is `display:none` (`vector_timemachine.js:97`). Score cards stay |
| Render push lost | Previous shell, both pages | Previous shell |
| `macro-update` failing | Previous `site.served` copy, both pages | Same |

## 4. Qualified path, and the smallest fixes

Qualified path for the measured product (display tier; not a trade instruction):

1. Nightly `daily` collect (`daily.yml:384`) lands the stores. Source dates move only when an adapter upserts a new bar (`collectors/base.py:651-654`).
2. The engine job runs `python -m scripts.build_vector` (`daily.yml:3626`) then `python -m scripts.build_crypto` (`:3631`). Order is load-bearing: H6 reads the cockpit file the vector bake just wrote (`daily.yml:3627-3630`).
3. `scripts/optimize_assets.py` stamps public `.js`/`.css` (`daily.yml:4511`).
4. `scripts/ci/daily_engine_commit_outputs.sh:64` commits `data/`, `site/`, and `reports/` to `main`.
5. Within 3 minutes `macro-update` resets to that commit and rsyncs `site/` → `site.served` (`setup.sh:75`, `update.sh:263-296`).
6. Caddy serves the two HTML files at `max-age=60, must-revalidate` (`Caddyfile:423-437`).
7. Live prices are a second plane (`/live/quotes.json`, `no-store`, 65-minute crypto stale). They do not set "data through".

`render.yml` and `engine-render.yml` may repeat steps 2–6 from already-committed stores. They are allowed to renew `built` / `generated_at`. They are not allowed to be described as a new source date. Vector-only workflows in section 3 are not a qualified crypto publication.

Instrument readings (one series, one ETF print, one funding number) are not a market verdict. The crypto page stance is a display sentence from 30-day total-cap and dominance (`crypto_market_state.py:154-184`). H5 is a split of a BTC budget, and today it can show a number when `btc_decision.status` is `unavailable`.

### Gaps (proposals only; no code in this lane)

1. H5 prints `0%` / `100% cash` when signals are missing (`build_crypto.py:177-189`) and ignores `btc_decision.status`. Smallest fix: if the decision status is not `ok`, render the exposure as unavailable and do not emit 0. Owner: the P0B path named in `WS-CRYPTO-INTELLIGENCE.md:30-40`. Do not add a second allocation.
2. Crypto `as_of` is `max()` of unequal series (`crypto_market_state.py:282-287`). Smallest fix: set the page "data through" from the BTC daily / signal index, and print each family's own date on its cell (the Farside date already exists at `crypto_market_state.py:317` and is not shown).
3. `vector_chart.js`, `vector_timemachine.js`, `vector_risk_strategy.json`, and `vector_timeline.json` are outside `site_access` public, so the public HTML's chart fetch 401s and the loading line never clears (`site/vector_chart.js:252-256`). Smallest fix: on fetch failure, replace that line with "unavailable"; either inline the chart payload in the HTML or add those four paths to `config/site_access.yml` and both Caddy public lists with `max-age=60, must-revalidate` (the JSON is not content-hashed, so it must not be `immutable`).
4. `vector_risk_strategy.json` has no `as_of` (`build_vector.py:220-228`). Smallest fix: write `as_of` from `sig.index[-1]` and have the chart ignore a payload whose `as_of` disagrees with a data attribute on `#vec-risk-chart`.
5. Scheduled vector-only lanes (`closing-bell.yml`, `weekly.yml`, `sentinel.yml`) move `vector.html` without `build_crypto`. `earlyclose.yml` can do the same if dispatched. Smallest fix: each of those workflows calls `build_crypto` immediately after `build_vector`, or it stops writing `crypto_cockpit.json`. Owner: each workflow file. Not a hand bake.
6. `freshness_sentinel` does not watch either page. Smallest fix: add two surfaces keyed on the "data through" date, budget one daily bar, and do not treat `built` as freshness. Owner: `scripts/freshness_sentinel.py` and `app/deploy/macro-sentinel.timer`.
7. A replayed render can put an older `as_of` back on `main` (`render.yml:1392-1393`). Smallest fix: the render commit refuses `site/crypto.html` and `site/vector.html` when the baked data-through date is older than the file already on `origin/main`. Owner: the render push loop.
8. `write_page` is not atomic (`lib/pages.py:745`) and the nightly commit is `if: always()`. Smallest fix: write to a temp file in the same directory and `os.replace`. That function is shared; this lane does not edit it.
9. Altseason bar width is 0 when the value is missing (`crypto.html.j2:221`). Smallest fix: omit the filled segment when the value is none.
10. Do not "fix" freshness by uploading these pages to R2. The qualified copy is the git commit the VPS reset. R2 on this repo is a different plane (`daily.yml:4863-4876`).

`A31` / `A14` as named acceptance tests: not found in the search bound in the header. UNVERIFIED against any seat scratchpad outside this tree.
