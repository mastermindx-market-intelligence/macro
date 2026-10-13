# G3 CN rights evidence — `510300.SS` (evidence only)

**Program:** `WS:GREY-DEER-RISK-INTELLIGENCE` (MAS-258) · **Operation:** `risk-radar-pullback-20261009` ·
**Lane:** G-CN · **Date of this note:** 2026-10-12 · **Terms pages fetched:** 2026-10-13T02:38Z ·
**Writer:** Grey Deer W4 lane G-CN.

**Status: EVIDENCE ONLY.** This note assembles what a data-source owner needs in order to decide
manifest gate **G3**. It is not a rights determination, not a register row, not a grant, and not a
choice among the options in §6. G3 stays open. `DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT` stays in force.
No price series was downloaded. No account was created.

Read-only anchors, not edited here: manifest v1.0.0
`research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md`; prereg v1
`research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md` (no `510300` string); standing kills
`research/DO_NOT_REBUILD.md`; continuation handoff
`research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md`.

---

## 0. Producer in one screen

| Question | What the tree shows |
|---|---|
| Who writes `510300.SS` closes? | One adapter: `collectors/china_prices.py` `ChinaPriceAdapter` (`name = "china_prices"`, `group = "china"`), registered at `scripts/collect.py:231`. `git grep` of `group = "china"` under `collectors/` hits only that file. |
| Upstream | `yf.download(..., auto_adjust=True)` (`collectors/china_prices.py:126`). The library's current master names hosts `query1.finance.yahoo.com` and `query2.finance.yahoo.com`. No TuShare, Eastmoney, Sina, or akshare call writes this series. |
| Where it lands | `data/china/510300.SS.parquet` via `lib/store.py` (`data/<group>/<name>.parquet`). |
| Columns actually stored | `close`, `volume`. Index is a normalized timestamp. No vendor, source, basis, currency, `adjustment_asof`, or other provenance field is written. |
| What `close` is | With `auto_adjust=True`, current yfinance master renames Yahoo `Adj Close` to `Close` (`yfinance/utils.py` `auto_adjust`). House vocabulary for that idea is `TRADJ` (`lib/dataos/price.py`). The stored name is `close`, not `close_tradj`. |
| How humans label it | Config display name is `CSI 300`. A config comment says CSI 300 ETF. Strategy caveats say total-return ETF close (EN and ZH). The radar comment says dividend-adjusted. Those labels disagree with each other and none of them is a column. |
| Rights row | None. `config/dataset_registry.yml` has no `data/china/` price id. `research/licenses/` has three files (Massive, ThetaData, the US Prophet register) and no CN price record. Manifest row 10 is already `source_unavailable`. |
| Registry flag the US Yahoo store has | `licensing: vendor_terms_personal_use` on `equity.bars.daily.yahoo`. That field is not on the CN store, because the CN store has no registry row. |

The universe list itself is root `config.yml`, which the mandated directory `git grep` does not cover.
Those lines were read with a separate `git grep -n 510300 -- config.yml` (§2.3).

---

## 1. Gate this evidence is for

Manifest v1.0.0 already records the disposition. This note does not reopen it.

- **D6** (`PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md:36`): `collectors/china_prices.py`
  downloads with `auto_adjust=True`; no CN rights record exists; the DNR kill is cited. CN inputs
  are `source_unavailable` beyond internal diagnostics. The `510300.SS` labelling decision (handoff
  open item O-d) is recorded as open and routed to the data-source owner.
- **Row 10** (same file, line 141): input "CN closes incl. `510300.SS`"; producer
  `collectors/china_prices.py` (`yf.download(..., auto_adjust=True)`); store `data/china*/`; rights
  cell is the DNR kill; vintage `CURRENT_VINTAGE, adjusted`; described units `CNY · TRADJ · CN`;
  disposition **`source_unavailable`** — killed tape + no rights + no labelling decision.
- **G3** (same file, line 220): "CN rights determination + `510300.SS` labelling (handoff O-d)."
  Owner: data-source owner. What closes it: "A CN row in the register; the DNR kill stays."
- Handoff **D6** (line 66): the `510300.SS` proxy is total-return and must be labelled (EN/ZH) or
  re-sourced raw before any user-facing use; user-facing CN publication is gated on a rights
  determination.
