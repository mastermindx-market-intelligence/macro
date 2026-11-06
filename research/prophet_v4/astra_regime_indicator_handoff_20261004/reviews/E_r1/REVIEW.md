# E ROUND 1 independent review

Checkout: `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7` (DETACHED `052e02d085b0`).
Lane record: `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/` (`result.json` sha256 `5c1bbaeecd1d6807…`).
Round 0: `scratchpad/results_prev/E_r0/result.json` sha256 `a2cf30bd8337baa2…`.
Scratch: this directory (`SCR`). Checkout was not written.

## STATUS

PASS

## RESULT

**Recommended ruling: ACCEPT**

Round 1 closed K1–K12 under the pre-declared rule. `result.json` (not RESULT.md prose) has `verdict = SCOPED_NULL`, `n_tests_above_floor = 10`, empty `winners`, and eight era-cells on every test. The two INSUFFICIENT tests are participation × P1 and participation × P2. The three named mutants were applied on SCR copies and failed the named tests. B1 ROUND 3 panel/pairs shas match live parquets and the `results_prev/B1_r3` copies; the live B1 `RESULT.md` / `result.json` mismatch is the expected round-4 rewrite, not a defect of E.

### Per-item verdict

| Item | Verdict | file:line |
|---|---|---|
| K1 floor gate | FIXED | `stats.py:168` `floor_gate_eight_cells`; `result.json:1799` `n_tests_above_floor=10`; `result.json:1801` `verdict=SCOPED_NULL`; `test_E.py:272` |
| K2 bootstrap | FIXED | `stats.py:330` `np.bincount`; `result.json:1651-1652` test 12 SE/p; `test_E.py:330` |
| K3 seeds | FIXED | `run.py:138-144` `SeedSequence(20261004).spawn`; `result.json:2282-2284` identical run shas; `test_E.py:430` |
| K4 provenance | FIXED | `result.json:13-19` load=writeout=pin; `hashes.txt:1-2`; `test_E.py:553` |
| K5 citation | FIXED | `run.py:71-94` / `result.json:29-40`; `test_E.py:451`; fabricated `pd.iso_weekday_or()` gone |
| K6 negative control | FIXED | `test_E.py:357` `test_unclustered_resample_fails_cluster_invariant` |
| K7 secondaries | FIXED | `run.py:273-274`; `result.json:1806+` H21 and `1955+` 3D.p0 rows carry both era keys |
| K8 participation | FIXED | `features.py:118-119` `.where(valid)`; `test_E.py:211`; RESULT.md:24 survivorship caveat |
| K9 law conformance | FIXED | RESULT.md:278 `` `17 passed` `` (counts only); RESULT.md:300 per-test pairing deviation |
| K10 record | FIXED | RESULT.md:252-267; `result.json:2123-2131`; independent leaf diff matches lane table |
| K11 write order | FIXED | RESULT.md:278 `17 passed` / 0 skipped; hashes.txt 00:30:39 then empty DONE 00:30:42 (HOST last-act) |
| K12 disclosures | FIXED | `result.json:148-153` 7-day staleness 4696 + `regime_series_ended_late_2026`; RESULT.md:7 |
| Provenance.host | FIXED | `result.json:2287-2296`; RESULT.md:282-283 |

### Defect list

None remaining. Closing re-checks (already executed):

