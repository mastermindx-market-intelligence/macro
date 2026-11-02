# R1 completion spec — 2026-10-06

PROPOSAL for owner ratification. Nothing in this file completes R1 (program §8 R1; seat D18). HOLD-FOR-SOL.

This is an owner-addressed checklist plus the metric names of a read-only probe. It takes no owner decision. It does not invent an issuer, a currency, a fiscal-year-end, an accounting basis, or a rights class. It does not backfill any row.

Program law, read from commit `94fc98253dc467e57672474533d28308f5255f7c` (that file is not in the current main tree), section 8 row R1:

> R1 — source owner completion | Missing native identity/basis/use decisions and actual lineage acceptance | Owner-issued receipts; natural unchanged/changed/failure/rollover cohorts; no hindsight backfill | SRC-A1, identity, provider-use and common baseline owners

> R1 is not an instruction to fabricate missing metadata or buy a new feed. Source-use decisions, common schema changes, provider activation and live installation remain with their actual owners.

Seat decision D18, as written on this revision in `research/INFORMATION_TO_PRICE_CONTINUATION_HANDOFF_2026-10-06.md` lines 35–37:

> D18 — R1 completion stays with the source owners (program §8 R1 row). The seat commissions measurement and owner-addressed proposals only; it assigns no rights class, invents no identity, buys no feed.

