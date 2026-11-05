---
key: BOTTOM-LEDGER-MASKED-CRASH-FROM-BIRTH
claim: >
  The Bottom Ledger P1 forward advancer (scripts/grade_bottom_calls.py, shipped PR #3184)
  produced NOTHING for its entire life: it raised
  `TypeError: Cannot compare tz-naive and tz-aware timestamps` inside `mature_rows()` on
  every run, at the maturity pre-check `as_of < pd.Timestamp(flag_date) + pd.Timedelta(
  days=BR.H)`. `as_of` came from `pd.Timestamp.utcnow().normalize()` (tz-AWARE, and
  deprecated in pandas 3.x); every producer writes a plain `YYYY-MM-DD`, so `flag_date`
  parses tz-naive. The crash lands BEFORE `_atomic_write_parquet` and before the emit, so
  neither `data/bottom_ledger/rows.parquet` nor `site/factordata/us_bottom_ledger.json`
  has ever existed in git history — confirmed by `git log --all -- data/bottom_ledger`
  returning empty and `git ls-files | grep bottom` listing neither path. `.github/
  workflows/daily.yml` invoked it as `... --nightly || true`, so the nightly reported
  success every night. A second, quieter defect shares the root: when a price index and a
  flag_date disagree on tz-awareness, `bottom_ruler.grade_call` matches no bar and returns
  `None` SILENTLY, so rows would accrue forever and never mature with no error at all.
  The suite could not catch either one: every pre-existing pipeline test in
  tests/test_bottom_ledger.py points the price readers at EMPTY directories, so
  `_read_prices` returns None and every row is skipped before the maturity comparison is
  ever executed — 16/16 green over a code path that could not run in production.
falsifier: >
  A `data/bottom_ledger/rows.parquet` or `site/factordata/us_bottom_ledger.json` blob
  appearing anywhere in git history (`git log --all --oneline -- data/bottom_ledger
  'site/factordata/us_bottom_ledger.json'` returning any commit), or the pre-fix advancer
  completing against real inputs. Runnable repro on the pre-fix tree:
  `python -m scripts.grade_bottom_calls --force-local --out-dir /tmp/bl` → TypeError at
  scripts/grade_bottom_calls.py:479, and /tmp/bl left EMPTY (no partial write).
so_what: >
  Two standing lessons. (1) `|| true` on a nightly step does not make a module "resilient" —
  it makes its death invisible, and the absence of output reads as "nothing has matured
  yet", which is exactly what the artifact was designed to say during accrual. A non-fatal
  step must still be LOUD: emit a line-start `::error` and let the artifact carry its own
  `advance.status`. (2) A test fixture that starves a code path (empty price dirs) buys
  green without coverage; the maturity comparison is reachable only when rows actually
  mature, so a maturing fixture is mandatory for any grader. Repaired by the clock contract
  in engine/ledger_clock.py — see DEC:BOTTOM-LEDGER-CLOCK-CONTRACT-IS-CIVIL-DATE.
kind: landmine
verified_at: 2026-09-18
verified_by: >
  `git log --all --oneline -- data/bottom_ledger 'site/factordata/us_bottom_ledger.json'`
  (empty) and `git ls-files | grep -i bottom` (neither path present) on
  main@c265eded353465f41eaad32580d4297ab264ae86; pre-fix crash reproduced with
  `python -m scripts.grade_bottom_calls --force-local --out-dir <dir>` (TypeError at
  scripts/grade_bottom_calls.py:479, output dir left empty); the starved-fixture gap read
  directly from tests/test_bottom_ledger.py::_grader_env (STOCKS_DIR/YAHOO_DIR point at
  non-existent dirs).
scope: [macro]
confidence: verified
---

