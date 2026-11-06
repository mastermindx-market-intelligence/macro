# SNI shared library equivalence with shipped S1/S2

This is an SNI-local comparison of `sni_inference` and `sni_seal` against the
lane-local S1 residual and S2 event-response code already on the INT1 branch.
The libraries consume caller-supplied opaque identity strings and counts; they
do not mint issuer or security identifiers and they do not feed a rank, gate,
size, signal, escalation, or trade path.

## Summary

(a) yes — one-sided binomial p-values agree for every (k, n) with 1 <= n <= 300 and 0 <= k <= n; max absolute difference 8.881784197001252e-16 (shared vs S1 at k=63, n=270). Shared vs S2 max absolute difference 6.661338147750939e-16 (k=0, n=95).

(b) yes — the shared sign test agrees with S1's sign test wherever both are defined (0 <= pos, neg <= 120 except pos=neg=0); max absolute difference 5.551115123125783e-16 at (pos, neg)=(79, 71). At pos=neg=0 S1 returns 1.0 and the shared library raises ValueError("sign test on zero non-tied observations is not estimable").

(c) no — `sni_seal.canonical_json` is not byte-identical to S1's `s1_prereg.canonical_json` on any fixture. First differing fixture: empty_dict (`{}`). Shared encoding is S1's compact sorted JSON plus a trailing newline.

## Agreement table

| Function pair | Domain tested | Max abs diff | Verdict |
|---|---|---|---|
| `sni_inference.binom_p_one_sided_greater` vs `s1_stats.binom_p_one_sided_greater` | all 45450 cells 1<=n<=300, 0<=k<=n, p0=0.5 | 8.881784197001252e-16 | agree within 1e-12 |
| `sni_inference.binom_p_one_sided_greater` vs `s2_stats.binomial_one_sided_greater` | same 45450 cells | 6.661338147750939e-16 | agree within 1e-12 |
| `sni_inference.sign_test_two_sided` vs `s1_stats.sign_test_two_sided` | 14640 cells 0<=pos,neg<=120 with n=pos+neg>0 | 5.551115123125783e-16 | agree within 1e-12 |
| `s2_stats.hit_rate_test` unrounded `binomial_one_sided_greater(k,n)` vs shared one-sided binomial | empty / all-0 / all-1 / alternating / 50 lists from `random.Random(20261013)` | 8.88e-16 class (same as the binomial pair) | unrounded p agrees within 1e-12; stored `p_value` is `round(p, 6)` |
| `s1_stats.mirror_mean_ci` vs `s2_stats.mirror_trick_ci` | 20 seeded (values, cluster_keys) inputs | 0 (identical lists, including None) | same estimator (engine `block_bootstrap_ci`, 800 draws, seed 7, 4-decimal bounds) |
| `sni_inference.cluster_mean_ci` vs S1/S2 mirror CI | same 20 inputs | not a shared estimator | properties only: empty and one cluster abstain/None; two or more clusters give finite lo<=hi |
| `sni_seal.canonical_json` vs `s1_prereg.canonical_json` | 28 fixtures (nested dicts, key order, NFC/NFD, 1 vs 1.0, -0.0, empty containers, long strings, lists of dicts) | n/a (bytes) | every finite fixture differs by a trailing newline only |
| committed S1 p-values vs shared recompute | 144 (k,n) or (pos,neg) fields in four result JSON files | 5.551115123125783e-16 | agree within 1e-12 |
| `sha256_text(sni_seal.canonical_json(s1_prereg.build_spec()))` vs committed S1 prereg digest | `runs/s1_residual/results/P01.json` (and the same digest on P02 and the S1 seals) | n/a (hex) | differs |

## Differences

### Sign test at pos = neg = 0

- Input: `pos=0`, `neg=0`.
- `s1_stats.sign_test_two_sided(0, 0)` returns `1.0`.
- `sni_inference.sign_test_two_sided(0, 0)` raises `ValueError("sign test on zero non-tied observations is not estimable")`.
- For every other (pos, neg) in 0..120 the two functions agree within 1e-12. S1 doubles the larger tail `2 * P(X >= max(pos,neg))` capped at 1; the shared function uses `min(1, 2 * min(P[X>=pos], P[X<=pos]))`. At p0=0.5 those formulas match when n>0.

### S2 `hit_rate_test` rounding and empty list

- Empty list: `s2_stats.hit_rate_test([])` raises `ValueError("n must be >= 1")` because `binomial_one_sided_greater` requires n>=1. The shared one-sided binomial accepts `k=0, n=0` and returns 1.0; this lane does not call it that way for the empty-list case.
- Non-empty lists: S2 stores `"p_value": round(raw, 6)`. Example from seed 20261013: k=18, n=40, shared raw 0.7852047460783069, S2 reported 0.785205. The unrounded S2 binomial matches the shared function within 1e-12.

### Bootstrap / mirror CI — not the same estimator

S1 `mirror_mean_ci` and S2 `mirror_trick_ci` are the same estimator:

- resampling unit: unique cluster labels (stamp dates) via `engine.grading_stats.block_bootstrap_ci`;
- construction: D9/E9 mirror panel `dates=concat(k,k)`, `vals=concat(x,-x)`, `mask=concat(1,0)`, so the gap statistic equals mean(x);
- draws: 800 (`BOOT_DRAWS`);
- seed: 7 (`BOOT_SEED`) through `numpy.random.default_rng`;
- percentile: `numpy.percentile` at 2.5 and 97.5;
- bounds rounded to 4 decimal places;
- returns `None` when there are no observations or fewer than 2 unique cluster labels.

