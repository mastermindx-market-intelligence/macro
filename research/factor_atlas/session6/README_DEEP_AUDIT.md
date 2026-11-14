# Factor Atlas S6 - reproducible deep audit

This package contains author-controlled synthetic tests and methodology diagnostics.
It is not real market validation, source admission, independent acceptance or a
production release. No command below uses credentials, market APIs or holdouts.
The original inactive market registration remains unchanged.

## Inputs and source

- Original PR #8696 / predecessor fbaa3812510a67e879c17defa270e16f717d3ce3.
- `source/` is the exact predecessor test target, retained for reproduction only.
- `prototype/structural_guards.py` is the repaired research-only instrument.
- `DEEP_ASSESSMENT_2026-10-09.md` states findings and remaining scientific gates.
- `evidence/DEEP_AUDIT_RECEIPT.json` records source and raw-output digests.

No authority follows from a caller's metadata or a passing synthetic test. The
instrument does not authenticate a source, verify a full roster, implement an
exchange calendar, or compute a financial hypothesis p-value. Its numeric bounds
are research resource limits, not production policy.

## Reproduce

Use a disposable checkout or extracted copy so rerunning only replaces disposable
local evidence, never canonical history. The commands write under `evidence/` and
pytest temporary directories only. Mutation tests use disposable temporary source
copies; the normal source is not modified.

Observed environment: Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, pytest 9.0.2 on the
isolated Linux conversation container. Packages were already installed; no new
installation or paid computation was performed. Other BLAS/library versions may
change floating-point roundoff in synthetic regression results.

```sh
mkdir -p evidence
cd prototype
python -m unittest -q test_structural_guards
python -m pytest -q test_structural_guards.py test_deep_guards.py
python audit_original.py
python mutation_check.py
OPENBLAS_NUM_THREADS=1 python synthetic_methods.py
OPENBLAS_NUM_THREADS=1 python bootstrap_diagnostic.py
```

Expected scope: original 36 tests retained; 197 parametrized tests plus 3 subtests
passed in the observed environment. Test presentation of subtests varies by pytest
version/plugins. All eight selected semantic mutants were detected. The original
29 counterexamples deliberately expose old failures and therefore are expected
negative findings, not failures of the repaired source.

The two simulation JSON specifications were written before their respective
synthetic runs. They are outcome-free method-test protocols, NOT owner-accepted
market experiment registrations. Their results cannot establish a market edge,
production false-positive rate, actual source coverage or user comprehension.
Do not substitute the known-covariance oracle for a feasible inference method.

## Preserved gates

The existing Evaluation OS must accept a source-bound revised experiment before
novel market outcomes are examined. Original Data OS/price/GMI/options owners must
admit exact inputs. Trend Persistence, Factor Intelligence and K3E frozen families
are not reopened. An independent reviewer must judge this author's code and design.
Real authenticated browser, entitlements, correction/replay, mobile and human
acceptance remain separate. No merge, deployment or financial authority is given.
