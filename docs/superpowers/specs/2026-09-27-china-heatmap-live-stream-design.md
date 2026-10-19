# China A-Share Heatmap Live Stream Design

**Status:** Chairman-approved architecture; implementation carrier `sol/china-heatmap-live-stream-20260927`
**Repository:** `mastermindx-market-intelligence/macro`
**Base:** `808432ecfb2824b55ec37dcbf6b448e5fd31411a`
**Protected procedure pin:** `mastermindx-market-intelligence/Mastermind@dcc4829a811d3f6e4fe8c16a103f813c3501f48e`; `docs/sol_skills/INDEX.md` blob `94d1af402598894372858793a5b1931019c5fa77`; Skillpack `mastermind.sol_skillpack.v1` `1.0.1`, bootstrap major `1`.

## 1. Outcome

The China dashboard's embedded A-share heatmap at `china.html#cnx-dlg-markets` and the standalone `china_heatmap.html` must update from current mainland-market observations during the session instead of remaining a last-close image. The experience must remain coherent across tile colour and return, sector aggregates, breadth, movers, hover details, compact scorecard, and expanded view.

Completion requires more than a merged implementation. A natural mainland-session production receipt must show a source-current live artifact, high universe coverage, correct UI repainting on both customer journeys, honest session/freshness labels, and safe degradation when the live source is unavailable.

## 2. Current State and Root Cause

The canonical `site/marketdata/china_heatmap.json` is intentionally a point-in-time daily-close artifact. It correctly owns:

- the 1,702-name heatmap membership;
- sector classification and display names;
- market-cap tile sizing;
- daily and multi-day historical returns;
- settled-session identity and observation metadata.

`templates/heatmap.js` refreshes that artifact every ten minutes. It also contains an incomplete live hook that hides `.nb-chg` elements in some full-map tiles and waits for `live.js` to mutate them. The same-origin `live/quotes.json` display universe does not contain the full heatmap universe, the embedded scorecard does not share the hook, and the dashboard analytics continue to read `tile.perf`. The visible result is a stale and internally mixed heatmap.

The daily-close artifact must not be repurposed into an intraday publisher. It remains the structural and historical baseline. A single additive live overlay supplies only current-session observations.

## 3. Governing Constraints

1. Preserve one canonical daily heatmap publication owner. The live component may overlay current observations but may not replace the daily history, membership, sector, sizing, or correction authority.
2. Do not create another market identity, queue, event store, replay system, or browser-side vendor connection.
3. Credentials remain server-side. The browser fetches only a normalized, atomic same-origin projection.
4. Tushare `rt_k` is the primary whole-market source. Tencent is an availability fallback, not a second canonical source.
5. Missing or low-quality live observations never become zero. A tile without a current accepted quote is unavailable for live 1D computation and must not silently retain a stale daily move under a live label.
6. Multi-day timeframes remain daily-close based. The live overlay affects only `1D`.
7. Mainland session semantics use `engine.prophet_live.cn_clock`; lunch is a closed segment, not stale tape, and closing auction/post-close are named states.
8. The live artifact is display context only. It does not change Prophet ranks, scores, signals, admissions, evaluation, or trading authority.
9. Existing public China heatmap access remains public. The new derived live overlay is registered explicitly in every public-serving inventory.
10. `templates/heatmap.js` and `site/heatmap.js` remain byte-identical.

## 4. Architecture

### 4.1 Baseline plane — unchanged authority

`site/marketdata/china_heatmap.json` remains the immutable baseline for a browser session. The consumer loads and validates it through the existing China heatmap contract. It supplies tile structure and every non-1D timeframe.

### 4.2 Live producer

Create `engine/china_heatmap_live.py` as the contract and compute owner and `scripts/build_china_heatmap_live.py` as the transport/runtime owner.

The producer reads the canonical daily heatmap to obtain the exact requested universe and baseline session. It then obtains a whole-market snapshot and filters it to that universe.

Source order:

1. **Tushare `rt_k`** — one request using `6*.SH,3*.SZ,0*.SZ`, with an explicit field list including `trade_time`. Normal cadence: two seconds during a running mainland segment.
2. **Tencent `qt.gtimg.cn`** — bounded parallel batches only when Tushare is unavailable or rejects the request. Fallback cadence is no faster than once per fifteen seconds.
3. **Last accepted snapshot** — retained only while its source clock still satisfies the phase-aware freshness contract. A republished heartbeat never resets the source clock.
4. **Unavailable state** — published when no accepted source remains. The browser falls back to the daily baseline and says so.

The service does not call either vendor during holidays, weekends, pre-open, or the lunch break. It republishes a phase heartbeat from the last accepted snapshot at a low cadence so the browser can distinguish break/closed from a dead producer.

### 4.3 Durable runtime

Add `macro-live-china-heatmap.service` as a dedicated persistent, resource-capped systemd service:

