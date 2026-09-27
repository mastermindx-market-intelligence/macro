# Q06 SEC comparable-revenue prospective capture candidate — 2026-09-26

**Operation:** `prophet-economic-evidence-research-20260926-sol-001`
**Parent:** Macro #6817 / `prophet-cockpit-four-market-recovery-20260904-sol-001`
**US programme:** Macro #6805 / `WS:PROPHET-US-V4-RECOVERY`
**Evaluation owner:** Packet3 `prophet-selection-evaluation-first-cohort-20260924-sol-001` on #7288
**Consumer owner:** Packet4 / incumbent Prophet experience source owners; this record changes no adapter or UI
**Status:** `FIRST_SOURCE_UNIT_COMPLETE / RECORDS_ONLY / NUMERICAL_RESULT_UNCOMPUTED`

Protected procedure was re-pinned before this unit at
`mastermindx-market-intelligence/Mastermind@4c6b206d3fb7fbc6d077faf61ae361bedf259925`
(`mastermind.sol_skillpack.v1` 1.0.1 / bootstrap major 1). Source base is
`macro@b95cfc873a4de44e0f2fae15be30f777077a8151`.

## 1. Decision

The first preregisterable Q06 construction is **not** an earnings-surprise or
transcript-guidance signal. It is a source-bound SEC operating-change feature:

```text
Q06-SCR-01/v0.1
comparable quarterly GAAP revenue growth
= ((current-quarter total net sales / same-quarter-prior-year total net sales) - 1) * 100
```

The current rights register admits SEC EDGAR acquisition, processing, storage,
model use and redistribution with citation/trademark limits. It does not admit
Nasdaq storage/model use, Yahoo expectation model use, generic consensus, or
transcript redistribution/model use. The AAPL 9–11% FY2026 Q4 guidance remains
useful diagnostic context, but its current `rp_public_primary_v1` transcript
profile is internal/context-only and cannot define the confirmatory feature.

This is a narrower construction than the earlier provisional
`Q06-IGL-01/v0.1`. That provisional guidance-first label is superseded for the
first confirmatory source unit. No source or result from it is discarded; the
transcript field remains a separately typed diagnostic input.

## 2. Exact supported case

### Identity and source

| Field | Exact value |
|---|---|
| Event | `evt_cik0000320193_2026q3_results` |
| Issuer / CIK | Apple Inc. / `0000320193` |
| Accession | `0000320193-26-000018` |
| Form | `8-K`, Exhibit 99.1 |
| Fiscal period | FY2026 Q3, quarter ended 2026-06-27 |
| Source URL | SEC archive Exhibit 99.1 carried by the owner workspace |
| Production source-available clock | `2026-07-30T20:30:28Z` |
| Fixture metadata clock | `2026-07-30T16:30:00Z` — conflicts with production; not used as the decision clock |
| Original source body SHA-256 | `070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb` |
| Current source body SHA-256 | `5cab65a7cba3d7f81dba0c6ac16687a13157678f9b78d4cc5ec64d44a698d5ad` |

### Field construction

The same SEC table is headed `Three Months Ended`, with columns `June 27, 2026`
and `June 28, 2025`. `Total net sales` is:

| Role | Value | Unit/basis | Raw-byte evidence |
|---|---:|---|---|
| Current quarter | 109,417 | USD millions / GAAP | bytes `[19519,19526)`, text SHA-256 `4a745d359dd176f4216117d625d1a5b92600458fe8e374d71ee3878b379f82c7` |
| Prior-year comparable quarter | 94,036 | USD millions / GAAP | bytes `[20003,20009)`, text SHA-256 `2606ce5cfae97e1126fb0267bc90724fe830c01af1dc59e3d9dde6c1acea746c` |

Deterministic feature value:

```text
(109417 / 94036 - 1) * 100 = 16.356501765281383 percent
```

The existing D5 projection materializes current revenue but emits prior revenue as
typed absence `no_span_addressable_evidence`; therefore `Q06-SCR-01/v0.1` is a
**source-supported construction, not a currently materialized production field**.
Packet4 may consume the accepted field contract later through the incumbent owner;
this seat does not edit the adapter.

### Diagnostic-only transcript context

The owner workspace also carries FY2026 Q4 revenue-growth guidance of 9%–11%
(midpoint 10%, width 2 percentage points), status `introduced`, from transcript
SHA-256 `a8ff5d03e875fef5604791edbf625186c447af049e6e02f55bb89c68c7cc9f9f`.
Its exact text hash is
`52288830a4c55ada7d850d445fa57229272e35864bb8c95f91bfeb139eebe328`.
It is **excluded from the confirmatory feature set** until a source-specific rights
record admits persistence/model use and an exact publication/observation clock.

