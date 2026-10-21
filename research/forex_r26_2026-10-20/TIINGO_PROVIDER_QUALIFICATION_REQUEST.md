# Tiingo Forex — concrete provider qualification request

Prepared 21 October 2026 for the existing source/rights owner. **Not sent.** This packet asks for the remaining contract facts needed by the existing Forex R26 source owner; it does not grant identity, feed, rights or finality admission.

## Context to include with the request

We are qualifying literal currency-pair price-close conditions at a UTC 4H interval for EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, USDMXN, USDBRL and USDCNH.

We used the existing licensed-account ingestion route. Preserve the account owner's plan attestation; this request does not presume that another purchase is necessary. No API token, key fingerprint, account identity or raw price rows are included.

The exact historical request pattern was:

```text
/tiingo/fx/{lowercase_pair}/prices?startDate=2026-10-19&endDate=2026-10-20&resampleFreq=1min
```

Use the exact escaped request strings in `source_evidence/tiingo-nine-pair-plan.json` when comparing server logs; the readable pattern above is not a byte-identical request identity.

Nine requests succeeded at HTTP level. Eight produced 17,011 total rows; USDBRL produced an empty array. A separately planned one-request `/tiingo/fx/usdbrl/top` probe also returned an empty array. Both empty responses were verified against retained raw receipts; neither establishes global non-support. The top response remains RAW_ONLY because the incumbent materializer has no reviewed top-of-book projector.

For the nonempty responses the first vendor timestamps on 19 October ranged from 11:30 to 13:15 UTC, despite the requested start date being 19 October. The last timestamps were 20 October 23:59 UTC, except USDMXN at 23:56. Observed steps between unique timestamps ranged up to 180–480 seconds by pair. These facts are diagnostic observations; we have not classified every omitted minute as data loss.

Full per-pair counts, request identities, capture clocks and raw hashes are in `source_evidence/tiingo-nine-pair-receipts.json`. Original prices stay in the existing archive.

## Questions requiring an authoritative answer

| Contract question | Concrete information requested | Why it changes implementation |
| --- | --- | --- |
| Historical OHLC basis | Are `open/high/low/close` built from bid, ask, midpoint, transaction prints, or another defined series? If midpoint, is it computed from synchronous bid/ask observations, and what filtering applies? Is the rule identical for all nine requested pairs? | Establish the exact threshold meaning. We cannot infer the historical basis from the separately documented top-of-book mid field. |
| Timestamp and request boundaries | Does each historical `date` label the start, end or another point of its interval? What timezone and inclusion rules apply to startDate/endDate? What explains the observed midday first rows for the exact receipts? | Map vendor clocks to interval boundaries without shifting observations or treating request dates as publication times. |
| Sparse minutes and completeness | Is a minute omitted when no accepted quote changes, when there are no valid input quotes, or for another reason? Is any close carried forward? How can a consumer distinguish a legitimate omitted interval from an incomplete response? Are row/window limits or pagination involved? | Decide whether a 4H bucket is complete. An elapsed wall clock or a row count alone is insufficient. |
| Four-hour anchoring | Is native 4H resampling supported, with which exact resampleFreq value? What are the bucket anchors, boundary inclusion rules, and timezone/DST behavior? Can buckets be bound to 00:00, 04:00, 08:00, 12:00, 16:00 and 20:00 UTC without a different price construction? | Use one documented UTC 4H convention and avoid conflicting vendor/local aggregation semantics. |
| Market closures and exceptional sessions | What are the documented weekly open/close rules, timezone names, DST handling and holiday/exception rules? Are partial boundary buckets emitted, omitted or labeled? | Avoid counting closures as missing data or treating a partial bucket as a complete observation. |
| Finality and corrections | When is a historical bar considered complete? Can OHLC change after it first appears or after the interval closes? What correction window, revision indicator or supported retrieval policy distinguishes replacement values? Is a finalized status available? | Define a defensible finalization and correction-selection policy. We will not infer finality from the passage of time. |
| Availability and freshness | Does the API expose original first-publication/availability time or only the vendor interval label/current response? What latency/delay applies to this account/product? Is there a supported way to detect stale successful responses? | Preserve capture time separately, avoid invented historical availability, and determine prospective freshness behavior. |
| USDBRL and offshore CNH identity | Is literal USDBRL supported on these two documented request shapes and this account entitlement? What does an empty array mean? Confirm that USDCNH denotes the intended offshore RMB spot pair and whether any requested pair is an indicative/derived/non-spot series. | Keep the requested cohort honest. No BRL omission, futures substitution, reciprocal fallback or CNH/CNY substitution is assumed. |
| Existing product-use rights | Ask the existing rights owner to map the already-attested account entitlement to the intended in-product display, derived 4H conditions and notification use, using the applicable agreement. | Resolve the product-use mapping without treating public marketing, successful access or a proposed new purchase as the account's contract. |

The requested response is a link to versioned documentation, an authoritative provider answer, or an explicit statement that a property is not offered. Each answer should identify the endpoint/product, applicable pairs, effective date and any exception. A broad statement that historical data is available does not answer clock, correction or completeness questions.

## Acceptance after an answer

The existing source owner will bind each accepted answer to the retained receipts and the existing identity/rights owners. Implement only the documented mapping, keep unresolved fields unknown, and add discriminating boundary/correction cases against that mapping. There is no requirement to manufacture a retrospective availability timestamp if the vendor does not provide one.

A future qualified feed must still pass the existing evaluator contract: literal pair and price basis, qualified final 4H interval, explicit UTC boundary and calendar, observation identity/revision, availability/freshness, and gap/correction handling. A dense minute series or a successful provider response does not itself admit a live feed.

The current bridge remains a diagnostic surface: all 17,011 candidates stay outside `eligible_observations`; the verified empty USDBRL raw capture remains separate from a missing materialized artifact or failed reader.

## Primary references already checked

- [REST Forex documentation](https://www.tiingo.com/documentation/forex): historical OHLC and top-of-book fields; historical date description does not settle the required boundary/publication contract.
- [Forex product](https://www.tiingo.com/products/forex-api): historical minute coverage and aggregated bid/ask product descriptions.
- [Symbology](https://www.tiingo.com/documentation/appendix/symbology): base currency followed by quote currency.
- [Provider Forex API overview](https://www.tiingo.com/blog/forex-api/): distinguishes quotes from interval bars and notes that FX daily-close conventions require a choice; it does not settle the historical 4H, correction or availability contract above.

No message has been sent to the provider. This is a prepared packet for the existing source owner, not a provider response.
