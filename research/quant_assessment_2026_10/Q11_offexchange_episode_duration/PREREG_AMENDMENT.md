# Q11 PREREG amendment A1 — code-integrity guard and audit fixes

PREREG.md (sha256 `10846dad35ab5a29c267f297a70755415e9fe7e071b068d537164b2d67eccd50`) is unchanged
and stays frozen. This amendment was written after the independent audit (PASS_WITH_FIXES,
0 blockers, 0 majors, 5 minors) and before any further evaluation output was read. It changes
no hypothesis, bar, metric, sample, split, seed, grid or stop rule.

## Reason

- **Audit finding 1.** PREREG §5 pins the candidate module at
  `f3a3134d2abd97b38c79956ba87f8d5978111913351fed744fff98f3701d1189` and the incumbent at
  `4483200a3c09456bb1f26b76850c5f216925d2b0b2e681cc8698608bcb1e95ec`, but evaluate.py only
  recorded the module hash and did not refuse on a difference. The original text of
  `f3a3134d` was not retained, so the exact pin can no longer be satisfied after the
  docstring-only edit that RUNS.log records (module `3b322794…`, byte-identical outputs).
- **Audit finding 2.** `update_detection_records` appended nothing when a record was open but
  the live episode was a different, newer one. This function is not on the evaluation path.
- **Audit finding 3.** The module docstring overstated gap behaviour. Docstring only.

## Rule (replaces "records the observed ones" in PREREG §5 for the candidate module)

evaluate.py refuses (exit 2, logged to RUNS.log as `module_check`) unless:

1. the incumbent `engine/darkpool_signals.py` equals its PREREG §5 pin exactly; and
2. the candidate module either equals its PREREG §5 pin exactly, or its evaluation-path AST
   digest equals the pin below. The digest is the sha256 of `ast.dump` over the module's
   import statements, the constants `MAX_SERIES_LEN`, `MAD_SCALE`, `_LOG_2PI`, and the
   definitions `robust_activity_z`, `DurationFilterParams`, `exit_hazards`, `_t_logpdf`,
   `FilterPath`, `filter_path`, `Episode`, `episodes_from_path`, `fit_emission_params`, with
   every docstring removed (see `eval_path_ast_digest` in evaluate.py); and
3. this file's own sha256 appears in FREEZE.log as `PREREG_AMENDMENT.md sha256=<hex>`.

eval_path_ast_sha256=3b9130bb9f18ca4c534d1376282edc4ec97872580f8179776518b054b2029805

The pin was computed on module `3b322794a333bcf674116374ca4fcd4b5f4dba0734abc8bf19d54beea7c07a01`,
the module whose evaluate.py run (RUNS.log, 10:00:02Z) reproduced the frozen-module run's
outputs byte-identically. The same digest holds for the post-fix module
`1afb0d15c673cd02d6af0d43ecec7bc219d4a262af28b2a4b3f2ad9ce9acb598`, because findings 2 and 3
touch only `update_detection_records` (off the evaluation path) and docstrings.

## Re-run condition (PREREG §14)

One deterministic re-run of evaluate.py is made under this guard. It must reproduce
`results/eval_summary.json` `0e829db76ebd6dd8521ef7b315cfe2889f2e1d217d8c919a5c4270f566257d50`
and `results/eval_replicates.csv` `5d9c4b751109d47dee610b6d91b6b9a1ee16c2dc8b58ec6e8e6ec4fd9a33204d`
byte-identically. If it does not, the original 09:58:41Z results stand as the verdict and the
divergence is reported in VERDICT.md; no second re-run is made.

## Known limit

The guard proves equality to the module that reproduced the frozen run, not to the
unretained `f3a3134d` text itself. That link rests on the RUNS.log record of byte-identical
outputs between the `f3a3134d` and `3b322794` runs.
