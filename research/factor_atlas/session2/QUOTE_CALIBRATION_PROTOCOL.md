# Factor Atlas S2-P3 — Same-minute BVC / quote-reference comparison

**Research-only / market study NOT_ADMITTED / no source authority / no economic or institutional-flow claim.** This specification applies to `prototype/quote_calibration.py` and its synthetic-only tests.

## Measured objects, not interchangeable truths

- BVC `PressurePoint` estimates buyer/seller fractions from one-minute prices and turnover using its registered versioned mathematical profile. Its net numerator is signed **proxy** dollars on the source bar's stated price/volume basis.
- Quote-reference `TapeResult` estimates aggressor side from past valid NBBO and eligible prints. The reference itself has error: SIP sequencing, stale quotes, locked/crossed markets, midpoint ties, off-exchange reporting and excluded corrections. It is **not an exchange aggressor flag**.
- Actual true aggressor labels, ETF primary-market creation/redemption, fund ownership, institutional holders and future returns are separate evidence classes. Nothing in this comparator identifies them.

## Exact bounded join

For one supplied security-minute, compare `PressurePoint.bar` on the exact half-open UTC interval `[start,end)` with `TapeDetail.trade_event_ns` satisfying that same security, ET session date, session phase, and **exact monetary basis version**. The underlying quote tape and BVC record must have the same declared historical observation mode.

For `as_observed`, require the BVC bar's closure and source availability by the explicit evaluation cutoff. Every matching quote-referenced trade must also have a genuine actual first-seen timestamp by that cutoff. Later/unrelated trades do not enter the target numerator or its input digest. For `corrected_history`, a reconstructed decision is never re-labeled as a historically available one.

The function rejects forged/contradictory source-derived buy/sell/unknown/excluded totals and all positive authority flags. A reference stream's source labels or content digest remain evidence to be independently authenticated by its existing source owner, not permission. No consumer, ingestion or revision owner is created.

## Separate denominators and equations

For eligible matched prints, let `B,S,U` be the quote-inferred buyer, seller and unsigned **eligible** print notional. Excluded and unresolved/canceled prints are not in this denominator. Then:

    eligible_tape = B + S + U
    classified_tape = B + S
    quote_coverage = classified_tape / eligible_tape
    quote_covered_pressure = (B - S) / classified_tape
    quote_full_observed_net_bounds = [B - S - U, B - S + U]

BVC's signed-dollar ratio is `bvc_net / bvc_gross` only if the BVC direction is usable and gross is nonzero. The comparative absolute ratio gap is:

    abs_ratio_disagreement =
        abs((bvc_net / bvc_gross) - ((B-S)/(B+S)))

This is a **proxy/reference disagreement**, not per-trade classification accuracy or realized forecast error. The quote-covered subset may be selected nonrandomly, so this metric is computed only when that subset represents at least 90% of eligible print notional (research default, not empirical authority).

Also emit `relative_gross_gap = abs(bvc_gross - eligible_tape) / max(bvc_gross, eligible_tape)`, with a research-default 5% tolerance. This is an **obvious-incompatibility diagnostic**, never sufficient proof that a close×volume aggregate and an exact-print tape represent the same transaction universe. Quote classification coverage and gross-data coverage are different measures. Do not equate a numeric close-notional approximation with raw consolidated eligible-print notional.

## Mandatory bar/print condition warning

Massive's published stock aggregate rules use **trade-specific sale conditions**: a transaction may contribute volume while not updating open, high, low or close. Consolidated CTA and UTP update rules differ by condition, and the extended-hours policy has further differences. Therefore an independent print eligibility bool and close×volume proximity do **not** by themselves certify that the print sample reconstructs the bar's recorded volume or price basis. The incumbent source owner must verify `updates_volume`, `updates_open_close` and any source revision/late correction against the actual condition map before treating this comparison as a real same-population experiment.

Primary: https://www.massive.com/blog/understanding-trade-eligibility ; https://massive.com/knowledge-base/article/why-are-there-missing-aggregates-in-massives-data ; https://www.massive.com/docs/rest/stocks/aggregates/custom-bars .

Massive's September 22, 2026 historical Tape B metadata correction also means the reported tape identifier for certain Tape B securities can be wrong in pre-September-21 historical records. Do not segment a pilot's historical SPY/IWM population using that unqualified raw tape label. Preserve the vendor vintage/identifier correction through existing source owners; no independent data repair is authorized here. Source: https://www.massive.com/changelog .

## Explicit outcomes

- `COMPARABLE_PROXY_DIAGNOSTIC`: sample meets registered numeric thresholds **but remains unqualified market research**, not true exchange-side accuracy.
- `QUOTE_COVERAGE_INSUFFICIENT`: quote-signed subset fails the fraction floor; disagreement null.
- `GROSS_NOTIONAL_MISMATCH`: reference and aggregate gross diverge beyond registered proxy-tolerance; disagreement null.
- `BVC_DIRECTION_UNAVAILABLE`: first bar, neutral warmup or invalid BVC direction; disagreement null.
- `NO_ELIGIBLE_TAPE`: no relevant valid-eligible print within the exact minute; not measured zero.
- Contract mismatch/late source/positive authority/forged accounting: raise and withhold.

The raw BVC and quote ratios can still be displayed internally as **provenance-carrying sensitivity diagnostics**, not traded, scored or promoted. `is_statistical_confidence_interval=false`: the quote unknown-dollar interval is an accounting bound on the observed sample, not a sampling interval or probability distribution.

## Implemented synthetic evidence and next owner action

TDD exposed initial missing implementation, mismatched test fixture identity, an insufficient derived-ratio string length, lost source monetary basis in quote records, and a false future-dependent input digest. Each was corrected on the dedicated research carrier; preceding source and denial boundaries were preserved. The combined prototype suite passes **184 controlled-fixture tests**, including comparison, gross coverage, valuation, quote partials, exact basis refusal, source cutoff, future-prefix isolation and non-authority. This tests deterministic software, not market classification accuracy, economic value or a production data source.

Next licensed-data proof remains **S2-P1**, owned by the incumbent source/basis/calendar/revision/rights teams. Do not run S2-P2 or customer publication unless an exact AAPL/MSFT/NVDA + SPY one-minute input cohort is admitted with actual source/reader receipt clocks and revision-correct condition mapping. If it cannot be qualified, preserve `NOT_ADMITTED` rather than inventing a backtest or buying a new feed.