- Handoff **O-d** (line 85): the determination is recorded, never assumed.
- Handoff tripwire (line 42): reading the `510300.SS` total-return drawdown as nominal damage is a
  failure; label or re-source, never silently mix.
- Handoff **F5** (line 73), a prior seat measurement this lane did **not** repeat: a 5-year join
  recorded `510300.SS` 1038 of 1211 rows differing (ratio 0.9047–1.0, 5 distributions), against
  0 differing rows for `000001.SS` and `399001.SZ`. **F6** (line 74): no China index-price rights
  record under `research/licenses/`. That absence is still true on this branch.
- Frozen prereg v1 does not mention `510300` (`git grep` of that file: no hits). The packet's
  14-ticker panel is a later prereg and is not frozen. This note does not draft it.

The manifest's row-10 words `CNY` and `TRADJ` are the manifest's description. They are not fields
on the parquet.

---

## 2. Repo census

### 2.1 Commands and counts

Scoped as the lane asked: `engine/`, `collectors/`, `scripts/`, `config/`, `lib/`, `research/`.
Counts are matching lines (`git grep -n` prints one line per matching line).

```
git grep -n 510300 -- engine collectors scripts config lib research | wc -l
```

**315 lines** in **138 files**.

| Directory | Lines |
|---|---:|
| `engine/` | 104 |
| `collectors/` | 5 |
| `scripts/` | 71 |
| `config/` | 3 |
| `lib/` | 0 |
| `research/` | 132 |

```
git grep -n -i -E 'a-share|ashare|csi 300|csi300' -- engine collectors scripts config lib research | wc -l
```

**2557 lines** in **500 files**.

| Directory | Lines |
|---|---:|
| `engine/` | 592 |
| `collectors/` | 137 |
| `scripts/` | 506 |
| `config/` | 25 |
| `lib/` | 26 |
| `research/` | 1271 |

Outside that pathspec, `git grep -l 510300` also sees files under `tests/` (31), `reports/`,
`docs/`, `agentos/`, and root `config.yml`. Those are not in the 315. Root `config.yml` is cited
in §2.3 because the producer reads it.

### 2.2 Twenty `510300` lines that identify the producer, the store, or the label

| # | Hit | One-line meaning |
|---|---|---|
| 1 | `collectors/china_prices.py:3` | The adapter stores an EOD adjusted close plus volume under `data/china/`. |
| 2 | `collectors/china_prices.py:10` | The module calls yfinance an unofficial API, replaceable by design. |
| 3 | `collectors/china_prices.py:28` | `group = "china"`, so the series file is `data/china/510300.SS.parquet`. |
| 4 | `collectors/china_prices.py:36` | The ticker list is `config["china"]["yahoo"]`, whose indices include `510300.SS`. |
| 5 | `collectors/china_prices.py:93` | The frame keeps `Close` and `Volume`, renamed `close` and `volume`. Nothing else. |
| 6 | `collectors/china_prices.py:126` | The download is `yf.download(batch, period=period, auto_adjust=True, ...)`. |
| 7 | `scripts/collect.py:231` | The nightly registry binds that class as collector `china_prices`. |
| 8 | `engine/market_state_cn.py:24` | UI pair is `("510300.SS", "CSI 300", "沪深300")`, with no basis word. |
| 9 | `engine/china_strategies.py:36` | `CSI300 = "510300.SS"`. |
| 10 | `engine/china_strategies.py:207` | English caveat: benchmark is the CSI 300 (`510300`) total-return ETF close. Line 211 is the ZH "总回报 ETF 收盘价". |
| 11 | `engine/china_radar.py:333` | Onshore read is `data/china/510300.SS.parquet`, described as dividend-adjusted. |
| 12 | `engine/baskets_china.py:11` | Basket benchmark is `store.read("china", "510300.SS")`, called the CSI 300 ETF. |
| 13 | `engine/index_momentum.py:78` | Momentum row labels the same ticker `CSI 300` / `沪深300` / market `CN`. |
| 14 | `engine/china_intel_hub.py:649` | Benchmark path is hardcoded `data/china/510300.SS.parquet`. |
| 15 | `engine/pick_lab/profile.py:235` | Pick-lab loads CSI 300 closes with `store.read("china", "510300.SS")`. |
| 16 | `engine/factor_exposure.py:32` | Calls `510300.SS` the only cached onshore proxy, on a different clock from US names. |
| 17 | `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md:141` | Manifest row 10: this input is `source_unavailable`. |
| 18 | `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md:220` | G3: rights plus labelling stay with the data-source owner; the DNR kill stays. |
| 19 | `research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md:42` | Tripwire: do not read the total-return drawdown as nominal damage. |
| 20 | `research/CHINA_DATA_AUDIT.md:13` | Audit chose the ETF because index symbols such as `000300.SS` were shallow or flaky. |