## 3. Production revision-chain receipt

At `2026-09-27T03:17:23.733408Z`, a bounded canonical-style read of the public R2
workspace chain verified:

Durable compact receipt: `research/prophet_v4/r6_program/wave3/q06_aapl_revision_chain_receipt.v1.json`, SHA-256 `3800cb3f6c6082ff3a05b825bd61a965115f6d1280a660aea188f2162bf34ef4`; full scratch read digest `b9a9dc057429f3d3bf72b60953cce454c8a1ef58c2bfa356b726a4e26811f33b`.

- current marker generation `2db5fb7235184c40ba2e201c`;
- current marker SHA-256 `fb53b63ee8f8a4dfd2335b2a43014c9ad5199e3962aa918a90b92504c6b30576`;
- current AAPL workspace SHA-256 `ee65aec043f314e72dcdf7c739323ff6304e0ee93f6fbfca4ff73d6f32d8c5b0`, 111,562 bytes;
- 186 manifest links verified through exact predecessor-manifest hashes;
- 186 generations carrying the AAPL event;
- 10 distinct source-body revisions after consecutive carry-forward deduplication;
- original revision generation `0da3b64d4d9c843f004cd558`, workspace SHA-256
  `906d306102072a553da14c49e4842b7e876f3ce69ab693dab472426f48223acb`;
- calibration generation `f709a0a6ec514282d5769e7d`, manifest SHA-256
  `47abc17122d34f50a558e4908d30ba6ad8282901587d258e2b09e3463da67557`,
  workspace SHA-256 `dbd50e5c30e8a031f844e02362ffd53b25e3230e75eeef19bf3825543cb81197`;
- current revision lifecycle: `corrected`, source available
  `2026-07-30T20:30:28Z`, observed `2026-09-26T05:02:59Z`.

Across the 10 distinct source revisions, the comparable revenue value and its
exact text hash remain stable; the 9%–11% transcript-guidance bounds and exact text
hash also remain stable. The original `questions_count` typed-absence row exists
only in the first source revision. Source bytes and workspace bytes therefore
changed without changing the selected economic field.

### Correction rule frozen for this study

A new body SHA is **not by itself** an economic-feature correction.

1. `SOURCE_BYTES_CHANGED / ECONOMIC_FIELDS_UNCHANGED` when the exact field tuple
   `(identity, fiscal period, metric, value, unit, currency, accounting basis,
   source text hash)` is unchanged.
2. `ECONOMIC_FIELDS_CHANGED` when any tuple member changes, a field disappears, or
   a newly admitted comparable field changes the construction.
3. `CLOCK_ONLY_CHANGE` when only the owner observation/generation clock changes.
4. Any unverified or broken predecessor link is `UNESTIMABLE`; no current-body
   fallback is permitted for a decision-time claim.

All classes retain the source-body lineage. Only class 2 versions the feature
value. Classes 1 and 3 are still reported because repeated source churn can reveal
capture instability even when the economic value is stable.

## 4. Coverage-qualified cohort

A row enters the prospective cohort only when all conditions are true before the
outcome clock begins:

1. ordinary-accounting operating company, canonical issuer/security/identity epoch;
2. source is an exact SEC 8-K or 6-K release body with accession, form, fiscal
   period, source-available clock, system-observed clock and immutable body receipt;
3. one same-table current and prior-year comparable quarterly revenue pair;
4. identical currency, unit, accounting basis and period role; no GAAP/adjusted,
   continuing/discontinued, quarterly/year-to-date or currency mixing;
5. exact current/prior source spans and text hashes;
6. source/body correction lineage verified through the decision cut;
7. market-data, benchmark, corporate-action and fill evidence available under an
   admitted source owner;
8. no outcome inspection was used to choose the issuer, event, fiscal period or
   field.

Typed exclusion reasons include `NO_COMPARABLE_PRIOR`, `BASIS_MISMATCH`,
`UNIT_OR_CURRENCY_MISMATCH`, `PERIOD_ROLE_MISMATCH`, `IDENTITY_UNRESOLVED`,
`CLOCK_UNPROVEN`, `LINEAGE_BROKEN`, `RIGHTS_BLOCKED`, `PRICE_BASIS_UNAVAILABLE`,
and `OUTCOME_NOT_MATURED`. Excluded rows remain denominator-visible.

