# Q16 PREREG amendment 1 — provenance reproduction run (no design change)

Frozen design: `PREREG.md` sha256 `edc8a34a3a77878960cc0ae4a96bda7ea0b4036b3539a30b5420015c490853c0`
(unchanged; FREEZE.log unchanged). This amendment is written, and its sha256 witnessed in
`AMENDMENT.log`, BEFORE the reproduction run it authorizes and before any new outcome is read.

## Reason

The independent audit found one MAJOR defect: the harness module
`engine/interval_delayed_calibration.py` was edited after the single evaluation run
(RUNS.log record 2 recorded sha256 `a8eba0a0017fa4f3e3616622c56c09aa0727db0dc5e82763e31eb0d953df67cb`;
the shipped file is `59db81bd854a1b5a18722a25fa3e3397680661ca068f65519b754825661b6725`). PREREG §4
permits only the `Q16_VERDICT` string and the docstring verdict sentence to change after the run,
but no pre-run copy or diff survives, so that claim cannot be checked, and `evaluate.py` did not
hash-check the module. The code that produced the evidence was therefore not provably the
shipped code.

## What changes

1. `evaluate.py` now refuses (exit 3) unless sha256(`engine/interval_delayed_calibration.py`)
   equals `59db81bd854a1b5a18722a25fa3e3397680661ca068f65519b754825661b6725`, and refuses (exit 2)
   unless this amendment's sha256 equals the `AMENDMENT_SHA256=` line in `AMENDMENT.log`. It also
   logs this file and `AMENDMENT.log` among the RUNS.log inputs. New `evaluate.py` sha256:
   `68119d1dc0189a869b2f75d5c88082ca8027edd647353683198209d400b72dcd`.
2. The record-2 outputs are moved, byte-unchanged, to `prior_run_record2/`
   (controls.json `7f464a9b…14a9`, empirical.json `661aa666…ee4b`, decision.json `dacfee6c…1085`),
   so the existing single-holdout stop rule (refuse while `decision.json` exists) admits exactly one
   reproduction run and refuses any further one.
3. Exactly ONE reproduction run of `evaluate.py` is authorized under this amendment.

## What does not change

Every parameter of PREREG.md: assets, horizon 22, alpha 0.2, split 2014-12-31, gamma grid, window
504, min calibration 252, tune start 504, bootstrap block 44, B 2000, seed 16, control seeds and
R = 200, decision rule c1–c5, honest-block floor 60. Data inputs and `engine/vol_forecast.py`
hashes are unchanged and re-checked. `q16_common.py` is unchanged. This is the same study, not a
new design.

## Pre-committed reading of the reproduction

- The reproduction run's outputs and verdict GOVERN, because they are produced by the shipped
  module under a hash check.
- Expected: `controls.json`, `empirical.json` and `decision.json` byte-identical to the record-2
  hashes above (the computation is seeded and deterministic; the post-run edit was claimed to touch
  only non-executing verdict text). Byte identity is reported as the evidence that the post-run edit
  did not change any computed number.
- If any output differs, the difference is reported in VERDICT.md and the reproduction's numbers and
  verdict replace record 2's; no further run is made.
