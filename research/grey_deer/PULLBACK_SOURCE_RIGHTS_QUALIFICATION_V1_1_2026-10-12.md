# Pullback source / clock / basis / rights qualification — manifest v1.1.0 FROZEN (14-ticker panel)

**Program:** `WS:GREY-DEER-RISK-INTELLIGENCE` (MAS-258) · **Operation:** `risk-radar-pullback-20261009` ·
**Carrier key:** `grey-deer-fable-orchestration-20261003-001` · **Parent execution:** `grey-deer-20261003-astra-pickup-001` ·
**Extends:** manifest `1.0.0` (`research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md`) ·
**Manifest version:** `1.1.0` FROZEN (written 2026-10-12, frozen 2026-10-13) · **Lane:** G-XT-MANIFEST, commissioned by the Grey Deer seat (session `da1ad7ad`).

**Status: FROZEN — seat values filled, G7 decided (A1/D14), calendar pinned (A1/D15). The seat records this file's git blob sha outside it, in prereg v1.1 §0 and `MANIFEST_BLOB_SHA` in `scripts/research/grey_deer_pullback_stage1b.py`; changed bytes are a different file, not this manifest.**

This file is the frozen eligible-input manifest for the stage-1b panel. It is a projection over v1.0.0
plus public corporate-action notices and the seat's store receipts (as_of 2026-10-07). It is not a source store, not a rights grant, not a freeze of
prereg v1.1, and not a fitting result. It creates no entitlement. Per-ticker missingness, content hash, subframe sha256, row count, and first and last dates in §4 are those measured receipts. Where a public notice was not found, the cell
is `UNVERIFIED` and names the search. No sentence here is a customer-facing claim.

Read-only parent: v1.0.0, quoted below only for gate wording that this manifest is required to keep.
v1.0.0's non-panel input rows (its §4 rows 2–17) are incorporated by reference and are not reprinted.

---

## 0. Changes from v1.0.0

| Item | v1.0.0 | v1.1.0 |
|---|---|---|
| Qualified price universe | US SPY only (§4 row 1, §5) | QQQ, IWM, DIA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY. SPY is excluded because its stage-1 results have already been seen (seat D2). |
| Declared window | 2021-07-06 → 2026-10-07 | Same window. A ticker whose first row falls after the window start is a refusal (`BLOCKED / PANEL_COVERAGE`). The runner never trims. Measured first date is 2021-07-06 and measured last date is 2026-10-07 on every ticker. Raw row counts are 1320 (QQQ, IWM, XLE, XLF, XLI, XLP, XLRE, XLU, XLY) and 1321 (DIA, XLB, XLC, XLK, XLV). Intersection coverage is 1320 common sessions. |
| Calendar | One ticker against the NYSE session set | Intersection of the 14 tickers' sessions (A1 / D15). Pinned exclusion `{"2026-08-18"}`. Any other symmetric difference is `BLOCKED / CALENDAR_MISALIGNED`. Never forward-fill (seat D3). Expected panel: 1320 common sessions, 2021-07-06 through 2026-10-07. Detail is the D15 row. |
| Identity pins | SPY subframe sha256 and row count were deferred out of the manifest (v1.0.0 §5) | Per-ticker content hash and subframe sha256 are one digest: the stage-1 normalized-subframe sha256 over IDENTITY_COLUMNS of the raw, unadjusted rows ≤ as_of in the window. Both cells hold that digest. Row counts are filled in §4. |
| Basis and split guard | RAW `close_raw`. Discontinuity guard is S08 `SPLIT_LIKE_RATIO = 0.75` (refuse, never re-adjust). | Raw unadjusted bytes stay the identity pin. Adjustment is only the pinned D14 table, then the log(1.25) check runs on adjusted closes. Dividends stay unadjusted and that is disclosed. Detail is the D14 row. |
| Split adjustment (A1 / D14) | v1.0.0 refuses a split-like ratio and does not re-adjust. The pre-amendment v1.1 draft left G7 open between adjust and exclude, and a declared action on a break date refused `SPLIT_UNADJUSTED`. | DECIDED. Pinned table `{(t, "2025-12-05"): 2.0 for t in XLB XLE XLK XLU XLY}`. Rows before 2025-12-05: open, high, low, and close divided by 2.0; volume multiplied by 2.0; transactions unchanged. The observed close ratio on 2025-12-05 must lie within ±10% of 2.0, else `BLOCKED / SPLIT_TABLE_MISMATCH`. Any remaining log(1.25) break on adjusted closes is `BLOCKED / SPLIT_DISCONTINUITY` and is never inferred. Raw subframe sha256 stays the pin. Code: `scripts/research/grey_deer_panel_adjust.py`, landed by PR #9091. |
| Calendar exclusion (A1 / D15) | One series against the NYSE sessions, with no pinned exclusion. The pre-amendment v1.1 draft required equal session sets and refused any symmetric difference. | The panel calendar is the intersection of the 14 tickers' sessions. The pinned exclusion set is exactly `{"2026-08-18"}` (absent for QQQ, IWM, XLE, XLF, XLI, XLP, XLRE, XLU, XLY; present for DIA, XLB, XLC, XLK, XLV). Any other symmetric difference is `BLOCKED / CALENDAR_MISALIGNED`. Expected panel: 1320 common sessions, 2021-07-06 through 2026-10-07. 2026-08-18 is a source gap routed to the `massive_stock_day` collector owner. A diagnosis exists: `research/grey_deer/reviews/MASSIVE_STOCK_DAY_PARTIAL_DAY_DIAGNOSIS_2026-10-12.md`, on main via PR #9082. |
| Gates | G1–G6 open (§8) | G1–G6 remain open. G2's wording is unchanged. G7 is DECIDED by seat amendment A1 / D14. |
| Status | `RECORDED — owner projection` | `FROZEN — seat values filled, G7 decided (A1/D14), calendar pinned (A1/D15); file blob sha recorded by the seat outside this file` |
| Rights | Massive tape pointer for internal SPY fitting; publication undesignated | Same tape, same pointer, no new grant. Publication remains undesignated under G2. |
| Corporate actions | No per-ETF action table | §6, one row per panel ETF, issuer or exchange URL, or `UNVERIFIED`. |
| Non-panel inputs | §4 rows 2–17 written in full | Incorporated by reference to v1.0.0. Not reprinted. |
| Outcomes | Not a fitting result | Still not a fitting result. No panel outcome is computed (seat D13). Nothing is written under `research/grey_deer/pullback_stage1b/`. |