- `Type=simple`, `Restart=always`, `RestartSec=2`;
- `/opt/macro/.venv/bin/python -m scripts.build_china_heatmap_live --loop`;
- `/etc/macro-live.env` as the credential/config carrier;
- atomic publication to `/var/lib/macro-live/public/live/china_heatmap.json`;
- no `data/` writes and no git operations;
- bounded CPU, memory, timeout, and filesystem permissions consistent with the existing live plane.

A persistent service is required because a one-minute timer cannot deliver the approved two-second current-session experience. This service owns only the live overlay artifact and therefore does not duplicate the Asia-close daily publisher.

### 4.4 Public transport

Caddy serves `/live/china_heatmap.json` from the existing VPS public live root with `Cache-Control: no-store`. `config/site_access.yml` and all mirrored public-path inventories explicitly register it. There is no direct browser-to-Tushare or browser-to-Tencent connection.

### 4.5 Browser consumer

`templates/heatmap.js` owns one shared China live refresher per base heatmap URL. Full view, embedded scorecard, and expanded overlay consume the same in-memory accepted snapshot.

The refresher:

- starts only for a validated China stock heatmap;
- fetches every two seconds while visible and the published phase is running;
- uses lower cadence in break/closed states;
- never overlaps requests;
- bounds headers and JSON-body reads with an abort timeout;
- rejects malformed, regressive, future, wrong-baseline, low-coverage, or stale-source snapshots;
- retains the last accepted snapshot through a transient request failure;
- dispatches one `hm-live-refresh` event only after an atomic accepted-state replacement.

All 1D reads route through one helper. That helper returns the accepted live `changePct` for a covered ticker, `null` for an uncovered ticker while the live overlay is active, and the baseline daily value when the overlay is not usable. Direct `tile.perf['1D']` reads must not remain in live-sensitive analytics.

## 5. Public Contract

`/live/china_heatmap.json` uses `china_heatmap_live.v1`:

```json
{
  "schema": "china_heatmap_live.v1",
  "market": "china",
  "map_type": "stocks",
  "baseline_asof": "2026-09-24",
  "session_date": "2026-09-28",
  "phase": "afternoon",
  "status": "live",
  "source": "tushare-rt-k",
  "generated_at": "2026-09-28T05:02:04.000000+00:00",
  "source_observed_at": "2026-09-28T05:02:02+00:00",
  "requested": 1702,
  "resolved": 1689,
  "coverage": 0.992361,
  "usable": true,
  "fallback": false,
  "quotes": {
    "600519.SS": {
      "price": 1412.8,
      "prevClose": 1398.0,
      "changePct": 1.058655,
      "ts": 1790571722000,
      "open": 1399.5,
      "high": 1418.0,
      "low": 1390.1,
      "vol": 3214000,
      "amount": 4512000000
    }
  },
  "breadth": {
    "n": 1689,
    "adv": 1020,
    "dec": 621,
    "flat": 48,
    "pctUp": 60.390764
  }
}
```

Contract rules:

- `requested` equals the validated baseline tile count.
- `resolved` equals `len(quotes)` and `coverage == resolved / requested`.
- `usable=true` requires at least 95% coverage, a baseline/session relationship accepted by the mainland clock, a fresh source observation against `expected_latest_quote_time`, and a coherent breadth count.
- Quote keys are a subset of the baseline universe and use `.SS/.SZ` canonical symbols.
- Numeric values are finite. `price` and `prevClose` are positive.
- `changePct` is recomputed from `price` and `prevClose`; provider percentages are not trusted as a separate truth.
- `ts` is a real provider market timestamp, never the producer heartbeat clock.
- A no-trade placeholder is omitted rather than represented as current zero change.
- `generated_at` may advance for a phase heartbeat; `source_observed_at` may not advance without a newly accepted source observation.
- Public diagnostics disclose only normalized state (`status`, `fallback`, coverage). Raw vendor bodies, messages, credentials, and internal paths are never published.

## 6. Session and Freshness Semantics

The session phase is resolved by `engine.prophet_live.cn_clock.phase`.

- `morning`, `afternoon`: source must be within 45 seconds of `expected_latest_quote_time`; status `live`.
- `session_break`: retain the 11:30 snapshot; status `break`. The source is compared with the 11:30 expected clock, not wall-clock noon.
- `closing_auction`: publish observations but label the phase explicitly; no other product state changes are inferred.
- `post_close` and same-day `closed`: retain the final accepted snapshot as a settled current-session display until the daily baseline catches up; status `closed`.
- `pre_open`, `holiday`, `weekend`: do not fetch. The live overlay is not active unless a final snapshot and baseline relationship are independently coherent; the default presentation is the daily close.

The client independently rejects a producer heartbeat older than 120 seconds. This catches a dead service without misclassifying lunch as stale market data.

