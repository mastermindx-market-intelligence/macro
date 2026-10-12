# Q18 verdict: KEEP (research reference only, nothing wired)

Preregistration: `PREREG.md`, sha256 `1c9ee1ef6a71a5d4667f8de197b96f1d4bb2bc0c976151ae86411fc0e49d028c`,
frozen `Fri Oct  9 10:31:30 UTC 2026` (`FREEZE.log`). One primary holdout run (`RUNS.log`
line 2, evaluate.py, exit 0). After the independent audit, `PREREG_AMENDMENT.md` (A1 + A2,
reporting/input guards only, written before any rerun) authorised one reproducibility rerun
of the amended code (`RUNS.log` line 3, exit 0). It produced byte-identical outputs
(`primary_results.json` `08c3049c…9cb5`, `per_block.csv` `345ec0dc…bf3`), so the first run
remains the primary record and the verdict is unchanged. Nothing was selected from the rerun.

## Decision

The preregistered rule was: KEEP if and only if H1 and H2 hold. Both hold.

| | Value | Rule | Result |
|---|---|---|---|
| H1 mean d0 = mean(\|E0−T\| − \|E2−T\|) | **0.1357** | ≥ 0.05 | pass |
| H1 MBB 95% CI (4-quarter blocks, B=5000, seed 18, pairs joint) | [0.0756, 0.1872] | lower > 0 | pass |
| H1 per-pair mean d0 | CSI300 0.1024; HSCEI 0.1690 | both > 0 | pass |
| H2 mean d1 = mean(\|E1−T\| − \|E2−T\|) | **0.0817** | point ≥ 0 | pass |
| H2 MBB 95% CI | [0.0018, 0.1401] | reported only | lower bound barely above 0 |
| Newey–West lag-3 SE of quarterly cross-pair mean | d0: 0.0282; d1: 0.0379 | cross-check | consistent with MBB SE 0.0288 / 0.0358 |

Honest N: 27 eligible holdout quarters (2020Q1–2026Q3) and 54 pair-blocks. No block was
dropped. The minimum support across blocks was 117 HY overlap pairs, 60 matched target days
and 54 matched E0 days.

The claim this verdict supports, and only this claim: for Asia-close index exposures on
SSE/HKEX clocks against SPY on the NYSE clock, a Hayashi–Yoshida correlation over declared
close timestamps is materially closer to the US-clock ETF proxy correlation (ASHR–SPY,
FXI–SPY), i.e. less attenuated, than either (a) the naive same-date join used by the
incumbent `covariance_spine` factor block, or (b) the fixed lag-1 convention of
`hk_global_beta`/`cn_global_beta`. Against that proxy, the naive join attenuates the
dependence by more than half. The proxy is not the true integrated correlation
(Limitation 1, which bounds when this ordering could be overturned). No lag or lead in this
study is a causal direction; outputs are context-only measurement records.

**Coverage caveat.** The time unit is the calendar quarter: 27 holdout quarters, so a
4-quarter moving-block bootstrap has about 27/4 = 6.75 effective blocks
(`results/support_report.json`), and the Newey–West cross-check rests on 27 points. Interval
coverage of the MBB percentile CI at this size is not guaranteed to be nominal. H1's lower
bound (0.0756) is far from zero; H2's (0.0018) is effectively at zero and should be read as
"not worse than lag-1", not as a precise improvement.

## Holdout block means (descriptive)

| Pair | T (proxy) | E0 naive | E1 lag-1 | E2 HY | E3 weekly | MAE E0 | MAE E1 | MAE E2 | MAE E3 |
|---|---|---|---|---|---|---|---|---|---|
| CSI300 (510300.SS vs SPY; target ASHR–SPY) | 0.379 | 0.123 | 0.174 | 0.308 | 0.306 | 0.267 | 0.231 | 0.165 | 0.229 |
| HSCEI (_HSCE vs SPY; target FXI–SPY) | 0.437 | 0.143 | 0.217 | 0.373 | 0.339 | 0.298 | 0.226 | 0.129 | 0.241 |

Per-block signs (descriptive, post-run):

| | d0 > 0 | d1 > 0 | E0 < E2 < T | E2 > T |
|---|---|---|---|---|
| CSI300 | 22/27 | 16/27 | 16/27 | 9/27 |
| HSCEI | 23/27 | 19/27 | 17/27 | 8/27 |

E2 still sits below the proxy target on average in both pairs, so the gain cannot be
explained by HY overshooting.

Training-period descriptive statistics (used to choose nothing):

| Pair | Mean d0 | Mean d1 | Blocks |
|---|---|---|---|
| CSI300 | 0.104 | 0.080 | 24 |
| HSCEI | 0.345 | 0.186 | 60 |

The direction is the same as in the holdout.

## Baseline reproduction (pre-freeze, RUNS.log line 1)

`baseline_repro.py` ran the incumbent seam `engine/neuralweb/covariance_spine.py::_build_factors_block`
unmodified, feeding it factor_series files written to a scratch workdir, and recovered
|rho| = 2·share − 1. It ran on two inputs:

* Synthetic pair, true rho 0.6, asynchronous closes: incumbent implied 0.1826, independent
  complete-case Pearson 0.1826 (reproduced). HY on the same draw gave 0.4477 (n=400).
* Real 510300.SS vs SPY, training window 2018-11-06..2019-12-31 (252 obs): incumbent implied
  0.2564, independent Pearson 0.2564 (reproduced). On the same window, naive uncentered gave
  0.236, lag-1 0.175 and HY 0.383.

