# Source readiness R2: observed facts, not inferred availability

Continuation of PR #9507. Source pin: Macro `3ab3382af89242c7b7fe8c65360bd883a7dd3504`. Local metadata observation: **2026-10-17T04:58:33.581812+00:00**, as reported by M2. This is a named local research-cache observation, not proof of the deployed producer, production freshness or dataset rights.

## 1. Findings that change the execution plan

**The first all-sector study needs thirteen series: eleven sectors, SPY and the BIL bill-ETF proxy.** All thirteen local price files exist, but existence is not source qualification. The current optional availability-capture path covers only nine original sectors, excludes XLC/XLRE/SPY/BIL, is default-off and explicitly does not establish historical original availability. The existing source acceptance says scheduled collection remains unchanged. No second capture service should be built to solve this.

**Local sector-flow history is short and date alignment is incomplete.** The observed sector-flow files have 68–69 rows, while equity prices end on October 9, BIL on October 8 and sector flows on October 7. This is enough to reject a claim that this cache already supports a long-history, aligned flow-augmented forecast. It does not prove all production stores are stale or that a different lawful historical source is unavailable.

**BroadFlowAdapter has two concrete research-input problems:** it stamps `date.today()` rather than a provider observation date, and permits `regularMarketPrice` when `navPrice` is absent. The current output discards the distinction. A synthetic probe executed the exact source class and reproduced these behaviors, including a Sunday observation index. No production code or real provider request was executed.

## 2. What was actually inspected

Named path: the installed Macro source checkout's `data/yahoo` and `data/flows` directories on M2. The probe first inspected file existence/size, then Parquet footer schema/row counts and **timestamp-column statistics only**. No price, return or volume column was decoded. No native outcome study, vault peek, trial registration, collector run or provider acquisition occurred.

Footer min/max dates establish bounds, **not complete calendars, valid individual rows, historical information availability or a coherent immutable snapshot**. The initial observation did not lock live writers or establish transaction-wide immutability; later empirical use must bind actual owner snapshots. Filesystem modification dates were not used as market evidence.

| Local price series | Rows | Earliest timestamp in footer | Latest timestamp in footer | Columns |
|---|---:|---|---|---|
| SPY | 8,482 | 1993-01-29 | 2026-10-09 | close_price, close, volume, Date |
| XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY | 6,992 each | 1998-12-22 | 2026-10-09 | same |
| XLC | 2,089 | 2018-06-19 | 2026-10-09 | same |
| XLRE | 2,767 | 2015-10-08 | 2026-10-09 | same |
| BIL | 4,872 | 2007-05-30 | 2026-10-08 | same |

| Local flow series | Rows | Earliest timestamp in footer | Latest timestamp in footer |
|---|---:|---|---|
| XLB, XLE, XLP | 69 each | 2026-06-09 | 2026-10-07 |
| XLC, XLF, XLI, XLK, XLRE, XLU, XLV, XLY | 68 each | 2026-06-09 | 2026-10-07 |
| SPY | 71 | 2026-07-12 | 2026-10-08 |
| BIL | absent | not observed | not observed |

The flow schema is nav, aum_mn, so_mn and its timestamp index. July 12, 2026 was a Sunday: that local SPY timestamp is an observation to reconcile, not by itself proof of an erroneous actual transaction. The source-level synthetic witness independently explains how a retrieval-date row can arise. BIL fund flows are not required for a BIL return benchmark; their absence is not an invented blocker.

The exact named `.availability_capture/receipts` directory was absent in this source checkout. No receipt objects or captured price images were read. This is a local absence, not an estate-wide census or proof that the accepted dormant capability is broken.

Full supporting footer metadata is retained under the existing M2 evidence path `readiness-source-20261016/source-readiness-metadata.json`, SHA-256 `3ae0df11c269db3304cdc2eac5d10ad8bc91cceef8b42a64ca8fbbb2673ccca0`.

## 3. Exact-source broad-flow witness