## 7. UI Behavior

When the overlay is usable:

- tile colour and visible percentage use live 1D returns;
- sector headers and sector leader/laggard analytics use covered live names only;
- breadth, median, gainers, losers, market pulse, compact scorecard, hover card, and expanded view use the same accepted snapshot;
- uncovered names render unavailable for live 1D rather than carrying the prior session's move;
- 1W, MTD, 1M, 3M, 6M, YTD, and 1Y continue using the baseline;
- the source label shows current phase, source freshness time in China Standard Time, and `resolved/requested` coverage;
- a live dot appears only for a running, source-fresh phase;
- lunch, auction, closed, degraded, and daily-fallback states each have distinct truthful copy.

When the overlay is unavailable or rejected, every view remains internally daily-close coherent and keeps the last validated baseline date. No green live dot or current-session wording survives.

## 8. Deployment and Secret Delivery

Create an operator-triggered workflow dedicated to this lane. It uses the existing `VPS_DEPLOY_KEY` and `TUSHARE_TOKEN` repository secrets, writes only `TUSHARE_TOKEN` into `/etc/macro-live.env` by stdin, preserves mode `0600`, restarts only `macro-live-china-heatmap.service`, and verifies:

1. the service is active;
2. the public artifact is valid JSON;
3. the artifact has the expected schema and current baseline identity;
4. during an active segment, coverage is at least 95% and the source clock is current;
5. the public URL returns `Cache-Control: no-store`.

`live-setup.sh` installs/enables the service. `update.sh` restarts it when its unit, producer, engine contract, Tushare client, Tencent quote adapter, or heatmap consumer changes. Ordinary unrelated deploys do not restart it.

## 9. Health and Failure Handling

Extend the existing VPS live health/heartbeat owner rather than creating another monitoring plane.

Health fails when:

- the public producer heartbeat exceeds 120 seconds;
- a running session has `usable=false`;
- active-session coverage is below 95%;
- source observation age exceeds the phase-aware bound;
- baseline identity differs from the served canonical heatmap;
- the service is inactive or repeatedly restarting;
- the public route is cached or access-classified incorrectly.

Failure is lane-local. The last validated daily heatmap remains available. A failed or partial live fetch never deletes or rewrites the canonical daily artifact and never blocks unrelated live-plane outputs.

## 10. Security and Compliance

- Tushare token is read only from the process environment and never enters logs, files in git, URLs, browser responses, or command arguments.
- The producer requests only the approved real-time daily endpoint and publishes a normalized derived display contract.
- Tencent fallback uses bounded requests, no browser exposure, and no credentials.
- Public output is allowlisted field-by-field and JSON-validated before atomic replacement.
- The Chairman-settled Tushare compliance override remains in force; this design does not reintroduce a vendor-letter gate or raw-redistribution plane.

## 11. Verification

### Unit and contract proof

- Tushare row normalization, suffix conversion, timestamp parsing, no-trade omission, percent derivation, and universe filtering.
- Tencent fallback normalization and bounded concurrency.
- phase-aware source freshness across morning, lunch, afternoon, auction, close, holiday, and weekend.
- coverage/breadth accounting and rejection of duplicates, foreign tickers, non-finite values, malformed dates, future clocks, wrong baseline, and count drift.
- last-good retention without heartbeat-based freshness fabrication.
- browser live contract validation, one-owner polling, overlap prevention, abort/recovery, atomic state replacement, and multi-view sharing.
- complete replacement of live-sensitive direct `tile.perf` reads.
- Caddy/site-access/public-inventory parity, systemd resource caps, update/install wiring, and secret-workflow hygiene.
- template/served JS byte identity.

### Real-path acceptance

During a natural mainland trading segment:

1. `/live/china_heatmap.json` reports the current session, a source observation near the expected market clock, and at least 95% coverage.
2. `china.html#cnx-dlg-markets` repaints within one browser poll and shows the same 1D values, breadth, sectors, and movers as the artifact.
3. `china_heatmap.html` and its expanded overlay show the same accepted state.
4. A multi-day timeframe remains unchanged when the live snapshot changes.
5. Pausing or breaking the live source causes an honest degraded/daily fallback without a partial repaint or stale live label.
6. A later natural tick advances without manual intervention.

Only then is the requested capability `PROVEN_LIVE`. A green PR, installed service, or one synthetic browser fixture is `BUILT_NOT_PROVEN`.

## 12. Non-Goals

- Replacing the daily China heatmap publisher or its historical store.
- Adding intraday history, replay, chart bars, order book, or tick tape to the heatmap.
- Changing Heatmap membership, sectors, market-cap sizing, Prophet, Terminal, signals, ranking, calibration, or trading logic.
- Making Yahoo/yshares a preferred live source. They remain outside the live truth path.
- Creating a second health scheduler, credential store, publication root, or browser WebSocket.