The other collector hits are not close producers: `collectors/china_qvix.py:3` (implied vol for the
300ETF), `collectors/china_margin_detail.py:58`, `collectors/china_lhb.py:59`, and
`collectors/china_block_trades.py:73` (they read the stored series to list session dates), and
`collectors/china_flows.py:172` (a shares-outstanding unit check that mentions `sh_510300`).
The three `config/` hits are benches, not writers: `config/qual_ladder.yml:313`,
`config/qual_ladder.yml:421`, `config/synapse.yml:2559`.

### 2.3 Root `config.yml` (outside the directory pathspec)

```
git grep -n 510300 -- config.yml
```

| Line | Text role |
|---|---|
| 663 | `live.universe_extra` includes `510300.SS`. `live.intl_source` at line 646 is `yahoo`. That is a live last-price overlay, not the historical parquet. |
| 6294 | `china.yahoo.benchmark: "510300.SS"` with the comment "CSI 300 ETF — sector RS benchmark". |
| 6299 | `china.yahoo.indices` display name: `CSI 300`. |
| 6519 | `china.engine.rs_ranking.benchmark: "510300.SS"`. |

A related symbol that the `510300` grep does not see: `scripts/build_live_quotes.py:120` puts
`000300.SS` on the China live strip and the comment calls that tile CSI 300. `000300.SS` is not in
`china.yahoo.indices`. The historical store and the live index tile are different Yahoo symbols.

### 2.4 Twenty A-share / CSI 300 lines that separate planes

| # | Hit | One-line meaning |
|---|---|---|
| 1 | `collectors/china_prices.py:1` | Plane A headline prices, including the ETF, come through yfinance. |
| 2 | `collectors/china_stock_prices.py:1` | Per-name A-share OHLC is a second yfinance store, not the ETF file. |
| 3 | `collectors/china_stock_raw.py:3` | Says every other A-share close in the repo is dividend/split-adjusted. Line 4 names that plane `auto_adjust=True` total-return. |
| 4 | `collectors/china_stock_raw.py:14` | The raw plane uses the A-share search set. Line 13 sets `auto_adjust=False` and a separate group. The file does not list `510300.SS`. |
| 5 | `collectors/china_universe.py:1` | Search-universe membership is a different collector from the ETF close. |
| 6 | `collectors/china_universe.py:118` | Bare 6-digit codes are converted to Yahoo tickers for that name set. |
| 7 | `collectors/china_universe.py:282` | Sina supplies the ranked A-share name list, not the `510300.SS` close. |
| 8 | `collectors/china_universe.py:711` | CSI 300 and CSI 1000 constituent lists are unioned into search membership. |
| 9 | `collectors/china_tushare_spine.py:185` | TuShare spine talks about A-share 0.01 CNY ticks. It never names `510300`. |
| 10 | `collectors/china_tushare_spine.py:2914` | `TushareAShareSpineCollector` is the A-share name/bar spine, a different store. |
| 11 | `lib/store.py:71` | Documents adjusted-series seams on A-share names when a short window is spliced. |
| 12 | `lib/cn_calendar.py:1` | SSE/SZSE session calendar. It does not fetch prices. |
| 13 | `lib/dataos/identity.py:430` | A-share symbol normalization. Not a price source. |
| 14 | `engine/china_strategies.py:14` | Strategies describe one risk asset: CSI 300, total-return adjusted close. |
| 15 | `engine/baskets_china.py:4` | Thematic baskets are benchmarked to the `510300.SS` ETF. |
| 16 | `engine/market_state_cn.py:21` | Calls CSI 300 the benchmark of the broad A-share tape. |
| 17 | `lib/glossary.py:263` | A China tile is labelled SSE / CSI300 / ChiNext. Display copy, not a feed. |
| 18 | `research/CHINA_DATA_AUDIT.md:6` | 2026-06 audit: Plane A prices via yfinance; Plane B macro via Eastmoney. |
| 19 | `research/CHINA_DATA_AUDIT.md:13` | Broad-ETF row names `510300` CSI300 as the benchmark and rejects shallow index symbols. |
| 20 | `research/DO_NOT_REBUILD.md:92` | `DNR:KILL-ASHARE-SUBSECTOR-GATE` falsifies gating A-share reversal by subsector state. |

