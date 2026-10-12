# Crypto science R3 — input field identity and source-observed cohorts

Date: 2026-09-28. Parent: WS:CRYPTO-INTELLIGENCE / Macro PR #8050. Existing operation crypto-vector-r2-20260926-sol-001 and M2 Studio Direct workspace/carrier. Baseline 40ab75b261fba57b4357e1c7ffb38ddd62f62871. Protected Mastermind e981ec1b0b6e3bd47e267b6abc92adee4a94d6a8, INDEX94d1af402598894372858793a5b1931019c5fa77, compatible Skillpack1.0.1/bootstrap1. Current Chairman Continue supplies present intent. PRINCIPAL_JUDGMENT: input equivalence and cohort policy cannot be decided by a routine coding worker; no independent review is claimed. Working on draft source/research only, no deployment or live gate update.

## Current facts, before new cohort outcome calculations

R2 has completed the full timing correction and replay; those results and original R1 artifacts must remain immutable. R2's three impulse legs did not clear their full gate; do not lower a threshold or change the event taxonomy to rehabilitate one. Independent review and exact release remain owed.

The funding collector maps a one-value response to `funding_rate`, but multi-value responses to prefixed fields. Raw stored data now contains `funding_rate_fundingRate`, `funding_rate_markPrice` and legacy `funding_rate`. The default `_col()` selects physical first column. The current signal uses the first, 80-row field; R2 reported the older 1,089-row field separately. A column name/order change must not accidentally feed mark prices into the funding model.

Public-document reads this turn: provider landing page links the Scalar documentation at https://api.bitcoin-data.com/scalar.html, whose HTML links `/v3/api-docs`. That static OpenAPI document (version0.1, observed SHA2565b79637596b021d69f06849f9ff9fbfa71d6d4e179f38805f7b66a87e0b7396c) describes `/v1/funding-rate` response merely as `type:object`; it does not settle old/new field equivalence, venue, interval or daily aggregation. The provider's explanatory page says funding is usually every8h but varies by exchange. No `/v1/` dataset call, account, subscription, credential or new collector was used. A failed local container DNS read was a read-only transport issue; the approved Studio carrier fetched the public documentation successfully.

Ruling: make field identity deterministic using the exact currently consumed `funding_rate_fundingRate` field. Missing/duplicate/invalid field stays unavailable; never fall back to markPrice or merge legacy history. Preserve finite signed and zero rates; do not invent clipping, rescaling or an8h guarantee. Retain the existing annualization unchanged pending a separate documented interval contract. Prove numeric parity on the currently stored inputs. This is a protection against schema/order drift, not restoration of missing funding history.

## Bounded implementation design

A. Existing `engine/btc_inputs.py`: add private `_funding()` selector; use it only for the `funding` key in `load_all()`. Exact field `funding_rate_fundingRate`, finite numeric values only. No changes to generic `_col` or other sources. Tests in already-enrolled `tests/test_btc_signals.py`: column reorder, missing/legacy-only/duplicate field, zero/negative/null, and current-load wiring. Verify tests fail first.

B. Existing `engine/btc_impulse_radar.py`: add optional keyword `preserve_unknown=False` to `fire_series`. Default must retain current alert/gauge behavior byte-for-byte in emitted booleans. The opt-in view has nullable booleans and all three known leg columns, including all-unknown for absent sources. Conditions/thresholds remain the existing condition builders; no second model. Mask the opt-in output by complete daily observations and finite nonzero-variance feature operands. D2 requires62 completed source observations for60-day trailing z plus preceding z. D3/U1 require91 completed SOPR observations for90-day trailing z, plus6 finite positive daily closes for the5-day price change. Missing/invalid observations must invalidate dependent lookbacks; zero-variance z is unavailable. Return-date/duplicate/intraday input validation applies only to the opt-in path; preserve default compatibility.

Tests in already-enrolled `tests/test_btc_impulse_radar.py`: warm-up/missing source, known calm False, zero variance, missing calendar day, nonfinite data, default parity, future perturbation/prefix invariance and no source write. Tests must fail before implementation. No live `compute`, alert owner, gate writer or decision sizing change.

C. Reuse existing evaluator `_labels`, `_lift`, `_perm_p` for research. Do NOT change `validate()` defaults or write gate artifacts in R3: source-observed cohorts are not proven publication-time cohorts. Produce diagnostics in `research/crypto_science/r3/` and a same-directory study script, not a new evaluator/control/forecast owner.

## Frozen diagnostic before results

Use the same currently stored source snapshot, with hashes and R2-engine source identity. Retain the three existing D2/D3/U1 definitions and +/-5% next3daily-close outcome taxonomy. No signal fitting, parameter search, trading model, funding splice, new annualization or full-PnL experiment.

Compare three denominator policies, explicitly labeled: (1) R2 default booleans with mature labels; (2) opt-in source-observed nullable booleans with mature labels; (3) policy2 under assumed1and2calendar-day publication delays. Delay the completed signal/observation mask together, then evaluate the unchanged next3-close target from the delayed decision date. These are conservative latency sensitivities, NOT known historical release lags. Price sources and label horizon must remain continuous.

For each leg and full/reused2024+ periods report eligible rows, true trigger rows, positives, conditional frequency, base rate and lift. Do not call these probabilities calibrated. Compute no new gate status or lift threshold. The existing gate remains untouched.

Also retain first observed false-to-true onsets (previous calendar day must be observed False; no fabricated first fire after missing coverage). Select earliest chronological onsets with subsequent selections strictly more than3calendar days apart; this prevents overlap of the3-day labels, not all statistical dependence. Show an additional fixed7-day separation sensitivity without choosing whichever looks better. Report episodes/hits/false episodes, false episodes per30eligible days and downside/upside conditional excursion at those dates. No headline event recall unless independent market-event definition is specified; do not substitute bar-level recall for episode-level detection.

Uncertainty: fixed30calendar-day blocks, seed20260928,1000block-bootstrap replicates of episode hit fraction; no bootstrapped accuracy when fewer than2episode-containing blocks. Preserve all outcomes, including weak/unavailable results. The estimated interval remains dependent on block convention and retrospective data, not proof of independent trials or a new holdout.

## Publication and review gates

Commit this plan before reading new cohort outcome aggregates. Keep R1/R2 files unchanged; hash source inputs and existing gates before/after. Stage changes only on the same owned branch. Source custody check: current branch clean, no matching active workspace process; observed main fbd78d1242a370e323a3d576f54166db8a5237c5 has identical btc_inputs/radar source. Full open-PR metadata507 records shows only #8050 and #7645 in the Crypto/Vector/funding/BTC topic; known #7645 is table/template-scoped. This metadata census is not a claim every unrelated PR's files were scanned.

Done for this R3 batch: field-order-safe selector, default-preserving nullable observations, adversarial tests, complete cohort/delay/episode outputs, funding equivalence status, immutable results and canonical checkpoint readback. New fast-exit/recovery policy and production release remain incomplete. If funding equivalence stays unresolved, block only funding-history restoration and continue the independent D2/SOPR cohort study.
