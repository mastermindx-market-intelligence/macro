# TOI W2 data, clock and Terminal recovery audit

Audit date: 2026-10-03. Advisory research return to the parent TOI recovery commission. This file changes no source, production service, dataset, admission, trade rule or organizational owner. No market outcomes were read or computed. Production requests were bounded, credential-free HTTP GETs for bar construction parity; raw market-price corpora are not reproduced in this return.

## 1. Material conclusion

W2-0 already exists. Macro PR #7094 is the canonical carrier at 5bb1bc68c99146fab040aade04bbf1903c51e5b7, draft/open, with a complete archaeology report and PARTIAL / HOLD result. Its records say semantic review passed but release remained blocked. Calling W2 “undispatched” or its reports absent would now be wrong. The reported combined U.S.-equity Weekly/Daily/4H panel remains unadmitted. [R1–R4]

Two later Terminal changes must be consumed:

- PR #593 merged the actual-close calendar repair on 2026-09-16 as 8f518af76231667a75d5af91a79ae8454b937424. Its final historical receipt correctly said MERGED / BUILT_NOT_PROVEN because deployment was refused before execution.
- PR #594 merged source-construction lineage on 2026-09-16 as 34874e71c11fdd69e328ee889a2e9e4c0c9779ed. It adds descriptive API evidence, not scientific admission. [R5–R8]

Fresh observation supersedes the *historical* deployment absence: at 2026-10-03T09:47:19Z public Terminal HTML reported data-dpl-id=41b8af2da46614cedd2a485214e53003d4f030fc, exactly the current Terminal source pin supplied by the parent. The live API returns the new source_evidence schema. No deployment action was taken in this audit.

The original early-close defect is now corrected in the sampled production API. Nevertheless, fresh full comparison still yields a HOLD for a **different reason**: all 20 timestamp/OHLC comparisons match, while five September cases compare integer-volume stored 5m bars to fractional-volume live-tail 4H bars and exceed the established binary64 tolerance. A remaining provider-hourly fallback also fabricates a 09:30 label over source history whose first bar starts at 10:00. “20/20 parity” and “the early-close bug still exists” would both misstate the result.

## 2. Pins and evidence files

- Protected procedure pin supplied by parent: Mastermind 20adcaf65c2dd1bb734ab06e215feb1a0eb65659.
- Current Macro source: 5fc7af4a1aa2510966a7b566f97e5b894f2632f8.
- Current Terminal source and observed production marker: 41b8af2da46614cedd2a485214e53003d4f030fc.
- W2 candidate: Macro #7094 / 5bb1bc68c99146fab040aade04bbf1903c51e5b7.
- Session-repair evidence carrier: Macro #7168 remains draft/open; inspected head 641904a3a350c1cdb5ab10c765dc59e01b7f6346.
- Support-context candidate: Terminal #647 remains open, unmerged; API head is 2c3b04b12237e50e4b0227a335c8af8e0ed5ceca. Its body still names an older cab3da8 head. Do not silently reuse exact-head proof.
- Complete selected-field current HTTP receipts: w2_terminal_parity_current.json and w2_terminal_volume_fallback_current.json beside this memo.
- The former output receipt SHA256 was 257e499a46606836b46d4f8d76f704b2b6bb3eb1221865d14d670d1837e9dd97. It records response digests and actual input-store digests per case. These are audit artifacts, not another price or event store.

## 3. Fresh production parity: component results

Five symbols: AAPL, SPY, NVDA, JPM, XOM. Four dates: 2026-09-10, 2026-03-06, 2026-03-09, 2025-11-28. Forty current HTTP responses from /api/intraday supplied 5m and 4h series. Dates are the original prespecified archaeology controls, not chosen from market outcomes.

The comparator used 09:30 local anchoring and actual closes from the already-inspected immutable calendar projection, with a 240-minute nominal bucket. It required exact timestamp and OHLC equality, full expected 5m timestamp grid for these liquid controls, and volume error no larger than (number of admitted 5m rows + 2) × binary64 epsilon × absolute expected volume. This is the prior repair’s disclosed numerical bound, not a new relaxed tolerance.

