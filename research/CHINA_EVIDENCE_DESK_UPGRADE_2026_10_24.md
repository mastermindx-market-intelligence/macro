# China Evidence Desk upgrade — 2026-10-24

Operation: `china-altdata-upgrade-20261024-c3`.
Authorizing mission: Chairman's request to research, design, implement and complete a substantial upgrade to `china_altdata.html` autonomously.
Repository baseline: `a8940f33956551a79c0884c67b62edafa9f983d7`.
Protected procedural pin at entry: Mastermind `f572e1d7bb13ea3651160609390b460ea1d11a6f`.
Release-source comparison: Mastermind `aef9b0e2681a36a36888c15cbb3ef51baada6737`; INDEX, REVIEW_RETURN and RECONCILE_STATE loaded at that same commit, schema/version 1.0.1 and bootstrap-major 1 compatible. Its one intervening commit changes Executive migration/ACL implementation, not this mission's governing procedures or source custody.

## Diagnosis and decisions

“Dormant” was a participation classifier, not website uptime. Several independent defects nevertheless made the page less useful:

1. The nightly producer recomputed late-arriving inputs but appended only new dates, then published from the old first-observed archive. Current information could remain hidden behind an older snapshot.
2. The limit-tape loader interpreted a RangeIndex as dates even though the producer supplied an explicit date column.
3. The fixed gauge value 44 was a label mapping, not measured confidence. Coverage was easy to confuse with agreement; missing volatility was easy to confuse with calm.
4. Company excerpts hid the full eligible universe. Placeholder ticker names prevented real provider names from replacing them, leaving 3,002 names undisclosed in the earlier projection.
5. Existing company loaders discarded supplied source snapshot/observation dates. A newly built page could consequently look fresher than its underlying inputs.
6. Event presentation compressed distinct metrics/revisions and omitted supplied reporting periods, stages and filing links.

Preserve the first-observed tape and backfill qualification. Compute a separate current projection from current source versions, append only genuinely new archive dates, and label the current view explicitly as non-point-in-time. Current recomputation does not repair or mature historical first-seen evidence.

