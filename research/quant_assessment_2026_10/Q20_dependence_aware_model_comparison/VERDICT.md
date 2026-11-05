# Q20 — Dependence-aware challenger comparison on the existing trial budget: VERDICT

**Study verdict: KEEP.** The Q20 module (`engine/challenger_spa_comparison.py`) is kept as a
research-only, unwired diagnostic for the existing statistics owner. Every pre-registered
§8 method-control gate passed, and the single frozen empirical comparison ran on the
eligible admitted family (PREREG §9).

**Empirical claim: VANISHES.** The admitted `vector` allocation family claims to beat
buy-and-hold. Under risk-matched, selection-aware, dependence-preserving SPA on the
evaluation window that claim does not hold: p_c = 0.283 at block 21, and 0.245–0.283
across blocks 7–63. Following the brief's falsifier and stop rule, the incumbent algorithm
stays unchanged and this negative comparison is filed. No friendlier test, benchmark,
block length, window or lag was chosen afterwards. The window is REUSED, and this result
grants no promotion, gate, rank, size or alert change.

Author: Claude. The environment reports the served model as Opus 5.5, model ID
`claude-opus-5-5`.

## 1. What was frozen and run

- **PREREG.md** sha256 `ccd454e000457c0219058b9c0162a7571405ebe4da452d6c646b5ea48fffafeb`,
  frozen as recorded in FREEZE.log. It was never edited after the freeze, and no amendment
  was needed.
- **evaluate.py** final sha256 `c6bed238b063d494bea2c8ad9099c8ef6f95f14a6a981911c9464cd8f171870b`
  (the original runs used `79c38ae0124f5f6570731f63abce6b1476689d9db634b816dabf55e5f7e58f74`).
  It refuses to run on a PREREG hash mismatch and appends every run to RUNS.log. The final
  version adds replay stages for every output and two guards. A computing stage refuses to
  overwrite an existing results file. `--stage empirical` also refuses whenever RUNS.log
  already holds an exit-0 `stage=empirical ok` entry, even if the results file was deleted.
- **Inputs:** macro-main data vintage cdab6268, read-only. The sha256 in every RUNS.log
  entry matches PREREG §3:
  - `data/vector/signals.parquet` `b0df9712370c4af4f5cf779512c862c0ba6e453639d2ec51b0e54a411ada1996`
  - `data/vector/calibration.json` `1fc7b6e664d55bf6c75d39d42ae430d02f394b748af4bcc5078e6b680ba290ce`
  - `data/trial_ledger.jsonl` `58b7feba20efafca5125faaf21330343a07141496379b4b9aea0fa8cc112380d`
  - `config.yml` `b8963682e5f2fe209cee1a604f19e51bbce232992d75c0b26c60a615600a310f`

RUNS.log holds seven entries, all with exit 0, in this order:

| # | Stage | Output sha256 | Module sha256 |
|---|---|---|---|
| 1 | baseline | `baseline_repro.json` `d1c8b06d…` | `2ac04a98…` |
| 2 | simulate | `simulation_controls.json` `6ae8b228…` | `2ac04a98…` |
| 3 | empirical, run once | `empirical_comparison.json` `a588404e…` | `da665dcf…` |
| 4 | replay-empirical | identical | `4fdea54e…` |
| 5 | replay-baseline | `d1c8b06dbb479f34332bb65563dd0d14bcaa169d01cd8e87bf86bb53794aecff`, identical | `5c0a8bee…` (final) |
| 6 | replay-simulate | `6ae8b228322362d03b08e0b94570f202df70d8b8bc3440cc68fca38961d5078a`, identical | `5c0a8bee…` (final) |
| 7 | replay-empirical | `a588404ed3839b2efbbe7496a52dccd34763f7fca6fd0d63340759f5018d2851`, identical | `5c0a8bee…` (final) |

Entries 5–7 ran under the final module bytes
`5c0a8beedbc517d1ac2ba9c5c76e083441ea446af884feaf27ecfdd4f49b97dc` and the final evaluate.py.
Each one recomputed its stored results file and matched it byte for byte, so all three
results files are reproduced by the code that ships. Between the module versions only the
docstrings changed. Details are in REQUIREMENTS.md under "Module byte history".

