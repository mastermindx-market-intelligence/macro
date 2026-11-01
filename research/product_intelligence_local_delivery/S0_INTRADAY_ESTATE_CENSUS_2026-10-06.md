# S0 intraday bar/quote estate census (read-only)

**MAIN_PIN:** `0beebb3bd1f246a13396c3bd8f996103a26c3b77` (`git rev-parse origin/main` after `git fetch origin main` on 2026-10-06).

## C0 (answer first)

**PARTIAL** — On MAIN_PIN, there is no positively recovered, canonical-git US single-name **minute** (or replay-grade) intraday bar estate for a theme-relative strength study: `git ls-tree -r origin/main --name-only data/intraday/` is empty, and `engine/stock_identity/replay/registry.py:109` records that no U.S. equity intraday bars exist in-repo. A **partial** runner-local path exists as **hourly**, **split-adjusted**, **15-minute-delayed** Polygon/Massive aggregates (`scripts/build_polygon_intraday.py:1-14`, `data/intraday/` gitignored per `.gitignore:70`). **DISTINCT** from the closed Trend Persistence family (`DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-C`, `DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE`): Package S is theme-relative **intraday** descriptive strength at a frozen decision clock, not eleven-sector daily group-persistence cells scored for 20/60-session forward returns relative to SPY.

---

## Q1. Estate table

| Source | Asset class / universe | Granularity | Fields | Adjusted | Session / TZ | Storage (ls-tree / path) | Workflow | Rights (names only) | Cadence | US single names? |
|--------|------------------------|-------------|--------|----------|--------------|---------------------------|----------|---------------------|---------|------------------|
| Polygon hourly accrual | US equities + ETFs | 1h, 15m delayed | OHLCV | adjusted (`build_polygon_intraday.py:135-136`) | Vendor timestamps; RTH labeling in `engine/intraday_flow.py:43-44` | `data/intraday/<T>.parquet` — **not on main tree** (gitignored) | `intraday.yml:55-60`, `collect.py:907-913` | `POLYGON_API_KEY`, `MASSIVE_API_KEY` | Hourly + daily accrual | **Yes** (curated `data/stocks` universe) |
| Massive OPRA minute | US options | 1m contract bars | OHLCV+txns | UNSTATED | UNSTATED in collector | S3 `us_options_opra/minute_aggs_v1/` | Cred probe in `collect.py:924-926` | `MASSIVE_S3_*` | Daily flatfile | No (options) |
| Databento tcbbo | US options NBBO+trade | tick/slice | price,size,bid,ask | UNSTATED | ISO window param `databento_tbbo.py:48-51` | NONE committed | NONE (calibration) | `DATABENTO_API_KEY` | Ad hoc | No |
| ThetaData | US options | EOD + trade_quote | greeks, OI, quotes | UNSTATED | ≤7d bulk windows `thetadata.py:20-27` | Local `thetadata_eod` store | `daily.yml` options band | `THETA_TERMINAL_URL` | Nightly when terminal up | Underlyings only |
| TuShare stk_mins plane | China A-share | 1–60m | OHLCV, amount | **unadjusted** nominal `tushare_minutes_plane.py:33-36` | China session; auction bar `tushare_addons.py:321` | `data/tushare_minutes/...` | Operator backfill only | `TUSHARE_TOKEN` | Bulk gated | No |
| `_stock_ohlc` / China adapter | CN/HK equities | daily | OHLCV | adjusted + raw groups ` _stock_ohlc.py:92-96` | Last completed SH session `china_stock_prices.py:16-17` | `data/china_stocks/` | daily collect | NONE (Yahoo) | Nightly | No |
| Coinbase | Crypto | 1h + daily | OHLCV | UNSTATED | UTC candles `coinbase.py:10-11` | `data/coinbase/` | daily collect | NONE | Nightly | No |
| OKX | Crypto | daily + hourly series | OHLCV, funding | UNSTATED | UNSTATED | `data/okx/` | daily collect | NONE | Nightly | No |
| CBOE | US index options context | daily snapshot | P/C, GEX | UNSTATED | `date.today()` gate `cboe.py:48-50` | `data/cboe/` | daily collect | NONE | Nightly | No |
| IBKR borrow | US equities | intraday snapshot | fee, availability | UNSTATED | IBKR #BOF US/Eastern `ibkr_borrow.py:7` | `data/ibkr_borrow/daily/` | daily collect | NONE (anon FTP) | ~15m vendor refresh; 1 capture/run | **Yes** (panel; not OHLCV) |
| Intraday flow ledger | US flow-tracker names | derived hourly | flow metrics | inherits Polygon adjusted | `intraday_flow.py:43-44` | `data/intraday_flow/ledger.parquet` (on main ls-tree) | `intraday-fastpath.yml`, `closing-bell.yml` | upstream `POLYGON_API_KEY` | 30m fastpath | **Yes** (subset) |
| Marketdesk extractor | Research PDFs | N/A | text/metadata | N/A | UNSTATED | NONE | NONE | out of band | N/A | No |