The seat assigned version `1.1.0` for this panel extension and froze it together with prereg v1.1
(`research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md`). Seat D11's trial family
`grey_deer_pullback_v11` is frozen at budget 66 in the runner. The seat's real run registers it in
`data/trial_ledger.jsonl` before any outcome is computed.

---

## 1. Determinations this manifest relies on

v1.0.0 D1–D8 stand for everything this manifest does not reopen. The panel additions are the seat's
D2, D3, D4, and D5, plus amendments A1 / D14 and A1 / D15, recorded here and not re-decided.

| # | Determination | Consequence |
|---|---|---|
| P1 | The price store for the panel is the same Massive `us_stocks_sip/day_aggs_v1` tape as v1.0.0 §4 row 1 (`equity.bars.daily.massive`, `adjustment: none` / `close_raw`). The lane that wrote this file did not read `data/` (sparse checkout) and does not assert that any panel parquet is present. | Per-ticker inclusion, coverage, missingness, content hash, and subframe sha256 are the seat's measured receipts in §4 (as_of 2026-10-07). The rights pointer is the same register pointer as v1.0.0 row 1. This manifest does not widen that pointer into a new grant. |
| P2 | SPY is not a panel member (seat D2). The fourteen tickers are QQQ, IWM, DIA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY. The declared window is 2021-07-06 through 2026-10-07, the same window as v1. | A first row after the window start refuses `BLOCKED / PANEL_COVERAGE`. The sample is never trimmed to the overlap. |
| P3 | Calendar (seat D3, as amended by A1 / D15). The fold calendar runs on the panel's common DATE axis, which is the intersection of the 14 tickers' sessions. | A symmetric difference other than the pinned exclusion in P7 refuses `BLOCKED / CALENDAR_MISALIGNED`, and the refusal names that difference. No forward-fill. A missing row is `absent`. |
| P4 | Identity (seat D4). Each ticker is pinned by a normalized-subframe sha256 from stage-1 `normalize_subframe` / `subframe_sha256` over `IDENTITY_COLUMNS` `(date, open, high, low, close, volume, transactions)`, plus row count, first date, and last date. The pin is the raw, unadjusted rows at or before as_of. | The seat filled those pins in §4. Content hash and subframe sha256 are one digest. A runner that still holds the literal `PREREG_V11_PENDING` refuses `BLOCKED / PREREG_V11_PENDING` before any feature, label, or outcome. That runner token is not a measurement cell in this file. |
| P5 | Price adjustment (seat D5 amended by A1 / D14), which is gate G7 and is DECIDED. See §7. Raw subframe sha256 stays the pin. | D14 adjusts from the pinned table `{(t, "2025-12-05"): 2.0 for t in XLB XLE XLK XLU XLY}`. Rows dated before the effective date have open, high, low, and close divided by the ratio and volume multiplied by the ratio; transactions are unchanged. Each pinned split is confirmed by the observed close ratio on the effective date lying within ±10% of the ratio, else `BLOCKED / SPLIT_TABLE_MISMATCH`. The log(1.25) break check then runs on adjusted closes, and any remaining break is `BLOCKED / SPLIT_DISCONTINUITY` (never inferred). Dividends stay unadjusted. |
| P6 | v1.0.0 D4 / gate G2. User-facing publication of a derived pullback probability still needs the feed-specific written designation. | G2 stays OPEN in v1.0.0's words. This lane is not the rights owner. |
| P7 | Calendar exclusion (seat amendment A1 / D15). The panel calendar is the INTERSECTION of the 14 tickers' sessions in the window. The pinned excluded set is exactly `{"2026-08-18"}`. | 2026-08-18 is absent for QQQ, IWM, XLE, XLF, XLI, XLP, XLRE, XLU, and XLY, and present for DIA, XLB, XLC, XLK, and XLV. It is a source gap routed to the `massive_stock_day` collector owner. A diagnosis exists: `research/grey_deer/reviews/MASSIVE_STOCK_DAY_PARTIAL_DAY_DIAGNOSIS_2026-10-12.md`, on main via PR #9082. Any symmetric difference other than that pinned set is `BLOCKED / CALENDAR_MISALIGNED`. Horizons count sessions on the shared intersection calendar, so a ticker that prints 2026-08-18 drops that close before targets are built. Expected panel: 1320 common sessions, 2021-07-06 through 2026-10-07. The constant is `PINNED_CALENDAR_EXCLUSIONS` in `scripts/research/grey_deer_panel_adjust.py` (`prepare_panel`), lane G-ADJ, landed by PR #9091. |

Yahoo, breadth, CBOE, intl ETF, basket OHLCV, CN, and FRED rows are unchanged from v1.0.0 and stay
out of the panel sample. CN remains under `DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT`.

---

## 2. Scope and method

**In scope for new rows:** the fourteen panel tickers, as Massive US daily closes, plus public
corporate-action facts for 2021-07-06 through 2026-10-07 (splits, reverse splits, ticker changes,
fund mergers, and index-methodology changes that change holdings materially).

**Method for prices and rights.** Rights text is copied by pointer from v1.0.0 §4 row 1 and §8.
No parquet, no price series, and no vendor extract was read by this lane. The counts and hashes in §4
are the seat's store receipts, copied in. They are not estimated and not recomputed here.

**Method for corporate actions.** Issuer and index-provider pages, and exchange notices, are the
citations. A quote is at most fifteen words. A page that did not state the fact is not cited for it.
Aggregator and commentary pages (price history, split compilations, fund-flow writeups) were not
used as citations. Their figures are not copied.