**Provenance note (independent audit, minor).** Before the empirical run, an earlier version
of the module docstring stated an empirical outcome that had not yet been computed. That
sentence was replaced with a neutral pointer before stage 3 ran. The original bytes of that
sentence were not kept, so it cannot be quoted here. It is also not possible to establish
from the surviving files who wrote it or what it was based on. The risk to the result is
bounded for three reasons. The comparison is a deterministic function of the frozen PREREG
and the hashed inputs. Replay entries 5–7 reproduce every results file from the final code.
The recorded outcome (VANISHES) is the negative one, so the earlier sentence could not have
steered the analysis toward a friendlier result. PREREG.md was not edited.

**Where the module lives (correction to PREREG §10, which stays unedited).** PREREG §10
says Q20's SPA "lives only in the research tree". That is inaccurate. The module ships at
`engine/challenger_spa_comparison.py`, which makes it a second, research-only SPA
implementation alongside the incumbent `spa_test` in `engine/validation.py`. It stays a
research reference with no production role. Nothing imports it, nothing registers or
schedules it, and it does not replace or call the validation core. That file was never
opened because its read was refused. Folding the two implementations together is a
decision for the statistics owner and is not made here.

**Missing-trial check scope.** `map_candidates_to_trials(..., source=...)` checks only the
itemized trials of the given family and source. Budget trials of the same family from any
other source (or carried only by a `declared_budget` row) stay in `original_trial_budget` and
count as attrition; they are never dropped. This is pinned by
`test_req1_cross_source_budget_trials_are_attrition_not_silently_dropped`. In the empirical
run, the 67 trials without a retained loss panel are exactly this attrition.

## 2. Baseline reproduction (incumbent, PREREG §7)

The incumbent's published full-sample figures reproduce within tolerance at lag 1. Every
|ΔSharpe| is at most 0.0071 and every |ΔCAGR| is at most 0.27 pp.

| Series | Reproduced Sharpe | Reproduced CAGR | Published |
|---|---|---|---|
| optimal | 1.4129 | 61.25% | 1.42 / 61.5% |
| HODL | 1.0467 | 60.71% | — |

Published DSR is 0.9601 with n_trials 71.

## 3. Method-control simulation (PREREG §8). All gates pass.

Settings: n = 2100, k = 20 candidates, AR(1) phi = 0.3, B = 499, 1000 reps, block 21,
alpha 0.05.

| Scenario | SPA p_c rejection rate | Naive best-candidate rate | Gate |
|---|---|---|---|
| N1 null, rho 0.9 | 0.063 | 0.150 | size ≤ 0.075, passes |
| N2 null, rho 0.5 | 0.071 | **0.382** | size ≤ 0.075 and naive oversizes ≥ 0.10, both pass |
| N3 null with poor alternatives, rho 0.9 | 0.055 | 0.123 | size ≤ 0.075, passes |
| P1 planted edge, rho 0.9 | 0.901 | 0.974 | power ≥ 0.80, passes |

Trial-budget monotonicity: adding 0, 10 or 50 null candidates correlated at rho 0.5, 0.9 or
0.99 always leaves the budget at 71. It never falls below the original declared budget
of 71.

## 4. The single empirical comparison (PREREG §2, §4–§6, §9)

**Family and trials.** The family is ledger family `vector`, source `alloc_variant`. Its
four candidates map to their generation-time trial identities using the ledger's own
config-hash rule:

| Candidate | Config hash |
|---|---|
| conservative | `0692c70992c525bb` |
| moderate | `8018a48758dddb05` |
| aggressive | `3fe71a26c76dfed9` |
| optimal | `911496757c3b4247` |

All four were generated on 2026-07-02 at 03:43Z. The trial budget stays at the declared 71.
The other 67 trials have no retained loss panel. They count in the budget as
`UNAVAILABLE_LOSS_PANEL` and are not dropped. The `alloc_*_raw` columns carry no
generation-time trial identity, so they are excluded and named.

**Loss contract.** The differential is `d_k,t = r_k,t − beta_k · r_BTC,t`, with:
- lag 1;
- 10 bps one-way cost;
- beta_k = sd(strategy)/sd(BTC), estimated on the training window only.

Training-window betas:

| Candidate | beta |
|---|---|
| conservative | 0.5028 |
| moderate | 0.5833 |
| aggressive | 0.6637 |
| optimal | 0.5857 |

**Split and support.** Training covers 2015-01-01 up to 2021-01-01, n = 2190. Evaluation
runs from 2021-01-01 to 2026-10-07, n = 2106. That is 100 non-overlapping 21-day blocks,
and the best candidate's Newey–West T_eff is 2239. Lags removed 2 rows.

**Primary SPA.** Hansen studentised, using one common stationary-bootstrap index matrix,
B = 5000, seed 7, mean block 21:

| Candidate | Annualised mean differential | t |
|---|---|---|
| conservative | +0.0488 | 0.52 |
| moderate | +0.0790 | 0.86 |
| aggressive | +0.0172 | 0.18 |
| optimal | +0.0771 | 0.84 |

- Best candidate: moderate, at 0.0790 annualised, which clears the 0.02 effect bar.
- p_l = p_c = p_u = **0.2832**, statistic 0.861. The three agree because every candidate
  mean is positive, so the recentring choices coincide.

**Block-length sensitivity (p_c).**

| Block | 7 | 14 | 21 | 42 | 63 |
|---|---|---|---|---|---|
| p_c | 0.2818 | 0.2832 | 0.2832 | 0.2524 | 0.2448 |

**PREREG §9 checks.**
1. Primary p_c ≤ 0.05: **fails** (0.283).
2. Every sensitivity p_c ≤ 0.10: **fails**.
3. Effect bar ≥ 0.02: met.

Result: **VANISHES**.

**Secondary output, non-decisional.**
- Naive best-candidate HAC p-value: 0.204. It ignores selection and is kept only as a
  discriminator. The budget-Bonferroni bound over 71 trials is 1.0.
- CSCV PBO = 0.599 with S = 16 and 12870 splits. This is supplementary: it cannot set the
  verdict and does not replace the chronological holdout.
- SPA against cash: p_c = 0.0512. This is the strategies' raw edge over zero and is not the
  claim under test.
- Annualised log growth against unscaled HODL:

  | Candidate | Value |
  |---|---|
  | conservative | −0.0014 |
  | moderate | +0.0417 |
  | aggressive | −0.0007 |
  | optimal | +0.0405 |

**Window disclosure.** The evaluation window is labelled **REUSED**. It starts before
generation and overlaps the incumbent's calibration window, which runs from 2021-01-01
until the calibration asof. It is "reused outcome window — not fresh confirmation".

The post-generation slice has n = 97, about 4 blocks, which is fewer than the minimum of 10
independent blocks. It is labelled REUSED because nightly display reruns overlap it. It
would be FRESH_UNDERPOWERED if those reruns were ignored. It is descriptive only and
untested. Its annualised mean differentials are −0.46 to −0.63, but 97 days are far too few
to read anything into that.

## 5. Interpretation

All four allocation variants beat buy-and-hold on raw headline numbers. That advantage
comes mostly from lower volatility at a similar CAGR. Once the benchmark is scaled to the
same risk, the selection-aware, dependence-preserving SPA cannot separate the best variant
from zero edge: p_c is around 0.25–0.28 whatever the block length. The naive best-candidate
p-value of 0.20 is no better.

This does **not** show that the vector allocator is worthless. It shows that the specific
claim "beats risk-matched buy-and-hold" is not statistically supported on this reused
window with honest dependence and selection accounting. A kill closes only this tested
construction. Forward evaluation on fresh blocks remains the only path to confirmation.

## 6. Standing kills and holds respected

- DNR:KILL-OUTCOME-AUDITION: one frozen pass, with no outcome-driven re-selection.
- DNR:KILL-FUSED-COMPOSITE and DNR:KILL-REGIME-SCORECARD: no composite or scorecard is
  formed.
- DNR:KILL-LLM-ORIGINATION: no LLM originates any signal or score.
- DNR:KILL-POSITIONING-FUSION, DNR:KILL-CAUSAL-DAG-ALPHA, DNR:HOLD-PSS-AF1-FINRA and
  DNR:HOLD-PSS-CD1-CROWDING: none of their inputs are used.
- DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR: no reliability monitor is built.

`engine/validation.py` was never opened, imported or replaced, because its read was
refused.

## 7. Limitations

- Only 4 of the 71 budgeted trials have a retained loss panel. SPA therefore compares 4
  candidates, while the budget, the Bonferroni bound and the disclosure all carry 71. With
  the full 71 panels the bootstrap max would face a larger selection penalty. Only an
  unseen trial with a stronger studentised edge than `moderate` (t = 0.86) could lower
  p_c. This is unproven either way, and it is disclosed, not assumed.
- The benchmark is risk-matched with a single static training-window beta. A time-varying
  match was not pre-registered.
- The evaluation window is REUSED, so even a SURVIVES result would not have been fresh
  confirmation.
- The post-generation window is underpowered: 4 blocks against a minimum of 10.
- One instrument, BTC, over one regime history.