| Component | Result | Meaning |
|---|---:|---|
| Requested symbol/date identity | 20/20 pass | API request identity is consistent; this does not prove Data OS security identity |
| Expected sampled 5m grids | 20/20 pass | 78 rows on ordinary dates; 42 on early close |
| 4H timestamps and OHLC | 20/20 exact | Narrow observed construction proof |
| Original early-close cases | 5/5 pass | Last admitted 5m row is 12:55; one 09:30–13:00 4H bucket |
| March DST controls | 10/10 full comparisons pass | Both sides retain local 09:30 anchors |
| Volume within binary64 bound | 15/20 pass | All five September cases fail |
| Same returned construction family | 15/20 pass | September 5m is stored_5m; September 4h is live_tail |
| Same exact stored-file digests in both assemblies | 20/20 pass | The assemblies read the same files, but live bars override overlapping stored bars |
| Combined strict sample qualification | 15/20 pass | Full same-family OHLCV comparison remains HOLD |
| Broad universe, PIT or research admission | Not established | Every live evidence record says research_admission=not_assessed |

The API's assembly_store_reads refer to the *whole assembly*, not necessarily the returned dated bars. A hash of a 5m file is therefore not proof that the returned 4h bars used that file. This distinction is correctly exposed by the existing lineage module. [R9–R11]

### Five volume discrepancies

Every stored 5m volume in these ten September buckets was integral; every corresponding live-tail 4h volume was fractional. Below, delta = live 4h volume minus the sum of stored 5m volumes.

| Symbol | 09:30 bucket delta, 48 base rows | Allowed numerical error | 13:30 bucket delta, 30 base rows | Allowed numerical error |
|---|---:|---:|---:|---:|
| AAPL | 25.8617879972 | 4.559215e-7 | 12.5511220023 | 1.270545e-7 |
| SPY | 23.0988769978 | 2.657015e-7 | 13.7879829966 | 9.471680e-8 |
| NVDA | 24.3505290002 | 6.349877e-7 | 12.5738100037 | 1.641491e-7 |
| JPM | 23.8172060000 | 2.029030e-8 | 12.7947950000 | 8.614222e-9 |
| XOM | 26.2861890001 | 7.799256e-8 | 14.2990899999 | 2.708838e-8 |

These differences are not floating-point summation noise. Current Terminal backfill explicitly casts v to int, while the live fetch preserves b.v. The live 4h request uses 30m provider bars and a 60-day window; 5m uses a 10-day live window. September 10 lies inside the first window and outside the second. withStoredHistory makes live timestamps win, so the same historical date has different construction families across requested grains. [R10, R12–R13]

The magnitudes are consistent with per-base-bar truncation: losses are positive and below the number of 5m bars. That is a supported explanation, **not an exclusive attribution**; exact vendor raw 5m/30m responses from one correction vintage were not retrieved. Provider correction or aggregation differences remain possible contributors. No efficacy impact was inferred from the share-count deltas.

Current Massive documentation independently states that aggregate volume can be fractional and integer casts lose real volume. Its 2026 fractional-precision update also says stock flat-file volume changed from integer to decimal in place. Current Macro daily ingestion likewise casts volume to int64. W2 must qualify volume precision across both daily and intraday stores, rather than assuming that only Terminal is affected. [V1–V3; R14]

### Remaining hourly fallback: current discriminating example

Current DINO / 2026-06-15:

- 1h response: six source rows at 10:00, 11:00, 12:00, 13:00, 14:00, 15:00.
- 4h response: two bars labelled 09:30 and 13:30.
- Both report stored_1h; 5m file is missing.
- Both report provider_hourly_open_alignment_not_guaranteed.
- Exact 1h store SHA256: dfbe5dc5cccb3b7cda2e44cbba0769ca92c98f47e3c31ef8efbfb171e6341356.

Relabelling a provider hour cannot reconstruct the missing 09:30–10:00 segment or split a 13:00–14:00 source bar at 13:30. No claim that this is an exact full-session 4H corpus is lawful. The existing warning should remain visible to research adapters and future chart explanations. [R10–R13]

## 4. Source/store matrix: present truth

