---
key: HARDENING-A-UNIVERSAL-RESOLVER-AT-MODULE-SCOPE-CAN-BREAK-EVERY-IMPORT
claim: >
  A guard added at MODULE SCOPE inside a canonical resolver converts a config typo into a
  build-wide import failure, and the two idioms that look safest are the two that fail. (1)
  `float(os.environ.get(K, "10"))` at module scope raises `ValueError: could not convert string to
  float: ''` on the most realistic bad value — not a typo, but a workflow `env:` key declared with
  no value, which GitHub Actions passes as the empty string. Because `engine/thetadata_store.py`
  is imported by every ThetaData consumer, that one empty variable takes down the whole build, not
  the one lane that set it. (2) The obvious sanity check `if v <= 0: v = DEFAULT` does NOT catch
  NaN: measured here, `nan <= 0`, `nan < 0` and `nan == 0` are ALL False, so `float("nan")` passes
  every comparison guard and then raises `ValueError: Invalid value NaN (not a number)` inside
  `Thread.join(nan)` — turning a resolver documented as never raising into one that raises, deep
  in a call its own callers do not guard. `v != v` is the only test that catches it.
  Separately and for the same reason: `Thread.start()` raises `RuntimeError` when the process
  cannot create another thread, so even a correct budget can make a bounded probe raise; refusing
  to resolve because the PROBE could not start is the same false-RED the probe exists to avoid.
falsifier: >
  `python3 -m pytest tests/test_thetadata_resolver.py::TestAMalformedProbeBudgetNeverBreaksTheImport tests/test_thetadata_resolver.py::TestTheProbeNeverMakesResolutionRaise -q`
  (parametrized over "", "abc", "nan", "  ", "1e", "None", plus a NaN case and a valid-value case,
  plus a test that monkeypatches `threading.Thread.start` to raise RuntimeError). Direct mechanism
  check, re-run 2026-09-29: `float("")` -> ValueError; `nan <= 0` -> False; `nan != nan` -> True;
  `Thread(...).join(float("nan"))` -> ValueError. If a future refactor restores a bare
  `float(os.environ[...])` at module scope, or replaces the `v != v` branch with a comparison, this
  is refuted.
so_what: >
  When adding ANY module-scope configuration read to a module on a universal import path, assume
  the value arrives empty rather than absent — `os.environ.get(K, default)` returns "" not the
  default when the key exists and is blank, which is exactly what an under-specified workflow
  `env:` produces. Wrap the parse, and give NaN its own `v != v` branch rather than a comparison.
  And when a guard runs inside a thread, timer or subprocess, check what happens when the
  MECHANISM fails to start, not only when the check fails: a resolver whose callers document that
  it never raises (see `engine/options_skew.py` load_chain) must keep that contract even when the
  OS refuses it a thread.
kind: landmine
verified_at: 2026-09-29
verified_by: "PR #8203, merge 54f62e4d4b25c4e475ece482aff856d052e42e67; engine/thetadata_store.py::_probe_budget; direct python3 mechanism check 2026-09-29"
scope:
  - macro
  - engine/thetadata_store.py
  - WS:ADVANCED-DATA-OPTIONS
confidence: verified
---

## The two failing idioms, side by side

```python
_S = float(os.environ.get("K", "10"))      # ValueError at IMPORT when K="" -> whole build down
v = float(raw)
if v <= 0: v = 10.0                        # NaN passes: nan<=0 is False -> ValueError in join()
```

```python
def _probe_budget() -> float:              # the shape that holds
    raw = os.environ.get("K", "10")
    try: v = float(raw)
    except (TypeError, ValueError): return 10.0
    return 10.0 if v != v else v           # v != v is True only for NaN
```

## Why the blast radius is the whole build, not one lane

`engine/thetadata_store.py` is THE canonical resolver — every ThetaData consumer imports it. A
module-scope raise there is not a failure of the lane that set the bad variable; it is an
ImportError in every lane that imports the module, including lanes that never read the variable
and cannot see why they broke.

## Prior art

Same mechanism, different language: a NaN comparison silently defeating a `<=` guard is recorded
in account-local memory as `nan-comparison-makes-a-js-guard-fail-open`. It recurs here in Python
because the cause is IEEE-754, not the language — which is why it belongs in company memory
rather than one account's.
