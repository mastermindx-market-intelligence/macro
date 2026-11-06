# Epoch-2 October 6 Source-Only Partial Evidence (Not a Day Certificate)

**Status:** `SOURCE_CENSUS_INCOMPLETE` / `PARTIAL_UNCERTIFIED`. **Admitted events:** zero.
**Scope:** macro PR #8012, research-only. Frozen Epoch-2 activation: 2026-10-06T04:31:47Z.
**Owner:** Source documentation only; not executable authority, Source Day COMPLETE receipt, or authorization to query U.S./HK outcomes.

The prior `CROSS_SESSION_EPOCH2_SOURCE_DAY_OPEN_2026-10-06.json` remains an immutable historical open-day record. The adjacent three files are byte-identical, source-only working-evidence snapshots copied from the M2 source inventory following the October 16 reconciliation. Their source-only schemas intentionally do **not** use the executable `SCHEMA_SOURCE_DAY` certificate format.

## Evidence snapshot and hashes

- `CROSS_SESSION_EPOCH2_SOURCE_DAY_PARTIAL_2026-10-06.json` - SHA256 `5a6c4c55f5ff7b5a52863468b89cda6baadf10c7107771a3f986fab722ca12ca`
- `CROSS_SESSION_EPOCH2_SOURCE_COVERAGE_GAPS_2026-10-06.json` - SHA256 `829ed8cb8e0e3d9558f9cc3dce80ca6bf743aba7b80515b2c7d372d95a4088e6`
- `CROSS_SESSION_EPOCH2_UKMTO_ISSUE_VS_INCIDENT_2026-10-06.json` - SHA256 `af82e5f92ea9e0e7ec159acced51adbbb1958222829a82ccb067a41d1e07f64f`

The candidate snapshot includes 26 candidate/exclusion/confounded source rows, 16 clock/provenance corrections, and nine independent worker-group adjudications. The accompanying coverage worksheet explicitly records gaps in mandatory Reuters/wire original-publication coverage, UKMTO warnings/advisories and first-source issues. It is not a negative-coverage proof of missing events. Google News and GDELT discoveries were used only for recall, never as first-public clock or complete-source certificates.

## Critical chronology and exclusion controls

- India MEA says MT On Peace was attacked October 6 "earlier today". First independently recorded contemporary press bound: October 6, 10:47Z. UKMTO 156-26 reports a different/unidentified incident on October 5, 16:37Z; UKMTO 157-26 reports an unidentified October 5 incident and was published October 6. Ship-identity/late-report correspondence cannot be presumed and the On Peace October 6 candidate remains unresolved rather than automatically excluded or admitted.
- Official UKMTO X post identifiers for #157 and #159 yield platform posting bounds of 2026-10-06T12:13:22.230Z and 2026-10-08T14:54:26.784Z respectively. Industry-email/PDF first issue might precede those public posts; the PDF incident time is **not** a publication timestamp. #159 concerns an October 6 incident first reported time-late in the October 8 product.
- Bulgarian Black Sea twin-ship attack and separate Odesa rapeseed-oil vessel strike have original local/official Oct6 publication evidence but may share a campaign cluster; no count inflation. Zelenskiy and Saudi pipeline first-public/original-materiality decisions remain source-only and confounded by earlier news. Moscow drone campaign first publication predates activation; no later-source reanchoring.

Additional original-source chronology (October 16 reconciliation): the Panama Maritime Authority retrospectively dates MT On Peace (IMO 9893204) strike to October 5 at 19:30 UTC, conflicting with the India MEA October 6 statement saying "earlier today". This conflict cannot be projected back as an October 6 known fact. A distinct October 6 Israeli defense-minister military-readiness order in Gaza has a 06:47Z Times of Israel first-public upper bound, but the originating statement clock and materiality are unresolved. Neither is admitted.

One further October 6 official-change candidate: Israel Katz detailed a conditional West Bank/Palestinian Authority war contingency at the cabinet meeting (independently observed 14:33 IDT = 11:33 UTC). Earlier September threats and original ministerial issue time make novelty and first-public clock unresolved; this is not a claim that any new war began.

## October 24 source-access decision: do not certify October 6