| Source/store | Existing owner and physical path | Actual evidence and limitations | Capability | W3 gate |
|---|---|---|---|---|
| Massive raw daily | collectors/massive_stock_day.py and massive_flatfiles.py; R2 massive_stock_day/ canonical; local data/massive_stock_day/ mirror | Current protected manifest reports 21,667 tickers, 2021-07-06 through 2026-10-01, 1,368 processed weekdays, no recorded weekday holes, SPY 1,317 rows. These are manifest claims; this session did not inspect R2 bytes. Raw prices, latest date-write wins, original receipt/correction vintages absent; volume cast to int64 | PARTIAL | HOLD |
| Terminal stored 5m | Existing ingest/backfill_intraday.py; terminal/public/data/intraday/<SYM>.5m.json or existing TERMINAL_DATA_DIR | Current code defaults top=500, 5m days=400. Header prose mentions different historic limits; code is controlling. Current API demonstrates five liquid names. No full-universe denominator, first-receipt ledger or permanent correction lineage; integer volume | PARTIAL | HOLD |
| Terminal stored 1h | Same owner, <SYM>.1h.json | Code builds current manifest's US symbols, six-year request window; current DINO example cannot prove exact RTH 4H. “All US” is a producer intention, not measured historical complete coverage | PARTIAL | HOLD |
| Terminal live US aggregate leg | intradaySources.ts; existing provider adapter and in-memory route cache | Source base is 30/15/5/1m chosen to divide requested interval and land on 09:30; 4h normally uses30m. Current evidence labels live_tail and explicitly says construction not receipted. Current bar availability/finality is not a research clock | PARTIAL | HOLD |
| Macro optional hourly | scripts/build_polygon_intraday.py; data/intraday/<T>.parquet or existing VPS external mutable directory | Curated chart universe, adjusted=true, two-day overlap replacement. Current source records post-fsync exact-file receipt and15-minute floor. mtf_monitor still uses pandas resample("4h") | BUILT_NOT_PROVEN for TOI substrate | HOLD |
| Radar minute/bucket reader | engine/entry_radar/vendor_minutes.py, four_hour.py; existing runtime state c3_buckets/<TICKER>.json | Bounded episode-window reader; adjusted basis and completed-session vintage checks; partial session re-fetch; no general whole-US minute warehouse or historical first-receipt proof | Existing owner code established; TOI use limited to clock oracle | ADMIT_AS_CLOCK_ORACLE_ONLY, not data-panel ADMIT |
| Data OS security master | scripts/build_security_master.py, lib/dataos/identity.py; data/reference/security_master.parquet, vendor_aliases.parquet, receipt | Current receipt:2,382 security rows;2,381 active +1 superseded duplicate;6,037 aliases. Current GMI target is1,237, resolved total1,211,25 current refusals. None equals a complete historical all-US eligible denominator | PROVEN_LIVE within existing identity scope | HOLD for TOI denominator |
| Massive rights | Existing research/licenses/MASSIVE_ENTITLEMENT_RECORD.md; operator holds agreement privately | Current protected record admits relevant research, storage, display, redistribution and AI use, subject to feed-specific written conditions. This session did not inspect or reproduce private agreement | PROVEN_LIVE as incumbent entitlement record | ADMIT for covered rights axis only |

The relevant current source and receipts are [R9–R18]. Current Data OS identity exceptions explicitly refuse confusing B/GOLD histories; no TOI ticker-only join may bypass them. Terminal currently uppercases symbols and its API truthfully labels instrument_identity=not_verified. The daily owner has an existing case-safe artifact mapping for mixed-case vendor symbols; consume that owner instead of inventing another symbology normalizer. [R14, R18, V4]

### Local stores actually observed

At 2026-10-03T09:46:35Z:

