# T08 re-read — `engine/crypto_market_state.py`

Reviewer is not the author. Tree under review: `claude/cx-t08-20261012` @ `5b5cf29ae57d51ee5955971a8cc32032905bd4dc`. Parent (candidate base): `e82ba433585c3ab8f11091e8f00c81201e102207`. Diff scope: `git diff HEAD~1 HEAD` is five files; the engine edit is `engine/crypto_market_state.py` (+424/−89). No file outside that diff was edited by this re-read.

Verdict: **REQUEST_REPAIR**

## Tests at HEAD

`python -m pytest <file> -q -p no:cacheprovider` from `5b5cf29a`. No file was skipped. Pytest reported no errors (failures only).

| File | Passed | Failed | Attribution |
|---|---:|---:|---|
| tests/test_btc_decision.py | 41 | 0 | pass |
| tests/test_btc_impulse_falsifier.py | 17 | 62 | INHERITED |
| tests/test_btc_impulse_radar.py | 16 | 0 | pass |
| tests/test_btc_intraday_cvd.py | 22 | 61 | INHERITED |
| tests/test_btc_signals.py | 25 | 0 | pass |
| tests/test_crypto_cockpit_contract.py | 3 | 0 | pass |
| tests/test_crypto_collectors.py | 30 | 0 | pass |
| tests/test_crypto_wave2.py | 59 | 3 | INHERITED (NEEDS_DATA + sparse `site/`) |
| tests/test_crypto_wave3.py | 10 | 4 | INHERITED (NEEDS_DATA + sparse `site/`) |
| tests/test_okx_retail.py | 5 | 0 | pass |
| tests/test_vector_wave1.py | 10 | 0 | pass |
| tests/test_vector_r2_data_boundary.py | 7 | 1 | INHERITED (sparse `site/`) |
| tests/test_vector_r2_frontdoor.py | 14 | 1 | INHERITED |
| tests/test_crypto_market_state_semantics.py | 5 | 0 | pass (T08 suite) |
| tests/test_crypto_data_models.py | 7 | 0 | pass |

**No test fails at HEAD and passes at the parent.** Same six files fail at `e82ba433585` with the same failed-test names (`comm` head-only = 0, parent-only = 0) and the same counts.

Parent worktree: `git worktree add /tmp/cx-t08rr-20261012-base HEAD~1` → `e82ba433585`.

- `test_btc_impulse_falsifier.py`: parent `62 failed, 17 passed`. All 62 are `ModuleNotFoundError`. At the parent the package directory does not exist (`No module named 'research.crypto_science'`). At HEAD, T08 created `research/crypto_science/` for its note and patches, so the same tests fail one level down (`r3`…`r10`, including `r8_action_value_study` ×8 and `r9_prebreak_study` ×9). `git ls-tree -r HEAD` has none of those modules. `git ls-tree -r fd8095012e91` does (`r8_action_value_study.py`, `r9_prebreak_study.py`, `r10_source_qualification.py`). The candidate-base apply did not include `research/`.
- `test_btc_intraday_cvd.py`: parent `61 failed, 22 passed`. 60 × missing `research/crypto_science/r12/reference_cvd_before_price_guard.py.txt` plus one package import error. HEAD is 60 × the same missing file plus `No module named 'research.crypto_science.r10_source_qualification'`. The file is on `fd8095012e91` and on neither HEAD nor the parent.
- `test_crypto_wave2.py`: parent `3 failed, 59 passed`. `test_crypto_build_is_lightweight_and_live_wired` — `assert (None is not None)` at `tests/test_crypto_wave2.py:31` (`store.read("vector", "signals")`). `test_committed_universe_has_snapshot_provenance` — `assert 0 >= 20` at `:237` (`data/crypto_universe/market_*.parquet` absent). Both NEEDS_DATA. `test_allocation_and_strategy_legacy_urls_are_durable_redirects` — `site/vector_allocation.html` missing (sparse checkout).
- `test_crypto_wave3.py`: parent `4 failed, 10 passed`. Two tests hit the same `signals is None` assertion at `tests/test_crypto_wave3.py:19` (NEEDS_DATA). `site/nav_market.js` and `site/vector.html` are sparse-checkout misses.
- `test_vector_r2_data_boundary.py`: parent `1 failed, 7 passed`. `site/vector_chart.js` missing.
- `test_vector_r2_frontdoor.py`: parent `1 failed, 14 passed`. `AssertionError: R2 regressions are not invoked by the existing Vector CI owner` at `tests/test_vector_r2_frontdoor.py:71`. `.github/ci/legacy-jobs.yml` was not in the candidate-base apply and T08 did not touch it.

## Judgment

**Authority.** The edit adds no score, size, rank, gate, or escalation that a decision path consumes. `alt_score` is the pre-existing 0–100 display meter (`engine/crypto_market_state.py:596`); a missing share change no longer enters it as zero (`dom_30d` is required at `:589`). Grep of `engine/btc_*.py` for `crypto_market_state` / `build_market_state`: no hits. The only production caller is `scripts/build_crypto.py:469`, which writes `crypto.class_state/v1` with `"tier": "display"` and `"display_only": True` (`scripts/build_crypto.py:496-498`). New fields (`kind`, `observation`, `cap_basis`, `cap_attribution`) are labels. Module header `engine/crypto_market_state.py:1-5` still says the output does not alter Vector scores, exposure, or strategy rules.

**Missing stays unavailable on new engine paths.** Empty ETF and stablecoin frames return `value is None` and `observation == "unavailable"` (`tests/test_crypto_market_state_semantics.py:196-200`). A printed zero is `observation == "zero"` (`:183`), not a filled gap. Volume with no percentile is `"Unavailable"` (`:533-534`, locked by the test at `:256-257`). Altseason with `dominance_30d is None` keeps `value is None` (`:586-587`, test `:235-236`). `_delta(..., pct=True)` returns `None` when the base is 0 (`:45`). `level_ratio` stays `None` when it cannot be formed. A holiday stale label does not zero the 5-day sum (probe below: value stayed `50.0`).

