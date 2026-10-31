# RS Leadership Suite - group context integration contract

Task P3.1 of `RS_LEADERSHIP_SUITE_MASTERPLAN.md`. Recorded 2026-10-31 UTC / 2026-10-30 America/Edmonton. Source-only interface proposal, not an accepted adapter or data-source permission. Parent remains WS:LIVE-ENTRY-RADAR; GMI and leadership-rotation retain their owners. This document is subordinate to the existing source-admission and scientific protocols.

## 1. Inspected interface and decisive gaps

Inspected Macro Draft #10213 at exact head `46792c6956ae46fd20855892954f41f6f96188f5`, file `engine/sector_theme_factor_intelligence.py`, blob `7f5b70c7c832c03158ab25e9fccae04c9c7fb357`. It exposes `project_factor_frame(...)` and schema `sector_theme_factor_frame/v1`.

That pure projection validates coherent caller-supplied clocks and complete-window measurement structure. It explicitly does NOT authenticate historical membership, source rights, adjustment basis, benchmark returns, weight vintage or original known-at receipts. Its output carries `eligible_for_customer_publication=false`, `entry_or_sizing_authority=false`, `alert_authority=false`, `ranking_authority=false`, and `predictive_promoted=false`. This consumer must preserve those ceilings. A valid JSON object or matching hash is not owner qualification.

**No native 30m horizon exists in the inspected interface.** Declared horizons are 1m, 5m, 15m, 60m, rth, 1d, 5d, 20d, 63d, 126d, 252d, 756d and 1260d. Do not rename 15m/60m data to 30m, average two breadth percentages into a 30m measure, or silently rebuild another group engine. A later accepted owner revision may add a genuine 30m horizon; until then, a 30m pivot can display separately labeled known 15m, 60m or daily context with its own age. Same-window comparative claims require the actual same window, not just a similar timestamp.

The inspected frame has no authenticated issuer-exclusion receipt, retained weight-generation receipt, or independently qualified benchmark observation. `member_ids` are caller-provided canonical-ID strings; that validation alone does not establish whether they denote securities, issuers, listings or de-duplicated share classes. An adapter must resolve this through the incumbent identity owner before claiming ex-issuer context.

The existing partial-sample mean and full-cohort mean have different meanings. Missing members make the full-cohort return unavailable; the sample mean cannot silently replace it. Identification bounds on breadth are not confidence intervals. No implementation in this task changes #10213, its tests, CI or active writer.

## 2. One consumer, two discovery paths

A source-qualified stock observation can participate as a standalone leader even when no theme or catalyst is supported. The group-first path adds optional group context; it does not redefine stock eligibility, the original daily leader owner or the existing Entry Engine.

The proposed read projection is a leaf within existing Radar/Terminal. It reads references and returns a measurement annotation. It creates no new identity, ThemeState, authoritative group state, membership store, leaderboard, live event identity, scheduler, alert or evaluation ledger.

Keep six questions independent: discovery attention, descriptive leadership, entry accessibility, pivot structure, statistical forecast and incumbent entry permission. Displaying a strong group is not approval to rank, issue signals, size positions or trade. Research ordering must not be presented as a customer recommendation while the owner flags forbid ranking/publication.

## 3. Required owner-supplied join evidence

Every proposed join requires these facts from the existing owners, not newly invented fields asserted by this consumer:

| Fact | Required evidence | Failure behavior |
|---|---|---|
| Subject identity | Exact security and issuer identity valid at observation and visible by decision | Mandatory subject unavailable; do not guess by ticker |
| Group identity | Exact canonical theme/subtheme/group ID with relationship type and accepted source | Optional group unavailable; standalone path preserved |
| Membership | Owner-selected valid-time and knowledge-time version, revision reference and supported membership mode | No PIT group claim from CURRENT_ROSTER |
| Member units | Owner-resolved security-to-issuer map and share-class treatment | Ex-issuer contrast unavailable |
| Return basis | Consistent corporate-action/price-or-total-return definition and interval | Mixed basis unavailable, not a low score |
| Period | Exact interval start/end, horizon, exchange/session semantics | No same-window comparison across mismatches |
| Availability | Original observation/receive/known-at receipts and source/correction references | Retrospective reconstruction labeled; no prospective issuance inference |
| Benchmark | Qualified benchmark identity, matching period, basis and known-at | Market/parent RS unavailable without a qualified denominator |
| Weights | Exact lagged weights and proof available before the measured interval, when used | Weighted measurement unavailable; equal-weight may remain only if independently supported |
| Rights and use | Existing owner's allowed purpose, retention, display, redistribution and entitlement scope | No customer publication or copying beyond owner scope |
| Exclusion | Subject issuer removed from each claimed peer and relevant parent construction | Inclusive group context may be shown as inclusive where allowed; not ex-self evidence |
| Correction | Original observation reference plus newly visible correction lineage | Preserve original decision view and separately expose revision |

These are conceptual requirements on existing receipts, not a new credential or admission schema. Do not demand a replacement source service just to populate the table. The adapter must map the actual accepted owner contract and report unsupported facts explicitly.

## 4. Exact field mapping for the inspected frame

Preserve the original owner frame and its reference; the leaf must not rewrite it.