- /Users/chriswong/Documents/Cluade/Macro Dashboard, HEAD0f62daf545719e641036be9e5b88101c3af7ab5f:20,476 top-level daily parquet files; zero case-v1 files; no daily manifest; no data/intraday or data/reference.
- SPY/AAPL/NVDA metadata in that raw mirror:1,254 rows each, 2021-07-06 through2026-07-02, no duplicate date indices. Only date columns and parquet metadata were read. SPY file SHA256a04b4b27782c90707f84f9b19903914ca26e72bca9d739077da7df787a14fda6; AAPL5b2c3ea0396134b72c611f2a8f86b0caadc96428db7007ea254fac7150c5bd99; NVDA3f81d70ebabfb5c9ae2b7d0c4cd467917c2ae8b5f3f3b385ad1b712fd0fc397f.
- /Users/chriswong/Documents/Cluade/macro-main, HEADb4f95f98ef80b8cbb4636afbd723b5091658e1f1: zero raw daily parquet files despite a committed manifest reporting21,657 tickers through2026-09-30; five reference parquets; no data/intraday.
- No terminal/public/data/intraday directory exists in the checked /Users/chriswong/mastermind-terminal, /Volumes/Mastermind/repos/mastermind-terminal, or /Users/chriswong/Documents/Cluade/charting-app checkouts. The first two incidental local HEADs are54eb1caa799bd6f8f951cbe582be0f8ac9c7b0af and5224015c9c87b65457fc598b85b78a2be322bfc7.
- /Volumes/Mastermind/Mastermind/datasets was empty.

These bounded observations do not claim the entire fleet lacks data. They prove that a current repository manifest and an old local parquet tree cannot be joined into one purportedly current research corpus. The collector already provides local-mirror warning/refusal behavior; the commissioned data owner must restore/qualify the appropriate existing mirror if future execution needs it. No restore was run here. [R14]

## 5. Clock, session and finality contract

### 4H-CLOCK and 195M-RTH are different methods

| Contract | Ordinary RTH session | 13:00 early close | Required interpretation |
|---|---|---|---|
| 4H-CLOCK | 09:30–13:30 =240m;13:30–16:00 =150m | One09:30–13:00 =210m bucket | 4H is a nominal width; second bar is shorter |
| 195M-RTH | 09:30–12:45 =195m;12:45–16:00 =195m | 09:30–12:45 =195m;12:45–13:00 =15m | Independent construction and trial identity, not an alias for4H |
| Monthly context | Accepted completed exchange month | Calendar-dependent final session | Available only after the accepted daily inputs are available and final |

These are W2 specifications, not evidence that195M is better.195M-RTH is not in the current Terminal timeframe allow-list. The generic owner can parameterize nominal width, but the TOI195M scientific/data admission remains SPEC_ONLY. Do not use the existing4H detector's name or trial identity for a195M experiment. [R3, R4, R9, R15]

The current immutable Terminal calendar projection covers2016-01-01 through2028-12-31,3,267 sessions. Its source is Macro112eba2036fd1186e67b914e194f4fa541cfc4df with four owner-file SHA256 values. Closed in-coverage dates return null; unsupported/malformed inputs throw US_SESSION_CLOCK_UNAVAILABLE. Regeneration must consume the same owner after future calendar corrections. Source-level tests include early/full closures, both DST transitions, absent sessions, boundary sentinels, immutability and all projected sessions. These tests were inspected, not rerun in this read-only research audit. [R5, R9, R19]

The “display epoch” is an ET wall-clock encoded as if UTC; it is not a UTC instant. Macro source event timestamps use actual UTC instants. A data adapter must explicitly preserve both the event instant and display convention and must never subtract/apply the ET offset twice. [R9, R12]

The Radar four-hour object already separates nominal/effective duration, effective end, confirmed/provisional status, sampled-minute count and clipping. Its confirmed series excludes incomplete or empty buckets. TOI should consume these semantics while explicitly retaining missingness and interval coverage in its own source qualification, not treat a dropped missing interval as proof of a fully observed sequence. [R15–R16]

### Daily knowability must be source-specific

W2's historical JSON labels Massive daily RTH and bar_end=regular exchange close. That field-level characterization is not proven by the collector: it pivots vendor daily bars and does not construct an RTH tape. Current vendor docs describe flat files as capturing the full market session, with data generally available about11:00 ET the following day. Current aggregate docs also distinguish eligibility rules for which trades update price and volume. Exact daily OHLC versus volume session grammar therefore remains a qualification question; do not assert a measured price mismatch that this audit did not test. [R2, R14, V5–V7]

In particular, Radar's conservative “daily close usable next session open” rule must not be copied blindly onto a flat-file source that may publish later than09:30. For the selected data family, known_at must be no earlier than the input's actual available/received time. A later download cannot fabricate a historical first receipt.