One consumer still paints a missing altseason meter as zero: `templates/crypto.html.j2:404` uses `else 0` for the CSS rail while the numeric cell uses `else '—'`. That line is outside the engine diff. The T08 HTML patch does not change it. See finding 4.

**Thresholds.** `_MATERIAL_PCT = 1.0` (`:61`) is a percent, matching `_delta` (`:45`, `100 * (now/then - 1)`). The hero band is the literal `> 3` / `< -3` (`:418`, `:426`, `:435`, `:443`), the same cut `_direction(total_30d, 3, -3)` uses for `total_state` (`:491`). Both are in the source and in `research/crypto_science/CRYPTO_T08_CAP_FLOW_SEMANTICS_2026-10-12.md`. Neither is a field on `cap_attribution`, and `note_en` does not state the number. The 2×2 (price moved × supply moved) is internally consistent. It is applied to the wrong series. See finding 2.

**ETF holidays.** Yes, a holiday is mislabeled `stale`. `_business_day_on_or_before` (`:278-283`) walks back weekends only. The docstring at `:279` says exchange holidays are not in the cadence. `observation_status` (`:310-315`) then treats that Monday as a missed print. Probe, same function the tests import:

```
MLK Monday: last=2026-01-16 today=2026-01-19 -> stale
normal Saturday: last=2026-01-16 today=2026-01-17 -> pending
Christmas Friday: last=2026-12-24 today=2026-12-25 -> stale
Saturday after Christmas: last=2026-12-24 today=2026-12-26 -> stale
Good Friday 2026: last=2026-04-02 today=2026-04-03 -> stale
MLK etf stale Unavailable 2026-01-16 50.0
```

Counterexample: **2026-01-19** (NYSE closed, MLK Day), last Farside print **2026-01-16**. Status is `stale`, and `flows.etf.state` is forced to `Unavailable` (`:526-527`) even though Friday is the latest print the source could have made. A normal Saturday with that Friday on file is `pending`. **2026-12-26** (Saturday after Christmas Friday) is also `stale`, so a Friday holiday poisons the weekend that should be `pending`. The lane note calls this observation model supported and does not mention holidays.

**Old return keys.** No key was removed from the `build_market_state` dict. Stance strings and the three altseason state words were renamed. Grep of `scripts/build_crypto.py`, `scripts/build_vector.py`, `templates/*.j2`, and `tests/` for `Advancing with wider participation`, `Range-bound, waiting for participation`, `Alt participation broad`, `Bitcoin-led`, `Mixed participation`:

- `scripts/build_crypto.py:109-111` still maps the three old altseason words. `_state_zh` falls back to the English string (`:115`), so the new words do not raise. ZH renders as English until the builder patch. `scripts/build_vector.py` does not read them. `templates/crypto.html.j2:404` prints `state` / `state_zh` dynamically. `tests/test_crypto_wave2.py:749` passes the old phrase as a fixture and still passes.
- Hero `stance_zh` is supplied by the engine (`:615`), not by `_state_zh`.

## Findings

1. **MAJOR** — `engine/crypto_market_state.py:278-283` and `:310-315`, consumed at `:526-527`. NYSE holidays are labeled `stale` / `Unavailable`. Repair: treat full NYSE holidays as expected nonpublication (`pending`), including the following weekend when the prior session print is on file; `2026-01-19` with last print `2026-01-16` must be `pending` and must keep the 5-day direction word.

2. **MAJOR** — `engine/crypto_market_state.py:366-372` and `:409-415`, plus the valuation sentence at `:443-449`. Kind is a bitcoin price-vs-supply split (`:337-364`) and the headline narrates class total cap. Executed: price 0%, supply +2%, dominance 50→70 → `kind=issuance`, `total_30d_pct=-27.143`, stance `Market cap moved with token issuance`, note says the capitalization change tracks token supply. Second probe: price +10%, supply 0, dominance 50→75 → `kind=valuation`, `total_30d_pct=-26.67`, summary `Total market cap is lower over 30 days. That is a price change in capitalization`. Repair: emit an issuance or valuation sentence only when that leg and `total_30d` share a sign; otherwise say the class move is not explained by the bitcoin leg.

3. **MINOR** — thresholds are not on the payload. `_MATERIAL_PCT` at `:61`, hero band at `:435` and `:443`. Repair: put `material_pct: 1.0` and `hero_band_pct: 3.0` on `cap_attribution` and name them in `note_en`.

4. **MINOR** — `templates/crypto.html.j2:404` draws `--v: 0%` when `heat.altseason.value` is null. The engine returns null (`:586-587`). The T08 HTML patch does not touch this rail. Repair: omit the rail percent when the value is null. `scripts/build_crypto.py:109-111` also still lacks ZH for `ETH leading on relative trend`, `BTC leading on relative trend`, and `Mixed relative trend`; the existing builder patch already adds those three lines and is the repair.

## Patches

`git apply --check research/crypto_science/patches/cx-t08-20261012__build_crypto.py.patch` → exit 0.
`git apply --check research/crypto_science/patches/cx-t08-20261012__crypto.html.j2.patch` → exit 0.
Neither patch covers findings 1–3 or the altseason rail in finding 4.

## Verdict

**REQUEST_REPAIR.** Display tier only, and no T08 test regression. Do not ship the engine edit until finding 1 and finding 2 are fixed in `engine/crypto_market_state.py`. Findings 3 and 4 can ride with that repair.