`git grep -n 510300 -- collectors` returns five files, and none of them is a TuShare, akshare,
Eastmoney, or Sina module. Those vendors exist elsewhere in the CN stack (macro, search
membership, QVIX, the A-share spine, gold basis). They are not the `510300.SS` close upstream.

---

## 3. How the close is produced and labelled

### 3.1 Write path

1. `ChinaPriceAdapter.all_tickers` unions `indices`, `sector_etfs`, `allocation_etfs`, and `fx`
   from `config["china"]["yahoo"]`. `510300.SS` is an index entry, display name `CSI 300`.
2. `_download` calls `yf.download` with `auto_adjust=True`, `group_by="ticker"`.
3. `_extract` keeps `Close` → `close` and `Volume` → `volume`, drops rows with a null close.
4. On a short (`1mo`) window, `store.basis_shifted` (`collectors/china_prices.py:81`, tolerance
   `upsert_basis_tol` 1e-3 from config) discards the window and refetches `period="max"` when the
   overlap disagrees. The class does **not** set `overwrite_overlap`. The base default is `False`
   (`collectors/base.py:184`), and `collectors/base.py:651` passes that flag into `store.upsert`.
5. `Adapter.validate` normalizes the index. If `session_calendar_for_series` returns a market,
   non-session rows are dropped before upsert. For this symbol, `cash_market_for_symbol` maps the
   `.SS` suffix to `cn` (`lib/market_session.py:61`). That market code is not written into the parquet.
6. `store.upsert` writes the frame with `DataFrame.to_parquet`. No attrs or provenance sidecar is
   added in that function.

`requirements.txt:6` pins `yfinance>=0.2.50`. This worktree's venv does not have `yfinance`
installed, so the wheel a nightly host imports was not byte-compared. The `auto_adjust=True`
argument is in this repo either way. The rename of `Adj Close` to `Close` was read from current
yfinance master (`https://github.com/ranaroussi/yfinance/blob/master/yfinance/utils.py`, function
`auto_adjust`, fetched 2026-10-13T02:38Z): ratio `Adj Close / Close` is applied to OHLC, then
`Adj Close` is renamed `Close`.

### 3.2 Labels that already disagree

| Place | Label it applies to `510300.SS` |
|---|---|
| `config.yml:6299` display name | `CSI 300` |
| `config.yml:6294` comment | CSI 300 ETF, sector RS benchmark |
| `engine/market_state_cn.py:24` | `CSI 300` / `沪深300` |
| `engine/china_strategies.py:14` and `:207` | total-return adjusted close; total-return ETF close |
| `engine/china_strategies.py:211` | 总回报 ETF 收盘价 |
| `engine/china_radar.py:333` | dividend-adjusted |
| `collectors/china_stock_raw.py:3` | calls `auto_adjust=True` "total-return" for A-share closes generally |
| Manifest row 10 | `CNY · TRADJ · CN`, and G3 still says labelling is open |
| `lib/dataos/price.py` `AdjustmentBasis.TRADJ` | "total-return adjusted — splits plus distributions reinvested" |

No line in the producer stamps `TRADJ`, `SADJ`, `RAW`, `CNY`, or `ETF` onto the stored frame.
Consumers that want a basis have to know it from the collector source.

### 3.3 What this series is not

- Not the CSI 300 price index and not the official total-return index. The stored symbol is the
  Shanghai-listed ETF ticker Yahoo calls `510300.SS`. The audit preferred that ETF over `000300.SS`.
- Not the raw plane. `collectors/china_stock_raw.py` is `auto_adjust=False` for the A-share search
  universe. It does not name `510300.SS`.