Current vendor adjusted=true means split-adjusted; it does not mean dividend-adjusted or total return. Radar vendor_minutes.py's introductory “split or large cash dividend” phrase must not be promoted to the new source contract. Preserve its useful vintage invalidation mechanism while binding actual vendor semantics. [R16; V3–V4]

## 6. Explicit admission axes

ADMIT below is always scoped to a facet, never to the combined panel.

| Axis | Current decision | Specific proof or next requirement |
|---|---|---|
| Existing Massive rights | ADMIT | Current incumbent entitlement record; preserve dataset-specific conditions |
| Sampled early-close + DST timestamp/OHLC behavior | ADMIT for observed route component |20/20 time/OHLC; original early-close5/5 corrected; no broad extrapolation |
| Complete same-family OHLCV parity | HOLD |15/20 current strict cases; preserve integer/fractional precision and source-vintage distinctions |
| Broad intraday exact-session coverage | HOLD | Current DINO missing5m/hour fallback disproves coverage-by-label inference |
| Daily/intraday price basis | HOLD | Raw daily versus split-adjusted intraday; qualify one explicit family |
| Volume basis and precision | HOLD | Current int casts lose fractional volume; require field-preserving source contract and versioned repair |
| Session grammar, daily versus intraday | HOLD | Native daily field eligibility and availability require explicit proof |
| Historical first receipt / correction vintage | HOLD | Existing latest-write/current-receipt paths do not reconstruct availability history |
| Instrument identity | HOLD for TOI panel | Consume Data OS, including listing intervals, reuse, class/case and exclusions |
| PIT universe eligibility | HOLD | Current vendor ticker population and current GMI universe are not historical all-US eligibility |
| Missing intervals and finality | HOLD for combined corpus | Explicit effective end, provisionals, halted/missing rows, coverage and no manufactured fill |
| Broad Terminal chart/product parity | HOLD | Current API sample is not a new browser acceptance or all-consumer proof |
| W3, outcomes, Prophet promotion, Golden Confluence authority | HOLD | No new admission or promotion produced in this audit |

REJECT_BY_DESIGN examples for the master plan: silently spliced raw/adjusted prices; integer-truncated volume relabelled exact; fixed UTC bars relabelled session-aware;195M relabelled4H; current survivors relabelled PIT all-US; availability backdated to bar time; new tactical event/minute/replay/identity/calendar planes; a chart indicator or alert condition relabelled a validated signal.

## 7. W2 artifacts are useful but not an executable measurement suite

The five store contracts, four clock records, coverage/rights/parity JSON and architecture report are real recovered research. Their validation scripts mostly validate written assertions:

- run_toi_w2_clock_fixtures.py checks strings such as09:30 and actual_close; it does not execute the clock owner on fixtures.
- run_toi_w2_terminal_parity.py verifies20-count arithmetic and explicitly requires fail>0 and HOLD; it does not make HTTP requests or recompute bars.
- run_toi_w2_coverage.py verifies a manifest_tickers threshold and a written HOLD.
- The store validator validates enum/gate consistency, rights references and coarse ADMIT/PIT constraints. [R20–R23]

This does not invalidate the historical measured receipts. It limits what “four tests passed” proves and explains why a research-complete W2 foundation must add reproducible owner-level measurement and computed per-axis adjudication rather than relabel the existing receipt validators as empirical tests. Preserve historical receipts; new receipts must carry distinct observation/source versions.

## 8. Existing Terminal support/alert work belongs in the Do Not Rebuild map

Current protected Smart S/R already clusters confirmation-lagged pivots into frozen levels; its scoring uses the reaction contained in the confirmation wing; source comments distinguish visual current-role recoloring from immutable geometry. This is a technical display organ and event producer, not an opportunity success probability. [R24]

Open #647 adds nearest displayed intact support/resistance, touch counts, signed distance, equality/warmup/invalid states, and a latest-bar-may-be-open caveat. Its current source projection was read at actual2c3b04b head. It emits no forecast or cross-timeframe inference. The PR integrates existing sr_hold/sr_break conditions into incumbent Alert Center machinery; recorded sequence semantics do not promise that both events refer to the same level. The latest recorded merge-sweeper comments state required CI failures. Classify this increment BUILT_NOT_PROVEN / unmerged, and preserve the current carrier. [R25–R26]

