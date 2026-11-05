# P03 ULP stability (2026-10-13)

HISTORICAL-DESCRIPTIVE numerical-stability property of the frozen S1 v1.1
P03 comparison. This document is not a forecast, signal, validation, or
registration. It consumes committed observations and `results/P03.json`
owned by the S1 residual runner. Identity strings are caller-supplied
opaques owned by Stock Identity / Data OS.

Authority flags (literal false everywhere in this lane):

- rank_authority: false
- gate_authority: false
- size_authority: false
- signal_authority: false
- escalation_authority: false
- trade_authority: false

## Summary

Last-digit float drift of the size recorded in the XREP macOS arm64
addendum (worst relative difference 4.62e-12, worst absolute 5.50e-14)
does not flip a published P03 decision on this sealed tree: not a
verdict string, not the S0 criterion `met`, not the sign of delta_R2,
not the sign of the CI lower bound, not a 4-dp rounded CI bound, and
not a calibration coverage count. The perturbation used in the
regression is relative eps = 1e-11 (about 2x the observed worst
relative difference). The tightest measured decision margin is
3.711469e-07 on `P03|hkd_0700|h=63|TUNE|M2_vs_M1` (block), which is
3.711469e+04 times eps. Against the safety floor
of 1e3 * eps * scale, that margin remains above the floor. Two published CI lower bounds round to ±0.0 at 4 decimal places; their unrounded values sit 4.640575e-05 and 1.997605e-05 from zero, and 3.594246e-06 and 3.002395e-05 from a bound-changing 4-dp boundary — still far above ULP scale.

## Method

XREP measured macOS arm64 vs Linux seal drift on the ten P03 text
outputs only in the last digits of float tokens. This lane multiplies
every float field the decision path reads (`r__oc`, `common__oc`,
`challenger.common_ipca__oc`, `z__oc`) by `(1 + eps * u)` with
`u ~ Uniform[-1, 1]` from `random.Random(seed)` for seeds 0..7 and
`eps = 1e-11`. The harness rebuilds `by_model` maps the same way
`p03_blocks` does, including the adr_baba IPCA map from `challenger`,
and calls `p03_blocks` / `_comparison_block` / `_calibration` on the
perturbed rows. The engine's own 4-dp rounding of
`block_bootstrap_ci` is left unchanged. Unrounded CI bounds are
recomputed with the same seeded bootstrap (BOOT_DRAWS=800, BOOT_SEED=7)
without the final `round(..., 4)` so the distance to a 4-dp rounding
boundary `(k + 0.5) * 1e-4` is observable.

## Margin table

