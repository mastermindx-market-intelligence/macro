# Recovered Prophet SCREEN: metadata consumer proof

Research diagnostics only. No outcome columns decoded; no post-2019 event rows materialized.

| Population | Events |
| --- | ---: |
| outside_primary_analytic | 1,292 |
| primary_analytic | 21,773 |
| primary_any | 14,441 |
| primary_none | 7,332 |
| screen_retained | 23,065 |

## Context join

| Status | Events |
| --- | ---: |
| CONTEXT_WINDOW_INCOMPLETE | 205 |
| JOINED_DATE_PROXY_ONLY | 22,860 |

All original event IDs survive the join. ANY/A4 classify only the original primary analysis, not prospective eligibility.

## Limits

- Research diagnostic only; no forecast, ranking, sizing, gate or promotion.
- Source date is declared known date, verified visible on that price prefix; it is not an original first-seen receipt or a complete live-event census.
- bar_label is a display label and is never substituted for the decision date.
- Context uses the preceding expected NYSE session, without forward fill; input vintage is reconstructed, not original publication evidence.
- ANY/A4 are complementary only within the original primary analytic subset. Events outside that subset remain unclassified, not A4.
- Original primary membership reflects the original analysis selection, including label availability; it is not prospective eligibility.
- A2/A3 SCREEN80 cuts use the entire development window and are retrospective calibrations, not historically available thresholds.
- Native coverage grades are retained: 2013–17 survivor-biased, 2018–19 usable. The latter is the source designation, not a new general certification.
- This original archive predates the incumbent W1 split-calendar quarantine. No W1 exclusions, corrected labels, or corporate-action vintage are inferred.
- No new outcome comparison, holdout access, or experiment execution.