Source: `collectors/sponsors.py`, Git blob `8832230059f46b3b7db04f0977d49e346f511711`; BroadFlowAdapter lines 146–197 at the source pin. The probe verifies the full file's Git blob before extracting **only that class** with Python AST. It supplies a minimal Adapter base, an injected date, pandas and a synthetic yfinance object. Other imports from the extracted class are refused. No product module is imported and no provider/network call occurs.

| Synthetic case | Supplied evidence | Actual source output | Interpretation |
|---|---|---|---|
| Missing official NAV | navPrice absent; market price 103; valid synthetic assets/shares | nav column contains 103 | Field accepts market price without retaining NAV substitution provenance |
| Older provider market timestamp | provider timestamp October 14; retrieval October 16 | observation index October 16 | Returned provider clock is not used to identify the row's economic observation date |
| Weekend retrieval | same synthetic prior-market observation; retrieval Sunday October 18 | observation index Sunday October 18 | No exchange-session/observation-date qualification in this path |

Five fake ticker calls occurred per case and zero real calls. All three behaviors reproduced. This is **a diagnostic failure witness, not a fix, investment test or estimate of production incidence**. The probe should stop with a source-mismatch error after the source blob changes; it must not silently test a different implementation.

The published [probe_broad_flow_contract.py](probe_broad_flow_contract.py) and [broad_flow_probe_results.json](broad_flow_probe_results.json) retain the reproducible evidence. Result SHA-256: `2a7e3c6b42e58c2b3109b6e47d0dcb9717c6088397bf48632a8af98054f05519`.

### Root cause and bounded later repair

The collector normalizes heterogeneous `Ticker.info` fields into one three-column row without preserving per-field basis and source clocks. Replacing the UI label or filling a newer date would not solve that contract defect.

A later source-owner repair must retain observation and retrieval clocks separately, preserve whether a value is NAV or market price, validate compatible shares/assets/NAV dates and split handling, and make unavailable fields explicit. Do not invent a provider timestamp when none exists. Do not generate an exchange observation for a retrieval merely because the process ran on that date. No silent fallback to a different feed or market-price basis is permitted for a qualified fund-creation estimate.

Keep the existing display-only restrictions. This continuation does not alter collector behavior, its source writer, trading permissions or the dataset. The production incidence and actual provider field coverage remain unmeasured.

## 4. The useful capture infrastructure is already present—but dormant and narrow

Read directly:

- `lib/store.py`, blob `709203a336c874d74076312e128c130d598f7876`, especially line 37 and lines 160–223.
- `collectors/base.py` default-off `capture_yahoo_receipts` route and its exact-adapter condition.
- `collectors/yahoo.py`, blob `ac53401672ab0bddc5507bc5aabc52d74967332f`, current-call source-metadata method.
- `research/RESEARCH_CODEGEN_YAHOO_CAPTURE_SOURCE_2026_10_13.md`, blob `53c34ae65d87b8cd1848066cb187bd609b93508f`.

The source accepts only XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY with exact declared Yahoo Adj Close total-return lineage. It preserves separate provider-return and merged-return images, with different clocks. The receipt intentionally leaves provider availability, rights, source/operation identity and clock authentication unknown, and historical original availability false. A hash of a newly captured historical frame does not prove the frame existed at those past dates.

The best next infrastructure act is therefore **qualify and extend the incumbent capture path for the actual required cohort and reader**, not build another capture registry or automatically enable a dormant option. Activation still needs actual source-use, writer, calendar and consumer qualification. No such activation was attempted here.

## 5. Readiness by intended use

