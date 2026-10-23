# SLR-P0 — historical-reference recovery path (research-only)

Date: 2026-10-08. Owner: continuing SLR-P0 research under the Chairman’s Extra High execution directive. Source pin: Mastermind protected master `c7e47c859eb2925c5626931fd511800773ba09ac` (compatible Skillpack 1.0.1); Macro main observed `eefddf818163c557c2c7aabba05f02a4325b34d2`; unchanged frozen SLR-P0 protocol v1.0.1 at commit `4136eebc1d57b6d6c682403f1735849c5f9589f4`. This is a new source-research addendum on the existing PR #8645, not a change to the protocol or the previously refused checker implementation.

**Disposition: EXTERNAL_SOURCE_METHOD_IDENTIFIED / LOCAL_ACCESS_UNVERIFIED / HISTORICAL_PRIMARY_NOT_ADMITTED / OUTCOMES_NOT_OPENED.** Scientific study remains incomplete. This addendum neither grants vendor entitlement nor authorizes a data pull, credential read, replay of refused tool operations, new collector, prospective registration, ranking, trading or production effect. It introduces no alternate source of organizational or identity authority.

## 1. What was verified from current primary documentation

### A. Massive dated listing and reference APIs — available API shape, not proven local coverage

Official Stocks REST documentation identifies:

- `GET /v3/reference/tickers?date=YYYY-MM-DD&market=stocks&active=...`: point-in-time ticker listing; response fields include ticker, CIK, composite FIGI, share-class FIGI, type, market/exchange, active and delisted indicators. Documentation gives a historical availability floor of September 10, 2003, but does **not** prove completeness for this experiment or entitlement on the configured connection.
- `GET /v3/reference/tickers/{ticker}?date=YYYY-MM-DD`: reference details, including CIK, FIGIs, SIC, type and dates, with qualified coverage required per field. Critically, the official documentation states that information derived from SEC filings is indexed by the **SEC period of report**, which can predate the filing submission. A 2019-07-31 filing about the 2019-06-29 period can influence the result for a 2019-06-29 query. Therefore vendor `date` is **not** a sufficient decision-time knowledge gate for those fields.
- `GET /vX/reference/tickers/{id}/events`: an **experimental** ticker-change timeline. Its docs caution that a ticker-string query returns events for the entity **currently** represented by that ticker; it may not find the historical previous owner of a reused ticker. An immutable historical identifier from dated details must anchor reconciliation.

Official docs:
1. https://massive.com/docs/rest/stocks/tickers/all-tickers
2. https://massive.com/docs/rest/stocks/tickers/ticker-overview
3. https://massive.com/docs/rest/stocks/corporate-actions/ticker-events
4. https://massive.com/knowledge-base/article/how-does-polygon-handle-ticker-changes-and-acquisitions