| block key | delta_R2 | ci95[0] | distance to nearest 4-dp boundary | margin/eps |
| --- | ---: | ---: | ---: | ---: |
| P03\|adr_baba\|h=5\|TRAIN\|M1_vs_M0 | 0.18408397 | 0.0003 | 2.285980e-06 | 2.285980e+05 |
| P03\|adr_baba\|h=5\|TUNE\|M1_vs_M0 | 0.10975489 | 0.0001 | 2.573760e-05 | 2.573760e+06 |
| P03\|adr_baba\|h=5\|TRAIN\|M2_vs_M1 | 0.52577345 | 0.0012 | 1.759056e-05 | 1.759056e+06 |
| P03\|adr_baba\|h=5\|TUNE\|M2_vs_M1 | 0.54676282 | 0.0011 | 2.670373e-05 | 2.670373e+06 |
| P03\|adr_baba\|h=5\|TRAIN\|IPCA_vs_M1 | 0.01351695 | -0.0 | 3.594246e-06 | 3.594246e+05 |
| P03\|adr_baba\|h=5\|TUNE\|IPCA_vs_M1 | -0.00290051 | -0.0001 | 1.431367e-05 | 1.431367e+06 |
| P03\|adr_baba\|h=21\|TRAIN\|M1_vs_M0 | 0.10403221 | -0.0006 | 2.141859e-05 | 2.141859e+06 |
| P03\|adr_baba\|h=21\|TUNE\|M1_vs_M0 | 0.05614115 | -0.0014 | 1.780680e-05 | 1.780680e+06 |
| P03\|adr_baba\|h=21\|TRAIN\|M2_vs_M1 | 0.53929845 | 0.0039 | 2.623655e-06 | 2.623655e+05 |
| P03\|adr_baba\|h=21\|TUNE\|M2_vs_M1 | 0.53901104 | 0.0027 | 6.248624e-06 | 6.248624e+05 |
| P03\|adr_baba\|h=21\|TRAIN\|IPCA_vs_M1 | 0.00864227 | -0.0004 | 8.227381e-06 | 8.227381e+05 |
| P03\|adr_baba\|h=21\|TUNE\|IPCA_vs_M1 | -0.01964421 | -0.0011 | 1.120317e-05 | 1.120317e+06 |
| P03\|adr_baba\|h=63\|TRAIN\|M1_vs_M0 | 0.16935998 | -0.0017 | 2.991676e-05 | 2.991676e+06 |
| P03\|adr_baba\|h=63\|TUNE\|M1_vs_M0 | 0.03191235 | -0.0095 | 1.965420e-06 | 1.965420e+05 |
| P03\|adr_baba\|h=63\|TRAIN\|M2_vs_M1 | 0.59352940 | 0.0133 | 1.602383e-05 | 1.602383e+06 |
| P03\|adr_baba\|h=63\|TUNE\|M2_vs_M1 | 0.30317151 | -0.0079 | 2.244499e-05 | 2.244499e+06 |
| P03\|adr_baba\|h=63\|TRAIN\|IPCA_vs_M1 | 0.00358868 | -0.0022 | 1.182478e-05 | 1.182478e+06 |
| P03\|adr_baba\|h=63\|TUNE\|IPCA_vs_M1 | -0.02005018 | -0.0040 | 4.638029e-05 | 4.638029e+06 |
| P03\|hkd_9988\|h=5\|TRAIN\|M1_vs_M0 | 0.67209468 | 0.0025 | 2.271871e-05 | 2.271871e+06 |
| P03\|hkd_9988\|h=5\|TUNE\|M1_vs_M0 | 0.64736264 | 0.0016 | 3.982371e-05 | 3.982371e+06 |
| P03\|hkd_9988\|h=5\|TRAIN\|M2_vs_M1 | 0.02143186 | -0.0002 | 7.068565e-06 | 7.068565e+05 |
| P03\|hkd_9988\|h=5\|TUNE\|M2_vs_M1 | 0.00279343 | -0.0001 | 3.459969e-05 | 3.459969e+06 |
| P03\|hkd_9988\|h=21\|TRAIN\|M1_vs_M0 | 0.54944911 | 0.0050 | 3.239670e-06 | 3.239670e+05 |
| P03\|hkd_9988\|h=21\|TUNE\|M1_vs_M0 | 0.67827296 | 0.0054 | 2.088084e-05 | 2.088084e+06 |
| P03\|hkd_9988\|h=21\|TRAIN\|M2_vs_M1 | 0.08160776 | -0.0006 | 1.159736e-05 | 1.159736e+06 |
| P03\|hkd_9988\|h=21\|TUNE\|M2_vs_M1 | 0.02128548 | -0.0007 | 3.628925e-06 | 3.628925e+05 |
| P03\|hkd_9988\|h=63\|TRAIN\|M1_vs_M0 | 0.64629226 | 0.0047 | 3.022209e-05 | 3.022209e+06 |
| P03\|hkd_9988\|h=63\|TUNE\|M1_vs_M0 | 0.40734683 | -0.0017 | 6.166897e-07 | 6.166897e+04 |
| P03\|hkd_9988\|h=63\|TRAIN\|M2_vs_M1 | -0.03529472 | -0.0074 | 2.235521e-05 | 2.235521e+06 |
| P03\|hkd_9988\|h=63\|TUNE\|M2_vs_M1 | 0.06248689 | -0.0027 | 5.574563e-06 | 5.574563e+05 |
| P03\|hkd_0700\|h=5\|TRAIN\|M1_vs_M0 | 0.57576813 | 0.0010 | 4.070460e-05 | 4.070460e+06 |
| P03\|hkd_0700\|h=5\|TUNE\|M1_vs_M0 | 0.63124453 | 0.0008 | 9.450955e-06 | 9.450955e+05 |
| P03\|hkd_0700\|h=5\|TRAIN\|M2_vs_M1 | 0.06291382 | 0.0 | 3.002395e-05 | 1.997605e+06 |
| P03\|hkd_0700\|h=5\|TUNE\|M2_vs_M1 | 0.00507750 | -0.0001 | 2.401125e-05 | 2.401125e+06 |
| P03\|hkd_0700\|h=21\|TRAIN\|M1_vs_M0 | 0.61073409 | 0.0038 | 2.744648e-05 | 2.744648e+06 |
| P03\|hkd_0700\|h=21\|TUNE\|M1_vs_M0 | 0.62267340 | 0.0010 | 1.688874e-06 | 1.688874e+05 |
| P03\|hkd_0700\|h=21\|TRAIN\|M2_vs_M1 | 0.03396839 | -0.0008 | 1.006408e-05 | 1.006408e+06 |
| P03\|hkd_0700\|h=21\|TUNE\|M2_vs_M1 | -0.00576019 | -0.0004 | 2.463909e-05 | 2.463909e+06 |
| P03\|hkd_0700\|h=63\|TRAIN\|M1_vs_M0 | 0.61631175 | 0.0092 | 1.346327e-05 | 1.346327e+06 |
| P03\|hkd_0700\|h=63\|TUNE\|M1_vs_M0 | 0.62180687 | 0.0068 | 1.511563e-05 | 1.511563e+06 |
| P03\|hkd_0700\|h=63\|TRAIN\|M2_vs_M1 | -0.13727726 | -0.0068 | 2.532662e-05 | 2.532662e+06 |
| P03\|hkd_0700\|h=63\|TUNE\|M2_vs_M1 | -0.01802509 | -0.0028 | 3.711469e-07 | 3.711469e+04 |