- Not a Massive bar. Massive coverage in this repo is the US SIP tape.
- Not receipted. Manifest row 10 missingness is "Not receipted". This lane did not open `data/`.

---

## 4. Standing `DO_NOT_REBUILD.md` rows

Rows are cited as `DNR:<KEY>`, never by line number. Search used on 2026-10-13:

```
rg -n -i '510300|akshare|tushare|eastmoney|sina|a-share|ashare|china' research/DO_NOT_REBUILD.md
```

and a pass over table keys for `CN` / `China` / `A-share` / `Yahoo` / `adjust`.

Strings **absent** from `research/DO_NOT_REBUILD.md`: `510300`, `akshare`, `eastmoney`, `sina`.
`TuShare` appears only inside the reopen path of `DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT`.
`China` appears in the source cell of `DNR:KILL-ASHARE-SUBSECTOR-GATE`. `CN` also appears inside
three rows whose topic is not the CN price tape; they are listed so the read is complete.

These kills stand. This note does not reopen, narrow, or extend them.

| Key | ≤15-word quote | What the row forbids |
|---|---|---|
| `DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT` | "no withdrawn tape, artifact, receipt, result, reproducer, reader, or rendered surface may be restored" | The adjusted-price (Yahoo-plane) CN limit-alpha tape, the 14 artifacts re-landed by #5198, and their W2/W3 executable, result, or forward-ledger descendants. Nothing from either adjusted-price vintage, either forward seed, or any derived receipt may be graded, ranked, gated, sized, alerted, traded, promoted, displayed as a current probability, or used as numerical strategy evidence. Same row, also: "Qualitative ideas may inform a fresh preregistration". The written reopen path is unadjusted TuShare `daily` × same-key `stk_limit` under `research/CN_TUSHARE_FULL_A_SPINE_CONTRACT_2026-08-08.md`, not the yfinance `510300.SS` producer. |
| `DNR:KILL-ASHARE-SUBSECTOR-GATE` | "Gating A-share reversal by subsector state" | That gate. Verdict is falsified (hurts versus flat). It does not mention `510300` or a price vendor. |
| `DNR:KILL-CN-SUPPLY-ABSORPTION` | "re-entry needs a fresh operator-ratified prereg" | The `cn_supply_absorption` family, including the D4-01b staged re-entry. The price-only absorption construct stays closed. A new prereg is the row's own re-entry condition. It is not a price-vendor ruling. |
| `DNR:KILL-DEFENSIVE-FLOOR-BUNDLE` | "only CN+HK alerted pre-07-16" | The 4-of-4 defensive-lean floor bundle. The CN mention is why a claimed lead failed. It is not a CN data ban. |
| `DNR:KILL-200DMA-RECLAIM-VETO-FLAT` | "Revive ONLY as a regime-conditional construction" | A flat drop of the US 200-day reclaim veto. "CN handoff §6 machinery" is named as part of a revive condition for that US rule. It is not a `510300` rights ruling. |
| `DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION` | "bound HK/CN market-state persistence inside the retained candidate" | Remounting the UD-B1 hero as the primary `macro.html` composition, and treating the US-derived top score as a global composite. HK/CN bindings inside the retained candidate are do-not-redo. The hold does not authorize a CN pullback series. |

---

## 5. Public terms of the upstream the repo actually uses

The only upstream of the `510300.SS` close is Yahoo, reached through the yfinance library.
Pages below were fetched this session (2026-10-13T02:38Z) with a browser-like user agent.
No Yahoo account was used. No chart, quote, or download URL was requested.

### 5.1 yfinance, the client

Source: `https://raw.githubusercontent.com/ranaroussi/yfinance/master/README.md`.

| Quote (≤15 words) | Where |
|---|---|
| "not affiliated, endorsed, or vetted by Yahoo, Inc." | README important block |
| "intended for research and educational purposes" | same block, describing the tool |
| "the Yahoo! finance API is intended for personal use only" | same block |

The README points at three Yahoo URLs for "your rights to use the actual data downloaded":

1. `https://policies.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.htm` (YDN API terms; fetched; see §5.3)
2. `https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html` (Yahoo Terms of Service; fetched; see §5.2)
3. `https://policies.yahoo.com/us/en/yahoo/terms/index.htm` (fetched; navigation index only; see §5.4)

