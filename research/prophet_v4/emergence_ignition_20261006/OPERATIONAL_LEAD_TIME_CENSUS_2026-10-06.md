# Operational lead-time census

**Disposition:** material publication latency is observed; recoverable trading alpha is not measured. Research only. Historical information through 2026-10-06 remains discovery evidence.

## Answer

The September NVDA case contains **32 hours, 48 minutes, 32 seconds** between the inherited watchlist alert timestamp and first Git preservation of the formal plan. That interval is not a clean-source-to-plan delay and is not a claim about when a customer saw the plan. The alert used stale/mixed-vintage source information; the plan validator correctly refused it.

A more precise source receipt now separates the interval:

| Preserved event | UTC timestamp | What it proves |
| --- | --- | --- |
| Watchlist alert generated | 2026-09-25 09:02:33 | A `buy_zone_enter` alert was generated; inherited exact receipt from #8495 |
| Alert first preserved in Git | 2026-09-25 09:20:03 | Repository preservation, 17m 30s after generation |
| Clean-source observation clock in the accepted board snapshot | 2026-09-26 16:36:54.485866 | A clean source witness exists by this timestamp; earliest source availability is not independently established |
| Formal origination receipt | 2026-09-26 17:49:36.020384 | `NVDA-BULL-20260917` was built with the bound source/plan hashes |
| Plan first preserved in Git | 2026-09-26 17:51:05 | Repository publication proxy, 1m 28.979616s after the origination receipt |
| First production reader-visible plan | **Unknown** | No exact historical reader receipt was obtained in this census |
| First current canonical B4-open state | **Unknown** | A legacy board `buy_now`/`partial` state is not a substitute for a current B4 receipt |
| Actual fill | **Unknown** | No execution receipt is available; no fill is inferred |

The alert-to-clean-source-witness interval is **31h 34m 21.485866s**. The preserved clean-source-witness-to-origination interval is **1h 12m 41.534518s**. These are different operational quantities. In particular, the first interval includes an unqualified stale alert, so it cannot be called avoidable delay after lawful admission.