The incumbent cannot run on its own production input here, because `site/` is absent from
the sparse staging copy. This is recorded in `results/baseline_reproduction.json`.

## Clock classes and bootstrap support (reporting only, PREREG_AMENDMENT.md A2)

`report_support.py` (RUNS.log line 4, exit 0; reads no market data) wrote
`results/support_report.json`. Over all 1761 weekdays of the holdout period, the declared
close clocks classify as:

| Pairing | Clock class | Distinct close offsets (s) |
|---|---|---|
| SSE vs NYSE (510300.SS vs SPY) | DST_VARYING | 46800, 50400 |
| HKEX_INDEX vs NYSE (_HSCE vs SPY) | DST_VARYING | 42600, 46200 |
| NYSE vs NYSE (proxy target ASHR/FXI vs SPY) | SIMULTANEOUS | 0 |
| SSE vs HKEX_INDEX | NONSYNCHRONOUS | 4200 |

No studied Asia–US pairing is labelled simultaneous. Bootstrap support: 27 time blocks,
block length 4, 6.75 effective blocks, B = 5000, seed 18, Newey–West lag 3.

## Support, attrition, coherence

* Invalid prices: 0 in all five inputs. Winsor clipping (training 0.1%/99.9% bounds) clipped
  5 to 21 returns per series over the whole history.
* Holdout holiday-gap intervals (absorbed by HY, bridged and never zero-filled): 510300 47,
  _HSCE 75, US series 66.
* Zero returns are kept as MEASURED: 510300 20, ASHR 23, FXI 13, SPY 2, _HSCE 0.
* The DST-shift share of US holdout intervals is 0.76%, and Asia clocks have no DST. Under
  daily closes, DST and US early closes do not change the HY overlap pairs, because every
  US close falls between consecutive Asia closes.
* HY |corr| > 1: 0 blocks.
* The holdout HY matrix (510300, _HSCE, SPY) has min eigenvalue 0.304 and is PSD. It is
  reported only and never repaired; repair belongs to Q08.
* The synthetic witness (outside the trial family): true rho 0.5 gave HY 0.504 and naive
  0.206, against an attenuation prediction of 0.229.

## Process disclosure

* After the freeze and before the holdout run, `evaluate.py` was smoke-run once on truncated
  copies of the inputs containing only rows before 2020-01-01. The harness
  (`_fabric/Q18-work/smoke_eval.py`, sha256 `7a43d7a4…f425`, not shipped) imported the
  shipped `evaluate.py` and monkeypatched its globals in memory (truncated inputs and their
  hashes, pseudo-holdout 2015Q1..2019Q4, lowered minimums, scratch CSV path); the file
  itself was not edited. Because `__main__` did not run, no RUNS.log record was written at
  the time; it is now recorded as a `"kind": "note"` line in RUNS.log (A2). No holdout value
  was computed before the single primary run.
* RUNS.log line 1 (line sha256 `c0c858c2…c035`) is the pre-freeze, training-only baseline
  reproduction (`baseline_repro.py`), disclosed in PREREG §7; a RUNS.log note records this.
* RUNS.log records from the amendment onward carry `script_sha256` and `module_sha256`.
  The primary run predates that field; its code identity is the pre-amendment hashes listed
  in `PREREG_AMENDMENT.md` A1.
* Before the freeze, holdout rows were seen only as file metadata (shape, first/last index,
  first two rows), as disclosed in PREREG §7.

## Limitations

1. **The proxy target is not the estimand.** ASHR and FXI trade on the US clock, so their
   correlation with SPY can include US-hours premium/discount co-movement. FXI (FTSE China
   50) is not the same basket as HSCEI. A target inflated this way would favour higher
   estimates, but on average E2 lies between E0 and T. That ordering is not overturned
   unless the true integrated correlation is below roughly (E0+E2)/2 ≈ 0.22–0.26.
2. There are only two pairs, both China-equity vs SPY. Nothing here generalises the
   magnitude to other assets (rates, FX, commodities) or to intraday clocks.
3. Daily closes only. HKEX index close timing is declared as 16:10 HKT, and the vendor's
   exact timestamp is not observed. US early closes are flagged but not modelled.
4. H2's CI lower bound (0.0018) is barely above zero. Against the lag-1 convention the
   improvement is real in point terms but modest in precision. With about 6.75 effective
   bootstrap blocks, CI coverage is approximate (see the coverage caveat above).
5. The dependency chain Q18 → Q08 → Q17 is unresolved. Q08 (estimation, shrinkage, PSD
   repair) and Q17 (factor whitening) have not consumed this. Q18 only qualifies the
   interval measurement.
6. Research only. Nothing imports `engine/async_session_covariance.py`. Changing
   `covariance_spine`, `hk_global_beta` or `cn_global_beta` would be a separate admitted
   decision with its own study identity (DNR:KILL-OUTCOME-AUDITION is respected: no lag or
   estimator was chosen on outcomes).
7. Input ownership: inputs are read-only files owned by the existing macro-main data
   writers (vintage `cdab6268`, sha256s in PREREG §4 and every RUNS record). Q18 writes no
   data, mints no feed, and its module emits context-only records; this is enforced at study
   level (hash checks, no writes outside `results/`) rather than by a unit test.

Served model: Claude Opus 5.5 (model ID `claude-opus-5-5`).
