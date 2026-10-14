# Energy R5B — First historical expectations-event qualification: Equinor Q4 2024

**Research program date:** 2026-09-23  
**Operation:** `gmi-energy-sector-research-20260923-sol-001`  
**Carrier:** Macro PR #7791 / `sol/energy-sector-research-20260923`  
**State:** research only. No production ingestion, basket/rank/entry/size/trade authority and no Fable handoff.

## 1. What R5B closes — and what it does not

R5A established that issuer and issuer-linked consensus sources can provide useful current or source-labelled expectation observations. R5B tests a harder question: can Mastermind reconstruct a **historically knowable expectation before an actual result**, then compare the actual outcome and contemporaneous market response without backfilling current knowledge?

For Equinor Q4 2024, the answer is now **partially yes**.

There is a contemporaneous issuer invitation dated 13 January 2025 stating that Q4 2024 results would be published on 5 February and that Equinor publishes its collected analyst consensus one week before the result. An independent article published on 29 January at 08:07 reports the company-collected Q4 consensus from 24 analysts. The present Equinor historical-consensus archive reproduces the same core pre-tax, after-tax and production values and additionally shows adjusted EPS and the aggregation method.

This establishes a materially stronger historical-information chain than a current consensus page alone.

It does **not** establish the exact byte identity of the consensus file as it existed on 29 January, because today's historical PDF is a current archive compilation rather than an independently preserved 29 January file. The correct evidence state is therefore:

`PRE_EVENT_AGGREGATE_SUPPORTED / EXACT_HISTORICAL_BYTE_NOT_ARCHIVED`

That distinction should survive into the product.

## 2. Pre-event evidence chain

### 13 January 2025 — issuer process evidence

Equinor invited analysts to submit Q4 estimates. The issuer stated that Q4 2024 results would be released on 5 February and that collected analyst consensus is published one week before the actual release.

Source:
https://www.equinor.com/news/20250113-invitation-estimates-4q2024-results

This source proves the intended publication process and event date. It does not contain the final consensus values.

### 29 January 2025 — independently timestamped consensus values

Finansavisen / Infront TDN Direkt published at 08:07 that analysts expected:
- adjusted operating income before tax: **USD 7.709bn**;
- adjusted operating income after tax: **USD 2.061bn**;
- equity production: **2.093m boe/day**;
- source population: **24 analysts**;
and explicitly attributes the consensus to Equinor's own collection.

Source:
https://www.finansavisen.no/tdn/2025/01/29/06430685/eqnr-justert-driftsresultat-ventes-til-usd-7.709m-i-4.kv-2024

This is the strongest first-known receipt in the case because it is external to Equinor, date/time-labelled and predates the result.

### Current issuer historical archive — archival cross-check

Equinor's Historical consensus (2010-) archive identifies Q4 2024 as collected in January 2025 with 24 analyst inputs and reports:
- adjusted operating income before tax: **USD 7.709bn**;
- tax in total: **USD 5.648bn**;
- adjusted operating income after tax: **USD 2.061bn**;
- total equity production: **2.093m boe/day**;
- CFFO after tax ex-working-capital: **USD 4.026bn**;
- organic capex: **USD 3.591bn**;
- adjusted EPS: **USD 0.68/share**.

The archive states that segment/tax/production figures are averages after removing the highest and lowest input for each item.

Issuer parent:
https://www.equinor.com/investors/consensus

Because the current archive is not an independently archived 29 January byte snapshot, EPS 0.68 is useful historical context but receives a weaker first-known grade than the three metrics independently quoted on 29 January.

## 3. Actual result and metric-matched surprises

Equinor's 5 February release reports Q4 adjusted operating income of **USD 7.896bn**, adjusted operating income after tax of **USD 2.292bn**, adjusted EPS of **USD 0.63/share**, and total equity production of **2.072m boe/day**.

Issuer result:
https://www.equinor.com/news/equinor-fourth-quarter-and-full-year-2024-results

The matched descriptive surprises are:

| Metric | Pre-event / archival consensus | Actual | Difference |
|---|---:|---:|---:|
| Adjusted operating income before tax | USD 7.709bn | USD 7.896bn | **+2.43%** |
| Adjusted operating income after tax | USD 2.061bn | USD 2.292bn | **+11.21%** |
| Adjusted EPS | USD 0.68 | USD 0.63 | **-7.35%** |
| Equity production | 2.093m boe/day | 2.072m boe/day | **-1.00%** |

The surprise vector is mixed. Pre-tax and operating-after-tax results are above the archived aggregates, while adjusted EPS and production are below.

This is exactly why Mastermind should never reduce an earnings event to a single generic "beat/miss" bit.

## 4. A live data-quality conflict: USD 1.733bn is not USD 2.292bn

A same-day independent result article reports adjusted operating income before tax correctly at USD 7.896bn, but then describes **USD 1.733bn** as adjusted operating income after tax versus USD 2.061bn expected.

The issuer's own financial statements distinguish:
- adjusted operating income after tax: **USD 2.292bn**;
- adjusted net income: **USD 1.733bn**.