The same README says yfinance is under the Apache Software License. That license covers the
client code. It is not a grant to the market data.

Host strings in current master `yfinance/const.py` (same fetch): `_QUERY1_URL_ = 'https://query1.finance.yahoo.com'`, `_BASE_URL_ = 'https://query2.finance.yahoo.com'`, `_ROOT_URL_ = 'https://finance.yahoo.com'`. The repo calls `yf.download`. It does not set a Yahoo developer key in `collectors/china_prices.py`.

In-repo precedent, not a new fetch: `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md:135` records a 2026-09-23 fetch of the OTOS URL, and lines 147–153 record Yahoo basket/SPY closes as internal-only on acquisition, with model use and user redistribution "not a source". That register does not mention `510300.SS`. `config/dataset_registry.yml:104` labels the US Yahoo daily store `vendor_terms_personal_use`.

### 5.2 Yahoo Terms of Service

URL: `https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html` · HTTP 200 · fetched 2026-10-13T02:38Z.

| Quote (≤15 words) | What it sits next to |
|---|---|
| "exploit for any commercial purposes" | A ban on exploiting the Services, "including content, advertisements, APIs, and software", for commercial purposes. |
| "personal, royalty-free, non-transferable, non-assignable, revocable, and non-exclusive license" | The software-and-API license, limited in purpose to "enabling you to use and enjoy the benefit of the Services". |
| "high volume activity without our prior written consent" | Ban on commercial activity on non-commercial properties, or high-volume activity, without prior written consent. |
| "Yahoo Finance which is provided by Yahoo Finance LLC" | US defined terms. Yahoo Finance is called out as Yahoo Finance LLC, not Yahoo Inc. |

These clauses do not contain the words "research" or "model" as a permitted use of stored bars.
This note does not turn that silence into a permission or into a ban beyond the quoted text.

### 5.3 Yahoo Developer API terms (the first README link)

URL: `https://policies.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.htm` · HTTP 200, landed on `.../apiforydn/index.html` · fetched 2026-10-13T02:38Z.

| Quote (≤15 words) | What it sits next to |
|---|---|
| "must possess his or her own valid Yahoo account" | Who may accept the API terms. |
| "non-exclusive, non-sublicenseable, revocable basis" | The API license grant. |
| "derive income from the use or provision of the Yahoo APIs" | Prohibited without specific permission in the API documents or Yahoo's prior express written permission. The same sentence also bars sell, lease, share, transfer, or sublicense. |

**UNVERIFIED:** whether the unsigned `query1` / `query2` chart host that yfinance uses is "the Yahoo APIs" this YDN page licenses. The collector does not create a Yahoo developer app and does not log in. The page is cited because yfinance's README tells the caller to read it, not because this repo holds a YDN agreement.

### 5.4 Third README link, and the commercial-program link on it

URL: `https://policies.yahoo.com/us/en/yahoo/terms/index.htm` · HTTP 200 · fetched 2026-10-13T02:38Z.
Extracted text is a navigation index (about 1,600 characters). **UNVERIFIED:** a data-use clause on that URL. None was in the extracted text.

The index links "Enterprise Web Services Commercial License Program Terms" at
`https://policies.yahoo.com/us/en/yahoo/terms/advertising/ewsprogramterms/index.html` (HTTP 200, same session). The page is an advertising program. **UNVERIFIED** as a market-data license: the extracted text has no "market data" clause. It is not a `510300.SS` grant.

### 5.5 Vendors this close does not use

No terms page was fetched for TuShare, Eastmoney, Sina, akshare, CSI, or SSE as an upstream of
`510300.SS`, because the close producer does not call them. Their public fee schedules are
**UNVERIFIED** here. The DNR reopen path names TuShare for a different construction (limit-up
tape, unadjusted `daily` × `stk_limit`). That sentence is not a license for this ETF series.

---

## 6. Options for the data owner

Cost and risk only. No ranking. G3 stays open until that owner writes a register row, and the
manifest says the DNR kill stays when they do.

### (a) Drop the CN leg from the panel

- **Cost.** The panel has no China market. Manifest §2 already says SPY outcomes do not supply
  China probabilities. No new vendor work and no new collector.
