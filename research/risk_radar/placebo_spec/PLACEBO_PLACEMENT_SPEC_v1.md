# PLACEBO_PLACEMENT_SPEC_v1 — near-turn random-run placebo

Draft 2026-11-12T21:10Z by the Risk Radar leader. **Status: for RD co-signature. No code is
written against it until the RD signs and the validity rule in §6 is chosen and recorded.** It
binds `engine/risk_radar_eval/pivots.py` `placebo()` (Macro) and `catalogue/bm_ref.py`
`_placebo_draw_arrays` (desk) to one placement rule. It repairs the defect in #11137
comment 6835380019. Re-scoring with it is a correction line, not a new read. The chance account
stays at 14.

## 1. Inputs

- `alert`: a boolean series on index `idx` (length n).
- `runs`: the lengths of its maximal True runs, in **index order**. Mass M = sum(runs).
- `E`: the eligibility mask on closes `p = px.reindex(idx).ffill()`. `near="high"`: `p >= cummax(p)·(1−tol)`. `near="low"`: the existing
  lowest-close-since-running-high rule. `near=None`: all True. This is unchanged from today.
- `seed`, `n_draws` (default 2,000), cap `C = 10 · n_draws` attempts.

## 2. Placement rule (requirements 1–5)

A start s is **admissible** for a run of length ln, given the partial draw a, when all of these hold:
- `E[s]` is True. Eligibility binds the start only.
- `s + ln <= n`. The run is placed at full length, with no right-edge truncation.
- `a[max(0,s−1) : min(n,s+ln+1)]` is all False. Runs stay separate by at least one session.

One **attempt**:
1. `order = rng.permutation(runs)`. This is one call on the list in index order.
2. For each `ln` in `order`, compute the admissible starts `c` as an ascending integer array.
   - If `c` is empty, the attempt is **discarded**. No further rng call is made in this attempt.
   - Otherwise `s = c[rng.integers(0, len(c))]` and `a[s:s+ln] = True`.
3. A completed attempt is a **kept draw**. Assert `a.sum() == M` and that the sorted run lengths
   of a equal the sorted runs. Any failure raises; it is never skipped.

Attempts repeat until there are `n_draws` kept draws or `C` attempts.
- If the cap is hit first, the asset's placebo is **"not defined"**. No partial distribution is
  reported.
- If E is empty, the asset is "not defined" at once, with zero attempts. Nothing is ever placed
  at session 0 by default.
- Reported per asset and near: attempts, kept, discarded, acceptance, defined (yes/no), the
  eligible-session count, and the share of placed mass inside E beside the alert's own share.

**rng consumption order (exact).** There is one `np.random.default_rng(seed)` per asset, and it
is used only by this loop. Per attempt it makes exactly one `permutation` call, then one
`integers` call per placed run. A discard ends the attempt at once. Scoring never touches the
rng. Same seed and same inputs give identical kept draws in `pivots.py` and `bm_ref.py`.
(`rng.choice(c)` equals `c[rng.integers(0,len(c))]` on numpy 2.5.4. The spec names `integers`
so it does not depend on that.)

## 3. Cross-asset pairing (bm_ref cluster level)

- Each asset keeps its own stream, `default_rng(seed)`, with the same seed per asset as today.
  A single-asset `pv.placebo` call therefore reproduces bm_ref's stream for that asset.
- Cross-asset draw k pairs **the k-th kept draw** of every asset, for k = 0 … n_draws−1.
  Discards in one asset never shift another asset's draws.
- If any asset that contributes turns is "not defined", the cluster-level placebo for that set
  and near is **"not defined"**. Assets are never silently dropped from the pool. The report
  names the assets that were not defined and their discard counts.

## 4. Shared fixture (`placebo_fixture_v1.json`, inputs only until §6 is chosen)

Both sides run all five cases with seed 0 and n_draws 20. The first 3 kept draws (their starts)
and the discard counts must match exactly. Expected outputs are generated once from the signed
rule and added to the fixture under the RD's co-signature.

- **F1 short:** n = 40, runs [10, 3, 1], E = all True.
- **F2 right edge:** n = 40, runs [10], E True only on sessions 28–39. Only starts 28–30 are
  admissible.
- **F3 crowded:** n = 40, runs [6, 6, 6, 6], E True on sessions 0–24. Discards are forced
  (about 78 attempts are discarded before 20 are kept). It is defined.
- **F4 empty:** n = 40, runs [5], E all False. The result is "not defined" with 0 attempts.
- **F5 cap hit:** as F3 with E True on 0–21. Under 20 kept within the cap of 200, so "not defined".

## 5. Mass results on the 2022–23 loud series (no outcome joined)

These were measured with `measure_candidates.py`. The series is the shipped walk-forward loud
series 2022-01-03..2023-12-29: n = 501, 12 runs [1,3,2,20,86,60,2,9,2,2,1,5], M = 193. The
settings were seed 0, 2,000 kept draws and a cap of 20,000 attempts. Prices set eligibility
only.

| Candidate | near | start pool | attempts | discarded | acceptance | defined | placed mass in E (alert's own) |
|---|---|---:|---:|---:|---:|---|---:|
| today (`pivots.placebo`) | high | 15 | — | silent | — | reports | mean mass 32.2 of 193 |
| today | low | 61 | — | silent | — | reports | mean mass 124.7 of 193 |
| **A** start-only, random order | high | 15 | 20,000 | 20,000 | 0.000 | **no** | — (0.000) |
| **A** | low | 61 | 8,300 | 6,300 | 0.241 | yes | 0.183 (0.192) |
| **B** as A, longest run first | high | 15 | 20,000 | 20,000 | 0.000 | **no** | — |
| **B** | low | 61 | 5,514 | 3,514 | 0.363 | yes | 0.240 (0.192) |
| **C** as A, start ≤ 21 sessions after an E session | high | 37 | 20,000 | 20,000 | 0.000 | **no** | — |
| **C** | low | 177 | 4,087 | 2,087 | 0.489 | yes | 0.134 (0.192) |

On 2022–23 only 15 sessions are near-high: 2022-01-03/04 and 13 sessions in 2023-12-11..29.
Twelve full-length runs with gaps cannot start there, so **no full-length rule defines a
near-high placebo on this window**. The window w = 10 gives the same answer. Every kept draw has
mass 193 and the real run multiset, which was checked.

## 6. Candidate validity rules — choose one with the RD before coding

1. **Rule A**, with "not defined at this exposure" as the declared outcome when the cap is hit.
   This is the leader's preference. The order is unbiased, the band keeps its meaning, and on
   2022–23 near-high it reports "not defined" rather than a number.
2. **Rule B.** Acceptance is higher, but placement becomes conditional on a fixed order. That
   shifts more mass into the band (0.240 against the alert's 0.192), and it still does not
   define near-high.
3. **Rule C.** This widens the start band to the 21-session pre window. It still does not define
   near-high, and it dilutes "near" (0.134 in band).

The rule chosen, the cap, and the expected fixture outputs are recorded in a co-signed amendment
before either side scores with it. Every new table carries "placebo p90 under repair; part (a)
provisional" until the regenerated tables land.