1. **K1.** Re-read `result.json` `tests_12[*].cells` (len==8), `n_tests_above_floor==10`, `verdict==SCOPED_NULL`; named under-floor cells 17 months @ `2014-2019/T1/EXPANSION` and 20 months @ `2014-2019/T1/CALM`; pooled-6 mutant on a copy fails `test_floor_gate_counts_eight_cells`.
2. **K2.** Production path uses `np.bincount` multiplicity; test 12 SE/p quoted vs reference; `np.isin` restore on a copy fails `test_cluster_bootstrap_matches_analytic_se`.
3. **K3.** No builtin `hash()` Call in `run.py`/`stats.py` (AST); two printed shas identical; do not re-run `run.py` against the checkout.
4. **K4.** Load sha == write-out sha == `209e2246…` / `d20cd405…`; `shasum -a 256 -c hashes.txt` from repo root, with B1 concurrency split as specified.
5. **K5.** `grep -n` each cited file:line; fragment present; `test_regime_clock_citation_resolves` in the copied suite.
6. **K6.** Negative-control test is month-clustered synthetic with unclustered SE ≥30% below clustered; mutation B on a copy fails `test_unclustered_resample_fails_cluster_invariant`.
7. **K7.** Quote one H21 and one 3D.p0 row with `era_2014_2019` and `era_2020_2026` beside pooled I.
8. **K8.** NaN SMA50 excluded from num and denom; warmup test asserts share over valid names; RESULT.md one-line survivorship caveat.
9. **K9.** RESULT.md ## Tests is counts-only; DEVIATIONS records per-test bootstrap pairing.
10. **K10.** Independent leaf diff of twelve I/SE/p plus floor fields vs round-0 `result.json`; every mover attributed; max\|ΔI\| excl. participation ≤ ~1.5e-05.
11. **K11.** Lane pytest line 0 skipped / `17 passed`; post-hoc copied suite count reported (difference = live B1 RESULT.md rewrite); hashes.txt newest hashed payload file.
12. **K12.** `drops_by_reason` names 7-day staleness for late-2026 because the regime index ends 2026-07-02 (14,479 rows).
13. **Provenance.host.** Present in `result.json` and RESULT.md ## Provenance with host + five library versions.

Notes that are **not** defects:

- Participation × P1 has a second under-floor cell `2014-2019/T3/CONTRACTION` (22 months / 8,950 events / 1,948 names). The two expected cells are present and named. The lane attributes the extra cell to the K8 SMA50-denominator / tercile-cut shift. Verdict and 10/12 floor count are unchanged.
- `grep -n 'hash('` hits `run.py:1048` inside the repair-log string `"no builtin hash();"`. That is not a Call. `test_no_builtin_hash_token_in_run_or_stats` walks the AST and passes.
- Live `results/B1/RESULT.md` and `result.json` do not match `hashes.txt` (B1 round-4 rewrite in flight). Parquets match both live and `results_prev/B1_r3`.

## EVIDENCE

Environment: `/opt/homebrew/bin/python3` 3.14.7; pandas 3.0.5; numpy 2.5.2; pyarrow 25.0.1; scipy 1.18.0; pytest 9.1.1.

Copy hashes (byte-match live `results/E/code/`):

```
c9cb0fa8184961b712245027436f4a1ebf643e83aa60c7b5f9c3dcd485f4ce47  SCR/code/features.py
860301d8fd3f55c4522325f55ebde59718e38d73fa2d6332da42d8e098177c0e  SCR/code/run.py
d56f5fd2be6ce73f32902c66dc738b1c340966d879072653871eed2fbbd61110  SCR/code/stats.py
d32f28b9e9f2bf343edf7a8b1e6b6f3052969ce6fbbe9e6a160a8efc19e28d40  SCR/code/test_E.py
5c1bbaeecd1d6807a5a0a02b1bcb8a78e13ba0e23a77db8cb8993f293b001a45  results/E/result.json
006803c35f7712dbd9683f076455dee0576dc03e5f8b53f0013a67096b4137e5  results/E/RESULT.md
a2cf30bd8337baa29380aa5d5e25822a6c0daa208d2b5c5915fcb600f52bbcee  results_prev/E_r0/result.json
```

### K1 floor gate — FIXED

`result.json` (machine record, not prose):

- `verdict_rule` written as a constant (`result.json:5`) requiring eight `(T1,T3)×state×era` cells, SCOPED NULL if no winner and ≥8/12 above floor.
- `n_tests_above_floor`: **10** (`result.json:1799`)
- `verdict`: **SCOPED_NULL** (`result.json:1801`)
- `winners`: `[]`
- every `tests_12[i].cells` length **8**
- no test has `p_holm < 0.05` (test 12 is the smallest Holm at 0.816). Mechanical winner rule: no winners, 10/12 above floor → SCOPED_NULL.

INSUFFICIENT tests and failing cells from `result.json`:

- participation × P1_growth (`result.json:1024-1039`): `floor_pass=false`; failing `2014-2019/T1/EXPANSION` (**17 months**, 6,587 events, 1,864 names) and extra `2014-2019/T3/CONTRACTION` (22 months, 8,950 events, 1,948 names).
- participation × P2_stress (`result.json:1150-1164`): `floor_pass=false`; failing `2014-2019/T1/CALM` (**20 months**, 14,616 events, 1,944 names).

