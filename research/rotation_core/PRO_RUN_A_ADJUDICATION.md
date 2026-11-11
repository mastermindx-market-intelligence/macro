# PRO_RUN_A adjudication (Rotation Core lead)

- **Audit:** `/home/ubuntu2/tmp/rotation-core/pro_runs/PRO_RUN_A.md`, audited at pin `a809c227e7`.
- **Adjudicated against:** `9aec219537` (the Stage D head). The engine and runner code paths A cites are unchanged between the two; only logging and report lines moved.
- **Method:** every row was decided by running a fixture, not by reading the audit's claim. `PRO_RUN_A_fixtures.py` runs A's own counterexamples against a checkout and prints observed against required values. Outputs: `PRO_RUN_A_fixtures_before_9aec219537.json` (all 18 code findings reproduce) and `PRO_RUN_A_fixtures_after_0dfec2426e.json` (none reproduces).
- **Regressions:** each fixed finding has one in `tests/test_rotation_core_evaluation.py` (39 tests pass).

| ID | A's severity | Verdict at 9aec219537 | Reproduction (observed → required) | Fix | Real-data impact on Stage D |
|---|---|---|---|---|---|
| A01 | BLOCKER | **CONFIRMED** | Closes `[100, NaN, 120…]`: +20.00% → 0.00% | Raw availability mask kept separate from valuation marks; orders defer to the next observed close and are counted | None for ETF books: no sector, sleeve or SPY close is missing inside any instrument's life (0 deferrals) |
| A02 | BLOCKER | **CONFIRMED** | Sell after +20% at 5 bp: 19.95% → 19.94% | Dollar positions and cash; fee-funded self-financing rebalance; dollar-conservation assertion | ≤ 0.06 pp/yr on any contrast |
| A03 | MAJOR | **CONFIRMED** | J4-B fee after return: 0.199 → 0.1988012 | Fee funded at execution, before the label return | J4-B −2.97% → −2.98% |
| A04 | MAJOR | **CONFIRMED** | `[100, NaN, 50, 50]`: 0% → −50% | J4 valuation marks forward-filled inside each series' life (`marked_returns`) | J4-A unchanged at the shown precision |
| A05 | MAJOR | **CONFIRMED** | Temporary final gap flagged as ended → not ended | Same marks; an ending means the series stops | Treatment (iii) still binds on zero names |
| A06 | MAJOR | **CONFIRMED** | A-NaN months dropped from B and from coverage | Independent A/B masks; coverage over all 216 scheduled formations | G6 median coverage 59.6% → 56.1% |
| A07 | MAJOR | **CONFIRMED** | 100 real + 153 filled closes counted as eligible | Eligibility counts observed closes. My first fix made XLRE/XLC eligible in 1999; caught, fixed (`0dfec2426e`) and regression-tested | None after the fix |
| A08 | MAJOR | **CONFIRMED** | False-pivot cost 0 → 0.20 | Spell span = returns dated (exit, re-entry] | False-pivot costs move by up to 0.5 pp/calm-yr (e.g. B3 3.73% → 4.25%) |
| A09 | MINOR | **CONFIRMED** | Spell crossing the sealed tail counted false → censored | Spells overlapping the tail marked undetermined | Small |
| A10 | MINOR | **CONFIRMED** | Post-close weights `[0,1,1]` → `[0,1,0]` | Simulator records post-close holdings | Terminal row only |
| A11 | MAJOR | **CONFIRMED** | `l0_ge_99pct=False` still printed L0 | Release block reports L0 NOT MET or UNVERIFIED | Check passes on real data (L0 holds) |
| A12 | MAJOR | **CONFIRMED** | Weight −0.5 accepted, +5% earned → rejected | Targets validated finite, ≥ 0, sum ≤ 1; incumbent weights range-checked | None (no negative inputs) |
| A13 | MINOR | **CONFIRMED** | VFITX → IEF switch free | Registered as a costless synthetic-proxy convention in `deviations[]` | ≈ 0.04–0.1 bp NAV once, in 2002 |
| A14 | MINOR | **CONFIRMED** | Unresolved cash gap → 0% | Missing rate stays NaN and is counted (`cash_rate_missing_days_with_cash`) | Count reported |
| A15 | MINOR | **CONFIRMED** | No J4-B terminal sensitivity | J4-B books under treatment (iii) | Identical to the primary result |
| A16 | MINOR | **CONFIRMED** | Stock files not hashed | Every consumed stock file hashed into `inputs_sha256` | Reproducibility only |
| A17 | MINOR | **CONFIRMED** | First date excluded from metric masks | Masks inclusive of the first date | One session |
| A18 | MINOR | **CONFIRMED** | p = 1/3 → 1/4 | Literal B+1 denominator; non-finite draws never count as exceedances; `ci95` returns None when undefined | None on real data |
| A19 | MINOR | **CONFIRMED** (no fix needed at the pin) | Promised intervals absent for book metrics | Presentation contract narrowed explicitly in `deviations[]` | Presentation only |

**Method notes M01–M06** are protocol matters, not code defects. They are registered in `deviations[]` without changing the frozen header:
- **M01:** the 2013 Sahm release delay.
- **M03:** intervals for the exposure-matched X contrasts are conditional on realised exposure. v2 rebuilds the matched mix inside each resample, per parent ruling A.

M02, M04, M05 and M06 are noted as interpretations.

None of A's 19 findings was refuted, and none was already fixed at the Stage D head.
