# B06 economic source qualification — diagnostic, not a corrected return

Read on 2026-10-08 America/Vancouver (2026-10-09 UTC). This is a retrospective
primary-source qualification. It proves neither historical ingestion by Prophet
nor a decision-time trading policy. Native outcomes remain immutable.

## Distribution facts and revision history

1. Corteva's September 15 filing describes a one-for-one Vylor distribution, a
   September 24 record date and expected completion before the October 1 opening.
   It also describes **expected** when-issued Vylor and ex-distribution Corteva
   markets for September 25–30. Those are proposed trading arrangements at that
   source vintage, not proof that either market actually traded.
   [Corteva/EIDP September 15 Form 8-K, Item 8.01](https://www.sec.gov/Archives/edgar/data/30554/000119312526391369/d71834d8k.htm).
2. The September 24 issuer release explicitly says there would be no when-issued
   Vylor or ex-distribution Corteva trading before distribution. It retains the
   one-for-one ratio and expected October 1 regular-way listing. The change in
   trading arrangements must remain visible in revision lineage; applying the
   earlier expectation after this update would be wrong.
   [September 24 release, Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/2128626/000119312526401621/d118532dex991.htm).
3. Vylor's October 1 filing states that the separation completed on October 1
   through the pro-rata distribution to Corteva holders of record on September 24.
   It describes regular-way VYLR trading as expected to commence that day. The
   completion statement establishes the distribution event; it does not itself
   supply an executed quote, realized entitlement ledger or shareholder return.
   [Vylor October 1 Form 8-K, Item 8.01](https://www.sec.gov/Archives/edgar/data/2128626/000119312526409909/d115079d8k.htm).

This independently confirms why the handoff's CTVA discontinuity must stay
**UNRESOLVED** as an economic outcome. No corrected percentage is published here.
The sources above do not establish every evaluated row's actual entitlement,
distributed-security mark, matched quote basis/currency, effective trading instant,
cash in lieu, or execution convention. Missing facts are not zero distributions.

## Current implementation defects and retained owner

| Boundary | Current evidence | Required owner-native resolution |
| --- | --- | --- |
| Native mark versus shareholder wealth | `engine.grading.forward_metrics` and `engine.us_prophet_grades.grade_row` take close series, not distribution entitlement. A synthetic 100-to-14 series returns -86%; that is a price mark. | Existing grading/Evaluation owner qualifies economic basis and attaches revision lineage; preserve the original grade. No price-gap heuristic or ticker exception. |
| Corporate-action coverage | `engine.seasonality.universe.corporate_actions_asof` returns UNAVAILABLE, with `complete_point_in_time_security_and_corporate_actions_contract`. Registry coverage is bootstrap-only/incomplete. | Qualify the existing Data OS owner for the actual event and window. Do not infer universal coverage or no event from a partial adapter. |
| Publication/fill attribution | The plan chronology audit's native run, capture and Git clocks differ for real CRI evidence. | This branch now discloses unresolved publication/exposure/fill. A later owner integration must join actual accepted publication and executable fill evidence. |
| Benchmark alignment | Native `grade_row` forward-fills SPY onto the name calendar. | Preserve #8192's additive exact-calendar witness and study-specific eligibility; do not rewrite old marks or treat imputed sessions as observed tape. |
| Immutable outcome revision | Existing grade keys freeze `(stamp_date, ticker, board_definition, horizon)`. The plan correction overlay owns date/disposition corrections separately. | Extend the incumbent owner's correction attribution under reviewed schema, retaining original and revised evidence. Do not fork a second evaluator or overwrite parquet history. |
| Historical versus current identity | Current B1 intake can resolve an old source observation using a newer master snapshot. | Qualify the B02 knowledge clock before historical episode claims; consume #8626 for forward seeds and #8192 for prospective capture under their own gates. |

The economic source work does not rerun the frozen study, change its denominator,
grant actual position authority, or interpret no-fill/immature/unpriced rows as
losses or cash. Split, distribution, delisting terminal value, revision timing,
intrabar ambiguity and actual next-available execution remain required B06 cases.
