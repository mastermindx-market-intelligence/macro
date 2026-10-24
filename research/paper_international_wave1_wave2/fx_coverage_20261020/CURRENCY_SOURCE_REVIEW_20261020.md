# Currency source and contract review — 20 October 2026

## Decision

The bounded native C3 review accepted the final currency contract and the retained-response qualification path. No remaining semantic defect was identified in those inspected seams. This is source review and local implementation evidence; it does not establish scheduled ingestion, canonical-store availability, hosted CI or production adoption.

Reviewer: `/root/intl_fx_coverage_judgment`. Root implemented and integrated the changes. The reviewer made no edits, reacquired no data and did not claim to run the tests. An earlier unsuccessful review attempt had no source result and conveyed no approval; only the later completed reads support this decision.

## Findings and corrections

1. **Captured partial bars could mature on replay.** The original producer and consumer excluded only the evaluation day. An October 20 intraday quote could therefore become eligible on October 21 without a new response. Root reproduced all three reported cases before correction: the changed replay endpoint, a rehashed endpoint on the capture day, and an endpoint later than its capture receipt. The producer and consumer now both require observations before the earlier of the evaluation day and recorded UTC capture day. Freshness remains measured against the caller's evaluation day.
2. **The engine and assessment used different default day conventions.** The engine already used UTC; the assessment used local date.today(). The assessment now defaults to UTC as well. An explicit-clock regression verifies the default.
3. **Root's malformed-data tests found two exceptions.** An oversized serialized return and a timezone conversion below the minimum representable date raised OverflowError. Both now degrade to an unavailable reading.

The original failed test logs and pre-correction source snapshot are retained. The final selected suite reports **298 passed**, with two existing pytest cleanup warnings. The new currency module contributes 80 cases; the legacy component-evidence suite contributes ten. The final CSS-only typography adjustment is covered by the subsequent final browser capture, rather than a claim that it changed the financial calculations.

## Source chain reviewed

- `lib/intl_currency_observation.py`: instrument registry, source-kind distinction, exact reciprocal/direct currency conversion, month-end clamping, actual endpoint selection, inclusive seven-day anchor and fourteen-day freshness limits, captured-day exclusion, duplicate conflicts, serialized digest and arithmetic verification.
- `engine/intl_run.py`: a separate currency observation at the existing store assembly boundary; the legacy strength scalar and regime history remain separate.
- `lib/intl_country_assessment.py`: independent FX and equity clocks, the currency consumer and consistent UTC default.
- `qualify_retained_fx.py`: retained response byte length/SHA-256, exact requested/final URL, instrument/currency/quote orientation, daily granularity, timezone normalization, no timestamp after capture, independently selected endpoints and 40-digit Decimal arithmetic.
- `source_qualification.json`: all seven countries pass with the original response identities retained.

Each response contains 133 timestamp rows, 132 valid quotes and one missing quote. One valid quote per response is excluded at the capture-day boundary. The selected window is **17 July → 19 October 2026**; the calendar target is 19 July, so the actual start precedes it by two days.

| Currency | USD-value change | Quote convention |
|---|---:|---|
| JPY | +2.90% | JPY per USD; exact reciprocal return |
| KRW | +10.91% | KRW per USD; exact reciprocal return |
| TWD | −0.38% | TWD per USD; exact reciprocal return |
| INR | +1.76% | INR per USD; exact reciprocal return |
| AUD | −0.39% | USD per AUD |
| GBP | −1.06% | USD per GBP |
| EUR | −1.92% | USD per EUR |

These values describe the retained October 20 acquisition, not prices after that snapshot. Exact endpoints, unrounded calculations, source URLs, original bytes and acquisition receipts are in the qualification report and its bound artifacts.

## Boundaries that remain explicit

- Configured-store frames do not carry retrieval receipts. Their receipt fields remain null; a source reference, file modification time or computation time does not become a retrieval clock.
- The stored-record self-digest is an integrity check, not external authentication. The qualification script separately binds the endpoint calculation to retained provider response bytes and the complete normalized series.
- Same-day exclusion for configured-store quotes is conservative selection from dated daily quotes. It is not proof that the provider finalized an official close.
- The legacy 63-observation strength feature is unchanged. The country display uses a separate three-calendar-month USD-value return.
- The isolated checkout had no seven FX parquet files when inspected. That observation says nothing about their availability in production. No canonical store was populated by the research qualifier.
- The original publisher action remains uncertain. No commit, ref advancement, push retry, alternate publication, merge, deployment or updater restart was performed.