Therefore the third-party article appears to map the adjusted-net-income value to the wrong metric label. This is not a reason to discard the article's contemporaneous existence. It is a reason to prevent a third-party label from overriding issuer metric definitions.

Independent result article:
https://www.finansavisen.no/tdn/2025/02/05/06433741/eqnr-justert-driftsresultat-usd-7.896m-i-4.kv-2024-ventet-7.709

The product requirement is deterministic:
**when numeric value and metric label conflict across sources, preserve both records, bind the issuer-defined actual to its canonical metric, and surface the conflict rather than silently choosing whichever creates a stronger surprise.**

## 5. Market reaction: context, not causal proof

Nasdaq Stockholm's February 2025 Nordic Derivatives report records for `EQNR NO`:
- earnings-related implied move: **4.5%**;
- actual earnings move: **-4.1%**;
- latest earnings date: **2025-02-05**.

Source:
https://www.nasdaq.com/docs/2025/04/03/NordicDerviativesReport_Feb2025_v2.pdf

The report's visible footnote describes the implied-move measure as an absolute price-change estimate derived from option volatility and cites Bloomberg. Its visible table does not fully specify a reproducible Mastermind window for the actual move. Therefore `-4.1%` is retained as an **exchange-reported event-move observation**, not as our own event return.

More importantly, 5 February was also Equinor's **Capital Markets Update 2025**. The same release package included changes to free-cash-flow outlook, investment plans, production ambitions, renewables spending and capital distribution. The stock move cannot therefore be attributed to the quarterly surprise vector alone.

This event is excellent for testing information clocks and metric matching; it is a poor clean causal experiment for earnings surprise.

## 6. What this teaches the re-rating system

### "Beat" depends on which economic claim is being tested

The same event has:
- positive pre-tax surprise;
- positive adjusted-operating-after-tax surprise;
- negative adjusted-EPS surprise;
- negative production surprise;
- negative externally reported market move.

None of these observations cancels the others. They answer different questions.

A research synthesis should instead ask:
1. Which business drivers caused the deviations?
2. Which metric most closely maps to the forecast investors were using?
3. Which other information arrived at the same event?
4. Did the forecast for later periods change?
5. Did the valuation paid for those later forecasts change?

### Historical availability must be an explicit field

Proposed evidence states:
- `PRE_EVENT_TIMESTAMPED` — source/value independently observed before event;
- `ISSUER_PROCESS_SUPPORTED` — issuer documented the publication process but exact value timestamp not independently preserved;
- `ARCHIVAL_CONTEXT_ONLY` — current archive contains value but no proof of when that exact value was public;
- `POST_EVENT_ONLY` — value only observed after result;
- `UNAVAILABLE`.

Q4 2024 pre-tax/after-tax/production qualify for strong pre-event support because the 29 January article fixes the values before the event. Archived EPS does not get upgraded merely because it sits beside them in today's PDF.

### A historical event study needs an event-confound ledger

For each event, record same-day:
- earnings/result release;
- management guidance;
- capital-markets-day strategy;
- M&A;
- financing;
- policy/regulatory event;
- commodity shock;
- macro event;
- corporate action.

A price move is not an earnings-surprise response if several new value-bearing disclosures arrive together and the design does not separate them.

## 7. Proposed R5B product acceptance cases

1. Reject a consensus value first observed after the event as a pre-event expectation.
2. Preserve exact first-known source and timestamp separately from current archive retrieval time.
3. Current issuer archive does not prove historical byte identity.
4. Require metric-definition matching before computing surprise.
5. Adjusted net income cannot substitute for adjusted operating income after tax.
6. A mixed surprise vector cannot be collapsed into one unqualified beat/miss.
7. External event-move measures retain provider methodology and are not silently renamed Mastermind returns.
8. Implied move is magnitude, not expected direction.
9. Same-day Capital Markets Update creates an event-confound flag.
10. Event-confounded price moves cannot train a clean earnings-surprise rule without a declared treatment.
11. Contributor count and aggregation method travel with every consensus value.
12. When a third-party metric label conflicts with issuer definitions, preserve conflict and prefer issuer definition for issuer actual.
13. Archived EPS receives a weaker historical-availability grade than independently timestamped metrics when no separate timestamp is found.
14. No single-event case establishes predictive edge.
15. Historical event research cannot change ranking, entry, sizing or trading authority.
16. Later restatements must not overwrite the pre-event information set without bitemporal/version treatment.

## 8. Next historical case

R5B should now add a **cleaner ordinary-quarter case** without a simultaneous capital-markets update. Candidates are:
- Equinor Q1 2025, whose current historical archive records a January/April lineage and whose result was 30 April 2025;
- Equinor Q2 2025, if a pre-result first-known consensus artifact can be independently recovered;
- Fortum Q2 2026, once its source-labelled July view is independently tied to pre-release public availability.

The selected case must use a predeclared return convention and include benchmark/commodity controls before any return-attribution claim.

R6 remains the final owner-compatible product design, implementation sequence, rights/source mapping and real-path acceptance plan. Fable handoff remains `NOT_ISSUED`.