TOI should consume original level/event identities and existing alert transport when separately admitted. It should not rebuild a support calculator, alert table, scheduler or proprietary-vendor imitation. Existing5m tactical ownership stays with Live Entry Radar.

## 9. Concrete minimum W2 qualification plan

This is the proposed successor work on existing owners, subject to current admission/custody. It is not a dispatch or production authorization.

1. **Reconcile the W2 carrier and freeze the renewed source matrix.** Retain #7094's archaeology and HOLD. Replace the obsolete *current* early-close diagnosis with the observed repaired component, retain the original failed receipt historically, and register current volume/lineage/hourly/availability/identity gaps.
2. **Qualify one explicit same-basis source family.** Choose raw plus point-in-time corporate-action records or a fixed adjusted snapshot with declared vintage; keep total-return/dividend assumptions separate. Bind price and volume basis, decimal precision, trade-eligibility/session rules, native cadence, source request/response digest and actual received clock. Extend the existing owners and artifact contracts; do not make another data plane.
3. **Repair fractional-volume preservation in the incumbent ingesters.** Test a fractional-volume source and same-symbol daily/5m/30m construction, including small-volume instruments. Existing truncated history cannot be recovered from its integer output alone. Any source re-acquisition is an explicit existing-owner qualification with a new receipt, not fabricated fractional reconstruction or silent historical rewriting.
4. **Close exact-clock and source-boundary qualification.** Reuse actual-close/session owner and present tests. Include early/full closures, both DST directions, clipped durations, known source gaps, partial last bars, overlap corrections and the transition between stored5m/live30m/hour fallback. Require equivalent content and provenance, not only matching chart labels. Keep provider-hourly fallback outside exact4H admission unless qualifying source granularity exists.
5. **Produce the denominator through Data OS.** Enumerate security/listing intervals and PIT eligibility by date, including entrants/exits, ticker reuse, class changes, delisting coverage, source floors and exclusions. Keep security, issuer, ticker and population identities distinct. Current21,667-ticker and2,382-security counts are diagnostics, not the denominator.
6. **Preserve observation clocks and revisions.** Required fields: event/bar start, effective end, source availability, actual first receipt if known, correction receipt, content version/hash, calendar revision, security/listing identity, source/price/volume basis, missingness, finality and the computed knowledge cutoff. Corrections may change a later revision; they cannot retroactively become knowable.
7. **Return per-axis ADMIT/HOLD/REJECT plus complete consumer proof.** Recompute a bounded independently specified parity suite using exact inputs; report construction strata separately. Demonstrate the selected research reader and actual Terminal consumer consume the same admitted object and source version. Revisit W3 only after the explicit combined data admission and original scientific gates; no automatic W3 release from a source fix or green CI.

The proposed contract with Temporal Grain is an input/decision interface: species and security identity; exact data-family/version; grain, anchor/session grammar, kernel/memory, effective durations and availability; supported scope, uncertainty and abstention; experiment/trial/proof reference. TOI consumes the sibling's G/A/K/D evidence and never repeats its outcome-selection experiment under a new name.

## 10. Remaining limits and stop reason

This bounded audit is complete. It discovered real existing carriers and new current production evidence, proved the old early-close diagnosis stale, and identified a reproducible replacement data HOLD without reading market outcomes. No further production requests, tests, broad fleet sweeps, dispatches or mutations are needed to answer this lane.

Still unobserved: current R2 source bytes as a complete corpus; all-US PIT denominator; exact same-vintage vendor raw5m/30m volume attribution; historical first-receipt/correction ledgers; renewed Terminal browser proof; current-runtime adoption of every optional Macro or Radar source; accepted W2/W3 admission. Parent should persist these results into the existing research commission and carry the qualified repair plan forward.

## References