`test_floor_gate_counts_eight_cells` (`test_E.py:272-288`) builds a synthetic frame with 17 months on `2014-2019/T1/EXPANSION`, asserts `floor_pass is False`, that cell named, `len(cells)==8`, and that `floor_gate_pooled_six_MUTANT` returns `(True, 6)`.

Mutant (SCR/mut_k1): production `floor_gate_eight_cells` return replaced with the pooled-6 `floor_pass`. Suite (hashes deselected to isolate):

```
FAILED .../mut_k1/code/test_E.py::test_floor_gate_counts_eight_cells - assert True is False
1 failed, 15 passed, 1 deselected in 2.06s
```

Failing test named: **`test_floor_gate_counts_eight_cells`**.

### K2 bootstrap — FIXED

Production (`stats.py:327-332`):

```
if mode == "weight":
    for k in range(n_draws):
        drawn = rng.integers(0, n_m, size=n_m)
        w = np.bincount(drawn, minlength=n_m).astype(float)
        out[k] = _I_from_month_weights(w, sum_y, cnt)
```

`np.isin` remains only in `mode == "isin"` (round-0 mutant used by tests).

Test 12 structure × P2_stress (`result.json:1644-1652`) beside reviewer reference:

| | I | SE | CI lo | CI hi | raw p |
|---|---:|---:|---:|---:|---:|
| record | −0.00686653 | **0.00390222** | −0.01453099 | +0.00044147 | **0.068** |
| reference (1,000 draws) | — | 0.00383 | −0.01477 | +0.00013 | 0.058 |

SE is close to 0.0038; raw p is close to 0.06. Round-0 (unrepaired isin) was SE 0.00289189 / p 0.014 — the ~25% SE understatement is gone.

`test_cluster_bootstrap_matches_analytic_se` exists (`test_E.py:330`): synthetic month-clustered series; weighted bootstrap SE within 10% of analytic cluster SE; isin path must miss the 10% gate.

Mutant (SCR/mut_k2): `mode=="weight"` body restored to `np.unique` + `np.isin` keep-mask.

```
FAILED .../mut_k2/code/test_E.py::test_cluster_bootstrap_matches_analytic_se
  AssertionError: weighted SE 0.00905 vs analytic 0.01230 rel=0.264
  assert 0.2640392872606964 < 0.1
FAILED .../mut_k2/code/test_E.py::test_unclustered_resample_fails_cluster_invariant
  assert (abs(se_c - analytic) / analytic) < 0.1
2 failed, 14 passed, 1 deselected in 2.49s
```

Named failing test for the isin restore: **`test_cluster_bootstrap_matches_analytic_se`** (collateral: the cluster-invariant test, because clustered SE is now the isin SE).

### K3 seeds — FIXED

`grep -n 'hash('` on `run.py` and `stats.py`:

```
run.py:1048:               "how": "SeedSequence(20261004).spawn; no builtin hash(); two-pass sha recorded"},
```

One prose token in `k_repair_lines()`, not a Call. `test_no_builtin_hash_token_in_run_or_stats` (`test_E.py:430`) AST-walks both files and passed on the copy.

Seeding (`run.py:136-144`):

```
root = np.random.SeedSequence(SEED_BASE)          # SEED_BASE = 20261004
primary_ss, h21_ss, sec_ss, ctx_ss = root.spawn(4)
"primary": [np.random.default_rng(s) for s in primary_ss.spawn(12)],
"h21":     [... h21_ss.spawn(12) ...],
"sec":     [... sec_ss.spawn(12) ...],
"ctx":     [... ctx_ss.spawn(24) ...],
```

Indexed by fixed test position; separate spawns for H21 / 3D.p0 secondaries / context.

RESULT.md:280 and `result.json:2282-2284`:

```
cb16e951115df666c21ca164440b80e5beef9e3df9c982cde30a6998a471b92d
cb16e951115df666c21ca164440b80e5beef9e3df9c982cde30a6998a471b92d
byte_identical=True
```

`run.py` has no output-directory override (only `E_REPO`, which still writes `results/E/` under that repo). Did **not** re-run `run.py`. Determinism check is the two printed shas (12-test core, not full `result.json`).

### K4 provenance — FIXED

`result.json:13-19`:

```
panel_sha256          209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8
panel_sha256_load     209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8
panel_sha256_writeout 209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8
pairs_sha256          d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae
pairs_sha256_load     d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae
pairs_sha256_writeout d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae
```

