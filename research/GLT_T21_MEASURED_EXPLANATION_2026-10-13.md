# GLT T21 measured explanation — Liquidity & Central Banks workspace

This note documents the T21 measured-explanation change in the Liquidity &
Central Banks workspace: what is shown, what is refused, and where each
value comes from.

## 1. What the workspace now answers and refuses

The workspace now answers "what changed" for three central-bank balance
sheets (Fed, ECB, BoJ) and three dollar-funding legs (broad dollar,
high-yield spread, ten-year real yield) in MEASURED terms only: per-leg
local-unit level, the standardized contribution against that leg's own
history, the 13-week and 52-week percentage change for the central-bank
balance sheets, the producer's own coverage for monetary and funding
groups, the source release record for each leg, and a USD translation
row for ECB and BoJ flagged as never fresh money.

The workspace REFUSES on this lane (T22 owns forward-looking reading
separately): any forward-looking reading of a kind listed in item 3;
any computed USD translation value (producer publishes none, so the
row's value is `None` with a typed absence); a level row for the
funding legs (the GLT artifact publishes no funding level); a freshness
tag better than the receipt allows (re-wrapping with a later clock
never improves the rank).

## 2. The chain, one receipt per hop

1. Producer field — `site/liquiditydata/global_liquidity_transmission.json` `freshness.components.monetary.fed` (and four sibling legs): `grep -n "components" site/liquiditydata/global_liquidity_transmission.json`.
2. Build dispatch — `engine/market_os/macro_workspaces/build.py` `build_all` calls `liquidity_central_banks.compose`: `grep -n "liquidity_central_banks" engine/market_os/macro_workspaces/build.py`.
3. Composer — `compose()` in `engine/market_os/macro_workspaces/liquidity_central_banks.py`, reads `fr.components.<group>.<leg>` via `_get(g, "freshness")` and stamps the four clocks: `grep -n "_apply_leg_clocks" engine/market_os/macro_workspaces/liquidity_central_banks.py`.
4. Presenter — `lib/macro_suite_view.py` `_metrics` maps snapshot to view rows with `normalized`, `unit`, `basis`, `fx_translation`: `grep -n "_is_normalized_metric\|_strip_currency_unit\|_fx_translation_view" lib/macro_suite_view.py`.
5. Label — `lib/macro_suite_labels.py` resolves `glt_fed_monetary_contribution_z`: `grep -n "glt_fed_monetary_contribution_z" lib/macro_suite_labels.py`.
6. Template variable — `templates/_macro_suite_shell.html.j2` row block for the metric grid: `grep -n "metric-row\|mq-metric-name" templates/_macro_suite_shell.html.j2`.
7. Rendered element — `test_t21_linkage_fed_label_reaches_rendered_element` asserts `<span class="mq-metric-name"><span class="l-en">Fed balance sheet, against its own history</span><span class="l-zh">美联储资产负债表（对比自身历史）</span></span>`.

## 3. Words shown and words refused

Refused-word list: `will`, `expected`, `projected`, `forecast`,
`outlook`, `将`, `预期`, `预测`, `展望`, `预计`. None of the new strings
added by S7 contains any of those words. (Item 1 mentions them only as
things the workspace does not show.)

UNIT: `"USD billions"` "USD bn"/"十亿美元"; `"EUR billions"` "EUR bn"/"十亿欧元"; `"JPY billions"` "JPY bn"/"十亿日元"; `"local currency"` "local currency"/"本币"; `"ratio_0_1"` "share (0–1)"/"占比（0–1）".

BASIS: `"fx_translation_not_fresh_money"` "Currency translation — not new central-bank money"/"汇率折算——非央行新增资金"; `"standardized_monetary_contribution"` "Standardized contribution to the central-bank money reading"/"对央行货币读数的标准化贡献"; `"standardized_funding_contribution"` "Standardized contribution to the dollar-funding reading"/"对美元融资读数的标准化贡献"; `"trailing_13w_pct_change"` "Change over the last 13 weeks"/"近13周变化"; `"trailing_52w_pct_change"` "Change over the last 52 weeks"/"近52周变化".

DIRECTION: `"higher_more_expansionary"` "Higher = more expansionary"/"数值越高＝越扩张"; `"higher_easier_funding"` "Higher = easier dollar funding"/"数值越高＝美元融资越宽松"; `"higher_more_accommodative"` "Higher = more accommodative"/"数值越高＝越宽松"; `"higher_more_coverage"` "Higher = more coverage"/"数值越高＝覆盖越全".

METRIC (selected; full table in `lib/macro_suite_labels.py`): `"glt_fed_monetary_contribution_z"` "Fed balance sheet, against its own history"/"美联储资产负债表（对比自身历史）" and the same pattern for the other five `glt_*_contribution_z` keys; `"glt_ecb_usd_translation"` "ECB balance sheet in US dollars"/"欧洲央行资产负债表（美元折算）"; `"glt_boj_usd_translation"` "BoJ balance sheet in US dollars"/"日本央行资产负债表（美元折算）".

## 4. Clock rationale

`_apply_leg_clocks` stamps the four clocks on a per-leg metric row from
the leg receipt:

- `observed_at` ← `receipt.reference_date` (YYYY-MM-DD as published).
- `released_at` ← `receipt.available_date` (the date the source published).
- `available_at` ← `clocks.evidence_available_at_contributions[group]`
  (the producer's evidence-available-at; conservative — greater than or
  equal to every leg's release in the same group, so the workspace
  never claims a leg is knowable before the group knows it).
- `collected_at` ← `clocks.first_known_at` (the producer's
  first-known-at, the producer's record of when the dataset landed).

`calculation_as_of` is the GLT asof string passed to `_metric`
(`state.asof`, e.g. `"2026-10-09"`); not overwritten. When the leg has
no receipt, `_apply_leg_clocks` is a no-op and the four clock fields
keep the values `_metric` produced. cb_desk rows keep their own
cb_desk clocks and are NOT passed through this mapping (S5).

## 5. STEP 4 fixture table (verbatim)

Composed at `built_at 2026-10-17T00:00:00Z` from the TRACKED
`site/liquiditydata/global_liquidity_transmission.json` and the cb_desk
from `data/intl_risk/latest.json`:

```
id                                       value        unit           freshness      observed_at  released_at  available_at           collected_at
glt_fed_monetary_contribution_z          0.968795     std dev        LATE_WITHIN_TOLERANCE 2026-10-07   2026-10-08   2026-10-08T00:00:00Z   2026-10-16T18:16:51.754201Z
glt_ecb_monetary_contribution_z          0.953589     std dev        LATE_WITHIN_TOLERANCE 2026-10-02   2026-10-06   2026-10-08T00:00:00Z   2026-10-16T18:16:51.754201Z
glt_boj_monetary_contribution_z          0.830764     std dev        LATE_WITHIN_TOLERANCE 2026-09-30   2026-10-02   2026-10-08T00:00:00Z   2026-10-16T18:16:51.754201Z
glt_broad_dollar_contribution_z          -0.119342    std dev        LATE_WITHIN_TOLERANCE 2026-10-08   2026-10-09   2026-10-09T00:00:00Z   2026-10-16T18:16:51.754201Z
glt_high_yield_oas_contribution_z        -0.305917    std dev        LATE_WITHIN_TOLERANCE 2026-10-08   2026-10-09   2026-10-09T00:00:00Z   2026-10-16T18:16:51.754201Z
glt_real_yield_10y_contribution_z        -1.508251    std dev        LATE_WITHIN_TOLERANCE 2026-10-08   2026-10-09   2026-10-09T00:00:00Z   2026-10-16T18:16:51.754201Z
glt_ecb_usd_translation                  None         USD bn         NOT_COVERED    -            -            -                      -
glt_boj_usd_translation                  None         USD bn         NOT_COVERED    -            -            -                      -
cb_fed_balance_sheet_level               6747.6       USD bn         CURRENT        2026-10-07   -            -                      -
cb_fed_balance_sheet_impulse_13w         0.18         %              CURRENT        2026-10-07   -            -                      -
cb_fed_balance_sheet_impulse_52w         2.38         %              CURRENT        2026-10-07   -            -                      -
cb_ecb_balance_sheet_level               5943.9       EUR bn         CURRENT        2026-10-09   -            -                      -
cb_ecb_balance_sheet_impulse_13w         -0.45        %              CURRENT        2026-10-09   -            -                      -
cb_ecb_balance_sheet_impulse_52w         -4.12        %              CURRENT        2026-10-09   -            -                      -
cb_boj_balance_sheet_level               625025.3     JPY bn         STALE_SOURCE   2026-09-01   -            -                      -
cb_boj_balance_sheet_impulse_13w         -13.67       %              STALE_SOURCE   2026-09-01   -            -                      -
cb_boj_balance_sheet_impulse_52w         -15.13       %              STALE_SOURCE   2026-09-01   -            -                      -
glt_monetary_coverage_ratio              1            share (0–1)    LATE_WITHIN_TOLERANCE 2026-10-09   -            -                      -
glt_funding_coverage_ratio               1            share (0–1)    LATE_WITHIN_TOLERANCE 2026-10-09   -            -                      -
glt_leg_fed                              freshness=LATE_WITHIN_TOLERANCE provider='Board of Governors of the Federal Reserve System' ref_period=2026-10-07 released_at=2026-10-08 first_known_at=2026-10-08T00:00:00Z collected_at=2026-10-16T18:16:51.754201Z definition_id=WALCL definition_version=1.0.0
glt_leg_ecb                              freshness=LATE_WITHIN_TOLERANCE provider='European Central Bank via FRED' ref_period=2026-10-02 released_at=2026-10-06 first_known_at=2026-10-08T00:00:00Z collected_at=2026-10-16T18:16:51.754201Z definition_id=ECBASSETSW definition_version=1.0.0
glt_leg_boj                              freshness=LATE_WITHIN_TOLERANCE provider='Bank of Japan via FRED' ref_period=2026-09-30 released_at=2026-10-02 first_known_at=2026-10-08T00:00:00Z collected_at=2026-10-16T18:16:51.754201Z definition_id=JPNASSETS definition_version=1.0.0
glt_leg_broad_dollar                     freshness=LATE_WITHIN_TOLERANCE provider='Board of Governors of the Federal Reserve System via FRED' ref_period=2026-10-08 released_at=2026-10-09 first_known_at=2026-10-09T00:00:00Z collected_at=2026-10-16T18:16:51.754201Z definition_id=DTWEXBGS definition_version=1.0.0
glt_leg_high_yield_oas                   freshness=LATE_WITHIN_TOLERANCE provider='ICE BofA via FRED and the repo append-only archive' ref_period=2026-10-08 released_at=2026-10-09 first_known_at=2026-10-09T00:00:00Z collected_at=2026-10-16T18:16:51.754201Z definition_id=BAMLH0A0HYM2 definition_version=1.0.0
glt_leg_real_yield_10y                   freshness=LATE_WITHIN_TOLERANCE provider='Board of Governors of the Federal Reserve System via FRED' ref_period=2026-10-08 released_at=2026-10-09 first_known_at=2026-10-09T00:00:00Z collected_at=2026-10-16T18:16:51.754201Z definition_id=DFII10 definition_version=1.0.0
```

## 6. Deviations and known gaps

Closed snapshot schema: `normalized` and `fx_translation` are VIEW-row
fields, not snapshot keys. USD translation value is `None` because the
producer publishes none; the row is flagged `NOT_COVERED` and the
bilingual basis names the pair and the absence of the fixing date.
Funding legs have no level rows in this lane (GAP: producer publishes no
funding level in the GLT artifact). `_base_cb_desk()` fixture strings
differ from producer strings (GAP, documented; rescaled producer-style
fixture used by tests). `METHOD_VERSION` and `DEFINITION_VERSION` are
NOT bumped: the composition method is unchanged — T21 only adds (a)
per-leg receipt-driven clock stamping, (b) USD-translation rows, (c)
per-leg release-record source rows; all read producer fields the method
already accepted. Composite-regex ruling (orchestrator): `test (f)`'s
composite-regex count is the sum of `count_file(path)["top"]`; the
STEP 1b whole-page figure `27` lives in the drawer bucket (the six
`glt_leg_*` source rows repeat the existing
`global_liquidity_transmission.json` path in Sources details); the
spec's `(f)` comment explicitly allows this and the existing `(f)`
implementation is correct.

Review repair (2026-10-17): leg source rows now carry the leg metric
row's own freshness token; translation rows carry no observed or
reference date; the T11 preservation check collapses exactly the
reviewed T21 label strings back to BASE's fallback text and still
fails on any other edit; the goldens are untouched.

## 7. T12 vocabulary citation

This lane reuses the T12 vocabulary and presenter shape via
`lib/macro_suite_view.py` `_metrics` and `lib/macro_suite_labels.py`.
The T12 target card is referenced only (never imported):

- `mastermind:brain/liquidity_lab/target_card.py@3a265caa9b0fe6d93f133bf8176243ae96b0ea0c`

## 8. Closure

"Existing tokens and components; no new material decisions." Dark
treatment: the new rows reuse the existing metric grid and Sources
list on the dark command-center material. Light treatment: the same
rows on the existing light research-workspace material; no new CSS,
no new token, no new component.
