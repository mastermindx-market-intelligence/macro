# Factor Atlas S2-P3 — Day-clustered quote/BVC disagreement study

**Status: native, synthetic-only methodology witness. NO market-data admission, measured real-world accuracy, statistical confidence or customer/trading authority.** The executable research-only function is `prototype/quote_study.py::assess_quote_study`. It composes the existing `quote_calibration.MinuteComparison` on *caller-declared* expected security-minute slots. It creates no feed, time-series store, experiment registry, queue, membership source, quote signer, service or publisher.

## Why a day-cluster is necessary

One-minute BVC and NBBO estimates are serially correlated within a stock/day and may share the same price/volume/market conditions. Treating each minute as an independent experiment makes accuracy and significance appear stronger than the data support. The diagnostic therefore computes the absolute disagreement **only on quote/BVC comparator minutes that satisfied its prior declared coverage/matching policy**, then produces one mean per distinct session. It requires at least three separate sessions (research minimum, configurable up to 252) before revealing the equal-weight daily result. A day with hundreds of observations receives the same weight as a day with one eligible observation. This is **not a defensible statistical accuracy study** until the incumbent source owner and quantitative review supply a stratified, point-in-time, outcome-independent population and a sufficient number of independent day clusters.

For day d with (n_d) comparable security-minutes and per-minute *proxy discrepancy* (e_{i,d} = |p^{BVC}_{i,d} - p^{quote}_{i,d}|), the implemented statistic is:

    m_d = sum(e_{i,d}) / n_d             for n_d > 0
    M = sum(m_d) / D                    for D distinct comparable days
    LOO_d = sum(m_j for j != d)/(D-1)
    stability_range = [min(LOO_d), max(LOO_d)]

The leave-one-day-out range measures **sensitivity to omitting one sampled session**. It is not a bootstrap interval, confidence interval, independent true label, data snooping correction, forecast validation or evidence of institutional fund trading. Inferences beyond description require held-out exchange-sign labels where legally available, day-cluster uncertainty methods, purged/embargoed chronological splits, execution-price controls and separate market/outcome owners.

## Inputs and strict denominators

The existing source/calendar/membership owner supplies a finite list of exact UTC `ExpectedSlot(security_id,session_id,phase,start,end)` rows. Days and phases are checked against ET event clocks, but no exchange holiday, halt, IPO/listing map or source availability is invented. A missing expected slot remains **missing**, not an explicit zero-dollar print. No input outside the expected grid is admitted; duplicate expected or observed slots and after-cutoff intervals fail closed.

A `TaggedComparison` wraps the existing `MinuteComparison` with its purported quote-age/calibration policy ID, population ID and observation mode. All observed rows must have an identical declared policy, population and mode for one report. These strings are **unverified**; they do not prove that the tape or bars are authentic, rights-bound, as-observed, revision-final or entitlement-qualified. The comparison must match exact security/date/phase/minute, authority all FALSE, and its `knowledge_class` must remain `ESTIMATOR_COMPARISON_NOT_TAPE_TRUTH`.

For each observed row, the reported **eligible** quote-reference gross must reconcile `classified_gross + unknown_gross` and remain finite and nonnegative. Unknown eligible gross stays in the denominator. Quote-classified notional share is summed over **observed eligible prints only**; it is not source file coverage. Only `COMPARABLE_PROXY_DIAGNOSTIC` rows may provide `absolute_ratio_disagreement`, and the reported ratio must exactly equal the absolute difference of its two dimensionless signed-pressure ratios, each between -1 and +1. Insufficient quote coverage, gross/volume mismatch, unavailable BVC direction and no eligible prints count as distinct explicit statuses with NULL comparison gaps.

The report discloses: expected/observed/missing minute counts; comparable versus not-comparable counts; per-day comparable and scheduled denominators; status distribution; observed eligible, classified and unsigned notional; quoted classification share; distinct observed session clusters; equal-day mean if sufficient; leave-one-day-out min/max; and a deterministic input fingerprint. Every output uses `source_receipts_verified=false`, `rights_verified=false`, `market_pilot_admitted=false`, `customer_publishable=false`, `is_statistical_accuracy_study=false`, `is_confidence_interval=false` and all rank/alert/size/trade/publish authority FALSE. A valid source-like label cannot change those fields.

## Synthetic verification and actual gate

The bounded `test_quote_study.py` suite uses **only synthetic** BVC/quote results and fabricated expected day slots to check: three-day and low-day withholding, densely sampled-day overweight resistance, day-order invariance, missing slot counting, eligible versus unknown notional, non-comparable states, duplicate slots, source/cutoff timing, competing policy/cohort/mode refusal, signed-gap arithmetic, forged authority and nonfinite/negative values. It makes **no empirical conclusion** about real hedge funds or factor returns.

Actual S2-P3 admission still requires the existing source owners to deliver an entitled retained minute/trade/quote sample, corrected sale-condition/volume rules, quote timestamps and reporting/transaction clocks, immutable source/reader receipts, broad enough quote notional coverage and a lawful benchmark label. Existing corporate action, calendar, listing, availability and release gates remain. A later independent scientific review may preregister and expand the allowed cluster count, quote-age sensitivities and market/regime strata—but must not tune those policies after seeing a target equity return or infer independent fund flows. The candidate is not a production research platform and does not replace Options Superintelligence or Market Structure Core.