Tightest 4-dp rounding margin: `P03|hkd_0700|h=63|TUNE|M2_vs_M1` at 3.711469e-07
(margin/eps = 3.711469e+04).
Smallest `|delta_R2|`: `P03|hkd_9988|h=5|TUNE|M2_vs_M1` at 2.793428e-03
(margin/eps = 2.793428e+08).

Published ci95[0] values that round to zero:

- `P03|adr_baba|h=5|TRAIN|IPCA_vs_M1`: published ci95[0] = -0.0, unrounded = -4.640575e-05, distance to nearest 4-dp boundary = 3.594246e-06.
- `P03|hkd_0700|h=5|TRAIN|M2_vs_M1`: published ci95[0] = 0.0, unrounded = 1.997605e-05, distance to nearest 4-dp boundary = 3.002395e-05.

Those zeros keep `ci[0] > 0` false. Crossing a published 4-dp step
requires the unrounded bound to reach a `(k + 0.5) * 1e-4` boundary,
which is the distance reported in the table.

## Calibration table

| cell | n | k at 1.96 | min distance of |z| to 1.96 | k at 1.0 | min distance to 1.0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| adr_baba\|M0\|h=5\|TRAIN | 347 | 327 | 1.789229e-02 | 248 | 4.938622e-03 |
| adr_baba\|M0\|h=5\|TUNE | 114 | 106 | 2.181473e-02 | 81 | 3.280701e-02 |
| adr_baba\|M1\|h=5\|TRAIN | 347 | 327 | 3.397760e-02 | 257 | 5.899976e-03 |
| adr_baba\|M1\|h=5\|TUNE | 114 | 108 | 9.905826e-05 | 82 | 8.456151e-03 |
| adr_baba\|M2\|h=5\|TRAIN | 347 | 325 | 4.231774e-02 | 253 | 2.074413e-03 |
| adr_baba\|M2\|h=5\|TUNE | 114 | 106 | 7.970808e-03 | 83 | 6.121994e-03 |
| adr_baba\|IPCA\|h=5\|TRAIN | 0 | 0 | n/a | 0 | n/a |
| adr_baba\|IPCA\|h=5\|TUNE | 0 | 0 | n/a | 0 | n/a |
| adr_baba\|M0\|h=21\|TRAIN | 94 | 91 | 3.678123e-02 | 65 | 6.660485e-03 |
| adr_baba\|M0\|h=21\|TUNE | 31 | 29 | 3.065478e-01 | 21 | 6.828385e-02 |
| adr_baba\|M1\|h=21\|TRAIN | 94 | 89 | 8.544829e-02 | 63 | 3.249327e-03 |
| adr_baba\|M1\|h=21\|TUNE | 31 | 29 | 2.954458e-01 | 21 | 2.383459e-02 |
| adr_baba\|M2\|h=21\|TRAIN | 94 | 87 | 1.324142e-02 | 73 | 1.527113e-02 |
| adr_baba\|M2\|h=21\|TUNE | 31 | 30 | 8.825988e-02 | 17 | 3.666367e-02 |
| adr_baba\|IPCA\|h=21\|TRAIN | 0 | 0 | n/a | 0 | n/a |
| adr_baba\|IPCA\|h=21\|TUNE | 0 | 0 | n/a | 0 | n/a |
| adr_baba\|M0\|h=63\|TRAIN | 32 | 32 | 1.018229e-02 | 19 | 2.943569e-03 |
| adr_baba\|M0\|h=63\|TUNE | 10 | 10 | 2.181819e-01 | 9 | 1.099152e-01 |
| adr_baba\|M1\|h=63\|TRAIN | 32 | 30 | 3.018260e-02 | 18 | 3.897850e-02 |
| adr_baba\|M1\|h=63\|TUNE | 10 | 10 | 3.053157e-01 | 8 | 1.093414e-01 |
| adr_baba\|M2\|h=63\|TRAIN | 32 | 31 | 4.114673e-01 | 25 | 8.467768e-02 |
| adr_baba\|M2\|h=63\|TUNE | 10 | 9 | 2.343590e-02 | 7 | 9.531141e-02 |
| adr_baba\|IPCA\|h=63\|TRAIN | 0 | 0 | n/a | 0 | n/a |
| adr_baba\|IPCA\|h=63\|TUNE | 0 | 0 | n/a | 0 | n/a |
| hkd_9988\|M0\|h=5\|TRAIN | 121 | 116 | 2.293705e-02 | 86 | 9.748485e-03 |
| hkd_9988\|M0\|h=5\|TUNE | 111 | 105 | 2.216839e-03 | 75 | 1.431230e-02 |
| hkd_9988\|M1\|h=5\|TRAIN | 121 | 113 | 3.797777e-02 | 100 | 7.851262e-03 |
| hkd_9988\|M1\|h=5\|TUNE | 111 | 105 | 7.826110e-02 | 79 | 6.849976e-03 |
| hkd_9988\|M2\|h=5\|TRAIN | 99 | 92 | 1.813912e-01 | 77 | 8.362114e-03 |
| hkd_9988\|M2\|h=5\|TUNE | 111 | 104 | 3.342746e-02 | 77 | 1.188081e-02 |
| hkd_9988\|M0\|h=21\|TRAIN | 33 | 32 | 1.640492e-01 | 21 | 2.385504e-03 |
| hkd_9988\|M0\|h=21\|TUNE | 28 | 24 | 4.646692e-02 | 21 | 3.291110e-03 |
| hkd_9988\|M1\|h=21\|TRAIN | 33 | 33 | 6.812551e-02 | 22 | 7.707316e-03 |
| hkd_9988\|M1\|h=21\|TUNE | 28 | 26 | 6.435733e-03 | 19 | 5.190782e-02 |
| hkd_9988\|M2\|h=21\|TRAIN | 26 | 24 | 9.140766e-02 | 18 | 6.354430e-03 |
| hkd_9988\|M2\|h=21\|TUNE | 28 | 27 | 1.885591e-01 | 19 | 4.128946e-03 |
| hkd_9988\|M0\|h=63\|TRAIN | 11 | 11 | 8.105930e-01 | 9 | 7.353174e-02 |
| hkd_9988\|M0\|h=63\|TUNE | 10 | 10 | 8.047299e-01 | 8 | 1.508573e-01 |
| hkd_9988\|M1\|h=63\|TRAIN | 11 | 11 | 8.939425e-01 | 10 | 6.605746e-02 |
| hkd_9988\|M1\|h=63\|TUNE | 10 | 10 | 1.561508e-01 | 9 | 4.370156e-02 |
| hkd_9988\|M2\|h=63\|TRAIN | 8 | 8 | 9.366043e-01 | 7 | 2.339574e-02 |
| hkd_9988\|M2\|h=63\|TUNE | 10 | 9 | 2.947115e-02 | 9 | 1.512970e-01 |
| hkd_0700\|M0\|h=5\|TRAIN | 404 | 376 | 7.848211e-03 | 277 | 1.138977e-04 |
| hkd_0700\|M0\|h=5\|TUNE | 109 | 100 | 7.007011e-02 | 80 | 5.047525e-04 |
| hkd_0700\|M1\|h=5\|TRAIN | 404 | 381 | 5.167365e-03 | 300 | 3.600648e-03 |
| hkd_0700\|M1\|h=5\|TUNE | 109 | 98 | 1.761914e-01 | 81 | 2.365287e-05 |
| hkd_0700\|M2\|h=5\|TRAIN | 101 | 96 | 3.311650e-02 | 68 | 1.428983e-02 |
| hkd_0700\|M2\|h=5\|TUNE | 109 | 97 | 3.680893e-03 | 78 | 4.731139e-03 |
| hkd_0700\|M0\|h=21\|TRAIN | 109 | 100 | 5.424433e-02 | 73 | 1.607655e-02 |
| hkd_0700\|M0\|h=21\|TUNE | 28 | 27 | 1.119839e-01 | 21 | 5.671288e-02 |
| hkd_0700\|M1\|h=21\|TRAIN | 109 | 103 | 2.408300e-02 | 72 | 3.076846e-03 |
| hkd_0700\|M1\|h=21\|TUNE | 28 | 27 | 1.599305e-01 | 17 | 7.831118e-03 |
| hkd_0700\|M2\|h=21\|TRAIN | 26 | 26 | 1.714782e-01 | 19 | 7.906766e-02 |
| hkd_0700\|M2\|h=21\|TUNE | 28 | 27 | 1.287971e-01 | 17 | 3.259092e-02 |
| hkd_0700\|M0\|h=63\|TRAIN | 37 | 34 | 3.883146e-02 | 22 | 5.472258e-03 |
| hkd_0700\|M0\|h=63\|TUNE | 10 | 10 | 5.282333e-01 | 6 | 6.002281e-03 |
| hkd_0700\|M1\|h=63\|TRAIN | 37 | 34 | 1.143861e-01 | 24 | 1.409909e-02 |
| hkd_0700\|M1\|h=63\|TUNE | 10 | 9 | 1.950358e-02 | 6 | 4.625717e-02 |
| hkd_0700\|M2\|h=63\|TRAIN | 8 | 8 | 2.112995e-01 | 7 | 2.744121e-02 |
| hkd_0700\|M2\|h=63\|TUNE | 10 | 10 | 1.283337e-01 | 6 | 9.141429e-02 |

