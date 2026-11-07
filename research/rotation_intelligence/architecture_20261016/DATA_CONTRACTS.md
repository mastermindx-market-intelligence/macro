# Data and consumer contracts for rotation research

Date: 2026-10-16. Status: design candidate, not an implemented schema or new data service. Current source: Macro `4ae7f2ac4c58e6e93945a6f09313bcaadba5709e`. No runtime data or market-outcome dataset was opened by this package.

## 1. Source admission is separate from a useful-looking feature

An observation is eligible for a study only when the existing source owner supports that purpose, population, time range and return basis. A public webpage, an installed collector, a file on disk or a current subscription claim does not establish historical point-in-time availability or permission to redistribute/model every field. Conversely, a missing registry entry is not a reason to invent a human approver: resolve the actual source contract through its existing interface.

These are proposed fields to carry through incumbent snapshot/feature interfaces, not a new standalone registry:

| Contract element | Required meaning |
|---|---|
| source reference and method version | Exact owner artifact, schema, revision/digest and extraction method |
| economic observation time | Time/period the value describes; may be a quarter rather than a session |
| first public availability | When an eligible observer could first know it, with timezone and uncertainty |
| actual capture/ingest time | When this system acquired it; distinct from first public availability |
| revision/vintage | Which version was available at the decision cutoff; corrections are not silently backdated |
| cohort and membership version | Exact population and membership/weight rules known at that time |
| units and basis | Currency, price/total return, fraction/percentage point, flow stock versus change |
| source-use boundary | Observed permissions and allowed research/product uses; not inferred from another field |
| missingness/coverage | Which expected inputs are absent, stale, invalid, estimated or unsupported |
| feature lineage | Input references, transformations, fit interval and parameters; no hidden full-sample fit |

For a decision cutoff t, use only values whose relevant availability is at or before t. A later file containing an old observation is not automatically an old information set. Preserve uncertain release windows instead of inventing exact seconds.

## 2. The as-known join

A join must respect two timelines: when a fact applies and when it became known. For memberships this means effective inclusion/removal and announcement/availability. For macro it means reference period and vintage release. For holdings it means portfolio date and filing/publication date.

A proposed research read takes an explicit cutoff and an immutable source snapshot. It returns a value with its admissibility evidence or a structured unmeasured reason. It must not silently use the latest revised value, nearest timestamp, a later benchmark close or today's membership merely because an exact match is absent.

Do not invent a second calendar. Reuse exchange-session and timestamp-convention owners. Cross-market comparisons require a declared comparable interval: US close, Asian close and a 24-hour crypto mark are not synchronous just because they share a date string. Terminal display epochs must be converted through their existing owner before being interpreted as UTC.

Historical records distinguish at least these evidence meanings through the existing evidence-mode vocabulary: naturally recorded as-known observations; reconstructions using independently known historical inputs; current-composition descriptive history; and unavailable history. Do not attach a reconstructed observation to an original event as if it had been recorded then.

## 3. Required input families and qualification questions

| Family | Existing source/consumer anchor | What to qualify before modelling |
|---|---|---|
| Sector ETF prices and returns | Existing price/Data OS owner; `sector_cycles`, `subsector_confluence` consumers | Real inception; executable prices; dividends/splits; delist/reorganization treatment; price versus total-return separation |
| Industry/theme member prices | `basket_index`, existing basket/Theme Graph membership owners | Membership vintages; missing constituents; synchronous marks; rebalance method; survivor and delisting handling |
| ETF primary-market activity | `collectors.sponsors`; `etf_flows`; `rotation_flows` | Issuer dates; shares precision; splits; estimated versus directly reported counts; in-kind versus cash interpretation |
| Broad-fund sector allocation | Existing fund holdings/exposure sources | Allocation-vintage lag; estimated look-through; overlap and fund-of-funds duplication; passive versus active changes |
| Institutional holdings | Existing 13F/beneficial-ownership sources; possible N-PORT adapter only through that owner | Actual filing availability; amendments; economic exposure versus long-equity holdings; cash/derivative omissions |
| Macro and rates | `regime_one`, `quad_vector`, `regime_vector`, existing macro collectors | Causal filtered versus smoothed state; release vintages; real/nominal/term-premium distinctions; rates and policy-expectation clocks |
| Breadth and concentration | Existing breadth, heatmap and leadership consumers | Fixed expected denominator; missing observations; heavy-name contribution; price versus revision breadth |
| Earnings expectations | Existing revisions/earnings owners, `theme_revisions` | Genuine dated analyst consensus versus issuer guidance or media witnesses; fiscal comparability; first-known changes |
| Industry economics | `demand_chain`, thematic activity/fingerprint/Foresight sources | Orders, inventories, capacity, pricing, competition and capital investment on their actual publication clocks |
| Trading frictions and risk | Existing quote/liquidity/portfolio-risk owners | Spread/impact/capacity observations; calibration population; covariance training window; cash instrument and mandate |