**Dispositions.** v1.0.0's meanings stand. `recorded` still requires a rights determination on main
for the stated use, a recorded first-available day, and declared basis, units, market, and cohort.
The tape-level pointer supports internal fitting and evaluation only in the sense v1.0.0 already
recorded for that tape. It does not, by itself, record a per-ticker rights receipt. User-facing publication
stays `source_unavailable` until G2 is closed by its owner. The seat's per-ticker measurement
receipts are in §4, and G7 is DECIDED (A1 / D14). The panel qualification as a whole is
frozen. The seat records this file's blob sha outside it (prereg v1.1 §0, runner `MANIFEST_BLOB_SHA`).

---

## 3. Evidence class, clock, calendar, basis

Evidence classes are v1.0.0 §2. The panel is aimed at **HISTORICALLY_AVAILABLE** on the Massive
tape (as-printed RAW bytes; the identity pin is those unadjusted rows), inside the declared window.
The seat's store receipt attests, for each ticker, 0 NaN cells, 0 non-positive closes, first date
2021-07-06, and last date 2026-10-07 (as_of 2026-10-07). CURRENT_VINTAGE series remain
ineligible as panel prices. This manifest produces no GENUINELY_ISSUED artifact. The D14 adjustment is a
later runner step on a working copy. It does not re-adjust the stored bytes.

Clock rules are v1.0.0 §3, plus:

1. The common DATE axis is the panel calendar: the intersection of the 14 tickers' sessions in the
   declared window (A1 / D15, rule P7). Folds, purge, and the seat D8 block bootstrap, when a later
   frozen runner implements them, sit on that axis. This manifest does not run them. Expected panel:
   1320 common sessions, 2021-07-06 through 2026-10-07.
2. The pinned exclusion set is exactly `{"2026-08-18"}`. That session is absent for QQQ, IWM, XLE,
   XLF, XLI, XLP, XLRE, XLU, and XLY, and present for DIA, XLB, XLC, XLK, and XLV. It is a source gap
   routed to the `massive_stock_day` collector owner. A diagnosis exists:
   `research/grey_deer/reviews/MASSIVE_STOCK_DAY_PARTIAL_DAY_DIAGNOSIS_2026-10-12.md`, on main via PR #9082.
   A symmetric difference other than that pinned set refuses `BLOCKED / CALENDAR_MISALIGNED` and the
   refusal names the difference. Nothing is carried forward from a neighboring session. Horizons count
   sessions on the shared intersection calendar, so a ticker that has 2026-08-18 drops that close
   before targets are built.
3. A printed close is data. An absent session is `absent` and is not filled. A legal zero is not
   absence (v1.0.0 §3.5). Per-ticker missingness, measured by the seat: 0 NaN cells and 0 non-positive
   closes on every ticker. The only session gap inside the window is the pinned exclusion in rule 2.
   These counts are the seat's receipts, not copies of SPY's receipt.
4. The stored basis is RAW `close_raw` for every panel ticker. The identity pin is those unadjusted
   bytes. A TRADJ or SADJ series is a basis mismatch and is refused, not reconciled (v1.0.0 D5). The
   only adjustment is the pinned D14 table, applied by the runner after the pin check, on a working
   copy. Dividends are not part of that table.
5. Dividends are unadjusted. An ex-dividend print stays in the RAW close. That is a disclosure, not
   a repair.
6. The rolling floor in v1.0.0 D1 still applies. A later floor shrinks the window and is not
   back-filled from a CURRENT_VINTAGE source.

---

## 4. Source table — panel daily closes

Columns follow v1.0.0 §4 row 1. The measurement columns are missingness, content hash, subframe
sha256, and row count. The seat filled every one of those cells from store receipts (as_of
2026-10-07). This lane did not recompute them.

**Common producer.** `collectors/massive_stock_day.py` (`load_ticker`). Canonical home is the
Massive store; this worktree does not hold the parquet bodies.

**Common store / registry.** `data/massive_stock_day/{ticker}.parquet` · `equity.bars.daily.massive`
(the registry row cited by v1.0.0 §4 row 1). No `licensing:` field on that row (G1, still OPEN).

**Common rights.** RECORDED by pointer only, the same pointer as v1.0.0 §4 row 1: register :16-20
→ entitlement record. Feed scope controlling. User-facing feed designation controlling (G2). This
manifest does not quote the entitlement record and does not add a grant.

**Common allowed uses.** Internal fitting and evaluation within the entitled feed scope.
User-facing publication of a derived probability: only under the feed-specific written designation
(register :20), which is not supplied here.

**Common disposition.** Frozen panel rows (manifest v1.1.0; the seat records the blob sha outside this file). Internal use follows the v1.0.0 tape pointer.
Publication is `source_unavailable` while G2 is OPEN. Identity, coverage, and missingness are the seat's receipts in the table below. G7 is DECIDED (§7, A1 / D14).

**Common units / basis / market.** USD · **RAW** (`close_raw`) · US, New York sessions · one ETF,
no ticker-identity feature (seat D6; features, when a frozen runner exists, are scale-free).

**Common available-at.** Intended class HISTORICALLY_AVAILABLE on the tape whose v1.0.0 receipt
names coverage 2021-07-06 through 2026-10-07. Declared window for every row: 2021-07-06 through
2026-10-07. Measured first date is 2021-07-06 and measured last date is 2026-10-07 for every panel
ticker. Raw row counts are in the table (1320 or 1321). The intersection calendar has 1320 common
sessions (P7). The union of panel sessions in the window is 1321.

The seat treats the content hash and the subframe sha256 as one digest: the stage-1 normalized-subframe sha256 over `IDENTITY_COLUMNS` of the raw, unadjusted rows ≤ as_of in the window, and both cells below hold that same value.