Closest `|z|` to 1.96: `adr_baba|M1|h=5|TUNE` at 9.905826e-05
(margin/eps = 9.905826e+06).
Closest `|z|` to 1.0: `hkd_0700|M1|h=5|TUNE` at 2.365287e-05
(margin/eps = 2.365287e+06).

## Positive control

A synthetic `|z| = 1.96 * (1 - 1e-13)` sits just inside the 1.96
coverage threshold. The same eps = 1e-11 relative perturbation flips
the `_calibration` coverage count for at least one seed in 0..7. That
shows test 02 is not vacuous: the perturbation is large enough to move
a decision that genuinely sits at its threshold. A paired set with
delta_R2 on the order of +1e-13 cannot flip `met` through this engine,
because `mirror_mean_ci` rounds bounds to 4 decimal places and a
1e-13-scale mean rounds to 0.0, so `ci[0] > 0` stays false; the
coverage-count control is the threshold-adjacent case.

## Bounds

Covers P03 only. Per XREP, P01/P02 outputs were byte-identical
cross-host (S1 v1.1 files compared = 48, identical = 35, named-exception
passes = 3, ulp-equivalent = 10, and those 10 ulp-equivalent files are
the P03 observations and `results/P03.json`). This document does not
re-pin SCHK and does not re-run macOS. Integer budget rows
(`declared_budget`, `literal_n`, `effective_n`) are trial-ledger
integers; the comparison path does not read them from float fields.

## Gaps

- No macOS re-execution in this lane; the perturbation scale is taken
  from the XREP addendum bound.
- Unrounded CI bounds are a local replica of `block_bootstrap_ci`
  without the final 4-dp round, using the same seed and draw count.
- POWER_FLOOR abstain is an integer comparison (`honest_n` vs 153) and
  is insensitive to ULP-scale float drift; it is checked for
  invariance, not for a float margin.
- This is a descriptive stability property of committed P03 numbers.
  It is not a reason to treat `ulp-equivalent` as `identical`.
