# R15fix — withheld position instead of a silent zero (2026-10-12)

Defect on origin/main `c5a79a69826`, `scripts/build_vector.py`: `alloc_equity` (722–725) and `scorecard` (728–730) both do `pos = alloc.shift(1).reindex(ret.index).ffill().fillna(0)`. A NaN that survives `ffill` becomes a zero position: flat equity, and that day counts as a zero-return observation.

## Rows `fillna(0)` still touches

`ffill` leaves only a leading NaN prefix. Six-row proof is in the lane packet. Summary:

- Leading NaNs plus one internal hole: `fillna(0)` touches the three rows before the first non-null *shifted* allocation. The internal hole is carried (the shifted NaN becomes the previous weight). It is not a `fillna(0)` row.
- All-present: only the `shift(1)` first row.
- All-null: every row.
- Internal holes only: only the `shift(1)` first row.

## Patch

`research/crypto_science/patches/cx-r15fix-20261012__build_vector.py.patch` (`git apply --check` passed).

Rows strictly before the first in-index non-null allocation are withheld. Equity is NaN there (a gap), then the original one-liner on the trimmed window. `scorecard` uses that same one-liner and adds `withheld_days`. All-null: `withheld_days == len`, every metric NaN, never 0.

The `shift(1)` row of the first *observed* allocation stays 0. That is the no-prior-day lag, not a missing print. Keeping it is what makes an all-present series bit-identical (`withheld_days == 0`). `ffill` carry of later holes is unchanged.

Consumer-safe edits in the same patch (a NaN equity point would otherwise raise, or publish a fake 0):

- `alloc_sizing` (765, 778–780): `dropna` before `cummax`. A finite curve matches the old brake. An empty curve reports the brake unavailable (`None`) instead of `round(NaN)`.
- Shadow strip (4101–4102, 4114–4115): `dropna` before the ratio, and raise into the existing handler when the window is entirely withheld, so `regret or 0` cannot print 0pp. A fully finite window is unchanged.
- View-model `cards` (4839): non-finite metrics become JSON null. Finite cards are unchanged. `templates/vector.html.j2` 599–600 reads only `data-m` and ignores `withheld_days`.
- `emit_risk_strategy_json` (209) still `fillna(0.0)` on its chart copy. `site/vector_chart.js` 133, 137 and 168 multiply every equity point and `toFixed` every alloc point; null becomes 0 or throws. The scorecard path (4310) does not pre-fill.

## Tests — the mutation each one kills

1. Leading-gap days counted as zero-return (`in_market` / sharpe) and a flat 1.0 equity through the gap. Strict xfail until the patch is applied.
2. Any change to the all-present one-liner. No marker. Passes before and after. `withheld_days`, if present, is 0.
3. A silent exclusion, or counting an `ffill`-carried internal hole as withheld. `withheld_days` equals the leading missing rows only. Strict xfail until applied.
4. All-null allocation published as 0% CAGR, 0 in-market, or a flat 1.0 equity. Strict xfail until applied.

## Consumers checked

Callers in `scripts/build_vector.py`: `emit_risk_strategy_json` 211; shadow 4097–4098; live equity 4306 into `alloc_sizing`; `cards` 4310 into `templates/vector.html.j2` 548 and 599–600. Chart reader: `site/vector_chart.js` 132–137 and 220.

Not callers. Separate copies that still `fillna(0)`: `scripts/build_override_shadow.py` 50–58 and `scripts/btc_gate_attribution_phase0.py` 68–71. `chart_risk_vs_strategy` (1191) is uncalled; `eq.iloc[0]` at 1221 would not tolerate a leading gap.

## Unchanged

Allocation values, signals, and the live brake on a finite equity curve. `ffill` carry. No new score and no sizing authority. Display-tier scorecard only.

MAJOR-1 of the R15 audit (missing-history test in `tests/test_crypto_wave2.py`) is not addressed here. The seat applies the patch; `build_vector.py` is shared.