This table is an acquisition/qualification map, not a claim that every source is present, licensed, complete or ready. Request metadata before large data movement. A feature with no historical archive may support prospective observation while remaining unavailable for a historical model.

## 4. Group index contract

### Membership and weight invariants

A group is identified by taxonomy version, group identifier, membership evidence version, weighting/rebalance method, market/calendar and currency/basis. Preserve announced/effective membership separately. A taxonomy change such as a newly formed sector cannot be backfilled as an investable ETF history.

Use two explicitly different chart products:

- **Current-composition descriptive tape:** today's membership applied to history, disclosed as such. Appropriate for understanding current exposures, not claiming a historical investable strategy.
- **Point-in-time investment tape:** dated eligible members/weights, deterministic rebalances, corporate actions and missing-data policy. Required for historical economic evaluation.

For a close-return index, chain weighted member returns with weights established before the return interval. The phrase equal weight must state whether weights rebalance daily, monthly or on membership changes. For intraday buy-and-hold shares, weights drift; reconstructing every mark with new equal weights silently describes a different strategy.

Do not renormalize missing members without a declared method and coverage disclosure. A stopped quote cannot remain a zero-return holding forever; equally, dropping a delisted loser at its last quote can erase its terminal loss. Source-authoritative terminal/corporate-action treatment and a visible unresolved state are required.

### Candle and turnover invariants

Weighted member daily highs/lows need not occur simultaneously. Therefore a weighted range is synthetic unless synchronized constituent marks establish the basket path. Close-only T2 can remain useful while ATR/range-dependent features stay unqualified. The deterministic counterexample is included in the research checks.

Aggregate dollar turnover is not signed demand. Even `close × volume` is an approximation to actual traded notional when intraday trade prices vary. A basket's traded activity, a constituent-level flow proxy and subscriptions into an investable fund must have different fields and labels.

### Price basis and currency

Price-structure studies, dividend-reinvested investment returns and a fund's actual executable quote are separate bases. Every return pair uses compatible benchmarks and explicitly handles currency conversion. Total-return backfills must not create synthetic executable intraday prices. Corporate-action factors need their own version and effective time.

## 5. Fund-flow decomposition without false causality

A change in split-adjusted shares outstanding times the appropriate NAV estimates primary-market creation/redemption notional. It is not secondary turnover and need not equal cash buying of every underlying constituent.

For sector allocation, a proposed look-through estimate weights a fund's activity by its latest *known* sector holdings. Preserve separate components for direct sector funds, broad funds, active-allocation changes and unallocated/unknown exposure. A shares change based on rounded AUM/NAV must carry the resulting precision limitation; an apparent tiny daily flow may be rounding noise.

Reconcile totals with a waterfall: source fund activity; directly mapped exposure; estimated exposure; overlap corrections; unavailable remainder. Do not sum a fund and a fund-of-funds holding it as two independent flows. Distinguish market appreciation from investors adding shares; distinguish passive broad-equity subscriptions from discretionary sector overweights.