**Rights / DNR:** Paid-metered paths include `DATABENTO_API_KEY` (`databento_tbbo.py:10-11`, inert without key) and Polygon/Massive keys for US hourly bars. Trend Persistence paid research is **closed**, not a provider kill: `DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE`, `DNR:KILL-TREND-PERSISTENCE-PATH-FEATURE-PROFILE` (`research/DO_NOT_REBUILD.md:133-134`). `DNR:KILL-INTRADAY-CHRONICLE` forbids intraday **chronicle** writes, not price bars (`DO_NOT_REBUILD.md:47`).

---

## Q2. Session definitions on main

| Location | Definition |
|----------|------------|
| `engine/prophet_entry_policy.py:58-66` | US RTH 09:30–16:00 ET; early close 13:00 on fixed 2026 dates; extended hours **fail closed** for B4 |
| `lib/nyse_calendar.py:10-13` | Full-day closure rules; **early closes NOT modeled** for `expected_last_session` |
| `engine/session_digest.py:43-44` | Options session digest hourly buckets through regular 09:30–16:00 ET |
| `engine/intraday_flow.py:43-44` | Same regular-session hourly expectation for volume-share |
| `engine/prophet_live/live_states.py:382` | Live `preopen` vs `rth` split at 09:30 ET |
| `collectors/tushare_addons.py:321` | China 09:30 auction (non-US) |

**One shared definition?** **No** — US cash-equity **calendar existence** (`lib/nyse_calendar.py`) disagrees with **execution/RTH policy** (`prophet_entry_policy.py`) on early-close modeling, and **display engines** embed 09:30–16:00 ET prose separately.

**Registration pin:** `engine/prophet_entry_policy.py:58-66` for US equity **decision/execution session law**, composed with `lib/nyse_calendar.py` for session **existence**, with an explicit amendment for early-close days currently split across modules.

---

## Q3. Existing strength computations (not a rename check)

| Module | Windows / benchmarks | Uses intraday bars? |
|--------|----------------------|---------------------|
| `engine/us_board_rank.py:1954-1977` | 63-session **trailing total return** z-score across universe; deliberately not residual alpha | **No** — daily closes |
| `engine/index_leadership.py:45-66` | Horizons 5/21/63/126/252 **daily** bars; 50-DMA breadth thrust | **No** |
| `engine/subsector_rotation_alerts.py:3-16` | Diff on **daily** `subsector_rotation` state machine | **No** |
| `engine/theme_context.py:105-121` | Reads `r10` from rank rows (daily basket tape) | **No** |
| `engine/narrative_rotation.py:851-858` | `r10` = 10-session basket cumulative return on **daily** levels; allocate uses daily `bench_close` | **No** |
| `engine/rotation_events.py:48-57` | Daily PARAMS_V2 windows (25/40 session lookbacks) | **No** |