- **Risk.** Display code will keep calling `510300.SS` "CSI 300" on other surfaces. Dropping the
  pullback leg does not relabel those surfaces. Legal exposure of a new pullback fit goes away
  because the series is not an input. G3 remains open for whoever next wants the series.

### (b) Keep the SPY panel only, and treat CN as a separate later prereg

- **Cost.** CN waits for its own prereg, its own basis label, and its own rights row. The frozen
  v1 prereg already has no `510300` string, so this matches the document that is frozen. A later
  prereg is a new artifact; this note is not that prereg.
- **Risk.** Lowest chance of reading a total-return ETF path as a nominal drawdown, which is the
  handoff tripwire at line 42. The series can still be misread by live code that already treats
  it as the CSI 300 benchmark. Waiting is not itself a rights grant.

### (c) Qualify the existing producer if the upstream's terms permit research use

- **Cost.** Someone has to write the CN register row G3 asks for, name the basis in EN and ZH, and
  show a Yahoo (or Yahoo Finance LLC) permission that covers acquisition, storage, and the
  research use. The pages fetched in §5 state a personal, non-transferable, revocable license and
  a consent requirement for commercial purpose and high volume. They do not state a research-use
  or model-use grant for stored daily bars. The US Yahoo store's recorded label is
  `vendor_terms_personal_use`, and the US rights register calls model use and redistribution
  "not a source". The CN store does not even have that label, because it has no registry row.
  Mechanically, the column is unlabeled `close`, the adjustment vintage is unrecorded, and
  `overwrite_overlap` is off.
- **Risk.** A public URL is not a right (the manifest's own T02 rule). Qualifying this producer
  for a numerical pullback outcome would put a Yahoo `auto_adjust=True` series into a use the
  limit-alpha kill already refused for adjusted Yahoo CN vintages. The kill does not name this
  parquet; it also does not name this producer as the allowed replacement. Handoff F5, not
  re-measured here, says this symbol's adjusted and unadjusted paths differ on most of a 5-year
  join, unlike the two headline indices.

### (d) A licensed vendor

- **Cost.** A contract, a fee this lane did not quote (**UNVERIFIED**), a new collector, a basis
  receipt (printed close versus adjusted), a Shanghai session calendar, and a register row.
  Coverage start is unknown until that vendor's receipt exists. Building it is a different
  change from this evidence note.
- **Risk.** A paid feed can still forbid model use or redistribution; the entitlement has to be
  written down the way Massive was, not inferred from a brochure. Mixing a vendor's raw print
  with the existing adjusted parquet is a basis break of the kind manifest D5 refuses on SPY.
  The DNR reopen path's TuShare `daily` is a limit-tape construction for A-share names. It is
  not, by that row, a qualified `510300.SS` history.

---

## 7. Which options the DNR rows already exclude

- **(a), (b), and (d)** are not forbidden by any row in §4. No standing row says the CN leg must
  be dropped, must stay SPY-only, or must not use a licensed vendor.
- **(c) is excluded for the withdrawn adjusted-price Yahoo CN limit-alpha vintages** and for any
  graded, ranked, or numerical-strategy use of those vintages, their receipts, their readers, and
  their rendered surfaces (`DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT`). The row allows qualitative
  ideas to inform a fresh preregistration. Its reopen path is unadjusted TuShare `daily` ×
  `stk_limit`, which is not `collectors/china_prices.py`.
- The other five rows do not exclude (a), (b), (c), or (d). They forbid a subsector gate, a
  supply-absorption family, a defensive floor bundle, a flat US reclaim-veto drop, and a
  dashboard remount.

This section names exclusions. It does not pick an option.

---

## 8. Limits of this pass

- No price, quote, chart, or history endpoint was called. Handoff F5's 1038/1211 figure is cited
  from the handoff, not recomputed. `data/` was not checked out and was not opened.
- yfinance's installed wheel was not inspected; master source and this repo's call site were.
- The YDN page's application to the unsigned chart host is marked UNVERIFIED.
- Vendor price lists for a licensed CN feed were not collected.
- This file does not add a `licensing:` field, does not edit the manifest, the prereg, the DNR
  registry, or any collector, and does not close G3.
