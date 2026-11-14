# Per-share numeric precision — focused proof (2026-11-08)

## Outcome and scope

The accepted V2 P3 witness supplies `2.18 USD/share` with `basis=per_share`. The existing raw formatter emits `2.2 USD/share` in both English and Chinese. The candidate preserves `2.18` and finer represented precision in the two unscaled amount branches. It does not derive an EPS forecast or change the frozen quantity, copy-template, unit-map, identity, evidence, ranking, sizing, or rollout contracts.

Source pin: `mastermindx-market-intelligence/macro@523e01d7d7d0835a2a18421eeae75dc02c0c939d`. Protected procedure pin reused: `Mastermind@1981aea5122943ce59d7ebe9706ddf5a658b377d`. Parent completion directive: [Macro #10244](https://github.com/mastermindx-market-intelligence/macro/pull/10244). Current exact-path open-PR search found no competing `prophet_adapter` carrier; the adjacent earnings binder PR #10468 has disjoint files.

## Why this is compatible with the frozen rule

`contracts/news_impact/copy_templates.v1.json` reserves one-decimal formatting for the scaled billion/million presentation and otherwise specifies a raw value with its unit. `news_impact_event.v1.schema.json` already admits `per_share` and numeric point/range values without a two-decimal limit. No frozen file is changed. The quantity schema remains SHA-256 `3edc71399f6b89411e6db128cce29a53e1a2cf15f9fd1e9bda2259c3d0dcf822`.

`engine/news_impact/prophet_adapter.py` uses the supplied `basis` to preserve an unscaled per-share number with fixed-point `Decimal(str(abs(value)))` formatting. Only fractional trailing zeros are removed. This preserves the represented value, not the source's unknown lexical decimal-place precision. Existing scale selection, currency/unit labels, signs, bounds, recursive range handling, boolean/non-numeric rejection and slot-length refusal remain in place. Non-finite raw per-share inputs still fail closed. Total amounts and basis-absent amounts retain their existing output.

## Verification

The 12 copied source/contract/test dependencies were checked against their pinned Git blob identities before execution. The original two affected modules pass 152 tests. Twenty added cases protect raw cents and finer decimals, tiny negative values, large integer precision, USD and JPY units, explicit scale units, zero, range bounds/signs, non-finite refusal, and unchanged scaled USD behavior. Against the original formatter, 13 new cases fail on lost precision and seven controls pass. Against the candidate:

```sh
python -m pytest tests/test_news_impact_f2_amount_format.py tests/test_news_impact_prophet_adapter.py -q
# 172 passed in 1.25s
```

Both test modules are already owned by the existing News Impact CI job. No new workflow or job, test exclusion, threshold change, contract relaxation or producer execution is introduced. A separate reasoning inspection checked the frozen rule, quantity shape, true adapter path and non-finite edge; this is not a GitHub approval.

## Limits and remaining V2 obligation

A focused execution of the accepted V2 fixture helpers plus the actual validator reproduces `base_t2_valid=true` and `claim_period_mismatch_refused=false` for its FY27 / Q3 2027 containment witness. The same supplied EPS object now formats as `2.18 USD/share` in both locales. This subset is not a replay of the complete V2 proof.

Only the precision subcheck is repaired. V2 P3 remains PARTIAL because the period witness is still admitted; its expected verdict and the seven-journey acceptance census are unchanged. Accounting-basis, fiscal-week, prior/consensus separation, live consumer wiring and production acceptance are separate obligations. This patch does not open the pure-leaf Prophet adapter's rollout gate, change the accepted DEFENSIBLE_NEGATIVE quantitative disposition, or alter the 600 / 74 / 135 / 40 routing-pending / 0 prospective populations.