The current R6 event set cannot support a confirmatory historical cohort: D07's
SEC comparable-event row remains null because the complete event set is not
reconstructable, and the D07 register itself is still Draft/unmerged on #7856.
Consequently:

- the AAPL case is an exact source-construction exemplar;
- public-information replay is diagnostic only;
- confirmatory evidence begins with prospective capture after registration;
- no protected return is opened by this record.

## 5. Preregisterable experiment candidate

```text
hypothesis_id: Q06-SCR-01/v0.1
mechanism: comparable quarterly GAAP revenue growth may retain opportunity after
           controlling for the price response already visible when the source is usable
primary horizon: H42 exchange sessions
supporting horizons: H21 and H63, descriptive only, no rescue authority
origin: first lawful post-usable-time decision cut
management: fixed across all comparison arms
result state: UNCOMPUTED
```

### Arms

1. **Economic change only:** `revenue_yoy_pct` with coverage/missingness facts.
2. **Observed price response only:** same cohort, source-to-first-lawful-entry price
   response and pre-event run-up.
3. **Economic + price response:** one simple, predeclared additive/regularized
   comparator; no unrestricted interaction search.
4. **Incumbent control:** existing owner policy on the identical eligible population.
5. **Cash / broad-market / PIT sector controls:** same origin and endpoint clocks.

### Primary reporting

- date-weighted H42 net excess outcome on the complete eligible cohort;
- episode-weighted H42 shown separately;
- participation, no-entry, unpriced, excluded and not-matured counts;
- absolute, broad-market-relative and sector-relative outcomes kept separate;
- downside/tail loss, turnover, fill/cost sensitivity and concentration;
- confidence intervals with date/issuer dependence preserved;
- selected-top-list metrics only if Packet3 registers a selection task; this source
  study does not create one.

### Execution law

- Decision time is `max(source_available_at, system_observed_at)` under the accepted
  exchange calendar.
- No fill at a close or bar already required to know the source or feature.
- A source published after the regular session uses the next lawful actionable
  price under the existing market-data/fill owner.
- Missing NBBO/spread/basis/corporate-action evidence is unavailable, never zero.
- The price/benchmark source must have explicit model-use rights. For US, the
  existing Massive enterprise family is the preferred candidate, subject to the
  exact feed designation; Yahoo/Nasdaq cannot silently fill this role.
- Entry timing, management and portfolio feasibility remain separate experiments.

### Falsifiers

- comparable rows fail basis/period/unit reconciliation at material frequency;
- the apparent effect disappears after the initial usable-time price response;
- the result is carried by a few issuers/dates or by one accounting era;
- realistic costs, gaps, unavailable fills or corporate actions erase the result;
- a simple own-price control matches or exceeds the economic feature;
- source-byte/correction instability changes the feature materially;
- chronological validation or independent review rejects incremental value;
- adequate independent dates cannot be reached without repeated holdout inspection.

A null, negative, inconclusive or insufficient-data result is accepted. No result
changes rank, B4, entry, sizing, plan history, execution or user positions.

## 6. Known-answer smoke fixture before real outcomes

Packet3 should consume, not duplicate, equivalent existing checks. Any missing
fixture must discriminate at least:

| Case | Required disposition |
|---|---|
| AAPL values 109,417 / 94,036 | exact `16.356501765281383%` feature |
| source observed after the simulated cut | `NOT_CAPTURED_AT_DECISION` |
| source published after the simulated cut | `NOT_PUBLISHED_AT_DECISION` |
| missing prior or zero denominator | typed unavailable; no numeric feature |
| adjusted/raw price-basis mismatch | refuse outcome join |
| same-bar source and favorable close | no same-bar fill |
| target and invalidation both touched in one unresolved bar | unresolved ordering, not favorable-first |
| omitted spread/cost | test failure / result not admissible |
| duplicate issuer/date/event row | one grouped decision, not two independent samples |
| cancelled/failed evaluator job | no result and no protected-test consumption claim |

## 7. Four-market transportability map