Use the existing company kernel, signed weights and participation thresholds. Count coverage independently of signed contribution agreement; zero is present. Show source dates, conflicts, flags and instrument links. Do not describe feeds as statistically independent or identify beneficial owners. Southbound means mainland investors trading Hong Kong securities, as described by [HKEX Stock Connect](https://www.hkex.com.hk/Mutual-Market/Connect-Hub/Stock-Connect?sc_lang=en).

Missing-input hardening preserves the formulas: financing changes explicitly use `fill_method=None`; broker rolling log-return spreads require a valid current endpoint. This prevents historical window coverage from implying a current observation when a required endpoint is missing.

## Execution custody

`DIRECT_PRINCIPAL_EXCEPTION` — terminal paid-lane failure. Principal owns bounded implementation through the responsive Studio C3 connection under `CRITICAL_PATH_SHORTCUT / UNIQUE_APPROVED_ACCESS` for this carrier. Native coordinator tool calls hung and both paid implementation attempts terminated with provider 429. This is not a claim that all Fabric is unavailable or that execution absence is proven. The native coordinator confirmed no source-write custody. Root remains the sole source writer.

Original runs under the same root, without replay:

- Audit `china-altdata-audit-20261024-c3-01`: terminal rc1, provider 429, no accepted result.
- Backend `china-altdata-backend-20261024-c3-01`: VERIFIED_TERMINAL rc1, complete response 497 bytes, provider 429 Ryan, SHA256 `d8803ffa74cffe033a5211e651a401d6dce242973c009015b5eba66b6a7a83a7`.
- Frontend `china-altdata-frontend-20261024-c3-01`: VERIFIED_TERMINAL rc1, complete response 497 bytes, provider 429 Kris, SHA256 `c2f3a7c71daff80633d0314938c36e7e7e81991f29c66c96f266286364b4414e`.

Both implementation runs returned QWEN_FINAL_RESPONSE_UNCONFIRMED, `retry_allowed=false`, and no code or artifact. No run is accepted as work. Workers were assigned isolated carriers; the principal workspace was clean before implementation.

Paper file `01M2WGNCX9475G79JRKJTCM08P` was inspected read-only. Its Desktop catalog was incompatible for writes and the file warned of size-related loss risk: `NOT_APPLIED_TO_PAPER`. Design was implemented and reviewed in the actual product.

Native review of supplied exact source excerpts identified future-source counting, event identity/provenance, useful prior comparisons and missing current metric endpoints. These were repaired with discriminating regressions. The follow-up reviewer reported no unresolved blocker in those corrected excerpts; this is not a substitute for complete immutable-head review or release gates.

## Product design and implemented workflow

Archetype: research desk. Preserve canonical navigation, semantic tokens and existing research links.

1. A compact briefing separates dated participation, company evidence, data health and validation. “Quiet participation” replaces the ambiguous prominent “Dormant” wording.
2. Six market readings show values, units, observation dates and actual changes against a comparable prior observation. Missing/future/same-date comparisons remain unavailable. The trend retains gaps and its current-source qualification.
3. A searchable company board exposes the full eligible universe through a lazy sidecar. Eight initial rows, direction/coverage/flag filters, stable sorting, pagination, reset and seven-source dialogs keep the workflow bounded.
4. Disclosed events retain chronological horizons, source snapshot, reporting period, metric, stage and supplied filing links. Planned and executed buybacks remain separate; unlock eligibility does not assert actual selling. Raw-record identity preserves distinct revisions and metrics.
5. A source catalog shows coverage and the actual range of supplied dates. Observation dates and collection snapshots remain distinct. Valuation snapshots from June are not silently stamped October.
6. Existing limit-up, narrative, sell-side and signal-lab research remains accessible through progressive disclosure.

The shared CNInfo relative-path normalizer was extracted into `lib/china_filing_urls.py`, preserving the Intel Hub's existing `_cninfo_source_url` alias. The new page reuses that pure helper without importing the unrelated Hub dependency tree. Display links accept only supplied official HTTPS exchange/CNInfo locations. No filing content or endpoint availability is inferred from URL normalization.

Dark theme uses restrained directional ink and readable values. Light theme uses white panels, neutral hairlines and subtle shadow. EN/ZH, 1440 desktop and 390 mobile, keyboard/focus behavior, native dialogs, no-JS preview, loading, empty and error states are covered. No copied global header, runtime style system or new tracking SDK was introduced. Raw company-search queries are not collected.

## Source-freeze verification

- Eight relevant Python/Node/browser suites passed **127 tests**, including the existing Intel Hub filing-normalizer contract after extraction. The subsequent missing-endpoint correction and two new regressions passed **57 affected participation/projection tests**. The first broad run emitted unrelated shared pytest temporary-directory cleanup warnings; the later focused runs used isolated temporary directories.
- The final built artifact passed **6 anonymous Chromium workflows** against the complete 5,357-company JSON. Search (including full-width ticker digits), filters, pagination, reset, mobile, EN/ZH, source dialog, Escape/focus return, company link, events, network/schema/nested-record/vintage failure, preserved preview and successful retry were exercised. Separate synthetic-fixture journeys also passed.
- Actual-data build: **5,357 named companies, zero ticker-placeholder names, 42 disclosed records, two supplied official filing links**. Observation 2026-10-22; newer partial tape session 2026-10-23. All six readings are present for the selected observation; overall health remains explicitly partial.
- Actual broker and CSI endpoints were read for October 21 and 22. The endpoint-validity correction leaves the October 22 broker log-return spread unchanged at `0.1133066193614059` before display scaling.
- First-observed archive SHA256 remains `f49c5a1b8f78ee691b85313f1f0491eb25f8bce37890035fe0c12243fd1cc611`. No archive restatement was performed.
- The full JSON is 6,746,564 bytes, 311,784 bytes when gzip-compressed locally, and fetched lazily. This compression figure is a local artifact measurement, not a claim about deployed response headers.
- Canonical final capture: **32/32 states**, covering dark/light × EN/ZH × desktop/mobile with rest, actual link hover, actual button hover and actual focus. PNG lengths and SHA256 values were verified; only the 32 referenced images remain. Manifest `page_tree_sha` is `d689050cf94478970aa07b11c2b9e3a2ffbec5dc`. Console errors and failed responses were empty. Anonymous capture does not claim authenticated-tier acceptance.
- The capture's heuristic `asof_present` probe was false; direct inspection and browser tests verify the separately labeled market-observation and build dates. No body-level horizontal overflow was reported. Local scrollable tables are intentional.
- Curated exclusive CI dependency closure passed with no findings after narrowly adding the shared helper to six consuming jobs and the page builder's actual input paths to its own job. No scope ceiling or gate was weakened. The workflow manifest validates 355 jobs; CI trigger closure previously reported 3,340/3,340 reachable paths with no gaps.
- Design token ratchet, runtime-style-injection baseline, template/site synchronization, JavaScript syntax and whitespace checks passed. The final screenshot-receipt gate passed against the complete tracked and new UI diff.

## Honest limitations and follow-up measurement

The canonical shared navigation still causes layout shift when its adaptive layout changes after first paint. Final local desktop CLS was approximately 0.55–0.58; mobile results varied by theme/language. Explicitly loading its existing stylesheet did not eliminate the shared JavaScript reflow. This release does not fork the shared navigation or claim clean layout stability. The local LCP readings are lab measurements, not field-performance or adoption evidence.

The connected PostHog project had no ingested events in the examined period. That does not establish actual traffic or user inactivity. No business-impact percentage is claimed. Evaluate discovery, successful research interactions, freshness and render reliability using the existing first-party anonymous telemetry before claiming increased user value.

The input feeds are not a complete market calendar or whole-market universe. Older snapshots, unknown dates, missing filing links and incomplete coverage remain visible. Neither alignment nor a participation label is a probability, return forecast or trading instruction.

## Release state at source freeze

Research, design, implementation and local verification are complete. The source branch remains `sol/web-china-altdata-upgrade-20261024-c3`, under the original operation and sole writer. Main was rechecked at `51f0ac98e5e33498af86fd1d55bcec52634ee2fc`; initial owned source paths and the shared helper extraction have no collision against the acquired baseline.

Publication, complete immutable-head review, hosted CI, normal merge/render and served-page verification remain separate acceptance gates. No live upgrade is claimed by this source-freeze document. The release PR must record the final source identity, gate results, merge/render identity and public-route verification.