| Owner field | Permitted consumer meaning | Prohibited inference |
|---|---|---|
| `group.group_id`, `cohort_id`, `membership_revision` | Identity and cohort labels after external owner qualification | Labels alone authenticate the group |
| `group.membership_mode` | PIT_AS_KNOWN versus CURRENT_ROSTER | Current roster was known historically |
| `clock.period_end`, `decision_at`, `membership_known_at`, `horizon` | Declared temporal scope, subject to source receipts | All events were available at period_end |
| `clock.moving_average_basis` | Actual daily-session or intraday-bar basis | A 50-bar MA is a 50-day MA |
| `universe.expected_n`, `measured_return_n`, `missing_by_reason` | Explicit coverage | Missing member is a loser or a zero return |
| `constituents[id].return_frac`, `rs_market`, `rs_parent` | Measured or typed unmeasured values on the frame's window | RS percentile or validated forecast |
| `equal_weight_observed_sample_return` | Observed-sample mean only | Complete group performance |
| `equal_weight_full_cohort_return` | Full supported cohort mean | Lagged-weight or investable-index performance |
| `lagged_weight_full_cohort_return` | Numerically complete supplied-weight calculation | Verified weight vintage or free tradability |
| `group_rs_market`, `group_rs_parent` | Owner relative-wealth measurement | Subject-excluded group residual |
| `positive_return_breadth` | Fraction positive on the declared return window with bounds | Relative outperformance breadth |
| `positive_rs_market_breadth`, `positive_rs_parent_breadth` | Fraction outperforming the named benchmark | Fraction above MA or RS new-high count |
| `above_ma50_breadth`, `above_ma200_breadth`, `uptrend_breadth` | Named technical participation | Interchangeable measures of the same event |
| `transitions.metric`, `change` | Currently uptrend transitions with endpoint coverage | RS acceleration, money inflow or membership-stable alpha |
| `evidence.*` | Original limitations preserved | Pure clock checks grant source admission |
| `authority.*` | Exact owner ceilings retained | Consumer can promote them on its own |

No unknown value becomes zero, neutral, no catalyst or false. The frontend should display a scoped reason rather than discard the whole stock when an optional group annotation is absent.

## 5. Relative strength and early-onset semantics

Use compounded relative wealth, `(1 + stock_return)/(1 + benchmark_return) - 1`, for matched cumulative windows with a valid positive benchmark gross return. Keep this distinct from simple return difference, log-relative return and cross-sectional percentile; label their units. A benchmark total loss or unsupported return is unavailable, not an infinite score.

Slope/acceleration research must use predeclared causal windows and actual complete history. Overlapping 3/5/10-day returns are not independent votes. Rank acceleration requires comparable PIT universes and coverage on both dates; a stock moving from percentile 70 to 90 because half the universe disappeared is not genuine acceleration. Report same-cohort changes separately from membership and coverage changes.

At first delivery expose directly observed measurements, not an unvalidated leader-probability or confluence score. A future onset research definition must specify benchmark, sign, horizon, liquidity scope, persistence, rearm and missingness before label access. Young-listing cases require separate short-history eligibility rather than imputed 252-day history. Stock price appreciation and merely falling less than the benchmark remain separate observations.

## 6. Timeframe joining

A pivot observation has its own event candle, decision and source-known time. Each optional context keeps its own interval and availability. A context is eligible for display at the pivot decision only if genuinely known by then and within its own accepted freshness envelope. Later context must not be attached as if it existed at the original pivot.

A completed 60m group measurement and completed 30m stock pivot can coexist as multi-timeframe context. They cannot be described as a synchronous 30m group confirmation. Current-session RTH cumulative return, rolling 60m return, previous completed daily return and calendar-day change are distinct rulers. Preserve exchange-open anchors, half-days, DST and overnight session labels. No arbitrary consumer-side age threshold is introduced before measuring the real source envelope.

## 7. Ex-issuer peer support

For any eventual peer comparison, use the existing accepted group calculation interface with lagged membership and weights, excluding every security of the subject issuer. Removing the ticker from the direct subtheme is insufficient if a parent shrinkage basket still contains that issuer. Report inclusive market ETF controls as inclusive; do not privately create a replacement ETF.

Report expected/eligible/observed peer members and weight, effective support `(sum w)^2/sum(w^2)`, largest-member concentration and source gaps. A three-name 90/5/5 basket has far fewer than three effective observations. Overlapping themes are not independent confirmations. A theme attached to several sectors need not be forced into a single tree. A fallback to parent-only context is a separately named supported observation, not fake subtheme breadth.

No ex-issuer numeric output is required from this leaf until the incumbent owner exposes and qualifies that path. Thin or unsupported peers leave the standalone stock measurement intact.

## 8. Acceptance fixtures for the eventual adapter

Mandatory mutation cases: future-known membership; CURRENT_ROSTER in historical mode; ticker reuse; two share classes from one issuer; subject reintroduced through parent; missing benchmark receipt; mismatched adjustment basis; mismatched period/horizon; invented 30m horizon; 15m labeled 30m; current-session versus previous-day mixing; partial cohort masquerading as full; percentile mislabeled breadth; bounds mislabeled confidence intervals; missing member zero-fill; future corrections changing prior output; unqualified supplied weights; rights refusal; unsupported parent fallback; and any authority flag elevated by the consumer.

Positive cases: qualified standalone stock without group/catalyst; known daily context beside a separately labeled 30m pivot; complete same-window group context; optional thin group with explicit missingness; corrected-now versus originally-known replay shown separately. Test no input mutation and deterministic output before customer integration.

## 9. Dependency disposition

The interface contract can be reviewed now. Runtime consumption of #10213 is **blocked pending its own source/review/acceptance and the relevant owner adapter qualifications**. Do not merge or modify that neighboring carrier from this task. P1 first-green synthetic descriptor is independent and can proceed. P3.2 cannot call this document proof that group data are admitted. P4 product integration needs actual accepted input and signed-in consumer evidence.

This is a source-bound proposal for the existing masterplan, not a new live capability. Exact implementation/review evidence will be attached to the same task tree rather than a second status database.