| Market | Existing owners/source reality | Clock/history state | Current class for this mechanism | Exact next source decision |
|---|---|---|---|---|
| US | SEC EDGAR + Earnings/Company Intelligence + Stock Identity; Massive candidate for prices | Exact SEC body and revision chain exist; complete historical event population does not | Exact exemplar; prospective confirmatory capture after registration | Materialize same-table comparable revenue through incumbent owner; freeze prospective event population and exact Massive feed designation |
| China A-share | CNInfo announcement metadata; Eastmoney/akshare disclosure calendar and preannouncement/quick-report snapshots; canonical CN identity owner | CNInfo is forward append-only metadata with `publish_ts`; current earnings/preannouncement stores are snapshots and do not provide an immutable body/revision chain | Prospective discovery/diagnostic only; no comparable SEC-style feature | Admit official body capture plus five-rights determination, exact publication/observation clocks and correction lineage; do not use current snapshots as history |
| Hong Kong | HKEXnews results metadata + HK filing bus + HK identity/price owners | trailing 90-day, keep-first headline tape; no numeric filing-body revision plane for this construction | Prospective discovery/display only | Add lawful official body/field capture and source-specific rights; preserve HK calendar/listing identity and do not infer values from headlines |
| Canada | current yfinance fundamentals/consensus context; SEDAR+ is native filing owner in product vision | yfinance is current snapshot with unknown model rights; public SEDAR+ automation/database construction is rights-blocked | NOT SOURCE-READY | Obtain licensed SEDAR+ DDS or equivalent first-party feed with clocks, revisions, identity and retention rights; qualify a non-Yahoo price feed |

SEC-reporting foreign private issuers may enter the US SEC construction through a
6-K where identity and source rules pass. That does not establish China/HK/Canada
native-market transportability or trading feasibility.

### Current primary-authority spot check — access is not a blanket rights grant

Checked on 2026-09-27 UTC against current official pages:

| Authority | Current fact established | What it does **not** establish |
|---|---|---|
| U.S. SEC EDGAR API documentation | `data.sec.gov` exposes unauthenticated REST JSON for filer submissions and XBRL facts from 8-K, 20-F, 40-F and 6-K families; submissions are updated through the day and bulk structures are republished nightly | It does not replace the source-family rights register, exact exhibit-body receipt, correction chain, fiscal comparability or decision-time capture required by this study |
| HKEX Listed Company Information Title Search | The official search exposes exact release timestamps, stock identity, document category and linked result/report documents; current examples include interim results and interim reports | It does not establish lawful bulk body retention/model use, a numeric comparable-field parser, historical completeness or immutable revision lineage |
| SEDAR+ public access and Terms of Use | The public can search and download documents, but the official terms prohibit constructing/storing a database from Public Information and prohibit scraping or automated reproduction of multiple pieces from the public website | Public browser availability is not an automated source grant; Canada remains blocked until written permission, licensed distribution access or another lawful first-party feed passes clocks, identity, correction, retention and model-use review |

Official references:

- `https://www.sec.gov/search-filings/edgar-application-programming-interfaces`
- `https://www.sec.gov/newsroom/press-releases/2021-159`
- `https://www1.hkexnews.hk/search/titlesearch.xhtml`
- `https://systems.securities-administrators.ca/onlinehelp/general-help/getting-started/general-public-access/`
- `https://systems.securities-administrators.ca/terms-of-use/`

These checks strengthen source feasibility and the Canada refusal; they do not
promote any market to confirmatory-ready, change the five-rights determinations,
or authorize a new collector.

## 8. Prioritized missing-data decision

The highest-value acquisition is **not consensus**. It is lawful immutable
issuer-source capture:

1. US: prospective SEC event-population manifest plus same-table comparable fields;
2. China/HK: official filing bodies with publication/observation/correction clocks
   and explicit model/redistribution rights;
3. Canada: licensed SEDAR+ DDS or equivalent first-party continuous-disclosure feed;
4. only afterward, a separately licensed comparable-expectations history with
   contributor, fiscal-horizon, revision and publication clocks.

Missing consensus remains typed absence. No beat/miss may be inferred from AAPL's
16.36% revenue growth or its transcript guidance.

## 9. Consumer and continuation boundary

- **Packet3 / #7288:** receives the hypothesis, population, smoke fixture,
  endpoints and every result field as `UNCOMPUTED`; it alone registers/evaluates
  through the existing Evaluation/QLedger owner.
- **Packet4 / incumbent consumer:** receives the accepted source-field construction
  only after review; it does not receive a score, recommendation or adapter edit
  from this seat.
- **B04/D07:** retain their current owners and open gates. This record does not set
  `evidence_class`, decision admissibility or current-view semantics.
- **Cycle #7868/#7871:** unchanged and held. No Cycle data, result or workaround was
  opened.

Exact next action: independent source-method review of this record and manifest.
On acceptance, Packet3 registers one prospective `Q06-SCR-01/v0.1` trial with an
exact data/environment/trial identity. Until then, all numerical outcome fields
remain explicitly uncomputed.
