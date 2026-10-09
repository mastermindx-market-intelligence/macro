# Macro input qualification: source-history and availability addendum

RESEARCH ONLY. Operation `market-topology-research-20260923-astra-001`, draft PR #7812. Addendum to `CONTEXT_CONDITIONED_TRIAL_V1.md` at `f90c1a99d2e874f2f4793cdb78034fd7c8ea1554`, before execution of that study. The chosen series and model have not changed. No source data were downloaded, refreshed or republished by this inspection.

## 1. High-yield spread: a newly verified constraint

Official FRED metadata for BAMLH0A0HYM2 says that, starting April 2026, this feed includes only three years of observations and directs longer-history users to the source. The notes restrict third-party redistribution without ICE approval and identify internal use as the supplied scope. Do not assume a fresh FRED pull supports the proposed longer training history or the user-facing product. An existing licensed archive may differ; its history and rights must be verified rather than assumed absent.

Source checked September 23, 2026: https://fred.stlouisfed.org/series/BAMLH0A0HYM2 . No historical observations or proprietary index values are reproduced here.

Consequences for this research are bounded: the C interaction using the named high-yield spread remains conditional on a qualified existing history with appropriate rights. The original stock-only P/PT trial has no new requirement. No silently substituted credit series, third-party mirror, archive reconstruction to evade access restrictions, or purchase authorization is introduced. A different economic series would be a dated protocol amendment with a distinct meaning, not an invisible fallback.

## 2. Real yields and the observation clock

FRED identifies DFII10 as the daily ten-year inflation-indexed Treasury constant-maturity yield, sourced from the Board of Governors' H.15 release. This is the intended economic series, not a corporate credit yield, nominal ten-year yield or a rate-shock identification. Source: https://fred.stlouisfed.org/series/DFII10 .

The official H.15 page states a daily 4:15 p.m. publication schedule on business days, excluding holidays/closures. The inspected release dated September 23 displays observations through September 22. That example is evidence that observation date and publication date must not be conflated, not a universal reconstructed timestamp for every historical value. Source: https://www.federalreserve.gov/releases/h15/ .

The existing source/calendar owner must provide availability relative to the research decision cutoff, including local-time and holiday interpretation. A source observation attributed to day t cannot enter a decision on day t merely because the numeric join key equals t. A genuinely faster quote feed would need its own source and timing evidence; no alternate feed was assumed or acquired here.

## 3. Vintage date is not a clock-time or served-system receipt

ALFRED describes vintages as values available at historical dates and distinguishes observation dates from the real-time interval during which a version was current. Its initial-release format reports initial release dates. A later-known revision-end date is not information that a past forecaster could have used. Source: https://alfred.stlouisfed.org/help/downloaddata .

Date-level vintage correctness does not by itself prove availability before a particular intraday decision, and it does not establish when Mastermind ingested and served a value. Keep source-as-of research and served-system replay separate, as tested in `MEASUREMENT_CONTRACT_V2.md`. Unknown publication/ingestion times remain unknown. A current latest-vintage series cannot silently become a real-time historical feature because its date axis looks historical.

## 4. Current disposition

This is a verified input constraint, not evidence that existing Macro collectors are broken or that their own archive has no history. No current market forecast, causal rate interpretation, trade, deployment, worker dispatch or new data authority follows. The enriched context comparison is still unexecuted; the existing Data OS/reference and source owners retain qualification and licensing responsibilities. Preserve these exact requirements in the eventual build package so Fable does not have to rediscover them.