| # | Input | Producer | Store / registry | Rights | Available-at / vintage | Units / basis / market / cohort | Missingness | Content hash | Subframe sha256 | Row count | Allowed uses | Disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **QQQ daily close (Massive)** | common producer | `data/massive_stock_day/QQQ.parquet` · common registry row | common rights | common available-at | common units · cohort QQQ | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | d6bd7575c5db3f0fb5d63e6baa2892a5a9d3610a8885562f8ead677a4444373f | d6bd7575c5db3f0fb5d63e6baa2892a5a9d3610a8885562f8ead677a4444373f | 1320 | common allowed uses | common disposition |
| 2 | **IWM daily close (Massive)** | common producer | `data/massive_stock_day/IWM.parquet` · common registry row | common rights | common available-at | common units · cohort IWM | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | ca2df002ee03ed68c19cd77e73b702c057be11f92435936b1f7d4fd57e218b8b | ca2df002ee03ed68c19cd77e73b702c057be11f92435936b1f7d4fd57e218b8b | 1320 | common allowed uses | common disposition |
| 3 | **DIA daily close (Massive)** | common producer | `data/massive_stock_day/DIA.parquet` · common registry row | common rights | common available-at | common units · cohort DIA | 0 NaN cells; 0 non-positive closes; no missing sessions vs SPY | f11d142d015fca21c404e4a96524791d17ecaee4eb08f489f620ac47a753d618 | f11d142d015fca21c404e4a96524791d17ecaee4eb08f489f620ac47a753d618 | 1321 | common allowed uses | common disposition |
| 4 | **XLB daily close (Massive)** | common producer | `data/massive_stock_day/XLB.parquet` · common registry row | common rights | common available-at | common units · cohort XLB | 0 NaN cells; 0 non-positive closes; no missing sessions vs SPY | 0863d459e79a40b0943b2ced0aeea42801e81d9a989b8df07823ee6445055628 | 0863d459e79a40b0943b2ced0aeea42801e81d9a989b8df07823ee6445055628 | 1321 | common allowed uses | common disposition |
| 5 | **XLC daily close (Massive)** | common producer | `data/massive_stock_day/XLC.parquet` · common registry row | common rights | common available-at | common units · cohort XLC | 0 NaN cells; 0 non-positive closes; no missing sessions vs SPY | 121c9b52c6ef4231540b73ad15362cf5927e7e5ae3c8df073ae231cbd158374d | 121c9b52c6ef4231540b73ad15362cf5927e7e5ae3c8df073ae231cbd158374d | 1321 | common allowed uses | common disposition |
| 6 | **XLE daily close (Massive)** | common producer | `data/massive_stock_day/XLE.parquet` · common registry row | common rights | common available-at | common units · cohort XLE | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | ebf4be8c9f7f53b2472b1a032d5f105f7ed5ce7f439411f468b6435939176ba3 | ebf4be8c9f7f53b2472b1a032d5f105f7ed5ce7f439411f468b6435939176ba3 | 1320 | common allowed uses | common disposition |
| 7 | **XLF daily close (Massive)** | common producer | `data/massive_stock_day/XLF.parquet` · common registry row | common rights | common available-at | common units · cohort XLF | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | da3a5aa47a06f469dd6a99288e7be423ff63e9a8b9dc10d6832dc7a4af5b1491 | da3a5aa47a06f469dd6a99288e7be423ff63e9a8b9dc10d6832dc7a4af5b1491 | 1320 | common allowed uses | common disposition |
| 8 | **XLI daily close (Massive)** | common producer | `data/massive_stock_day/XLI.parquet` · common registry row | common rights | common available-at | common units · cohort XLI | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | d153ab22f333d536bdf7c8ef84c981b9c5614e8f62969687d765f043e35e596c | d153ab22f333d536bdf7c8ef84c981b9c5614e8f62969687d765f043e35e596c | 1320 | common allowed uses | common disposition |
| 9 | **XLK daily close (Massive)** | common producer | `data/massive_stock_day/XLK.parquet` · common registry row | common rights | common available-at | common units · cohort XLK | 0 NaN cells; 0 non-positive closes; no missing sessions vs SPY | 7dc854d1e340f1619340c1c26c9be4cc17fd0c925a0bbe036c74c058d53d0e63 | 7dc854d1e340f1619340c1c26c9be4cc17fd0c925a0bbe036c74c058d53d0e63 | 1321 | common allowed uses | common disposition |
| 10 | **XLP daily close (Massive)** | common producer | `data/massive_stock_day/XLP.parquet` · common registry row | common rights | common available-at | common units · cohort XLP | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | a480545513732922a2be49c2cf807f7500baf923beb909cdf8d59eae70ef885b | a480545513732922a2be49c2cf807f7500baf923beb909cdf8d59eae70ef885b | 1320 | common allowed uses | common disposition |
| 11 | **XLRE daily close (Massive)** | common producer | `data/massive_stock_day/XLRE.parquet` · common registry row | common rights | common available-at | common units · cohort XLRE | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | c578f88c142f67a237f45a324097fc912c6994abd2aaa355080b5e94ca41fcae | c578f88c142f67a237f45a324097fc912c6994abd2aaa355080b5e94ca41fcae | 1320 | common allowed uses | common disposition |
| 12 | **XLU daily close (Massive)** | common producer | `data/massive_stock_day/XLU.parquet` · common registry row | common rights | common available-at | common units · cohort XLU | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | 238dbbd6d68fa71ae074020ad83a2bbc4ffcd0a45cc087ca1982d56fb4a5b2f1 | 238dbbd6d68fa71ae074020ad83a2bbc4ffcd0a45cc087ca1982d56fb4a5b2f1 | 1320 | common allowed uses | common disposition |
| 13 | **XLV daily close (Massive)** | common producer | `data/massive_stock_day/XLV.parquet` · common registry row | common rights | common available-at | common units · cohort XLV | 0 NaN cells; 0 non-positive closes; no missing sessions vs SPY | 64f9d9b448b7e93b9e11137db11d9860c1c61d4682b0c685f43a6ff73db5d251 | 64f9d9b448b7e93b9e11137db11d9860c1c61d4682b0c685f43a6ff73db5d251 | 1321 | common allowed uses | common disposition |
| 14 | **XLY daily close (Massive)** | common producer | `data/massive_stock_day/XLY.parquet` · common registry row | common rights | common available-at | common units · cohort XLY | 0 NaN cells; 0 non-positive closes; session 2026-08-18 absent (D15 pinned exclusion) | 870fa4c0b19e31d5ef33b2d0702b9e9815b89285f3e3eb925434afb36b758ed5 | 870fa4c0b19e31d5ef33b2d0702b9e9815b89285f3e3eb925434afb36b758ed5 | 1320 | common allowed uses | common disposition |

