# GLT T10 — Region-qualified liquidity scenario map (measurement-only)

Task: WS:GLOBAL-LIQUIDITY-TRANSMISSION T10 (macro) · Date: 2026-10-13 · Module: engine/global_liquidity_regional_scenarios.py · Schema: glt_regional_scenario_map.v1 · Authority: measurement_only · validated: false

## 1. Purpose

This note sits beside the T05 producer and qualifies five regions separately: us, euro_area, japan, china and hong_kong. Each region is marked measured, assumption_only_context or missing_input from owner inputs that are injected into the module. The module reads no parquet, adds no collector and does not change any producer output — the T05 `regional_gates` dictionary stays empty. T10 gates the downstream T19 reader; production wiring is T22.

## 2. Per-region status

| Region | Status with repository owners | Quantity and local unit | Release basis | FX line | Laws applied |
|---|---|---|---|---|---|
| us | measured | Fed total assets, WALCL, USD millions (unit_multiplier 1e6) | weekly as of Wednesday, observation_date, release lag 1 bday, release_lag_aligned_non_revised | none (local unit is USD) | reserve identity R = A − N; funding identity; T08 conditional accounting |
| euro_area | measured | ECB total assets, ECBASSETSW, EUR millions (1e6) | weekly, observation_date, lag 2 bdays, release_lag_aligned_revision_unknown | EURUSD=X close, translation only, never fresh money | local-unit stock; FX translation not fresh money |
| japan | measured | BoJ total assets, JPNASSETS, JPY 100 millions (1e8) | monthly end of period, month-end anchor (DSC:BOJ-ASSETS-REQUIRE-MONTH-END-ANCHOR), lag 2 bdays, release_lag_aligned_revision_unknown | USDJPY=X close inverted, translation only | local-unit stock; FX translation not fresh money; month-end anchor |
| china | assumption_only_context | none: PBoC stance label (engine/china_pboc_stance.py) and TSF direction (data/china_credit/tsf.parquet, CNY 100 millions, monthly increment, a flow) | stance as of its own date; TSF first known on day 16 of the following month | none | FX reserves are not a balance sheet; TSF not comparable to US credit |
| hong_kong | missing_input | none | none | none | currency-board aggregate balance |

US laws are refused for every other region: `us_reserve_identity_r_eq_a_minus_n`, `us_funding_identity_net_liquidity` and `us_conditional_accounting_t08` raise `us_law_transfer` outside the US, and a T08 outlook given to any other region raises `us_scenario_transfer`.

## 3. FX translation

ECB and BoJ stocks stay in their local units. The USD figure is a separate line with `is_fresh_money` false and basis `translation_only`, computed with the T04 helper `fx_rate_to_usd` from a fixing dated on or before `as_of`; a later fixing is refused (`fx_fixing_after_as_of`). In the T04 decomposition ΔV = q_prev·ΔL + L_prev·Δq + ΔL·Δq, the L_prev·Δq term is a currency valuation change, not new central-bank money. A missing fixing leaves the USD line null and does not demote the local-unit stock.

## 4. Refusal — PBoC FX reserves are not the PBoC balance sheet

Official FX reserves are an asset-side foreign-currency position, reported in USD and moved by valuation as well as by flows. The renminbi the PBoC created when it bought that foreign exchange has been sterilised to a degree that changed over time (central bank bills, reserve-requirement changes, open-market operations), so neither the level nor the change of reserves identifies PBoC total assets or base money. `data/china_pboc/fx_reserves.parquet` is therefore context only; offering it (by concept, store or column) as a central-bank balance sheet raises `fx_reserves_as_balance_sheet`. The open-market-operations store `data/china_omo/operations.parquet` is also refused as a balance sheet (`concept_mismatch`).

## 5. Refusal — Hong Kong is a currency board, not a Fed-style reserve system

Under the Linked Exchange Rate System the monetary base is backed by US-dollar assets of the Exchange Fund; interbank liquidity is the Aggregate Balance, which moves when the convertibility undertakings at 7.75 and 7.85 HKD per USD are triggered and when Exchange Fund Bills are issued or redeemed. There is no Fed-style reserve identity with Treasury-account and reverse-repo drains, so the US identity is refused. The Hong Kong quantity, if any, is the HKMA aggregate balance in HKD from a qualified owner; the existing column `agg_balance` in `data/hkma/interbank_liquidity.parquet` has unknown units and no first-known receipt, so the region is missing_input.

## 6. No global scalar

The map carries `global_scalar` null with status `insufficient_comparable_pit_coverage` (the T03 register status) because regional stocks are in non-comparable local units with different release bases, China and Hong Kong have no qualified balance-sheet owner, and FX translation is not fresh money. A global aggregate request is refused (`global_aggregate_requested`). The map refuses any probability, score, confidence or global liquidity number; it reports what is measured, what is context, and what is missing.

## 7. Exact missing inputs

- `PBoC total assets (central_bank_balance_sheet): no repository owner store; data/china_pboc/fx_reserves.parquet is an asset-side FX position, refused as a substitute`
- `HKMA aggregate balance: no qualified repository owner (data/hkma/interbank_liquidity.parquet agg_balance has unknown units and no first-known receipt)`

Either becomes measurable only after an owner store with units, release basis and a first-known receipt is registered in `config/global_liquidity_sources_v2.yml` (T03) — not inside T10.

## 8. Protocol and fitting

Stocks are treated as stocks and conditions as conditions (protocol §2.1). There is no FX fixing after `as_of`, no copied US probability, and no ChinaGate or Prophet machinery (§9). TSF is never joined with US C&I. new empirical fits use T14.

## 9. Case to test map

| Case | Test |
|---|---|
| C06 | test_c06_global_aggregate_refused_and_scalar_null |
| C19 (US law transfer) | test_c19_us_law_ids_refused_for_china_and_hong_kong |
| C19 (US scenario transfer) | test_c19_us_outlook_refused_outside_us |
| C19 (FX reserves substitute) | test_c19_fx_reserves_refused_as_pboc_balance_sheet |
| protocol §9 (FX fixing) | test_protocol9_fx_fixing_after_as_of_refused |
| regional independence | test_regional_independence_china_change_cannot_move_japan |
| Hong Kong owner | test_hk_without_owner_is_missing_input |
| local unit and FX line | test_ecb_eur_local_unit_with_separate_usd_translation |
| T08 reuse | test_us_reuses_t08_estimate_types_and_has_no_probability |
| key scan | test_payload_key_scan |

All tests live in `tests/test_global_liquidity_regional_scenarios.py`.