**Not a rename:** All listed strength/rotation surfaces are **daily close/session** constructions. None consume `data/intraday/*.parquet` for ranking. Intraday-adjacent **display** only: `scripts/build_intraday_flow.py:14-17` (hourly fastpath for flow tracker).

---

## Q4. Trend Persistence boundary

| | Content |
|---|---------|
| **Closed family tested** | Eleven GICS **sector** group features (relative strength, participation, coherence, etc.) in rank-linear form against **relative-to-SPY forward return** at **20 and 60 sessions** on S&P 1500 PIT universe; Wave C development pass → **C1-NULL**, no carry, family stops (`DEC-TREND-PERSISTENCE-STOPS-AT-WAVE-C`; `DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE`). |
| **Package S hypothesis** | Optional **theme-relative intraday** descriptive strength with frozen **decision time**, **session boundaries**, **trailing-only beta/vol**, benchmark overlap rules, and honest coverage/cost accounting — **prospective registration**, no outcome scan before registration, no rank/gate/size authority (package text verbatim in commission). |
| **Statement** | **DISTINCT** — different asset grain (dynamic theme baskets vs fixed sector cells), time axis (intraday decision clock vs daily formation forward horizons), and outcome family (descriptive intraday strength vs pre-registered group persistence null). Product owner may accept or refuse; not a reopen of Trend Persistence per package text and DNR kills. |

---

## Q5. Gap verdict

**CONFIRMED_GAP** for a consumable US single-name intraday estate on MAIN_PIN suitable for theme-relative strength research.

**Evidence:**

1. `git ls-tree -r origin/main --name-only data/intraday/` → empty (no tracked bars).
2. `engine/stock_identity/replay/registry.py:109` — explicit absence of U.S. equity intraday bars in-repo.
3. Documented accrual path is **hourly**, **delayed**, **gitignored**, key-gated (`scripts/build_polygon_intraday.py:1-14`, `.gitignore:70`, `intraday.yml:57-58`).
4. No engine module in the daily strength table consumes intraday equity bars for theme-relative research.

---

## Q6. Registration skeleton (pins only; no thresholds)

| Field | Main-side pin or GAP |
|-------|----------------------|
| Decision time | `engine/prophet_entry_policy.py:86-95` — **GAP** for package-S-specific freeze doc |
| Session boundaries | `engine/prophet_entry_policy.py:58-66` + `lib/nyse_calendar.py:10-13` (resolve early-close split) |
| Trailing-only beta/vol | **GAP** (no macro owner at theme/intraday grain; contrast Mastermind B* in `DEC-TREND-PERSISTENCE-STOPS-AT-WAVE-C:16-22`) |
| Benchmark overlap | `engine/narrative_rotation.py:843` (daily bench) — **GAP** for intraday overlap law |
| Self-inclusion | **GAP** |
| Stale/missing/zero returns | `scripts/build_polygon_intraday.py:171-185` (per-file tolerate) — **GAP** for study rules |
| Halts/corporate actions | **GAP** (adjusted flag only at `build_polygon_intraday.py:135-136`) |
| Membership cutoff | `scripts/build_intraday_flow.py:24-25`, `engine/theme_scoring.py:659` (daily theme membership) |
| Baselines | `engine/narrative_rotation.py:851-854` (descriptive r10) — **GAP** for intraday residual/raw baselines |
| Costs | **GAP** (metering guard `collectors/databento_tbbo.py:26-27` is unrelated) |

---

## Verify commands (recorded at delivery)

```text
python3 -c "import json;d=json.load(open('research/product_intelligence_local_delivery/S0_INTRADAY_ESTATE_CENSUS_2026-10-06.json'));print('estate',len(d['estate']),'sessions',len(d['sessions']),'strength',len(d['strength_modules']),'reg',len(d['registration']),'gap',d['gap_verdict']['verdict'],'c0',d['c0'])"
git status --porcelain
git diff --stat origin/main -- engine scripts app collectors site data templates .github agentos
```

Machine JSON: `research/product_intelligence_local_delivery/S0_INTRADAY_ESTATE_CENSUS_2026-10-06.json`.