Sources: [parent forensic and source audit](https://github.com/mastermindx-market-intelligence/macro/pull/8495); [bound origination receipt](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/data/prophet/origination_receipts/36241094249-1-716c0da79512aceb.json); commits [`a374fd966466`](https://github.com/mastermindx-market-intelligence/macro/commit/a374fd966466d342154e5147efec48281f77b501) and [`74e8f45060e8`](https://github.com/mastermindx-market-intelligence/macro/commit/74e8f45060e815a2cb7c515ae09f258919ab9da2). Deterministic values and source digests are in `results/operational_lead_time.json` and `results/operational_source_manifest.json`.

## A system-wide refusal, followed by incomplete recovery

The inherited failure checkpoint was re-read at its exact commit; the NVDA forensic was not re-created from scratch.

| Intake at preserved checkpoint | Sep 25 stale/mixed source | Sep 26 clean aggregate source |
| --- | ---: | ---: |
| Admitted candidates | 41 | 39 |
| Eligible after duplicate/open-plan skips | 15 | 31 |
| Plan validation failures | 15 | 9 |
| Plans originated | 0 | 22 |

The Sep 25 source was `source_asof=2026-09-21`, `source_board_asof=2026-09-23`, delayed and mixed-vintage. The Sep 26 source was through Sep 25 and not delayed/mixed. **A clean aggregate source did not make every individual plan valid:** nine of 31 still failed validation. The successful 22-plan batch must not be reported as universal recovery or as 22 accepted trades. Exact intake fields are retained in the result JSON.

## Broader receipt census

At analytical pin `731a23fb64b9f6f1a321c77618f927f1a58d2d41`, the committed origination-receipt directory contains:

- **27 receipts**, including **2 explicitly labelled backfill receipts**;
- **407 unique originated plan IDs**, representing **394 tickers**;
- receipt timestamps from Aug 9 through Oct 6;
- **25 forward receipts** with clean aggregate source flags;
- only **6/25 forward receipts** with both a precise source-observed clock and precise origination clock.

For those six timed forward batches, source-observed-to-origination latency ranges from **42.79 to 109.10 minutes**, with a **median of 81.04 minutes**. There are no negative intervals. This is a selected census of successful originations, not a service-level distribution for every candidate or failed run. It is insufficient for a p95/p99 claim.

| Receipt date (UTC) | Source session | Originated plans | Source-observed → origination |
| --- | --- | ---: | ---: |
| Sep 26 | Sep 25 | 22 | 72.69 min |
| Sep 27 | Sep 25 | 1 | 63.91 min |
| Oct 1 | Sep 30 | 15 | 89.38 min |
| Oct 3 | Oct 2 | 29 | 42.79 min |
| Oct 4 | Oct 2 | 1 | 109.10 min |
| Oct 6 | Oct 5 | 26 | 99.07 min |

Rows, missing clocks, selected plan origins and immutable source identities are in the accompanying CSV/JSON files. The date of a receipt is not a market session, so weekend receipts are not silently turned into extra trading sessions.

## Publication can consume the available price window

The parent final plan has an accumulation range of $220.50–$225.10 and a no-chase ceiling of $226.90. A bounded check of the already-retained daily price source found:

- first regular-session open after the Saturday plan commit: **Sep 28, $229.75**;
- Sep 28 low: **$228.039993**;
- minimum low across the six retained sessions Sep 28–Oct 5: **$227.029999** on Sep 29;
- **zero of those six daily bars** reached either the no-chase ceiling or the accumulation range in that retained price coordinate.

This confirms the parent's limited conclusion: the final plan does not establish a post-publication regular-session opportunity inside its fixed levels. It does not prove an actual fill, an extended-hours opportunity, reader delivery, basis admission for live action, or realized P&L. The historical price source is a final-vintage stored panel; price agreement is not substituted for canonical adjustment provenance.

Price source: `data/baskets/ohlcv/NVDA.parquet` at the analytical pin; Git blob `0e95a8c062c22f663fe7a80c9a76188bb444709e`, SHA-256 `e28878d447358938ef4280a807dd6ea9c23e176943f2e70eedf00e9fc82def58`. The compact price-context result is supplied with the ignition results.

## Golden and negative relations must remain episode-specific

The selected receipt census includes FORM and PWR plans built Aug 18, before their September emergence observations. They cannot count as successful downstream publication from those later observations. The ISRG selected receipt is an explicit backfill for a July formation. A same-ticker plan is not an exact emergence-to-plan relation.

Likewise, the weaker August NVDA plan remains a required negative case. Parent #8495 established that it expired/closed Sep 21; it did not block September origination. Neither the September winner nor this older plan can replace missing formal episode-to-plan joins. Keep event tier T1/T2 separate from management target T1/T2.

The ignition clock supplement separately documents original non-open states, delayed board preservation and price-basis disagreements for TSLA, ADM, PRIM, INTC and ISRG. Those are operational negative controls, not reasons to remove inconvenient cases from the primary historical comparison.

## What A2 and the existing publication owners should build

1. Keep the exact accepted source bundle, board revision and decision cut bound through signal, B4, alert, origination, publication and reader observation. An alert wall clock must never replace the source clock.
2. Extend the existing settlement/first-fresh receipt path to retain the candidate/plan relation and accepted artifact digest. The incumbent `scripts/freshness_sentinel.py` already owns reader observation and `sentinel.first_fresh/v1`; no second service or clock algorithm is needed.
3. Measure source-complete → board-ready → plan-built → artifact-published → reader-hash-observed separately. The six precise batches show a meaningful build/publication interval after the source witness; instrument that interval before prescribing performance changes.
4. Preserve stale observations in B03 as research context while current action remains unavailable. Do not fix the latency by relaxing plan provenance or keeping stale buy-style alerts.
5. Correct management missing-bar replay through the existing owner and correction lineage. The parent's catch-up-date defect is a historical-path accounting problem; repairing it must not backdate what an operator knew or claim a missed historical fill.

## Exact remaining measurement blocker

We cannot estimate the fraction of predictive edge lost to infrastructure because historical **first valid B4 action**, **reader-visible matching bytes**, and **same-basis executable quote/bar** are not jointly recorded for these observations. Six successful batches do not identify a population latency distribution. The next useful step is owner-native clock accrual with these joins, followed by an ordinary-refresh proof; another broad NVDA narrative or an inferred earlier fill would not resolve this blocker.

## Reproduce

```bash
python research/prophet_v4/emergence_ignition_20261006/scripts/lead_time_census.py \
  --repo /path/to/macro \
  --ref 731a23fb64b9f6f1a321c77618f927f1a58d2d41 \
  --output /path/to/research-output/operational
```

The input repository must contain the pinned current and inherited checkpoint objects. The script uses only Git-object reads and Python's standard library; it refuses production output directories. The inherited alert timestamp is explicitly identified in the script, and source reads/digests are disclosed. No collector, production engine or live state is invoked.