| Input/use | Evidence reached | What remains before that use |
|---|---|---|
| Sector ETF/benchmark price history for reconstructed development | Local files and dual-basis schema exist; coverage bounds observed | Actual rights, owner snapshot, valid calendar/rows, basis revision handling, common endpoints and explicit reconstruction classification |
| Naturally observed prospective thirteen-series forecasts | Dormant nine-sector capture source exists | Required four additional series, real invocation and normal-path capture proof, source/use and clock qualification, rejecting consumer |
| Sector-flow descriptive context | Small existing local history and explicit source computation | Source dates/precision/splits/gaps; no claim of long historical coverage |
| Broad-flow forecasting input | Exact source contract failures reproduced | Source-owner repair and historical/prospective provenance; preserve context-only use until qualified |
| BIL cash-proxy comparison | Local adjusted-return-labelled file exists with different tail date | Compatible total-return semantics, common endpoints, costs and explicit ETF-not-literal-bill label |
| Long-history flow or holdings increment | Not established by inspected cache | Lawful historical source or genuinely prospective accrual; no synthetic backfill from returns |
| Macro/revisions/industry mechanisms | Architecture and source-owner map exist | Variable-specific first-known/vintage/coverage evidence; do not assume maturity from price history |

Missing metadata limits the affected use, not the entire programme. Reconstructed development may be admitted under an honest contract without pretending to be point-in-time prospective evidence. More source data are not automatically needed when an existing pure-price baseline can be qualified independently.

## 6. Native research infrastructure: no replacement needed

The current `engine/trial_ledger.py` has source-level transactional ownership, fsynced configuration generation and declared-budget accounting. Its `effective_n` is **trial multiplicity**, not the effective sample size of a dependent return panel. Do not confuse those similarly named quantities.

The current `engine/holdout_vault.py` uses `VaultConsumptionRequest` with original root, family, hypothesis, window and source/protocol/seal hashes plus an independently held history anchor. Consumption spends access before a separate evaluator releases labels; it is not authentication or a dataset reader. Creating a request object does not admit an experiment. These current interfaces are more specific than the older generic plan references and should be reused.

Only source code was read. No TrialLedger instance, register_trials decorator, seal, peek, consumption request, family budget or runtime dataset was created or invoked. The broader allocation study must be attached to the incumbent owners without resetting related research history.

## 7. Public methodology checks that affect data acquisition

The sponsor's XLC/XLRE listing dates differ from inception dates; the first observed local rows match their listed first trading dates. This corroborates a boundary, not complete data quality. The local BIL first row is later than the sponsor's inception/listing date; it must not be claimed as full inception history.

TreasuryDirect describes discount-price-to-face-value bill returns. A discount yield is not itself a holding-period total return. The selected first comparison uses BIL with an explicit fund identity to avoid pretending a yield series is an investable bill account.

The SEC's official N-PORT rule page still labels its February 2026 change **Proposed** at retrieval. The April 2025 rule postpones the 2024 reporting amendments' effective/compliance dates. Do not treat the 2026 proposal or the separate Names Rule extension as proof that a real-time monthly holdings feed exists. Actual public filing availability controls the dataset. This is a data-engineering conclusion, not legal advice about a fund's filing obligations.

Sources: sponsor XLC/XLRE/BIL pages linked in TARGET_SCOPE_AND_BASELINES_R1.md; https://www.treasurydirect.gov/marketable-securities/understanding-pricing/ ; https://www.sec.gov/rules-regulations/2026/02/s7-2026-05 ; https://www.sec.gov/rules-regulations/2025/04/s7-26-22 . Only source identity/methodology is used; incidental page performance data are not used as a research result.

## 8. Next useful phase and held effects

The target specification is in [TARGET_SCOPE_AND_BASELINES_R1.md](TARGET_SCOPE_AND_BASELINES_R1.md). Next: qualify the thirteen-series existing source/reader path; convert the broad-flow witnesses into source-owner acceptance cases; and validate self-financing policy accounting before market outcomes. No engine fix, source refresh, capture activation or empirical study has been disguised as documentation publication.

The old PR head's main ci-gate and all twelve packs are now observed successful; the inactive pilot-base authority context remains separate. That old result is not copied onto these new commits. Independent final package review remains incomplete after its preserved provider refusal; no retry or provider-switch was made.
