# Q08 — PREREG_AMENDMENT 1 (provenance replay)

Author: Claude Opus 5.5 (model ID `claude-opus-5-5`), Q08 finisher lane.
Written BEFORE the replay run described below was executed and before any of
its outputs were read. `PREREG.md` is unchanged
(sha256 `23a6f671da42e23a0660447f984f92662c34db8d5ff894b95753125513bc8a03`,
as recorded in `FREEZE.log`).

## 1. Reason

An independent audit (verdict PASS_WITH_FIXES; 0 blocker, 1 major, 5 minor)
found that the shipped module `engine/covariance_shrinkage_diagnostics.py` has
sha256 `b591ee9bf634543cb8faf5ff55a53ddf76152fcfa107a4392667d1a22b434317`,
while PREREG §3 (at freeze) and both `RUN` lines in `RUNS.log` record
`93fa59944845560797eb0d2826cd8c11a53acbb882275aa7108b2536380789f5`. PREREG §3
allows only the module docstring's VERDICT text to change after evaluation,
but the `93fa…` bytes are not retained anywhere, so a docstring-only change
cannot be proven by sha reconstruction or AST comparison.

## 2. What this amendment does

It authorises exactly one replay of the preregistered evaluation, with an
IDENTICAL specification, on the module bytes that actually ship (`b591…`). The
replay checks provenance only. It is not a new test, not a holdout search, and
not an audition: the windows (W = 252, sensitivity W = 60), horizon 21, origins,
K = 17, losses, bootstrap (block 3, B = 10 000, seed 20261008, Bonferroni
1 − 0.05/3), HAC lag 3, PR bootstrap settings, effect bar 0.005 and decision
rule of PREREG §§4–8 are all unchanged.

Each mode runs exactly once:

    OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 nice -n 10 \
      env PYTHONPATH=<Q08> PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 evaluate.py --mode baseline
    (same prefix) ... evaluate.py --mode evaluate

## 3. Code state at replay (sha256)

| File | sha256 |
|---|---|
| `engine/covariance_shrinkage_diagnostics.py` (shipped, unchanged by the finisher) | `b591ee9bf634543cb8faf5ff55a53ddf76152fcfa107a4392667d1a22b434317` |
| `research/.../evaluate.py` (finisher edits below) | `6f0bc3889412da69a6f16981fe246ff60fc550726fd922d182065564e51a343f` |
| `research/.../PREREG.md` (frozen) | `23a6f671da42e23a0660447f984f92662c34db8d5ff894b95753125513bc8a03` |
| `engine/neuralweb/covariance_spine.py` (incumbent) | `61a556894986e1c91d6dff8beffd21536a554b0e3a044eace6bd41e73d1705a3` |
| `engine/validation.py` (incumbent HAC) | `9680d00241fa58ccb504b679d1ee19d64b52b6f46b6bf87a5149969bc7ec4e3b` |
| input `data/breadth/_factor_legs.parquet` @ cdab6268 | `cc3476e61b50e8eda312b11393fa2231fde587a821d011a8dd58d32987fe94bd` |

Finisher edits to `evaluate.py` since the original run (sha `172369a7…8bd5b`).
None of them changes any computation:

* the top-of-file no-op string became comments;
* a `--data` argument was added; its default is the same path and the same
  sha256 guard (exit 4) still applies;
* the incumbent-reproduction scratch directory is now created with
  `tempfile.mkdtemp()` in the system temp dir instead of inside the package
  directory (the incumbent reads only the JSON document written there);
* the sha256 of this amendment is logged among the run inputs.

## 4. Pre-declared reading of the replay

The original outputs were:

* `baseline_reproduction.json` `0e624c081469baf4856d31675b6c49486cccf638e285756ea4eb0edc37796d9a`
* `results.json` `4e72ab05c186b3204da8c1cf3b0c3b212f2ced864367ab52c1b39aaa74006df0`
* `results_detail.json` `17a2a5edbe5ccfd535c35f59098908c9bea589b25f420f0a46b0a5b67ad4523d`

* **Byte-identical replay** (all three sha256s equal): no result-bearing code
  path changed between `93fa…` and `b591…` for this evaluation. The original
  verdict stands, and the provenance gap shrinks to "the old bytes are not
  retained; equivalence of outputs is shown".
* **Any difference**: the replay on the shipped bytes GOVERNS. Its verdict
  under the unchanged PREREG §6 rule replaces the original, and the difference
  is disclosed in `VERDICT.md` and the PR body. No further run is allowed.
* **Crash**: one rerun with an identical specification (PREREG §9), logged.

A non-RUN `PROVENANCE` line comparing the sha256s is appended to `RUNS.log`
after the replay.