**Decision: `DO_NOT_CERTIFY_OCT6_SOURCE_DAY` / `SOURCE_CENSUS_INCOMPLETE`.** This is a documented evidence limitation, **not** a declaration that no source events happened. The 26 candidate/exclusion/confounded records and 16 corrections are a partial source-first research worksheet; none have an admissible COMPLETE-day receipt or market-outcome access.

**Why certification is blocked:** The frozen study requires verifiable 24-hour Reuters/original-wire coverage and UKMTO public/industry warning, advisory and notice issue histories, plus original issue timestamps and negative-search/completeness receipts. Neither has been demonstrated. Public Reuters syndications, historical Google News (100-result caps and cross-date indexing), and GDELT crawl/first-seen timestamps are not exhaustive or trustworthy original publication clocks. UKMTO incident-day pages and warnings #156-159 establish parts of the incident/product chronology, but do not prove every October 6 original issue or notification. The MT On Peace India/Panama original-source contradiction remains open; no hindsight-based source-clock reassignment is permitted.

**Access finding, not global impossibility:** LSEG Reuters News Service historical archives may provide a licensed route, but no authorized archive endpoint, credentials, full-day query, pagination or completeness receipt was verified for this research workspace as of October 24, 2026. Other operators may have licensed access; that is unknown, not denied.

**Reopen only** after verifying a first-party/licensed exhaustive original-wire query and a UKMTO full product/first-issue and negative coverage archive, then independently adjudicating the frozen candidate set **before** any U.S. or HSI measurement. Do not fabricate a census, narrow the event universe retrospectively, promote later press copy as `available_at`, reclassify Epoch 1, or publish signals/trades.

**Next independent lane:** exact-head adversarial review of the UTC source-day certification wall-clock guard and the sealed admission firewall. A CI-green PR without that review is not scientific acceptance. This ruling is also preserved on [PR #8012, October 24 evidence decision](https://github.com/mastermindx-market-intelligence/macro/pull/8012#issuecomment-6381542895).

## October 24 receipt-provenance enforcement repair

For **Epoch-2 admissions**, the research harness now refuses to promote a caller-asserted channel `COMPLETE` value or arbitrary nonempty `receipt` reference into scientific authorization. The private `_require_authoritative_source_day_provenance` guard runs **before an Epoch-2 completed-day receipt is sealed**, **before a synthetic/rehashed source-day receipt can seal an Epoch-2 admission**, and **before U.S./HSI outcome transport for Epoch-2 admissions**. Pre-activation Epoch-1 admission behavior is outside this guard. The frozen Epoch-1 quarantine explicitly lists ten event IDs; it is **not** a blanket prohibition on newly constructed pre-activation admissions reaching legacy U.S./HSI measurement paths. This repair leaves those historical paths unchanged, and makes no claim of universal Epoch-1 outcome quarantine. With no verified original Reuters/wire and UKMTO source-owner archive connected, the Epoch-2 path deliberately rejects the operation rather than minting a false `COMPLETE` certificate. A matching SHA-256 digest alone never authenticates origin or proves the all-channel negative-source census.

The existing source owner's authoritative evidence verification must be connected and independently reviewed to reopen this guard. The code does not create a second source registry, runtime authentication path, or manual CLI override. Contract tests deliberately simulate the absent owner in narrowly marked synthetic fixtures to preserve proof that the remainder of the frozen protocol can operate **only after** that trust check; they do not establish a genuine Reuters or UKMTO completed-day census. The 26 October 6 candidates and 16 corrections remain untouched, with zero admissions and no market-outcome reads.

## Before any scientific outcome access

1. Obtain verifiable full-day original Reuters/wire and UKMTO channel coverage with issue-time provenance, including negative searches and unresolved candidate dispositions. Do not infer completeness from a 100-item news index or the absence of a live warning-list row.
2. Resolve exact first-public clocks, vintage edits, parent clusters and materiality using only information knowable at that clock; keep the frozen protocol and no-reanchor/DATA_GAP rules.
3. Only then produce a **separate** executable `certify_source_day` receipt with true completed-channel evidence. This snapshot **never** qualifies as one. Epoch 1 remains quarantined and U.S./HSI market outcomes are deliberately unopened.

The `CROSS_SESSION_EPOCH2_SOURCE_COVERAGE_GAPS_2026-10-06.json` file contains historical M2 absolute paths as provenance, not current path requirements. Prefer these repo-relative snapshot files for cross-session review. Do not copy stale absolute paths into a runtime authority assertion.
