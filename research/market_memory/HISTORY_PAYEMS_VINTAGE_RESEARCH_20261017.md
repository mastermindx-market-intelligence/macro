# Market Memory — historical PAYEMS recorded-vintage research slice

**Scope.** This is a source-only, retrospective historical research component, not an installed Data & Lab action, not a macro collector, not a trade or forecast signal and not strict point-in-time eligibility. It preserves the original `engine.release_revision_model._value_at_vintage` as the numerical value-selection owner. The visible projection never includes future revisions or source supersession end dates.

## Source evidence already retained

The existing M2 Data & Lab source was previously inspected as `macro_snapshot:fred_vintage/payems_all_vintages.parquet`: 312,088 stored rows across four timestamp/value columns, with reported vintage dates from January 1997 through July 2, 2026 and some represented economic observation periods beginning in 1939. The previously saved raw-content SHA-256 was `4ee42f3dc6ea751bb45c2843fca556e98a23cd39906d4d1af57880a6cf51a87c`, and the observed owner source-version token was `statv1:bf1e91d7aff3f3f51c377c5eaf6fd173884baef34539f215deb2dcf71747aa20`. These are **previous observations**, not an assertion that the current host file or installed reader is unchanged.

The incumbent revision selector had previously matched recorded date-vintage cases for 2008-09-15, 2020-03-16 and 2022-09-13. The source did not retain an eligible vintage for a 1990 cutoff: older economic-period rows must not be promoted into contemporaneous 1990 availability.

## Source/reader contract

`select_payems_date` accepts only the four named DataFrame columns, a canonical calendar-date cutoff, an exact source reference, a version token and a declared content digest. The caller must separately verify the actual source bytes and descriptor/version guard before trusting either token. It never performs filesystem reads or vendor requests.

It uses the existing release revision-model's exact historical value-selection function for each displayed period, limits the count to 24 periods and the input to 400,000 rows, rejects malformed clocks, nonfinite eligible values, duplicate period/vintage keys and reversed eligible revision intervals, and explicitly distinguishes `NO_RETAINED_VINTAGE_AT_CUTOFF`. Supersession ends, later values, post-cutoff corrections and any forecast/trading authority stay outside the date projection. The earliest recorded macro-vintage day is not a verified intra-session availability time.

**Do not treat this as a complete historical macro revision panel.** It covers only the retained PAYEMS vintage family. Source units, original release timestamps, population completeness, contemporaneous consensus, and strict strategy input eligibility remain unqualified.

## Verification and next consumer

The previous prototype's 23 synthetic tests were expanded to 31. A local checkout/mirror of the incumbent selector passed 31/31; this is **not** a complete repository CI result or a full real-source reproduction. The existing `research-price-panel` CI owner is enrolled for the exact new module, tests, and incumbent helper. Hosted CI and exact-head merge are required before treating this component as repository-delivered.

The next *product* slice should read the exact PAYEMS bytes through the existing `DataWorkspace._file` source descriptor with its unchanged version/replacement guards, enforce bounded decoded Parquet size, verify the caller-supplied content digest, and add optional date-only PAYEMS context to the existing `history_dossier` response. Do not use feature-checkout code as the installed runtime or downgrade a concurrently installed newer release. The existing host selector inspection for transcript installation was safety-blocked, so this research change does not retry or re-home that operation.

Original mission root: `market-time-machine-20261015`. This phase is isolated source/test research under the existing Market Memory owner. No news-probe retry, persistent collection scheduling, source archive rewrite, public publication, or live Risk Radar setting change.