Load == write-out == pin. `inputs.b1_round = 3`, `n_1d_rows = 296637`. RESULT.md:1 says **B1 ROUND 3 panel**; grep for `round-1 panel` / `ROUND-1` under results/E returned no matches.

`hashes.txt` pins both shas on lines 1–2.

`cd <repo-root> && shasum -a 256 -c .../results/E/hashes.txt`:

```
.../B1/events_panel.parquet: OK
.../B1/confirmation_pairs.parquet: OK
data/regime/regime_v2_pit.parquet: OK
.../B1/code/universe_manifest.json: OK
.../B1/RESULT.md: FAILED
scripts/build_regime_v2_pit.py: OK
engine/inputs.py: OK
.../E/result.json: OK
.../E/RESULT.md: OK
.../E/code/{run,features,stats,test_E}.py: OK
shasum: WARNING: 1 computed checksum did NOT match
```

Concurrency split for the FAILED line (`fe0460d803d0a90e…` pinned):

| file | pin | live | `results_prev/B1_r3` |
|---|---|---|---|
| events_panel.parquet | 209e2246… | **OK** 209e2246… | **OK** 209e2246… |
| confirmation_pairs.parquet | d20cd405… | **OK** d20cd405… | **OK** d20cd405… |
| B1/RESULT.md | fe0460d8… | FAIL (rewritten; observed 55521988… then 073a47a0… then 4d4221ed…) | **OK** fe0460d8… |
| B1/result.json | (not pinned) | 2aa490bf… then e480d73a… | 0deef95b… |

Parquet mismatch against both would be a defect; it is not. RESULT.md/result.json live-only mismatch is the expected B1 round-4 rewrite.

`test_hashes_txt_verifies` is in the suite. On the SCR copy against the live checkout it failed on B1/RESULT.md only (same concurrency). Against the frozen B1_r3 bytes the pin verifies.

### K5 citation — FIXED

Citations in `result.json["regime_clock"]` and RESULT.md:5-13. `grep`/sed on the checkout:

```
scripts/build_regime_v2_pit.py:376
  f_pit = build_features(overrides=overrides)

engine/inputs.py:171
  idx = pd.bdate_range(closes.index.min(), end)

engine/inputs.py:262-267
  cyc = basket_index(closes, g["cyclical_basket"]).reindex(idx).ffill(limit=5)
  dfn = basket_index(closes, g["defensive_basket"]).reindex(idx).ffill(limit=5)
  ...
  ib_long = basket_index(...).reindex(idx).ffill(limit=5)
  ib_short = basket_index(...).reindex(idx).ffill(limit=5)

scripts/build_regime_v2_pit.py:103-105
  def pit_availability_panel(vintages: pd.DataFrame, sid: str) -> pd.Series:
  """... Reindex+ffill of this panel gives, on every date d, exactly
```

Quoted fragments are substrings of those lines. `test_regime_clock_citation_resolves` (`test_E.py:451-458`) opens each cited file:line and asserts the fragment; it passed on the copy. `iso_weekday_or` is absent from RESULT.md and `regime_clock` (only appears in the test that forbids it).

### K6 negative control — FIXED

`test_unclustered_resample_fails_cluster_invariant` (`test_E.py:357-387`): month-correlated synthetic (`sigma_u=0.03`); clustered `mode="weight"`; unclustered `mode="row"`; keep-all `mode="keep_all"`. Asserts `se_row <= se_c * 0.70` (≥30% below), clustered within 10% of analytic, unclustered and keep-all outside 10%. Real negative control, not a finiteness check.

Mutation B (SCR/mut_k6): `mode=="weight"` replaced by keep-all-months (`out[k] = obs`).

```
FAILED .../mut_k6/code/test_E.py::test_cluster_bootstrap_matches_analytic_se
  AssertionError: weighted SE 0.00000 vs analytic 0.01230 rel=1.000
FAILED .../mut_k6/code/test_E.py::test_unclustered_resample_fails_cluster_invariant
  AssertionError: unclustered SE 0.00165 is not ≥30% below clustered 0.00000
2 failed, 14 passed, 1 deselected in 1.73s
```

Failing tests named: **`test_unclustered_resample_fails_cluster_invariant`** (packet name) and **`test_cluster_bootstrap_matches_analytic_se`** (clustered SE collapsed to 0).

### K7 secondaries — FIXED

H21 trend × P1 (`result.json:1808-1816`) beside pooled I:

```
observed 0.00875263  era_2014_2019 0.01252122  era_2020_2026 0.00730810
```

