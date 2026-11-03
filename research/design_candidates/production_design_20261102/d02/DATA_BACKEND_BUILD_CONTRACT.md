# D02 backend, source and data contract

**Observed implementation plus proposed consumer requirements.** Source pin: Macro [fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9](https://github.com/mastermindx-market-intelligence/macro/tree/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9). This document changes no producer, public API, rights policy or model. The closed workspace schema is existing source; the legacy reading envelope below is a proposal.

## 1. Real source graph and responsibilities

| Consumer / data family | Real producer or source | Existing carrier / rendering entry | Contract to preserve |
| --- | --- | --- | --- |
| Canonical macro regime | engine/axes.py, engine/regime.py, engine/run.py | data/regime/latest.json → scripts/build_site.py → templates/dashboard.html.j2, mode=macro | Raw/confirmed/pending regime, hysteresis, axes, coverage, support/contradiction; do not replace with HMM mode |
| Market-state overview and path | engine/market_state.py; market_state_view and _ms_history_view in build_site.py | market_state VM; data/market_state/forward_log.jsonl; up-to-60-session path | Composite and factor scores are separate from two-axis regime confidence; current recomputation and issued history retain identities |
| RiskRadar | engine/risk_radar.py, risk_radar.v2 object | risk_radar in regime/latest.json; dashboard and Macro Context | State/ungated state/context gate, scare reading_state/display_score/coverage, target/horizon, model/config identity, authority |
| Probability evidence | engine/risk_radar_backtest.py; engine/risk_radar_scorecard.py | data/risk_radar/probability_evidence.json; scorecard.json; attached calibration_evidence | Reconstructed, issued historical and prospective cohorts remain distinct; exact model/surface matching, event counts, intervals and false validation flags survive |
| Slow macro/credit pressure | engine/conditions.py | conditions.drawdown_risk and vintages in regime payload | Composition, expected/resolved/missing legs; ≥10% future peak-to-trough decline over 63 trading days; different target from RiskRadar |
| HMM | engine/regime_hmm.py | regime_hmm in regime payload; producer-named hmm_latest artifact | Fitted membership, fit cutoff, full-sample-smoothed historical class, monthly transition matrix/hazard; display-only |
| Fed path and stance | engine/fed_path.py; engine/fed_stance.py | fed_path.implied and implied_source_meta in regime payload | EFFR/SOFR basis, contract reference interval, averaging law, target dates, comparability verdict; legacy numeric fields are not permission |
| Rates interpretation | engine/rates_inflation_command.py; scripts/build_rates_command.py | data/rates_command/latest.json → rates_command VM | board_generation, missing d1, source asof versus build, path level versus 20-session change, stance refusal |
| Settled risk envelope | scripts/build_risk_envelope.py::write called by build_site.py | data/ and site/riskdata/ canonical copies; risk_envelope VM | Same-session composition; additive failure yields absence, never a fabricated calm result |
| Policy/event/news/sentiment and markets | build_site.py source-backed VM adapters | macro_catalysts, event_strip, event_risk, prediction_markets, macro_news, macro_brief, fear_greed, fear_euphoria, market_tiles, sector_heat, policy_lever, shock_state and related fields | Each adapter's producer/date/authority remains attached; D10 owns reading, D15 deep transmission, D03 stocks; do not collapse all clocks into generated_utc |
| Macro Context | scripts/build_macro_context.py | data/macro_snapshots/latest.json; data/neuralweb/world_state.json; data/regime/latest.json; transitions.jsonl; market_state_history.parquet → macro_context.html and data/macro_context/latest.json | Snapshot identity, source disagreements, transition history, currencies/regions and raw-source dates |
| Fourteen workspaces | engine/market_os/macro_workspaces/* via closed registry | site/macrodata/workspaces/manifest.json + workspace/US/latest.json → lib/macro_suite_view.py → build_macro_suite_pages.py | Existing closed schema/version/digest, source clocks, rights, typed refusals, authority ceiling and prior publication |
| Command and eleven fragments | build_macro_suite_pages.py::build_hub / write_fragments | macro_monetary.html; templates/_macro_command_fragment.html.j2; site/macro/fragments/*.html; macro_command.js | Same snapshots/refusals as workspaces, lazy validated fragment response, exact section/subtab hashes; no independent model or clock |
| Anticipation | engine/anticipation.py::anticipate, macro_legs_frame/load_gate | data/stocks/<ticker>.parquet or data/yahoo/<ticker>.parquet; breadth parquet; data/regime/anticipation_gate.json → site/anticipationdata/anticipation.json and per-asset JSON | Asset/group, as_of/generated_utc, horizon quantiles, sample/gate/underpowered state, relative-confluence meaning |
| Odds Lab | engine/odds_lab.py; scripts/build_odds.py | adjusted OHLCV cache, regime_history.parquet → site/oddsdata/catalog.json and factor_match.json; site/oddsmatrix/<T>.json on existing R2 plane | Ticker validation, next-open-to-close returns, same-range baseline, matrices kept off Git, cache corporate-action basis, degraded catalog |
| Cycle | scripts/build_cycle.py and existing cycle engine/seed | site/cycle_data.js seed, proxy_fitness.json, falsifiers/forward log → window.CYCLE_ENGINE via generated engine JS | MEASURED/FRAME/dual classification, measured source, turns, projections, tolerance ledger, proxy evidence and falsifier state |
| Demand | engine/demand_chain.py, engine/demand_ledger.py; build_demand.py | EDGAR statements.parquet, basket membership, revisions, RPO/headcount maps → server-rendered demand.html | Ticker/chain identity, actual financial period, evidence class, denominator, divergence class, ledger qualification |
| Impulse | engine/impulse.py; build_impulse.py | close/volume caches aligned to common last session → impulse JSON and HTML | as_of/generated_utc/status, universe/with_volume, five lane counts, config and per-name evidence |
| Divergence Radar | engine/radar.py through build_baskets; engine/narrative_brain.py | site/basketdata/radar.json and narrative_brain.json → radar_panel.js; build_radar_page.py shell | Independent observable versus price/narrative; lifecycle, source time, loading/fetch failure distinct from empty |
| Internal Cross Asset / Signals | engine/cross_asset_trend.py and build_crossasset.py; build_site.py signal adapters | crossasset_flows.v2; macrodata/macro_signals.json; internal templates | Contested/display context and existing audience; no public route admission from this packet |

The dashboard VM contains cross-product objects. Presence in that dictionary does not transfer their ownership. Source reads establish entry points; they do not prove every underlying upstream service or current entitlement. Exact copied producer snapshots and references are recorded in the source manifest.

## 2. Existing closed workspace contract

Contract ID **mastermind.macro_workspace_snapshot.v1**, version **1.0.0**, is defined in contracts/market_os/macro_workspace_snapshot.v1.schema.json and validated by engine/market_os/macro_workspaces/contract.py. Its top-level required blocks are schema, workspace, region, generation, authority, availability, headline, axes, metrics, series, drivers, changes, implications, scenario_contract, alert_contract, sources, corrections and learning; prior_publication is optional. Unknown top-level keys fail closed.

The current registry has fourteen BUILT entries, all US. “Built” does not mean current data or a valid headline. The source manifest reports seven CURRENT, three LATE_WITHIN_TOLERANCE and four STALE_SOURCE snapshots. Preserve each record's underlying cadence rather than applying a page-wide elapsed-hour rule.

| Snapshot | Availability at inspected generation | Calculation as of | Domain complication |
| --- | --- | --- | --- |
| business_activity | CURRENT | 2026-10-31 | Leading/coincident/lagging periods differ |
| capital_structure | STALE_SOURCE | 2026-10-31T06:03:29Z | Partial event/issuer discovery; coverage ratio alone cannot certify completeness |
| consumer_payments | LATE_WITHIN_TOLERANCE | 2026-09-01 | Monthly sentiment and slower credit/delinquency observations |
| financial_conditions | CURRENT | 2026-10-30 | Weekly and daily inputs retain own source clocks |
| growth_real_economy | CURRENT | 2026-10-30 | Accelerating nowcast versus falling coincident hard-data tier |
| housing_real_estate | CURRENT | 2026-10-29 | Weekly mortgage rate versus monthly starts/prices/rent |
| inflation_system | LATE_WITHIN_TOLERANCE | 2026-10-16 | Reference month 2026-09 is not a release timestamp |
| labor_markets | CURRENT | 2026-10-30 | Claims, postings and recession indicators have distinct definitions |
| liquidity_central_banks | STALE_SOURCE | 2026-10-16T18:16:51Z | Required GLT/Fed balance-sheet inputs from October 7–9 |
| liquidity_regime | CURRENT | 2026-10-30 | Mixed funding/support axes; method-comparable prior publication |
| monetary_policy | STALE_SOURCE | 2026-10-20 | Path and balance-sheet legs stale; policy rate has another date |
| national_debt_liabilities | STALE_SOURCE | 2026-10-29 | Auction-demand lag plus issuance stress/calm-desk contradiction |
| rates_curves | LATE_WITHIN_TOLERANCE | 2026-11-02 | Different node dates; term premium late |
| trade_flows | CURRENT | 2026-09-01 | Trade totals August, price indexes September; normal publication cadence matters |

All were built at 2026-11-02T07:18:10Z, with generation code_version b188d09fcf027f2a6f77a396c9d3e79e4660929d. That provenance is not the current source-census SHA or a served release identity. It must not be overwritten by either.

### Identity, fields and units

Each metric record preserves metric_id, reference_id, definition_id/version, owner_ref, value/type/unit/basis/direction_semantics, reference_period, observed_at, released_at, available_at, collected_at, revised_at, calculation_as_of, market_session, source_refs/digest, transformation, model_version, uncertainty, coverage, freshness, rights_state, status, null_reason and authority_ceiling.

The [complete extract](evidence/workspace-contract-census.json) has all **321 metric records**, axis components/weights/transforms, **101 source records**, and metadata plus first/last points for **10 series**. It is a frozen source extract, not a new contract or replacement data store. Original series links preserve the complete points. Metric/source fields whose value is null remain null in the extract.

For example, liquidity funding_pressure=47.51 is a 0–100 score, not percent probability. Its four legs include percentiles scaled by 100, a declared z-score mapping and a passthrough scare score; source weights renormalize over present components. Balance-sheet support=26.78 has different label and quantity mappings. Axis direction, weights_law, min_components and coverage_floor explain the result; a designer cannot substitute equal weights.

Every workspace's authority is context_only/display_only; can_rank, can_gate, can_size, can_originate_signal and can_execute are false. Axes and metrics have a DESCRIPTIVE ceiling. Preserve those constraints in tooltips, exports and any machine consumer.

### Integrity, revisions and comparison

Canonical JSON is sorted, Unicode-preserving and rejects NaN/Inf. content_sha256 is computed after nulling only volatile generation fields: generation_id, built_at, rendered_at, content_sha256 and code_version. generation_id is workspace-region plus the first sixteen digest characters. A valid new build time does not create new analytical content.

Consumers must validate schema/version, non-placeholder digest and actual content hash before presenting the snapshot as current. A manifest and snapshot identity mismatch is a generation mismatch, not an empty market state. If a verified last-good snapshot is available, label it retained and expose the failure; do not silently join a new headline with old driver rows.

prior_publication is the last strictly earlier publication, including its headline and tracked metrics. Same-dated rebuilds compare to that object, not reconstructed changes.deltas. Preserve method version, prior effective date, correction_state, predecessor_generation_id and changed_fingerprints. A method change or no earlier publication must produce its typed non-comparison state, not a zero change.

## 3. Confidence and model contract

Use the exact quantity name. A universal confidence meter is prohibited by this proposed interpretation contract.

| Quantity | Actual meaning | Required UI qualification |
| --- | --- | --- |
| Regime confidence 0.22 | Mean of axis strength × agreement; can be zero for insufficient components | “Signal agreement 0.22 / 1”; coverage and method, no probability wording |
| HMM Q2 membership 0.6774 | Posterior membership under this fitted model | Separate from canonical label accuracy; historical path is full-sample smoothed |
| HMM hazard 0.4122 | Empirical monthly transition frequency from modal state | Not a daily flip countdown; expected dwell is not remaining life |
| Risk scare percentile score | Relative stress over producer's trailing history | Preserve eligibility and display_score; not loss probability |
| RiskRadar h21=0.22 | State/conjunction model estimate of ≥5% loss from issue close | Exact SPY closing-observation horizon, base rate and evidence class |
| Reconstructed observed rate 16/66 | Retrospective cell event frequency | 24.24%, wide 90% interval; overlapping/non-issued history; precision false |
| Slow risk band rate | ≥10% maximum peak-to-trough decline over 63 trading days | Different event, horizon and composition; do not compare as identical forecasts |
| Odds win rate | Matched historical positive-return frequency | Matched N and same-range base rate; nominal interval does not adjust for repeated searches/overlap |
| Anticipation percentile/cone | Relative confluence / conditional quantile distribution | Show representative window and exact horizon gate; constituent neutrality does not erase or invent composite qualification |

The incumbent RiskRadar/model producer owns validation and promotion. Current individual writer identity was not verified; historical research/grey_deer is provenance, not a live assignment. D02 owns correct consumption. The detailed [risk/Fed judgment](appendix/RISK_FED_CONTRACT_JUDGMENT.md) contains 14 source rulings and 30 discriminating cases; it is principal advice, not formal review approval.

## 4. Fed level, change and comparability

The inspected path is 3.88% current effective rate to 4.46% at twelve months (+58bp). Its 20-session change is −22.2bp. A falling expected rate can remain above the current rate. “~2 hikes” is rounded 25bp-equivalent level difference; it is not probabilities of two meetings.

The stronger defect is inconsistent refusal: the producer says the path is withheld until matched, board_generation.complete=false with d1_missing, and regime comparison metadata says not_comparable / basis_mismatch:reference_end. Legacy consumers still display the path/gap. Apply one producer comparability verdict to summary, chart, tooltip, table, accessibility text and takeaway.

Required interim behavior: show independently valid observations with their own bases/dates; state **“Comparison unavailable — reference periods do not match”**; withhold gap arithmetic and “more dovish than the Fed” claims. Do not remove all rate evidence. D15 and the incumbent rates producer resolve the actual comparison and release vintage. D02 must not make the comparison pass in a template.

Policy and Fed dialogs currently place the same current-year SEP projection at six and twelve months respectively. Use actual target dates or a separate dated projection table. Do not connect SOFR and EFFR as one curve without a qualified transformation. Missing SEP release vintage is “Release date unavailable,” not “latest.” Prediction-market outcome prices describe contract-implied probabilities, not percentages of traders.

## 5. Clocks, calendars, access and data quality

Separate reference period, observation date, release time, first-known time, collection time, calculation cutoff, build/render time and served release identity. Preserve precision: YYYY-MM, date-only and full timestamp are different claims. Unknown timezone or publication time stays unknown.

Mixed-frequency charts use source cadence and the relevant market calendar. Daily closes remain last-close observations over weekends/holidays; weekly/monthly sources can be current while older than a daily market quote. Preserve per-series dates and source-defined freshness. No UI wall-clock timer promotes source currentness. Observation/publication/availability evidence later than the permitted calculation cutoff requires a visible mismatch/refusal, not silent clipping. Future projection targets, futures contract reference intervals, model horizons and scheduled events remain valid future dates and must not be rejected by that evidence-cutoff rule.

The conditions vintage helper uses the last changed-or-first value in a forward-filled series. That is a last-distinct-value proxy, not a verified release receipt. Macro Context currently substitutes today for an international-risk date; that fallback must not certify freshness. These are producer/adaptor repairs required before future acceptance.

Existing workspace freshness states are CURRENT, LATE_WITHIN_TOLERANCE, STALE_SOURCE, NOT_YET_RELEASED, SOURCE_FAILED, RIGHTS_BLOCKED, NOT_COVERED, HISTORICAL_AS_KNOWN and SIMULATED. Presence is PRESENT, PARTIAL, ABSENT or DISAGREEMENT. Null reasons include UNKNOWN, NOT_APPLICABLE, NOT_YET_RELEASED, SOURCE_FAILED, RIGHTS_BLOCKED, INSUFFICIENT_HISTORY, WARMUP, REVISION_PENDING_REBUILD, DISAGREEMENT, COMPUTATION_REFUSED, OUT_OF_REGION and NOT_COVERED. Preserve combinations rather than flattening them to “no data.”

Zero is a valid value. Null/undefined/NaN, false, zero, negative numbers and an empty sample are distinct. A zero event count with positive N is an observed zero; N=0 does not support a rate. Sorting places missing values after valid numbers in either direction. Do not backfill p_up=0 to 0.5, a zero rate to another source, or an unavailable scare's raw score to a current display score.

Rights_state is OPEN, RIGHTS_BLOCKED or UNKNOWN. A shell route accessible anonymously does not mean its premium payload is authorized. Preserve config/site_access.yml and the server/data-plane owner. Denied internal routes remain 404; no hidden-data prefetch, public navigation exposure or frontend-only masking substitutes for server enforcement.

## 6. Proposed legacy reading envelope and mutation seam

For legacy fields that lack the workspace schema, D02 proposes a thin consumer adapter carrying: stable reading/series/instrument identity; source artifact and JSON pointer; producer/schema/model/config identity; value, unit, basis and transform; target/horizon/calendar; all available clocks and precision; source revision/input-bundle identity; coverage/reading state; evidence class/authority; comparability and invalidation. This is a **proposal**, not a live endpoint or released schema. Add missing fields through their producer owner; do not infer them from build time or another region.

The browser displays and navigates. Producers own calculation, model state, eligibility and thresholds. Existing build scripts own deterministic composition. F01 owns host state and authentication. D23 owns all saved-object/alert writes, identity, deduplication, activation, readback and uncertain outcome. This phase performs no writes to those services.

A proposed D23 handoff includes region/instrument identity, producer condition ID, threshold/unit, target/horizon, model version, evaluation cadence and source generation. A component margin is not automatically an executable alert predicate. Until D23 and the source owner qualify it, say “Condition saving is unavailable for this reading” and keep evidence access.

When a future save is supported, pending state cannot become success until authoritative readback identifies the object. Network timeout or session expiry after submission is uncertain; reconcile with the same operation identity before retrying. Navigation, filter changes, locale changes and opening evidence do not save or activate anything.

## 7. Refresh and publication requirements

No universal TTL is invented here. Reuse the existing source cadence, data-base shim, access owner, lazy client fetches and publication mechanisms. Command fetches a fragment on first activation; Odds matrices use their existing R2 plane; SSR content remains useful without JS. A refresh action rereads the same source scope; it does not recompute a model or trigger an alert.

Publish matching manifest/snapshot/fragment content as one compatible generation or retain explicit mismatch state. Honor existing atomic writes; preserve public data paths. Builders that intentionally catch exceptions and return zero require output/readback verification: process exit 0 alone cannot prove a new page exists. A rollout owner must prove served HTML, source payload and model identities match the accepted release. That proof is outstanding; the successful public-host reads in this phase are not a beta release certificate.