SPY is not row 15. v1.0.0 §4 row 1 remains the SPY record. It is not a member of this panel.
The seat's positive control on the same normalized-subframe method: the SPY subframe sha256 equals
the W3 pin `c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb`.

Launch dates checked because the seat named them: XLC inception is 2018-06-18 and its NYSE Arca
listing date is 2018-06-19, both before the window
([SSGA XLC](https://www.ssga.com/us/en/intermediary/etfs/state-street-communication-services-select-sector-spdr-etf-xlc)).
XLRE inception is 2015-10-07 and its NYSE Arca listing date is 2015-10-08, both before the window
([SSGA XLRE](https://www.ssga.com/us/en/intermediary/etfs/the-real-estate-select-sector-spdr-fund-xlre)).
Neither launch is an in-window corporate action.

---

## 5. Eligible origins — not frozen

An origin is not eligible for a frozen panel use until this manifest is frozen. The rule, once
frozen, is v1.0.0 §5 applied on the common DATE axis: every input the use needs is recorded for
that use, `available_at` is at or before the origin under a HISTORICALLY_AVAILABLE receipt, market
and basis and units match, and §3 guards pass. The measurement cells are the seat's receipts in §4.
This file is frozen, so a panel origin is eligible exactly when the conditions above hold. Pre-2021-07-06 dates stay excluded (v1.0.0 D1). SPY origins stay outside this panel
(seat D2). This manifest does not count episodes or event months.

---

## 6. Corporate actions, 2021-07-06 through 2026-10-07

One row per ETF. Shared Select Sector events are stated once, then each row cites the URL that
applies to that ticker. Quotes are from the cited page and are at most fifteen words.

### 6.1 Shared Select Sector events

These apply to the Select Sector index series. Membership effect is not uniform. This manifest does
not invent a per-name list the notice does not give.

**S1 — GICS structure, effective after the close on 2023-03-17.** S&P DJI:
[2022-03-31 GICS release](https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20220331-1451157/1451157_gicspressrelease31march2022.pdf).
Quote: "after the close of business (ET) on Friday, March 17, 2023."
The same release says the Information Technology "Data Processing & Outsourced Services"
sub-industry "will be moved to the Industrials Sector", that "transaction and payment processing
companies will be reclassified" into Financials, that payroll processors move to Industrials, and
that travel-related data-processing names are "moved to the Consumer Discretionary Sector".
A later S&P DJI note restates implementation in S&P DJI indices "prior to the open of trading on
Monday, March 20, 2023"
([2022-12-21 note](https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20221221-1460365/1460365_spasxalltechnologyindexconsultation12-22-2022.pdf)).
Named sector path: XLK loses the discontinued IT sub-industry; XLF and XLI receive the reclassified
names; XLY is on the path for the travel-related names. The release does not enumerate a per-ETF
residual for XLB, XLC, XLE, XLP, XLRE, XLU, or XLV. Those residuals are not asserted to be empty.

**S2 — Select Sector capping methodology, effective before the open on 2024-09-23.** Series-wide,
not an XLK-only rule. S&P DJI announcement text at
[1474128 (2024-09-03)](https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20240903-1474128/1474128_sp-select-sector-indices-results-20240903.pdf)
states implementation "prior to the market open on Monday, September 23, 2024."
S&P DJI's Indexology note of the same change: "The quarterly capping process is changing." and
"methodology changes that take effect on Sept. 23, 2024"
([Indexology, 2024-09-10](https://www.indexologyblog.com/2024/09/10/explaining-changes-to-select-sector-indices/)).
No separate **2023** XLK capping-formula amendment was found. The 2023 holdings change found for
XLK is S1, not a capping-rule change. The 2024-09-23 change is the capping-formula change.

**S3 — Legacy cap binding on the Technology Select Sector index in 2024, before S2.** This is an
application of the then-current rule, not an amendment. S&P DJI FAQ:
[June 2024 Technology Select Sector rebalance](https://www.spglobal.com/spdji/en/documents/education/faq-technology-select-sector-index-june-2024-rebalance.pdf).
Quote: "step 7 of the capping mechanism was triggered."
Indexology (same URL as S2) also describes the legacy mechanism binding at the March 2024 reference
date for that index. Weights are not restated here.

**S4 — Reference-date methodology, announced 2024-12-02, Select Sector indices included.** S&P DJI:
[1475776](https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20241202-1475776/1475776_constituent-weighting-reference-date-update-20241202.pdf).
Quote: "There are no changes to the methodologies concerning actual capping or weighting processes."
The announcement moves the Select Sector rebalancing reference date from the second Friday to the
Wednesday before that Friday, with the December 2024 rebalancing. It is a timing change, not a new
cap formula.

**S5 — Display-name change, effective 2025-12-01 (US local time). Tickers unchanged.** State Street
Japan notice, 2025-11-28:
[jp-press-release-20251128.pdf](https://www.ssga.com/library-content/assets/pdf/apac/important-information/2025/jp-press-release-20251128.pdf).
The ticker column is unchanged for XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, and XLY.
The notice is in Japanese. Its statement is that the change is the ETF name only and does not
affect investment policy, portfolio team, or objective. That sentence is a translation of the
notice, not a second source. This is not a ticker change and not a merger.

**S6 — Share splits, issuer notice 2025-11-20.** State Street Investment Management:
[share-split release](https://investors.statestreet.com/investor-news-events/press-releases/news-details/2025/State-Street-Investment-Management-Announces-Share-Splits-for-Five-Select-Sector-SPDR-ETFs/default.aspx).
Quote: "Shares will trade at their post-split price effective December 5, 2025."
Also: "there are no CUSIP changes."
Record date 2025-12-02, payable after the close on 2025-12-04, post-split trading 2025-12-05.
The notice names five funds, each 2-for-1: **XLK, XLY, XLE, XLU, XLB**. It does not name XLC, XLF,
XLI, XLP, XLRE, or XLV. Dollar prices printed in that notice are not copied here.

Seat primary sources for amendment A1 / D14, cited here without a new quote: the State Street Investment Management release of 2025-11-20 carried by Business Wire (<https://www.businesswire.com/news/home/20251120957218/en/State-Street-Investment-Management-Announces-Share-Splits-for-Five-Select-Sector-SPDR-ETFs>) and the SSGA Select Sector SPDR Fund Share Splits FAQ (<https://www.ssga.com/library-content/products/fund-docs/etfs/us/information-schedules/select-sector-spdr-fund-share-splits-faq.pdf>). The investors.statestreet.com release above is kept. The seat's raw-byte receipt shows one break above log(1.25) on 2025-12-05 for exactly XLB, XLE, XLK, XLU, and XLY, and no such break for the other nine panel tickers. Observed close ratios are not copied into this file.

### 6.2 One row per ETF

| # | Ticker | Splits / reverse splits | Ticker change / fund merger | Other in-window event | Citation | Quote | Status |
|---|---|---|---|---|---|---|---|
| 1 | QQQ | UNVERIFIED as a negative. Searched `site:invesco.com` for "share split", "stock split", and "2-for-1". No in-window issuer split notice was returned. | No ticker change found: the Invesco page still names QQQ. Fund merger: UNVERIFIED as a negative; no merger notice in the Invesco pages read. The UIT-to-open-end step below is a reclassification, not a merger. | (a) Nasdaq-100 special rebalance under the published methodology, effective before the open on 2023-07-24. Not a methodology amendment. Membership unchanged; weights redistributed. (b) Nasdaq-100 methodology updates approved effective 2026-05-01. The press release does not state the rule diff; the diff is UNVERIFIED. Current methodology through 2026-04-30. (c) Fund reclassified from a unit investment trust to an open-end ETF. Invesco page dated 2025-12-22. An Invesco semi-annual report dates the classification change after the close on 2025-12-19. Objective remains the Nasdaq-100. | (a) <https://www.nasdaq.com/press-release/the-nasdaq-100-index-special-rebalance-to-be-effective-july-24-2023-2023-07-07> (b) <https://www.nasdaq.com/press-release/nasdaq-concludes-public-consultation-nasdaq-100-indexr-methodology-2026-03-30> (c) <https://www.invesco.com/qqq-etf/en/market-outlook/whats-new-about-qqq.html> and <https://www.invesco.com/content/dam/invesco/hk/en/pdf/qqq-semi-annual-report-en.pdf> | (a) "will not result in the removal or addition of any securities." (b) "approved updates to the Nasdaq-100 Index methodology, effective May 1, 2026." (c) "QQQ was reclassified from its original unit investment trust (UIT) format." Date sentence: "Effective after market close on December 19, 2025." | MIXED. (a) and (c) cited. Split absence UNVERIFIED. Methodology-update substance UNVERIFIED. Merger absence UNVERIFIED. |
| 2 | IWM | UNVERIFIED as a negative. Searched "iShares Russell 2000" with "split" across 2022–2026. The OCC memo below is an option-symbol consolidation, not a share split. | No ticker change found. iShares still lists ticker IWM, CUSIP 464287655. Fund merger: UNVERIFIED as a negative. | (a) OCC flex-option consolidation of symbol 1IWM into IWM, effective 2025-12-29. Not a share split. (b) Russell US Indexes: consultation results published 2025-01-16; additional semi-annual reconstitution scheduled to begin in Q4 2026. FTSE Russell notice 2025-11-05 sets the new effective date at Friday 2026-12-11, which is **after** this window (window ends 2026-10-07). June reconstitution date "remains unchanged" (fourth Friday in June). The June 2026 reconstitution took effect after the close on 2026-06-26 and is inside the window as that June review, not as the first extra semi-annual date. An LSEG note dated 2025-12-17 describes the frequency move as "starting in December 2026", which matches the notice's Q4 2026 start. Ordinary June reconstitutions before that change are index maintenance, not a methodology amendment. | (a) <https://infomemo.theocc.com/infomemos?number=58054> (identity) <https://www.ishares.com/us/products/239710/ishares-russell-2000-etf> (b) <https://research.ftserussell.com/products/index-notices/home/getnotice/?id=2617649> and <https://www.lseg.com/en/ftse-russell/russell-reconstitution> and <https://www.lseg.com/en/ftse-russell/research/russell-us-indexes-move-to-semi-annual-reconstitution> | (a) "consolidate certain iShares Russell 2000 ETF flex series." (b) "scheduled to begin in Q4 2026." Also: "New Effective Date: Friday, 11 December 2026." And: "Beginning in 2026, the Russell Indexes are reconstituted semi-annually." | MIXED. (a) and (b) cited. In-window share-split absence UNVERIFIED. Merger absence UNVERIFIED. The extra reconstitution's effective date is outside the window. |
| 3 | DIA | UNVERIFIED as a negative. Searched SPDR DIA "share split" / "reverse split" for 2023–2026. The SSGA listing page shows ticker DIA and CUSIP 78467X109 and does not announce a split. | No ticker change. A 2026-02-24 State Street Japan notice changes the display name; the ticker cell stays DIA. The notice is in Japanese and describes a name and benchmark-display-name change, not a policy change (translation, same caution as S5). Fund merger: UNVERIFIED as a negative. | Constituent substitutions are not a methodology amendment. SSGA's DIA page names NVIDIA and Sherwin-Williams as additions that "joined the ranks on November 8, 2024." Removals are not named on that page and are not guessed. Searches for a DJIA methodology amendment returned other Dow Jones families (Yield Weighted; U.S. Style Total Stock Market; Best-in-Class), not the Industrial Average DIA tracks. No DJIA methodology amendment was read. That negative is UNVERIFIED as a complete methodology census. | <https://www.ssga.com/us/en/institutional/etfs/spdr-dow-jones-industrial-average-etf-trust-dia> and <https://www.ssga.com/uk/en_gb/intermediary/capabilities/equities/spdr-core-equity-etfs/dia-djia> and <https://www.ssga.com/library-content/assets/pdf/apac/announcements/2026/jp/announcement-etfs-dia-jp-ja-20260224.pdf> | "joined the ranks on November 8, 2024." | MIXED. Additions and display name cited. Split absence UNVERIFIED. Merger absence UNVERIFIED. DJIA methodology-amendment census UNVERIFIED. |
| 4 | XLB | **In-window split.** 2-for-1. Post-split trading 2025-12-05. S6. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 (no per-name residual asserted), S2, S4, S5. | S6 URL above. S5 URL above. S1 and S2 URLs in §6.1. | S6 quote in §6.1. | MIXED. Split CITED. Merger absence UNVERIFIED. |
| 5 | XLC | Not named in S6. No second in-window split notice found. Searched "Select Sector SPDR share split" with XLC. Complete split history: UNVERIFIED. Launch 2018-06-18 is before the window (§4). | Ticker unchanged (S5). Ticker on the SSGA listing page is XLC. Merger: UNVERIFIED as a negative. | S1 (residual not asserted), S2, S4, S5. | S6 URL (absence from the named five). Listing: <https://www.ssga.com/us/en/intermediary/etfs/state-street-communication-services-select-sector-spdr-etf-xlc> | S6 quote names the five that did split; XLC is not among them. | MIXED. Launch and name cited. In-window split absence UNVERIFIED. Merger absence UNVERIFIED. |
| 6 | XLE | **In-window split.** 2-for-1. Post-split trading 2025-12-05. S6. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 (no per-name residual asserted), S2, S4, S5. | S6 URL above. | S6 quote in §6.1. | MIXED. Split CITED. Merger absence UNVERIFIED. |
| 7 | XLF | Not named in S6. No second in-window split notice found. Searched "Select Sector SPDR share split" with XLF. Complete split history: UNVERIFIED. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 applies: payment-processing names were reclassified into Financials. Also S2, S4, S5. | S1 URL in §6.1. Quote from that release: "transaction and payment processing companies will be reclassified." | See S1 quote. | MIXED. S1 CITED. Split absence UNVERIFIED. Merger absence UNVERIFIED. |
| 8 | XLI | Not named in S6. No second in-window split notice found. Searched "Select Sector SPDR share split" with XLI. Complete split history: UNVERIFIED. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 applies: the discontinued IT sub-industry "will be moved to the Industrials Sector." Also S2, S4, S5. | S1 URL in §6.1. | "will be moved to the Industrials Sector." | MIXED. S1 CITED. Split absence UNVERIFIED. Merger absence UNVERIFIED. |
| 9 | XLK | **In-window split.** 2-for-1. Post-split trading 2025-12-05. S6. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 applies (IT sub-industry discontinued). S3 (legacy cap bound in 2024; not a 2023 formula change). S2 (formula change effective 2024-09-23, series-wide, material for this index). S4, S5. No 2023 capping-formula amendment was found. | S6 URL. S1 URL. S3 FAQ URL. S2 announcement URL. All in §6.1. | S3: "step 7 of the capping mechanism was triggered." S2: "The quarterly capping process is changing." | MIXED. Split, S1, S2, and S3 CITED. Merger absence UNVERIFIED. The specific label "2023 XLK capping change" was not matched to a capping-formula notice; see S1 versus S2. |
| 10 | XLP | Not named in S6. No second in-window split notice found. Searched "Select Sector SPDR share split" with XLP. Complete split history: UNVERIFIED. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 residual not asserted. S2, S4, S5. | S6 URL (absence from the named five). S5 URL. | S6 quote in §6.1. | MIXED. Name-change cited. Split absence UNVERIFIED. Merger absence UNVERIFIED. |
| 11 | XLRE | Not named in S6. No second in-window split notice found. Searched "Select Sector SPDR share split" with XLRE. Complete split history: UNVERIFIED. Launch 2015-10-07 is before the window (§4). | Ticker unchanged (S5). Listing ticker XLRE. Merger: UNVERIFIED as a negative. | S1 residual not asserted. S2, S4, S5. | Listing: <https://www.ssga.com/us/en/intermediary/etfs/the-real-estate-select-sector-spdr-fund-xlre> S6 URL. | S6 quote in §6.1. | MIXED. Launch and name cited. Split absence UNVERIFIED. Merger absence UNVERIFIED. |
| 12 | XLU | **In-window split.** 2-for-1. Post-split trading 2025-12-05. S6. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 residual not asserted. S2, S4, S5. | S6 URL above. | S6 quote in §6.1. | MIXED. Split CITED. Merger absence UNVERIFIED. |
| 13 | XLV | Not named in S6. No second in-window split notice found. Searched "Select Sector SPDR share split" with XLV. Complete split history: UNVERIFIED. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 residual not asserted. S2, S4, S5. | S6 URL (absence from the named five). S5 URL. | S6 quote in §6.1. | MIXED. Name-change cited. Split absence UNVERIFIED. Merger absence UNVERIFIED. |
| 14 | XLY | **In-window split.** 2-for-1. Post-split trading 2025-12-05. S6. | Ticker unchanged (S5). Merger: UNVERIFIED as a negative. | S1 applies on the travel-related path: those names are "moved to the Consumer Discretionary Sector." Also S2, S4, S5. | S6 URL. S1 URL. | "moved to the Consumer Discretionary Sector." | MIXED. Split and S1 CITED. Merger absence UNVERIFIED. |

Ordinary quarterly and annual reconstitutions that the index methodologies already scheduled are
maintenance. They are not each listed as a methodology amendment. The amendments and the one-off
special rebalance are the rows above.

---

## 7. Gates

G1–G6 keep v1.0.0 §8's gap, owner, and closing condition. Their v1.1 state is OPEN. This manifest
does not close any of them. G2's wording is the v1.0.0 sentence, unchanged. G7 is DECIDED by seat amendment A1 / D14.

| Id | Gap (v1.0.0 wording for G1–G6) | Owner | What closes it | v1.1 state |
|---|---|---|---|---|
| G1 | `equity.bars.daily.massive` registry row has no `licensing:` field (registry :134-152). | dataset-registry owner | Add the field pointing at the entitlement record (by pointer, no terms). | OPEN |
| G2 | Massive user-facing feed designation for derived pullback probabilities (register :20). | Chairman / entitlement holder | Feed-specific written designation recorded in `research/licenses/`. | OPEN |
| G3 | CN rights determination + `510300.SS` labelling (handoff O-d). | data-source owner | A CN row in the register; the DNR kill stays. | OPEN |
| G4 | COR1M / CBOE terms (row 7). | data-source owner | A determination recorded in the register; registry row for `data/cboe/`. | OPEN |
| G5 | `intl_etf`, `breadth`, `baskets/ohlcv` registry rows (rows 6, 8, 9). | dataset-registry owner | Registry rows with producer, basis and rights. | OPEN |
| G6 | FRED model-use determination (register :100). | rights owner | DETERMINED-FROM-PUBLISHED-TERMS row for model use. | OPEN |
| G7 | Price adjustment policy, decided by seat amendment A1 / D14. Pinned table `{(t, "2025-12-05"): 2.0 for t in XLB XLE XLK XLU XLY}`. Rows dated before the effective date have open, high, low, and close divided by the ratio and volume multiplied by the ratio; transactions are unchanged. Each pinned split is confirmed when the observed close ratio on the effective date lies within ±10% of the ratio (`SPLIT_CONFIRM_TOL = 0.10`, the closed interval from 0.9 times the ratio to 1.1 times the ratio), else `BLOCKED / SPLIT_TABLE_MISMATCH`. The log(1.25) break check then runs on adjusted closes, and any remaining break is `BLOCKED / SPLIT_DISCONTINUITY` (an unpinned split is never inferred). Raw subframe sha256 stays the pin on the unadjusted bytes. Dividends are unadjusted, and that is disclosed. Implementation, landed by PR #9091, is `scripts/research/grey_deer_panel_adjust.py` (`prepare_panel`, `PINNED_SPLITS`, `PINNED_CALENDAR_EXCLUSIONS`, `SPLIT_CONFIRM_TOL = 0.10`), lane G-ADJ. | Grey Deer seat | Closed by seat amendment A1 / D14, recorded in this row. | DECIDED |

**In-window splits under the decided rule** (issuer notice S6, positive declarations only): **XLB, XLE, XLK,
XLU, XLY**, each 2-for-1, post-split trading 2025-12-05. The rule is the pinned table in the G7 row
(A1 / D14): adjust those five, confirm, then run the break check on adjusted closes. The adjustment
is that pinned table only. Primary sources, cited without a new quote, beside the S6
investors.statestreet.com release that is kept:
<https://www.businesswire.com/news/home/20251120957218/en/State-Street-Investment-Management-Announces-Share-Splits-for-Five-Select-Sector-SPDR-ETFs>
and
<https://www.ssga.com/library-content/products/fund-docs/etfs/us/information-schedules/select-sector-spdr-fund-share-splits-faq.pdf>.
The other nine ETFs are not listed as split names: no issuer split notice was found for
them inside the window, and that negative is `UNVERIFIED` in §6 rather than a certificate of absence.

G1–G6 do not become panel-sample blockers beyond the blocks v1.0.0 already stated. G2 still blocks
user-facing publication. G7 is DECIDED (A1 / D14) and the measurement cells are filled, so neither
blocks this manifest, which the seat has frozen.
A freeze is not a run. The runner refuses before any feature, label, or outcome while any identity pin,
blob pin, or the trial budget is put back to `PREREG_V11_PENDING` (seat D11). Seat D13 stands: no panel outcome before prereg v1.1 and
manifest v1.1.0 are frozen by the seat and merged, and v1 §14's ceiling carries over (no customer odds, no
publication, no capital change, nothing written to PR #8721 or PR #8188).

---

## 8. Contract notes for a later runner (not code, not a run)

Carried from v1.0.0 §7, with the panel refusals named. This lane does not implement them.

1. Refuse an input whose manifest row is `source_unavailable` for the declared use.
2. Refuse before any feature, label, or outcome while the runner's identity pins or the trial budget
   are `PREREG_V11_PENDING` (`BLOCKED / PREREG_V11_PENDING`). The pin values in §4 are the seat's fill;
   the frozen runner carries the same values in `IDENTITY_PINS`.
3. Refuse `BLOCKED / PANEL_COVERAGE` when a ticker's first row is after 2021-07-06. Do not trim.
4. Build the panel calendar as the intersection of the 14 tickers' sessions. The pinned exclusion
   set is exactly `{"2026-08-18"}` (A1 / D15). Refuse `BLOCKED / CALENDAR_MISALIGNED` when the
   symmetric difference is anything else, and name that difference. Do not forward-fill. Expected
   panel: 1320 common sessions from 2021-07-06 through 2026-10-07. Horizons count sessions on that
   intersection, so a ticker that has 2026-08-18 drops that close before targets are built.
5. Apply the pinned split table before the break check (A1 / D14):
   `{(t, "2025-12-05"): 2.0 for t in XLB XLE XLK XLU XLY}`. Rows dated before the effective date
   have open, high, low, and close divided by the ratio and volume multiplied by the ratio;
   transactions stay unchanged. If the observed close ratio on the effective date is not within
   ±10% of the ratio, refuse `BLOCKED / SPLIT_TABLE_MISMATCH`. Then refuse
   `BLOCKED / SPLIT_DISCONTINUITY` on any remaining log(1.25) break in the adjusted closes. Do not
   infer an unpinned split. The raw subframe sha256 stays the pin. Dividends stay unadjusted.
6. Record `absent`. Do not fill. Do not treat a printed zero as absent.
7. Emit manifest version `1.1.0` only against this frozen file, whose git blob sha equals the
   runner's `MANIFEST_BLOB_SHA`. This file writes no result.

---

## 9. Versioning and what this file is not

- **Version `1.1.0` FROZEN — seat values filled, G7 decided (A1/D14), calendar pinned (A1/D15); file blob sha recorded by the seat outside this file.**
  A successor re-pins v1.0.0's file-and-line citations before relying on them, as v1.0.0 itself
  requires.
- **Not done here:** no store read by this lane, no price download, no label, no metric,
  no bootstrap, no panel outcome, and no file under `research/grey_deer/pullback_stage1b/`.
  The hashes, row counts, and dates in §4 are the seat's receipts, copied in, not computed here.
- **Not a rights grant** and not a ratification of the Prophet US register outside the pullback scope.
- **DO_NOT_REDO:** v1.0.0 is the parent and is not edited. Stage-1 SPY results and the deviation log
  are not edited. The CN adjusted-tape kill still stands (v1.0.0 row 10).