13F is delayed position evidence, not a purchase timestamp or actual cost basis. N-PORT acquisition, if useful and permitted, must follow actual available filings/datasets and current disclosure rules; do not hardcode a proposed regulatory cadence as enacted. No new subscription or data purchase is authorized by this design.

The source `etf_flows` explicitly retains `may_rank=false`, `may_gate=false`, `may_size=false`. This package does not revoke those restrictions. A separately admitted study may evaluate suitable raw observations under its source-use contract, but a display object cannot be fed into a new ranker by implication.

## 6. Macro-state quality is part of the feature

The current `quad_vector.build` first uses `regime_one.forward.p_quad`, labels a smoothed-HMM fallback as degraded, and otherwise emits a degraded uniform vector. Its confidence field is `max(p) × mean(axis agreement)`, not a calibrated probability that an allocation will work. Source: lines 120–181 at the design pin.

Consequences for research: a uniform fallback is **missing state information**, not evidence of a naturally balanced macro environment. A smoothed historical sequence cannot replace the causal filtered series in a forecasting backtest. Even when a smoothed final-state estimate coincides with a filtered final-state estimate for fixed parameters, fitting/parameter-vintage and historical-path leakage still need qualification.

The study must carry the producer and degraded reason, not just the four numbers. An unchanged last-good state keeps its original source date. A recently regenerated JSON is not a newly observed macro release.

Data-library methodology is also a vintage. The French Data Library states that its US research returns moved from CRSP FIZ to CIZ with the January 2025 release and that dividend reinvestment conventions differ; it also warns that historical returns can be revised. Pin the artifact and method rather than silently refreshing a supposedly fixed backtest. Only metadata were inspected for this package; no return download or native held research phase was initiated. Source: [official data library](https://mba.tuck.dartmouth.edu/pages/faculty/Ken.French/data_library.html).

## 7. Prediction and consumer boundaries

The existing ResearchEstimate requires all eleven identity fields plus a finite probability in [0,1], or an unmeasured marker. A candidate distribution extension should additionally identify the compared benchmark(s), entry/exit convention, cost model, calibration population, joint-cohort identity, fit/validation references and applicable allowed-use receipt. These are design requirements, not current implemented fields.

There must be no path from a coverage percentage or heuristic score into the probability slot. The object can be structurally valid while scientifically unsupported; preserve that distinction through the publisher and chat grounding layer.

A consumer must reject incompatible horizon/cohort/model versions rather than joining by ticker alone. A 20-session forecast is not a one-hour forecast; a sector rank is not a stock rank; an old parameter snapshot with a new input snapshot is a new forecast requiring its actual provenance.

When group ordering is shown for research, the label must say research-only and retain no investment authority. The eventual ranked product requires the existing source, scientific and policy owners to qualify that use. Do not change a display field's permission merely because the renderer can sort it.

## 8. Negative cases that adapters and readers must prove

The later bounded implementation must reject or disclose: duplicate source clocks; later-revised inputs; today-membership masquerading as historical; missing delisting treatment; an ETF before inception; incompatible return bases; mismatched currency/calendar; synthetic extrema passed as observed; missing-member denominator changes; copied current cap weights; a split treated as inflow; a broad-fund look-through presented as direct purchases; stale holdings treated as real-time; zero replacing unknown; degraded uniform quads treated as information; full-sample beta/preprocessing; immature training labels; marginal intervals promoted into selected-winner guarantees; and a research estimate promoted into sizing without the existing allowance.

Each failure should preserve the exact original source identity and reason. Silent fallback is not resilience when it changes the economic question.

## 9. Data-readiness stop conditions

Metadata and permitted non-outcome contracts may be investigated now. The following stop only the affected scientific use: unverified source rights; unknown first availability; incomplete constituent history; unresolved return basis; an unreconciled source revision; an unqualified cost/cash assumption; or a held outcome-reading phase. Do not bypass these by replacing the source with a more convenient unqualified dataset.

The next data deliverable is a compact qualification manifest referencing existing artifacts, not a new warehouse or registry. It must establish what is usable for development, what is prospective-only, and what remains unknown before any historical results are called confirmatory.