3D.p0-confirmed trend × P1:

```
observed 0.00523278  era_2014_2019 0.00313999  era_2020_2026 0.00621709
```

All 12 H21 rows and all 12 3D.p0 rows carry both era keys with finite values.

### K8 participation — FIXED

`features.py:118-119`: `cond = (roll["close"] > roll["sma50"]).where(valid)` with `valid = sma50.notna() & close.notna()`. NaN SMA50 is excluded from numerator and denominator.

`test_participation_excludes_sma50_warmup` (`test_E.py:211-229`): name B in SMA50 warm-up on dates 0–1; share on date 0 is **1.0** (valid names only), not 0.5.

RESULT.md:24: “Participation survivorship caveat: the date-level share's denominator is names with a *valid* SMA50 on that date (warm-up NaNs excluded from both num and denom, K8).”

### K9 law conformance — FIXED

RESULT.md ## Tests (line 278): `` `17 passed` `` — counts only, no wall time. (`result.json:2299` keeps `17 passed in 2.19s` for the machine record.)

RESULT.md ## Deviations (line 300): “Bootstrap draws are per test (SeedSequence(20261004).spawn(4) then spawn(12) per branch); pairing holds within a test, not across all 12 cells (K9).” Same text in `result.json:2307`.

### K10 record — FIXED

RESULT.md:252-267 prints every round-0 headline beside round-1 I/ΔI/SE/p/floor. Movers named: panel r2→r3 −32 1D rows; bootstrap repair SE/p (structure × P2: r0 SE 0.00289 / p 0.014 → r1 SE 0.00390 / p 0.068); floor repair verdict INSUFFICIENT_SUPPORT 0/12 → SCOPED_NULL 10/12. `max|ΔI|` excluding participation = **1.46e-05** (structure × P1), within ≲ 1.5e-05. Participation ΔI is larger (−8.61e-04 / +1.00e-04) from K8.

Independent leaf diff vs `results_prev/E_r0/result.json` (I, SE, p, floor):

```
fam            part              I0           I1           dI        SE0     SE1      p0     p1   fl0    fl1
trend          P1_growth   +0.00226887  +0.00226523  -3.641e-06  0.00359  0.00454  0.558  0.616  False  True
trend          P2_stress   -0.00508344  -0.00507638  +7.061e-06  0.00269  0.00348  0.078  0.154  False  True
momentum       P1_growth   -0.00144928  -0.00145006  -7.760e-07  0.00328  0.00434  0.702  0.894  False  True
momentum       P2_stress   -0.00462703  -0.00463187  -4.831e-06  0.00275  0.00362  0.094  0.192  False  True
compression    P1_growth   -0.00159534  -0.00159541  -7.100e-08  0.00233  0.00303  0.552  0.534  False  True
compression    P2_stress   +0.00229997  +0.00229804  -1.922e-06  0.00220  0.00280  0.338  0.460  False  True
participation  P1_growth   +0.00580250  +0.00494199  -8.605e-04  0.00420  0.00566  0.158  0.388  False  False
participation  P2_stress   +0.00013547  +0.00023581  +1.003e-04  0.00390  0.00492  1.000  0.944  False  False
rs             P1_growth   +0.00043525  +0.00042969  -5.560e-06  0.00323  0.00408  0.946  0.858  False  True
rs             P2_stress   -0.00125254  -0.00124944  +3.094e-06  0.00241  0.00299  0.622  0.698  False  True
structure      P1_growth   +0.00214568  +0.00213112  -1.456e-05  0.00359  0.00470  0.574  0.598  False  True
structure      P2_stress   -0.00687242  -0.00686653  +5.883e-06  0.00289  0.00390  0.014  0.068  False  True
max|dI|=8.605072e-04  max|dI| excl participation=1.455942e-05
```

Lane `round0_comparison.rows` ΔI / round0_I / round1_I / round1_se / round1_p match this diff at 1e-18 on all twelve rows. Floor field: r0 `n_tests_above_floor=0` / `INSUFFICIENT_SUPPORT` → r1 `10` / `SCOPED_NULL`. No unexplained mover. SE/p movement is the K2 repair (every SE rose); I movement excl. participation is the panel swap.

### K11 write order — FIXED

Lane pytest line (RESULT.md:278, `result.json:2300`): **`17 passed`**, 0 skipped. Write order in `run.py:1160-1191`: json/md → pytest → fold counts → rewrite json/md → `write_hashes_txt()` → post-hoc pytest (stdout only, no json rewrite) → empty DONE.