`sni_inference.cluster_mean_ci` is a different estimator:

- resampling unit: clusters grouped by `(type name, repr)` and sorted, then `random.Random(seed).choices`;
- statistic: mean of every observation in the sampled clusters (no mirror panel);
- default draws 2000, default seed 0;
- percentile: linear interpolation at `(alpha/2, 1-alpha/2)`;
- no 4-decimal rounding;
- abstains with `ABSTAIN_NO_EPISODES` on empty input and `ABSTAIN_INSUFFICIENT_CLUSTERS` when cluster count is below `min_clusters` (default 2).

On the 20 seeded inputs, S1 and S2 returned identical values. Shared vs S1/S2 matched after 4-decimal rounding on some inputs (empty, one cluster, two_clusters, several random draws) and differed on others (example: input `r1`, shared lo/hi about -0.0633 / 0.3732 vs S1/S2 `[-0.0733, 0.3575]`). The tests assert only the promised properties (None/abstain below two clusters; `lower <= upper` when both sides produce an interval).

### Canonical JSON trailing newline and non-finite floats

- `sni_seal.canonical_json` is `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"`.
- `s1_prereg.canonical_json` is the same dumps without `allow_nan=False` and without the trailing newline.
- `s2_seal.canonical_json` matches S1 (no newline, `allow_nan` left at the json default).
- First differing fixture: empty_dict. SNI bytes `b'{}\n'`; S1 bytes `b'{}'`.
- On all 28 finite fixtures the bodies match and SNI is exactly S1 plus `b"\n"`. NFC vs NFD stay distinct in both encodings; `1` vs `1.0` stay distinct.
- NaN: SNI raises `ValueError("canonical_json requires finite floats (no NaN or inf)")`; S1 returns `'{"x":NaN}'`.
- +inf: SNI raises the same error; S1 returns `'{"x":Infinity}'`.
- -inf: SNI raises the same error; S1 returns `'{"x":-Infinity}'`.

### S1 prereg digest

Committed digest in `runs/s1_residual/results/P01.json` (also P02 and `SEAL_AND_BUDGET.json`, and the v1.1 copies): `c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab`.

- `s1_prereg.prereg_digest(build_spec())` equals that committed value.
- `sha256_text(sni_seal.canonical_json(s1_prereg.build_spec()))` equals `a961ac90b0347eabe16b044900d9283c66bae715894a5742642d2daac5e979c2`.
- Result: differs. Cause: the extra trailing newline in `sni_seal.canonical_json`. Stripping that newline recovers the committed digest. Comparable, and not equal.

## Reproduced committed values

Count: 144 p-values recomputed with the shared library, all within abs 1e-12 of the committed number (max abs 5.551115123125783e-16).

Files that carry p-value together with k/n or pos/neg:

- `research/single_name_intelligence/runs/s1_residual/results/P01.json` — 24 (H0_1 binomial hits/n and H0_2 sign pos/neg)
- `research/single_name_intelligence/runs/s1_residual/results/P02.json` — 48
- `research/single_name_intelligence/runs/s1_residual_v1_1/results/P01.json` — 24
- `research/single_name_intelligence/runs/s1_residual_v1_1/results/P02.json` — 48

Files with no p-value field (so none reproduced):

- `research/single_name_intelligence/runs/s1_residual/results/P03.json` and `.../s1_residual_v1_1/results/P03.json` — incremental-explanation `delta_R2` / verdict, no p-value
- `research/single_name_intelligence/runs/s2_event_response/results/P04.json`, `P05.json`, `P06.json` and the three `s2_event_response_v1_1` counterparts — `test` is the string `ABSTAIN_NO_EPISODES` or `ABSTAIN_INSUFFICIENT_CLUSTERS`
- other committed JSON under those run trees (seals, manifests, input/lane manifests, census, version records, challenger universe) — no p-value together with k/n or pos/neg

JSONL ledgers and membership lines were not read as JSON objects for this count.

## Not tested

- n > 300, or p0 other than 0.5, for the one-sided binomial grid.
- Shared `binom_p_two_sided` against a dedicated S1/S2 two-sided binomial (S1 only exposes two-sidedness through the sign test; S2's hit-rate test is one-sided).
- Shared `wilson_ci` against `engine.grading_stats.wilson_ci` or the S1/S2 re-exports (S1/S2 round to 3 decimals and use z=1.96; shared uses a slightly different z and abstention labels).
- Byte identity of `s2_seal.canonical_json` vs `sni_seal.canonical_json` as a numbered grid; the S2 function was read and matches S1 (no trailing newline).
- Recomputing S2's prereg digest through `sni_seal` on `s2_seal.build_prereg_spec` / `run_s2.full_spec_digest` (that spec is not `s1_prereg.build_spec()`; the numbered digest check is the S1 committed digest).
- Bootstrap numeric equality under a forced common RNG (the libraries do not share a RNG type, so a common seed is not a common stream).
- Authority-flag refusal paths, identity-id construction, and then-known / news-impact claims — out of scope for this comparison and forbidden as SNI outputs.
