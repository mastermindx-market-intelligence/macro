# Tiingo Forex — internal technical qualification checklist

**UNSENT. Do not dispatch the former licensing/product-use inquiry.**

## Current authority — 22 October 2026

The Chairman confirmed special licensing approval for the intended Forex R26 product use and directed the session to mark that complete, avoid a Tiingo licensing/product-use email, and continue the project. [Canonical correction: Macro #9996 comment 6331071428](https://github.com/mastermindx-market-intelligence/macro/pull/9996#issuecomment-6331071428).

**LICENSING_AND_PRODUCT_USE: COMPLETE — Chairman-attested special approval.** This is the internal authorization basis; no new provider reply is claimed. Public documentation and successful HTTP access are not used as substitutes for that attestation. No purchase, account change, credential transfer or outbound message has occurred.

This file is an internal checklist for the existing source owner. Technical support is considered only if an indispensable fact cannot be resolved from retained data, incumbent code and primary documentation. The preceding prepared request remains historical in Git; its licensing question is superseded.

## Existing evidence

The fixed nine-pair historical request cohort comprises EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, USDMXN, USDBRL and USDCNH. Eight 19–20 October minute responses retained 17,011 rows; USDBRL returned an exact verified empty response. A separate USDBRL top-of-book request was also empty and remains RAW_ONLY because no reviewed L1 top-of-book projector exists. These two requests do not establish global vendor non-support.

The 21 October 22:45 UTC native EURUSD `4hour` capture retained seven rows. Its exact raw digest and receipt remain unchanged. Offline comparison with the earlier minute capture tests four interval-label hypotheses. Capture times differ by more than nine hours; a mismatch cannot uniquely identify aggregation rules versus revision effects.

A separate bounded pair of EURUSD requests for the closed 21 October UTC day was collected once through `scripts.tiingo_ingest.collect` on 22 October. Captures were approximately 1.904 seconds apart: 1,440 minute rows and six native four-hour rows. Exact request dimensions, raw hashes, actual capture clocks and research reader outcomes are in `source_evidence/tiingo-eurusd-20261021-paired-*.json`. Original prices remain in the incumbent archive.

## Questions to resolve locally before any support escalation

| Topic | Evidence or implementable policy | Required qualification |
| --- | --- | --- |
| Observable and quote identity | Provider-reported historical OHLC can be named explicitly; it must not be called midpoint, trade or executable price without evidence. Literal pair naming remains base/quote. | Source/product owner must accept the intended observable and literal spot identity, including offshore CNH. Saved conditions must not silently change meaning. |
| Interval labels and anchors | Compare each native bar against minute windows under start/end and boundary-inclusion hypotheses; separate dense equality from sparse equality. | Date labels are evidence for a mapping in the inspected cohort, not a universal vendor contract. Preserve partial first buckets and missing edges. |
| Sparse data and closures | Conservatively withhold incomplete windows. Do not fill or carry forward absent minutes. | Explicitly limit supported coverage; full calendar/DST/holiday support must not be inferred from one dense day. |
| Closure and corrections | Consider a versioned local closed-as-captured policy with later changes retained as revisions, through the existing owner. | Do not claim vendor immutability or silently choose a correction winner. Validate boundary, duplicate and conflicting-revision cases. |
| Availability and freshness | Keep original response-observation time separate from vendor labels and durable availability. The archive stamps observed_at_utc before publication and retains the original clock for identical same-day responses; a future policy needs a separately verified, conservative post-publication/readback clock. | Unknown historical first publication remains unknown. Re-reading or deduplicating a receipt is not a new freshness observation. A recent historical response does not prove natural-boundary publication latency or live delivery. |
| Empty BRL response | Preserve the exact empty responses and the full requested cohort. | Do not omit BRL, use a reciprocal/futures substitute, or infer global non-support. A specific unresolved support question may remain if existing evidence cannot establish intended coverage. |

## Admission boundary

The reusable bridge remains `INSPECTION / RESEARCH_ONLY_VENDOR_SOURCE`. Its report never supplies eligible observations, a production feed, activation or evaluator-ready bar fields. The generic reader's false admission flags describe this technical boundary, not an unresolved licensing approval.

A prospective feed must eventually bind explicit pair/feed identity, literal price meaning, UTC interval/calendar, observation identity and revision, capture-based availability, expiry/freshness, and conservative gap/correction handling to the existing evaluator contract. A local policy is an explicit product/source decision requiring its own proof; it is not an excuse to relabel unresolved data as vendor-final.

The existing inactive-condition storage rejects activation. No evaluator, queue, collector schedule, notification or publication plane is created by this checklist.

## Primary references already inspected

- [Tiingo REST Forex documentation](https://www.tiingo.com/documentation/forex): historical OHLC and separately described top-of-book fields.
- [Forex product](https://www.tiingo.com/products/forex-api): historical minute coverage and aggregated bid/ask product.
- [Symbology](https://www.tiingo.com/documentation/appendix/symbology): base followed by quote currency.
- `source_evidence/tiingo-documentation-request-syntax.json`: exact public documentation asset/excerpt provenance for `4hour`, minimum minute frequency and date-filter syntax.

No provider answer is fabricated, no external message has been sent, and licensing/product use must not be reopened.

## Post-boundary evidence added at 04:41 UTC

One bounded follow-up through the incumbent ingestion owner produced a dense 240-minute EURUSD 00:00–04:00 candidate interval whose native OHLC exactly matches the raw-Decimal minute aggregate. The following 04:00–08:00 interval remains partial at 42 minutes, with a differing close across response clocks 1.542572 seconds apart. Original 02:49 responses are preserved; their last open minute and native open interval changed. See SOURCE_QUALIFICATION.md and `source_evidence/tiingo-eurusd-post-boundary-20261022-qualification.json`.

The factual post-boundary observation is now available without provider contact. First publication time, low-latency availability and closed-bar immutability are not established by this one 41-minute-late sample. Continue the documented prospective policy through existing source/runtime owners; no licensing inquiry or product-use approval remains outstanding.