Timestamps `results/E/`:

```
00:30:18 RESULT.md
00:30:28 result.json
00:30:39 hashes.txt
00:30:42 DONE          (HOST: empty DONE is the very last act)
```

`hashes.txt` is the newest hashed payload file. DONE is 3s later as required by the HOST addendum.

Post-hoc copied suite (`E_REPO` → checkout, `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest SCR/code -q -p no:cacheprovider`):

```
................F
FAILED test_hashes_txt_verifies — hash mismatch for .../B1/RESULT.md
  - fe0460d803d0a90eff60cbcceff4e8ab177bbd9f11c3dc3599ed8b3a1e81bfca
  + 55521988f8daea6016b0f6286f8f5d4a5f9853ad06f763ee2b10a8de356d2143
1 failed, 16 passed in 2.13s
```

Excluding that concurrency line: **`16 passed, 1 deselected in 2.04s`**. Difference vs the lane's `17 passed` is solely `test_hashes_txt_verifies` against the live B1 RESULT.md rewrite. The other 16 invariants pass on the copy.

### K12 disclosures — FIXED

`result.json:142-153`:

```
no_prior_regime_row              0
match_older_than_7d              4696
regime_series_ended_late_2026    4696
```

RESULT.md:7: “Regime file index is business-daily 1971-01-04..2026-07-02 (14,479 rows). Late-2026 events whose prior regime row is older than 7 calendar days are dropped under `match_older_than_7d` because the PIT series ends on 2026-07-02 (K12).” `regime_clock.regime_index` records freq/start/end/n_rows=14479.

### Provenance.host — FIXED

`result.json:2287-2296`:

```
hostname m2studio
python 3.14.7  /opt/homebrew/opt/python@3.14/bin/python3.14
pandas 3.0.5; numpy 2.5.2; pyarrow 25.0.1; scipy 1.18.0; pytest 9.1.1
```

RESULT.md ## Provenance (line 282-283): same host + five library versions + `repo_head 052e02d085b01f29baf499357e224c836d8eb224`.

### Copied-suite baseline (non-mutant)

```
E_REPO=<checkout> PYTHONDONTWRITEBYTECODE=1 python3 -m pytest SCR/code -q -p no:cacheprovider
1 failed, 16 passed in 2.13s     # failure = B1 RESULT.md live rewrite
-k 'not test_hashes_txt_verifies'
16 passed, 1 deselected in 2.04s
```

## GAPS

- Did not re-run `run.py`. It has no output-directory override (`E_REPO` still writes `results/E/` under the repo). Full `result.json` byte-identity across two live runs was not re-computed; the determinism check is the two printed 12-test-core shas (`cb16e951…` == `cb16e951…`).
- Post-hoc `test_hashes_txt_verifies` cannot pass against the live checkout while B1 round-4 is rewriting `results/B1/RESULT.md`. Verified the pin against `results_prev/B1_r3/RESULT.md` instead. Parquets were OK on both.
- The two printed shas hash the 12-test core, not the entire `result.json` (which also contains pytest wall-time text).
- Did not independently recompute the 1,000-draw bootstrap on the full panel (forbidden: that is `run.py`). Test 12 SE/p closeness is a record-vs-reference comparison, not a reviewer re-draw.

## DEVIATIONS

- Tests on the SCR copy cannot derive the repo from `CODE_DIR.parents` (that walk lands in the scratchpad). Ran with `E_REPO=<checkout>`. Copied `result.json`, `RESULT.md`, and `hashes.txt` into `SCR/` (and each mutant parent) so tests that read `RESULTS_DIR = CODE_DIR.parent` see the record without touching the checkout.
- Mutant runs deselected `test_hashes_txt_verifies` after the full baseline had already shown that single concurrency failure, so mutant-caused failures could be named cleanly. Full baseline (with hashes) was still run.
- Mutants were applied with Python string replacement on SCR copies (`mut_k1`, `mut_k2`, `mut_k6`), not `sed`.
- `grep -n 'hash('` is not empty (`run.py:1048` prose). Treated as non-defect because the AST Call check is the seeding invariant and passed.
- Did not treat the extra participation × P1 under-floor cell as a defect: both expected cells are named, n_above=10, verdict SCOPED_NULL, and the lane disclosed the extra cell as a K8 tercile-cut consequence.