The existing in-repo Massive entitlement record (`research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, Macro source blob `3969a9aae918141b51baffbb0e17d8a2ec2485a0`) documents broad historical/reference research rights. That existing record should be preserved; this audit does not revoke it or infer that any particular returned field is complete, or that a separate named third-party dataset is covered.

### B. SEC EDGAR has filed-time evidence distinct from report-time fields

SEC’s official historical EDGAR header specification identifies `<CIK>`, `<ASSIGNED-SIC>`, `<FILING-DATE>` and `<PERIOD>` as distinct indexed fields. SEC archive examples also expose acceptance date/time in the raw SGML header. EDGAR documentation confirms CIK is not recycled, that historical filings have dated accession identities, that post-acceptance changes can occur, and that some evening filings disseminate the following business day.

Sources:
5. https://www.sec.gov/edgar/searchedgar/edgarzones.htm
6. https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
7. https://www.sec.gov/Archives/edgar/data/4457/000000445715000019/0000004457-15-000019-index-headers.html (2015 example with filed date, acceptance timestamp, registrant CIK and contemporaneous SIC; a public source exemplar, **not** an SLR population observation)

**Proposed provenance tuple for a historically known SIC observation:** `(registrant_cik, sec_accession, filing_accepted_at_utc, first_public_dissemination_at_or_after, report_period_end, sic_code, source_content_digest, known_at_basis, valid_from, valid_to)`. The acceptance and public-availability bounds must be separately established or conservatively lagged to the next trading session; reporting period is not a substitute for either. Corrections remain separate generations. This tuple is a *research acceptance specification*, not a request to mint another security/issuer authority.

SEC filings also carry registered security class, ticker and exchange in cover information; tagged `dei:TradingSymbol` and `dei:SecurityExchangeName` support suitable modern filings, but XBRL history and per-filing availability must be qualified. An SEC registrant CIK is not universally an economic-parent identifier; multiple legal filers and ADR/depositary structures require abstention or corroboration.

### C. Genuine historical GICS is a separate commercial source

S&P Global’s official GICS listing describes **GICS History**, including active and inactive companies, history from 1985 and dated `from`/`thru` classifications. This is the most direct candidate for preserving SLR-P0’s exact GICS-sector estimand, conditional on independently observed access, identifier coverage, correct chronology and a dataset-specific permitted-use record. **Its existence in the marketplace proves neither that Mastermind possesses it nor that Massive’s separate contract covers it.**

Source:
8. https://www.marketplace.spglobal.com/en/datasets/gics-(90)

### D. SEC SIC can be historically anchored but cannot silently masquerade as GICS

MSCI/S&P’s original November 2017 GICS announcement and November 2018 implementation reminder document the major 2018 reorganization. Alphabet and Facebook were among companies moved out of Information Technology into Communication Services; GICS Direct took the new structure after September 28, 2018 (effective October 1); index implementation dates differed.

Sources:
9. https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=C8yMx%2BzdSX8%3D
10. https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=A83vYj52YoU%3D

Even authentic, contemporaneous SEC SIC codes cannot be assumed to reproduce GICS reclassification. An SIC-derived 11-sector proxy is a **different classification method and potentially a different peer cohort**. A current fixed SIC→GICS map is not an admissible fill for frozen v1.0.1. The 2018 example is a concrete required falsifier for parity, not a measured estimate of mismatch frequency.

## 2. Admission matrix — observed versus not observed

| Proposed evidence | Public capability established | Native/current configured content verified | Frozen exact-GICS primary status |
|---|---|---|---|
| S&P GICS History with effective `from`/`thru` and stable company/security join | YES, source listing | NO, license/rights/file not observed | **POTENTIAL EXACT SOURCE; NOT_ADMITTED** |
| Massive dated Ticker List + Ticker Overview + historical identifier | YES, documented | NO, live historical response not sampled | **PARTIAL IDENTITY PATH; NOT_ADMITTED** |
| Massive Ticker Events | YES, experimental endpoint | NO, coverage/reuse behavior not sampled | **SUPPORT ONLY; NOT_ADMITTED** |
| SEC filed-date/accepted-time SIC and registered-class evidence | YES, official archives/examples | NO, event-cohort extraction/coverage not run | **POTENTIAL HISTORICAL SIC EVIDENCE, NOT GICS** |
| Existing Macro security/issuer master | YES, mounted metadata inspected in prior phase | YES, 2,382 security rows, 1,213 issuer rows; *current-only owner semantics* | **NOT_ADMITTED FOR HISTORICAL LINEAGE** |
| Existing Macro 2,589-row PIT-sectors-named file | YES, exact retained content digest | YES, zero era-correct rows according to unchanged existing receipt | **NOT_ADMITTED** |

Prior refusals of the broad host source inventory and historical alias/issuer row audit remain binding. No corresponding restricted host query was reattempted, and no alternate connector was used to fetch refused rows. This public documentation research is an independent no-credential lane, not evidence that the denied operations succeeded.

## 3. Two scientifically honest routes — no hidden fallback

**Route A: exact frozen GICS study (preferred scientific fidelity).** Existing authorised custodian identifies an actually accessible, licensed historical GICS from/thru dataset; binds it to stable historical security/issuer identifiers; verifies calendar validity and knowledge-time claims, not a modern ticker join; freezes positive/negative coverage and adjustment receipts. Only then can the original v1.0.1 challenge cohort be admitted for an outcome-blind event census. Do **not** acquire S&P credentials or license on this research record.

**Route B: SEC-SIC-defined *different* development species (potentially lower cost, not a fallback).** If exact historical GICS remains unavailable, a distinct protocol amendment/new research registration *before any outcome access* may define contemporaneously filed SIC groupings with a predeclared SIC→coarse-group mapping and separate null/missing treatment. Use dated Massive security observations and EDGAR filings only after source qualification; report the 2018 GICS migration as a structural basis difference; never present the result as v1.0.1 GICS-sector resilience. This route requires an explicit independent protocol/estimand decision, not a programmatic fallback on missing GICS rows. No such amendment is enacted here.

**Both routes require valid-time issuer and instrument identity.** An as-of API response may locate a CIK/FIGI, but only content-level and chronology checks can prove whether it reflects the issuer/security in 2014 rather than the current owner of a reused ticker. Verified SEC CIK equality can support same-registrant grouping; it is insufficient on its own for every economic-parent/share-class/ADR situation. The canonical Data OS owner, not a new SLR resolver, adjudicates collisions.

## 4. Exact outcome-blind acceptance probe once the permission/source gate is actually clear

This is a future **bounded qualification recipe**, not an instruction to run refused operations from another account/carrier:

1. **Source identity/rights:** record the incumbent source owner, feed/dataset designation, actual permission/read carrier, API plan/entitlement, permissible historical model use and immutable response digests. No blind API-key read or unapproved provider activation.
2. **Time:** for each returned field distinguish economic effective time, vendor as-of selection, SEC period-of-report, SEC acceptance/first dissemination, local first possession, and correction generation. Feature timestamp must not precede a permitted availability timestamp. Prospective and historical-final-vintage claims must be labeled separately.
3. **Security:** reconstruct period-specific ticker→security identifier, venue, type, issuer/registrant, share-class, rename/delist/reuse edges. Explicitly test BRK.A/BRK.B and GOOG/GOOGL same-issuer exclusion; an old-versus-current ticker reuser; a pure rename; and an ADR exception. Unknown mappings stay excluded.
4. **Classification:** test Alphabet/Facebook across the 2018 GICS transition, one utility, one financial firm, an IPO, a delisted issuer, an SIC reassignment, and sector changes after merger. Record actual GICS-vs-SIC comparison only if both sources are positively admitted; do not infer missing results.
5. **History depth:** include all dates needed for 2014 cohort preparation and prior-252-session regressions, not just headline 2014–2025 rows. Audit after-hours filing availability and missing lookbacks without backfills from future releases.
6. **Coverage:** compute input-only counts of matched canonical onsets, issuer-verified names, observed classification per era, identity/type exclusions, peer sets of at least 20 other issuers, first-shock observability, sector-date cells and independent potential shock blocks. **Do not open forward returns, protected CR1/AF1 state/outcomes or data from the already-consumed no-redo families.**
7. **Stop:** if actual eligible N, historical rights, identity validity or independent-shock floor fail, publish NOT_ADMITTED/INSUFFICIENT_INFORMATION and do not lower thresholds, import GICS from SIC, substitute SPY shock, or start the historical outcome run.

## 5. Why this is progress but not completion

The documentation search materially changes the blocker from “historical sectors and issuer relationships may require buying entirely new data” to **a testable existing-vendor/SEC route for historical identifier and SIC evidence plus a separately identified exact-GICS commercial source**. It also falsifies the shortcut “SEC SIC mapped to today’s GICS sectors equals historical GICS” and exposes the report-period-vs-publication clock trap.

No qualified live vendor response, actual dataset rights for S&P GICS History, historical issuer join, event incidence, statistical test, prospective study, signal, portfolio action, data-plane write or production consumer was established. The frozen protocol and original result stand unchanged. The next critical action belongs to the **incumbent reference-data owner on a positively permitted source/read carrier**, not to a new hidden tool or a fresh-chat retry of refused reads.

**Decision at this boundary:** SOURCE_METHOD_IDENTIFIED, **STRICT_PRIMARY_NOT_ADMITTED**. Parent mission incomplete. Future confirmation remains a distinct step after valid development and prospective registration.