Facts below are the accepted R1 census (PR #8505, commit `ab77f792ee91c95825fe9faca8647dc3d91ac502`, schema `r1-identity-coverage-census.v1`) as re-measured by `r1_readiness_probe.py` against `origin/main`. The committed receipt is `R1_READINESS_2026-10-06.json` (schema `r1-readiness-probe.v1`): `source_revision` `8018682842f9f0d7a29e7ca3579e99ea5ae88c8e`, `as_of` `2026-10-06T05:49:46Z`, cutoff `2026-10-03T06:31:51Z`. The universe is 1503 names. The sha256 of the sorted canonical names is `441a942e97950e2fae5c6a015f38535058b0647a540f8ee1ac2342d02bd6ddc5`, and the probe records `matched: true`. A sha mismatch is a failed run, not a new universe.

Prospective-only rule for every receipt below: only a row whose effective date is present and on or before the cutoff counts. A row with no effective date counts as zero prospective rows. Nothing already stored is rewritten to look as if the missing field had been there.

Owner rule: the only lawful owner of a path is a workstream whose front-matter `owns_paths` covers that path. The search on revision `8018682842f9f0d7a29e7ca3579e99ea5ae88c8e` was `agentos/workstreams/WS-*.md`: 80 files, 516 front-matter entries. An entry that ends in `/` covers that prefix. Any other entry covers that exact path. Body text is not an owner record.

## G1 — issuer identity spine

(a) 724 of 1503 universe names have no issuer id. The store-alias lookup at the cutoff, followed by the issuer master, resolves 779 names and leaves 724 unresolved. It is a fact that `data/symbol_directory/cik_map/2026-09-28.parquet` covers 1499 of those tickers and has no issuer-id column (10,428 file rows; columns are ticker, CIK, and title). This checklist does not design a join from that file, from OpenFIGI (898 universe tickers), or from `data/theme_graph/identity_resolution.parquet` (776 universe symbols with a non-null issuer id). Those counts are presence counts. They are not the spine.

(b) OWNER = UNOWNED. The 516-entry search hits no path for `data/reference/`, `data/reference/security_master.parquet`, `data/reference/vendor_aliases.parquet`, `data/reference/issuer_master.parquet`, `data/symbol_directory/`, or `data/openfigi/`. These lines do not close the gap: `agentos/workstreams/WS-GMI-THEME-GRAPH.md:19` is `data/theme_graph/` and covers only the theme-graph file; `agentos/workstreams/WS-STOCK-IDENTITY.md:23` is `data/stock_identity/` and does not cover `data/reference/`; `agentos/workstreams/WS-ALPHA-INTELLIGENCE-INTEGRATION.md:20` is `research/alpha_intelligence/` and covers this proposal, not the identity artifacts.

(c) RECEIPT the owner must issue: one row per universe name with the universe name, the issuer id, the security id when one is used, the effective date of that binding, and the source of the binding. The effective date is required. Only rows effective on or before `2026-10-03T06:31:51Z` count. The owner must not invent an id to fill the 724.

(d) GATE = probe metric key `issuer_id_resolved` on `gaps.G1`. The check is `issuer_id_resolved == universe.names`. The receipt value is 779 against 1503 names, so the status is OPEN.

(e) DEGRADED PATH: when the owner cannot supply an issuer id, the accepted form is a labeled absence for that name. The name stays unresolved and is left out of issuer-level studies. A CIK row without an issuer id is that labeled absence. It is never backfilled from ticker similarity, a CIK, or an OpenFIGI row.

(f) NOT COMPLETION: ticker similarity, a successful acquisition, a CIK row, an OpenFIGI row, a theme-graph identity row, or a seat or lane assertion that two names are the same company. None of those closes G1.

## G2 — dated alias and ticker-change history

(a) Dated alias history is not available for prospective use. Among the 779 resolved universe names, 777 have no `valid_from` on or before the cutoff, so prospective rows from those undated rows are 0. Two names, ECHO and VMRK, have a `valid_from` on or before 2026-10-03. MMC has a `valid_to` and no `valid_from`, and MMC sits inside the 777. The continuation handoff compresses this to "777 alias rows all undated." The census JSON records both `alias_dated` 2 and `undated` 777. This checklist follows the JSON. The raw alias file has more rows than the universe; the census count is the resolved-name count, not a raw-file count.

(b) OWNER = UNOWNED. The same 80-file, 516-entry search hits no path for `data/reference/vendor_aliases.parquet`, `data/reference/issuer_migrations.parquet`, or `data/reference/security_migrations.parquet`. Three universe tickers (FOXA, GOOGL, NWSA) have a migration time of 2026-08-19, which is on or before the cutoff. That is a census fact. It is not a dated alias receipt, and it does not close G2.

(c) RECEIPT the owner must issue: alias string, vendor, issuer id or security id, `valid_from` (required), and `valid_to` when the alias has ended (`valid_to` is exclusive). Only a row with `valid_from` present and on or before the cutoff counts as prospective. The 777 undated rows count as 0 prospective rows. The owner must not write a date onto them after the fact.

(d) GATE = probe metric keys `alias_rows_dated_le_cutoff` and `undated_alias_rows` on `gaps.G2`. The check is `undated_alias_rows == 0 and alias_rows_dated_le_cutoff == universe.names`. The receipt values are 2 and 777, so the status is OPEN. `prospective_from_undated_rows` is 0.

(e) DEGRADED PATH: an undated alias is a labeled absence of history. It may stay in the file as an undated row. It must not receive a fabricated `valid_from`. Prospective studies exclude it. A `valid_to` without a `valid_from`, as on MMC, is the same labeled absence.

(f) NOT COMPLETION: a row that merely exists, a `valid_to` without a `valid_from`, a ticker that looks similar, or a successful collection under the current ticker. None of those closes G2.

## G3 — currency, fiscal-year-end, and accounting basis

(a) Currency, fiscal-year-end, and accounting-basis fields are absent. They are absent as columns on the identity spine (security master, issuer master, and vendor aliases). On the observation file they are null on every row: currency 0, fiscal year 0, and basis 0, out of 495,320 rows.

(b) OWNER = UNOWNED. The same search hits no path for `data/reference/security_master.parquet`, `data/reference/issuer_master.parquet`, or `data/revisions/expectation_observations.parquet`. No workstream owns the columns that are missing.

(c) RECEIPT the owner must issue: currency, fiscal-year-end, and accounting basis for each issuer-resolved name, each with its own effective date and the source of the value. Only a value whose effective date is on or before the cutoff counts. Observation rows already stored stay null. They are not backfilled. This checklist does not invent a currency, a fiscal label, or a basis.

(d) GATE = probe metric key `currency_fye_basis_nonnull` on `gaps.G3`. The check is that the security master exposes currency, fiscal-year-end, and accounting basis, each non-null for every issuer-resolved name. The receipt lists `spine_columns_present` as empty and the three observation counts as 0, so the status is OPEN.

(e) DEGRADED PATH: when the provider cannot supply one of the three fields, the accepted form is a labeled absence of that field. A study that needs the missing field is excluded. The absence is never filled from a ticker, a sector, or a later filing.

(f) NOT COMPLETION: a populated estimate value, a successful download, or a seat assertion that the currency is dollars or that the year is a calendar year. None of those closes G3.

## G4 — rights class

(a) The rights class is the literal UNKNOWN. `collectors/equity_revisions.py` line 363 writes `"rights_class": "UNKNOWN"`. Line 86 sets the provider to yfinance. The census records the rights register as not a source. No decision record and no config assigns a class. This checklist does not assign a class and does not recommend one. The owner must assign a class or record a refusal.

(b) OWNER = UNOWNED. The same search hits no path for `collectors/equity_revisions.py` and no prefix `collectors/`. Eleven entries name some other file under `collectors/`. The positive control is a different file: `agentos/workstreams/WS-CALCBENCH-FILING-FORENSICS-PARITY.md:31` is `collectors/fundamental_forensics_acquisition.py`. That line does not cover the revisions collector.

(c) RECEIPT the owner must issue: either a rights class, with the class name, the effective date, and the instrument it covers, or a refusal that names line 363 and states that no class is assigned. A class whose effective date is after the cutoff does not re-label rows at or before the cutoff. Only rows whose class effective date is on or before the cutoff count as classified. Rows already stored stay UNKNOWN until that owner receipt. They are not rewritten by this file.

(d) GATE = probe metric key `rights_class_literal` on `gaps.G4`. The check is that the literal on `collectors/equity_revisions.py` is an owner-assigned class other than UNKNOWN, or that the same line records an owner refusal. The receipt value is the literal UNKNOWN at line 363, so the status is OPEN.

(e) DEGRADED PATH: UNKNOWN stays a labeled absence of a rights decision. Collection may continue. Any use that depends on a rights class stays excluded. A successful response is not turned into a class, and this file does not infer one.

(f) NOT COMPLETION: a successful acquisition, a non-empty HTTP status, a seat or lane assertion, or any sentence in this file that might be read as naming a class. None of those closes G4. This file names no class.

## G5 — publication and source clocks

(a) Publication and source clocks are absent. `source_effective_at` and `source_published_at` are non-null on 0 of 495,320 observation rows. `provider_observed_at` and `system_observed_at` are non-null on all 495,320 rows. Those two are capture clocks, not source clocks. The attempts file has 8,991 rows and carries only `attempted_at` and `completed_at` (status success 8,766, partial 79, null 146).

(b) OWNER = UNOWNED. The same 80-file, 516-entry search hits no path for `data/revisions/expectation_observations.parquet`, `data/revisions/expectation_attempts.parquet`, or `collectors/equity_revisions.py`. The collector itself says, at lines 354–356, that yfinance's estimate accessors do not expose source-issued clocks, and it writes both source clocks as null.

(c) RECEIPT the owner must issue: `source_effective_at` and `source_published_at` as real source clocks, a sentence that says what each provider clock means, and the effective date on which the collector may start writing them. Only a row whose source clock is present and on or before the cutoff would count. That count is 0 today. Rows already stored are not backfilled with a later clock.

(d) GATE = probe metric key `source_publication_clock_nonnull` on `gaps.G5`. The check is `source_effective_at_nonnull > 0 and source_published_at_nonnull > 0`. The receipt value is 0 and 0, so the status is OPEN.

(e) DEGRADED PATH: yfinance exposes no source clocks, so G5's degraded form is "capture clock only; event-time studies excluded". The capture clocks may be kept. They are a labeled absence of event time. They are never copied into the source-clock columns and never treated as publication time.

(f) NOT COMPLETION: a non-null capture clock, a successful download, or a sort by `system_observed_at` described as publication order. None of those closes G5.

## COHORT RECEIPTS

The owner's cohort vocabulary is quoted from `SRC_A1_POST_REPAIR_ACCEPTANCE_2026-10-03.md` at commit `94fc98253dc467e57672474533d28308f5255f7c`. This checklist does not redefine it.

- Line 52: "Later unchanged session retains a new receipt without fabricating a revision." Evidence named there: "UVV natural unchanged witness, complete prior/new rows and linked receipts retained."
- Line 53: "Changed values append and supersede exact prior rather than overwrite." Evidence named there: "V natural same-anchor changed-value witness, newest prior reference and complete field retention; current mutation test."
- Line 54: "Partial/null/failure cannot erase prior good observations." Evidence named there: "Natural JBGS partial-after-good; new real-writer partial/null-after-good tests; incumbent error and HTTP tests."
- Line 55: "Fiscal rollover is not a revision and raw horizons remain distinct." Evidence named there: "Scheduled KBH anchor rollover; repeated UVV/V horizon sets; current discriminating rollover/horizon tests."
- Line 90, gate 3: "Incumbent different-period-end/same-relative-horizon case remains original; same-anchor changed value supersedes; raw horizons stay distinct."

The cutoff for the counts below is `system_observed_at` or `attempted_at` on or before `2026-10-03T06:31:51Z`. The grain is provider, provider record class, ticker, metric, raw horizon label, and observation type, ordered by `system_observed_at` and then observation id.

What the existing attempts and observations can already yield prospectively:

- Unchanged. Measurable. Column logic: `correction_state` equals `unchanged`. The collector writes that label only when a prior good row exists on the same grain, the period ends are not two different real anchors, and value, unit, currency, and basis match. Full file: 291,081 rows. On or before the cutoff: 276,724 rows. This is a count of rows already labeled. It is not a new owner receipt, and it does not by itself reproduce the UVV witness's linked receipts for the whole file.
- Same-anchor changed value. Measurable. Column logic: `correction_state` equals `supersedes`, the superseded observation id joins to a row still in this file, both period ends are non-null and equal, and the value differs. A supersession whose anchor is null, or whose anchors differ, is not this cohort. Full file: 51,964 rows. On or before the cutoff: 47,731 rows. Of 54,042 supersedes rows in the full file, 2,078 have a null or different anchor, 0 point at a missing prior, and 0 are metadata-only on the same anchor. 51,964 plus 2,078 equals 54,042.
- Partial, null, or failure after a good value, in the only form these files can show. Measurable as an observation-grain count, and not the same thing as an attempt-status sequence. Column logic: on one grain, a row with `correction_state` equal to `missing` whose same grain still has at least one earlier row with a non-null value. Full file: 381 rows. On or before the cutoff: 303 rows. The earlier good row is still in the file. The named JBGS witness is inside this file and is not the attempt-status sequence: JBGS has 6 attempts, every one of status partial, and none of status success; those attempts' observation counts sum to 336; the observation file has 336 JBGS rows (missing 228, unchanged 61, original 28, supersedes 19). The attempt-status sequence, a later partial, null, or error after an earlier success with a positive observation count for the same ticker, is 0 for every failure label, both in the full attempts file (8,991 rows: success 8,766, partial 79, null 146) and on or before the cutoff (8,587 rows: success 8,373, partial 77, null 137). That zero is not the owner's JBGS cohort. JBGS never has a success attempt, so it cannot appear in an "after success" count.
- Fiscal rollover is not a revision, as a period-end comparison only. Measurable. Column logic: keep rows with a non-null value; on one grain, compare each row with the previous non-null-value row; both period ends are non-null and differ. That is the collector's newest-prior-good-row anchor test. The owner's cohort is the later row whose `correction_state` is `original`, not `supersedes`. Full file: 2,707 rows, all of them `original`, and 0 of them `supersedes`. On or before the cutoff: 2,561 rows.

What these artifacts cannot measure. Do not approximate any of these, and do not report zero as if it were a measurement:

- Whether a later partial, null, or failure left the prior good bytes unchanged. One current attempts file has no parent snapshot. The probe marks this UNMEASURABLE.
- Erasure of a good row that is no longer in the file. The missing-after-good count only sees an earlier good row that is still present.
- A change of currency or basis. Currency, basis, fiscal year, and fiscal period are null on every observation row. Zero non-null rows means the change cannot be seen. It does not mean there was no change.
- A fiscal-label rollover. `fiscal_year` and `fiscal_period` are entirely null. The 2,707 figure is a period-end comparison only.
- Event-time order. Both source clocks are entirely null. Capture-time cohorts above use `system_observed_at` only. Event-time studies stay excluded, which is the G5 degraded path.
- Natural HTTP, malformed, or error attempt statuses. Those statuses do not occur in this attempts file, so they are not measured as present.

Correction-state totals, so the cohort counts can be checked against the file: full file unchanged 291,081, original 75,779, missing 74,418, supersedes 54,042. On or before the cutoff: unchanged 276,724, original 75,630, missing 71,039, supersedes 49,807.

## WHAT THE SEAT MAY DO

- Commission measurement and owner-addressed proposals. This file is that proposal.
- Re-run the read-only probe against a git revision and compare shared counts with the #8505 census receipt.
- Report each gap as OPEN, CLOSED, or UNMEASURABLE from the probe. On this receipt, G1 through G5 are OPEN.
- Quote the owner's cohort sentences above without changing them.

## WHAT ONLY OWNERS MAY DO

- Issue the issuer-identity receipt, the dated-alias receipt, and the currency, fiscal-year-end, and accounting-basis receipt.
- Assign a rights class, or record a refusal to assign one. The seat does neither.
- Change the common schema, activate a provider, or install a live collector change.
- Decide that R1 is complete. Seat decision D18 leaves that with the source owners.
- No one may backfill. An owner receipt is prospective only. A missing field stays a labeled absence until that receipt exists.

## Path notes for the reader

The ruling names `data/reference/cik_map/2026-09-28.parquet` and `data/reference/openfigi/cusip_ticker.parquet`. Those two paths are not in the tree. The census and this probe read `data/symbol_directory/cik_map/2026-09-28.parquet` and `data/openfigi/cusip_ticker.parquet`. The census markdown table says 10,440 CIK rows; the census JSON and the file both say 10,428. This checklist follows the JSON and does not edit the census. The program file and the acceptance file are read from commit `94fc98253dc467e57672474533d28308f5255f7c` because they are not in the current main tree. D18 on this revision is the continuation handoff quoted above, not a heading inside the program file.