R1. [Macro PR7094 current carrier](https://github.com/mastermindx-market-intelligence/macro/pull/7094).
R2. [W2 report](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/research/technical_opportunity/W2_REPORT.md) and [store contracts](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/research/technical_opportunity/w2_store_contracts.json).
R3. [W2 architecture freeze](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/research/technical_opportunity/W2_DATA_CLOCK_ARCHITECTURE_FREEZE.md).
R4. [Clock matrix](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/research/technical_opportunity/w2_clock_matrix.json), [coverage](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/research/technical_opportunity/w2_coverage_receipts.json), [historical parity](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/research/technical_opportunity/w2_terminal_parity_receipts.json).
R5. [Terminal PR593](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/593).
R6. [Historical deployment-blocked receipt](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/593#issuecomment-5692630542).
R7. [Full repair acceptance/continuation in Macro7168](https://github.com/mastermindx-market-intelligence/macro/blob/641904a3a350c1cdb5ab10c765dc59e01b7f6346/research/technical_opportunity/TERMINAL_SESSION_CLOSE_REPAIR_2026-09-16.md).
R8. [Terminal PR594 lineage](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/594).
R9. [Current shared session and timeframe helpers](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/intradayShared.ts#L120-L173), [display epoch](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/intradayShared.ts#L176-L202), [calendar loader](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/usEquitySessionClock.ts), [projection](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/usEquitySessionProjection.json).
R10. [Current store selection/live override](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/intradayStore.ts#L45-L87).
R11. [Current descriptive evidence and explicit unknowns](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/intradayEvidence.ts#L30-L84), [route consumer](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/app/api/intraday/route.ts).
R12. [Live window, source cadence and volume preservation](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/intradaySources.ts#L111-L168).
R13. [Current Terminal ingestion, integer-volume cast and universe](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/ingest/backfill_intraday.py#L44-L250).
R14. [Current raw daily collector and storage/freshness contract](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/collectors/massive_stock_day.py#L1-L270).
R15. [Canonical Radar four-hour semantics and implementation](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/engine/entry_radar/four_hour.py#L1-L260).
R16. [Current bounded vendor-minute reader and basis cache](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/engine/entry_radar/vendor_minutes.py#L1-L265).
R17. [Current hourly receipt writer](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/scripts/build_polygon_intraday.py#L1-L260), [remaining pandas4h consumer](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/engine/mtf_monitor.py#L83-L104).
R18. [Current daily manifest](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/data/massive_stock_day/_manifest.json), [Data OS receipt](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/data/reference/_receipt.json), [rights record](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/research/licenses/MASSIVE_ENTITLEMENT_RECORD.md).
R19. [Current executable Terminal clock fixtures](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/__tests__/usEquitySessionClock.test.ts).
R20. [W2 clock receipt validator](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/scripts/research/run_toi_w2_clock_fixtures.py).
R21. [W2 parity receipt validator](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/scripts/research/run_toi_w2_terminal_parity.py).
R22. [W2 coverage receipt validator](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/scripts/research/run_toi_w2_coverage.py).
R23. [W2 store-contract validator](https://github.com/mastermindx-market-intelligence/macro/blob/5bb1bc68c99146fab040aade04bbf1903c51e5b7/scripts/research/validate_toi_w2_store_contracts.py).
R24. [Current Smart S/R owner](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/suites/structure/smartSR.ts#L1-L210).
R25. [Terminal support-context PR647](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/647), [current actual-head source](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2c3b04b12237e50e4b0227a335c8af8e0ed5ceca/terminal/lib/suites/structure/smartSRContext.ts).
R26. [Last recorded required-CI failure](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/647#issuecomment-5739383606).
V1. [Massive: decimal aggregate volume](https://massive.com/knowledge-base/article/why-does-volume-return-as-a-decimal-value-from-the-aggregates-endpoint), inspected2026-10-03; body lines51–103.
V2. [Massive: fractional-share precision changes](https://www.massive.com/blog/massive-now-returns-fractional-share-precision), inspected2026-10-03; lines10–53.
V3. [Massive: split versus dividend adjustment](https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends), inspected2026-10-03; lines51–88.
V4. [Massive custom stock bars schema](https://www.massive.com/docs/rest/stocks/aggregates/custom-bars), inspected2026-10-03; case-sensitive symbol169, split adjustment218, timestamp324, numeric volume328–330.
V5. [Massive stock flat-file overview](https://massive.com/docs/flat-files/stocks/overview).
V6. [Massive flat-file quickstart](https://massive.com/docs/flat-files/quickstart).
V7. [Massive extended-hours data and qualifying trades](https://massive.com/knowledge-base/article/does-massive-offer-pre-market-and-after-hours-data).

