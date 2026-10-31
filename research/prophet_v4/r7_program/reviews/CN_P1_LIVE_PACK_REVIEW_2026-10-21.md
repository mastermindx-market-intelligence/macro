# CN P1 live pack — adversarial review (PR #9929)

- **Reviewer seat**: ROUTE review / C1, read-only beyond this file.
- **Artifact**: `git diff a580ce7e780f46775fcacec282be590ed14ee802..0b543c573221`
  (head = BASE). Commits: `f364dcf168ec` (factordata board projection),
  `0b543c573221` (tradability gate on the armed-pack path). Both are cherry-picks;
  trailing `Co-Authored-By` trailers name both carriers.
- **diff --stat** (verbatim):

```
 .github/ci/legacy-jobs.yml        |   1 +
 engine/prophet_live/cn_pack.py    |  82 ++++++++++++++++-
 scripts/build_china_library.py    | 162 ++++++++++++++++++---------------
 scripts/build_cn_live_pack.py     | 102 +++++++++++++++++++--
 tests/test_cn_live_pack.py        | 157 ++++++++++++++++++++++++++++++++
 tests/test_cn_live_pack_frozen.py | 185 ++++++++++++++++++++++++++++++++++
 6 files changed, 609 insertions(+), 80 deletions(-)
```

## Frozen-spec conformance

Projection: (1) candidate order is exactly
`site/factordata/china_standouts.json` → `site/china_standouts.json` →
`data/china_standouts.json` (`scripts/build_cn_live_pack.py:49-50`). (2) A doc
carrying any primary array as a list goes through `CP.project_primary_board`
(`scripts/build_cn_live_pack.py:60-71`); refusal → `::warning` + `return {}`,
never a raise, never a clobber (see surface 3). (3) P8 pins the BASE defect
(see surface 4). Tradability: `load_tradability_metadata() -> dict[str, dict]`
sits at module level immediately after `stock_tradability_ok`
(`scripts/build_china_library.py:94-176`), returning exactly
`mktcap_by`/`name_zh_by`/`name_en_by`/`st_flag_by`; nightly `main()` passes
`tradable=tradable, universe_rows=rows` (`scripts/build_cn_live_pack.py:287-288`);
strict coverage raises `RuntimeError` naming `missing/total` and the first five
tickers, and the same raise covers the empty-map-over-non-empty-universe case
(`scripts/build_cn_live_pack.py:146-150`); `build(tradable=None)` path is
byte-equivalent to parent (`if tradable is not None:` skips for `None`, and no
existing caller passes `{}` — census in surface 8).

## Attack surfaces

### 1. Publication path and writer-before-reader ordering — PASS

Nightly workflow: `.github/workflows/asia-close.yml` (`name: asia-close`,
`schedule:` trigger, line 11). Job **`asia`** (`asia-close.yml:181`, `needs:
gate`) runs both scripts as sequential steps on the same runner workspace —
no checkout between them:

- Step **"build china a-share dashboard (spine — serial head, every CN surface
  reads it)"** (`asia-close.yml:347`) runs `python -m scripts.build_china`
  (`asia-close.yml:384`), which calls `build_china_library.main()` in-process
  (`scripts/build_china.py:171-173`). `main()` writes the canonical board at
  `scripts/build_china_library.py:4952`
  (`_standouts_path.write_text(_standouts_payload)`, where
  `_standouts_path = site / "factordata" / "china_standouts.json"`; the
  zero-universe outage shell writes the same path at `:5085`). The step's own
  planning comment names the artifact: "it writes … site/factordata/
  china_standouts.json … It also runs build_china_library.main() in-process"
  (`asia-close.yml:383-386`). `scripts/build_china.py:2169` reads the file back
  in the same step, after the library call.
- Step **"CN Prophet Live arming pass (settled-close trigger pack -> R2)"**
  (`asia-close.yml:427`) runs
  `python -m scripts.build_cn_live_pack --publish --out "$RUNNER_TEMP/cn_prophet_live_armed.json"`
  (`asia-close.yml:446-447`). No `--root` is passed, so `--root` defaults to
  `_CODE_ROOT` = the repo checkout (`scripts/build_cn_live_pack.py:261`), and
  `load_frozen(root)` reads the `site/factordata/china_standouts.json` written
  two steps earlier in the same job. The step's comment states the ordering:
  "# AFTER build_china (the library rebuild is in-process there)"
  (`asia-close.yml:428`).

Board row shape matches the projection contract at the writer:
`engine/china_board_rank.py:919` builds the nested `row["prophet"]`, `:661/:664`
assign `board_rank`, `:945` assigns `score_rank`; the top-level doc is
assembled with `as_of`, `buy`, `more_actionable`, `late_or_unfillable`,
`forming`, `reversal_watch`, `watch` (compat union alias) at
`scripts/build_china_library.py:4144-4157`. `tests/test_cn_live_reconcile.py:18-24`
independently pins the arming step's presence and non-fatality. No other
nightly workflow invokes `build_cn_live_pack` (grep across
`.github/workflows/*.yml` and `scripts/*.sh`: only `asia-close.yml:446`).

### 2. Fail-closed blast radius — PASS

A tradability refusal (missing key / empty map) raises `RuntimeError` inside
`build()` (`scripts/build_cn_live_pack.py:148-150`), which is inside `main()`'s
single `try` (`:265-307`); the handler prints
`::error title=cn-live-pack::<exc>` and `return 1` (`:308-310`) **before** the
`--out` write (`:311-313`) and the `--publish` R2 put (`:314-317`). So on
refusal nothing is written anywhere: not the local `--out` file, not R2.

Enclosing step: "CN Prophet Live arming pass" (`asia-close.yml:427`), which is
`continue-on-error: true` (`asia-close.yml:433`) and internally `set +e` +
rc-capture + `exit 0` (`asia-close.yml:445-450`):

```
          python -m scripts.build_cn_live_pack --publish \
            --out "$RUNNER_TEMP/cn_prophet_live_armed.json" > "$RUNNER_TEMP/cn_live_pack.log" 2>&1; rc=$?
          ...
          if [ "$rc" -ne 0 ]; then echo "::warning title=build_cn_live_pack::rc=$rc (non-fatal …)"; fi
          exit 0
```

`live_flow/cn_prophet_live_armed.json` (`r2io.CN_PACK_KEY`,
`engine/prophet_live/r2io.py:38`) has exactly one writer in the repo —
`scripts/build_cn_live_pack.py:315`, the post-success `--publish` path. On
refusal the previous night's armed pack stays intact in R2 (never replaced,
never deleted); the 5-minute evaluator lane reads it and reports `stale_pack`
(documented non-fatal semantics, module docstring
`scripts/build_cn_live_pack.py:3-5`). The only failure that could publish an
unfiltered pack would be a *successfully built* pack with a partial map —
exactly what the strict coverage check makes unreachable, and `main()`'s
complete-map construction (`:283`) plus the `assert set(tradable) == set(tickers)`
(`:284`) double-pin it. `--out` targets `$RUNNER_TEMP`, which is per-job
(`asia-close.yml:373-375`), so no stale local carryover either.

### 3. `project_primary_board` refusal path — PASS

Every structural defect returns `({}, {"refused": …})` instead of raising:
non-dict doc / bad `as_of` (`engine/prophet_live/cn_pack.py:160-166`, regex +
`strptime` both guarded), cross-array duplicate ticker
(`engine/prophet_live/cn_pack.py:193-194`). Per-row defects (bad ticker/score/
board_rank) exclude that row only, counted under a reason key
(`:178-191`) — a valid sibling still projects (P4 proves this). The caller maps
refusal to `::warning` + `return {}` (`scripts/build_cn_live_pack.py:63-66`) and
success to `::notice` + `return rows` (`:67-71`); nothing is written by
`load_frozen` at any point, so no empty map can overwrite a good projection —
the projection result and its return are atomic, and the loop returns on the
first primary-array doc either way. Note (non-blocking): a *refused* factordata
doc does not fall through to the legacy candidates (only an *unreadable* one
does, via the `continue` at `:59`) — deliberate fail-loud per the docstring,
and outcome-equivalent to BASE (frozen `{}`, pack still publishes with empty
frozen legs, same as a missing file). Also verified: the zero-universe outage
artifact (all arrays empty lists) projects to a non-refused `{}` — BASE-equivalent.

### 4. P8 realism — PASS (one NOTE)

`tests/test_cn_live_pack_frozen.py:141-158` (`test_p8_base_load_frozen_ignored_the_factordata_board`)
obtains the parent file exactly as the spec suggests — `git show` of a pinned
BASE SHA into a throwaway tmp_path module — and asserts the defect:
`assert base_mod.load_frozen(tmp_path) == {}` against the canonical
`_primary_doc()` fixture. The skip is named and fires only when the object is
absent: `pytest.skip(f"BASE {BASE_SHA[:8]} absent from this clone (shallow
checkout)")` gated on `git cat-file -e <sha>^{commit}`.

- The hardcoded `BASE_SHA = e5dd30c6344e…` is **not** the packet's BASE sha,
  but its `scripts/build_cn_live_pack.py` blob is byte-identical to
  `a580ce7e780f`'s: both resolve to `cd34927f428a45ab22c1da124f740d5c8bee3aee`
  (verified with `git rev-parse`); the object exists in this clone
  (`OBJECT_EXISTS`). The tested parent file is the exact BASE file.
- Discrimination: the assertion is true for the BASE module and false for the
  HEAD module on the same input (HEAD returns the 5 projected primary tickers —
  pinned by P1/P2, same fixture), so the defect is asserted from both sides:
  P1–P7 fail if the fix regresses, P8 fails if BASE was never broken.
- NOTE: P8 in isolation passes on a BASE checkout too (it always loads the
  historical module from git). Read with the packet's own clarification — "it
  must obtain the parent file … and assert the defect" — this is the blessed
  shape; the blocking rule targets tests whose assertion holds for both
  behaviors, which this one's does not.

### 5. `legacy-jobs.yml` registration — PASS

Exactly one line added — `tests/test_cn_live_pack_frozen.py` — inserted into
the existing `prophet-live P0 (G0.1 parity, ledger law, debounce, degradation)`
step of job **`express-render-guards`** (`legacy-jobs.yml:8709`, step list at
`:8915`); no job renamed or removed, no other line touched (diff shows `1 +`).
`python3 -c "import yaml; yaml.safe_load(open('.github/ci/legacy-jobs.yml'))"`
loads cleanly (`YAML_LOADS`). Matches the commit message's "rides
express-render-guards with the rest of the CN live-pack suites".

### 6. Sparse-tree hazard — PASS

`config/sparse_worktree.json` excludes `data`, `site`, `mockups`,
`verify_shots`. Every path the diff touches is guarded: `load_frozen` uses
`p.is_file()` per candidate (`scripts/build_cn_live_pack.py:52`);
`load_tradability_metadata` guards `members.parquet`/`moneyflow.parquet` with
`.exists()` and wraps the Tushare overlay in a broad `except` → `log.debug`
(`scripts/build_china_library.py:104-176` — a missing
`tushare/valuation.parquet` raises into the inner `except Exception` and is
swallowed); `china_liquidity._load` guards `p.exists()` and
`liquidity_map` additionally wraps each `profile()` in per-ticker `try`
(`engine/china_liquidity.py:38-56, 76-90`). On a bare sparse tree the script
degrades to empty metadata (pass-through tradability, empty frozen board) —
BASE-equivalent — rather than assuming `data/` exists. The new test fixtures
write only under `tmp_path` (module docstring: "the repository's real board is
never read").

### 7. Secrets / network / dependencies — PASS

New imports are `math`, `re` (stdlib, `engine/prophet_live/cn_pack.py:22-23`),
in-repo `from engine import china_liquidity`
(`scripts/build_cn_live_pack.py:32`) whose module level is `logging`/`pandas`/
`lib.config` only — no network at import, no I/O beyond the guarded parquet
reads at call time; and test-side `importlib.util`/`shutil`/`subprocess`
(stdlib; subprocess runs read-only local `git cat-file`/`git show`). No
`R2_*`/`*_KEY`/`*_SECRET`/`*_TOKEN` name appears anywhere in the diff. No new
third-party dependency; no package installs needed to run the tests.

### 8. Neutrality of non-tradable callers — PASS

Caller census (grep across `scripts`, `engine`, `tests`): `build()` from
`scripts/build_cn_live_pack` is invoked only by `main()` itself and the two CN
live-pack test files; no other module imports `build_cn_live_pack` (only a
doc-string reference in `scripts/cn_live_rescue.py:56` and a workflow-text
assertion in `tests/test_cn_live_reconcile.py:19`). `main()` is the sole
production caller and it passes the complete map. `build(tradable=None)`
preserves parent behavior exactly (`if tradable is not None:` —
`scripts/build_cn_live_pack.py:140`); the only behavioral delta is
`tradable={}` over a non-empty universe, which the frozen spec itself mandates
("an empty map raises"), and no caller passes it.
`build_china_library.main()`'s extraction is a faithful lift: the new
`load_tradability_metadata()` body is the deleted inline block verbatim (same
statements, comments, precedence, placeholder constant), and `main()` rebinds
the same four local names (`scripts/build_china_library.py:2285-2290`), so the
nightly board path is unchanged.

## Test runs (verbatim tails)

Command 1 (exactly as specified):

```
$ python3 -m pytest -q -p no:cacheprovider tests/test_cn_live_pack_frozen.py tests/test_cn_live_pack.py
........................                                                 [100%]
24 passed in 1.96s
```

Command 2 (exactly as specified):

```
$ python3 -m pytest -q -p no:cacheprovider -k "china and (live_pack or standout or tradab)" tests
…
INTERNALERROR>   File "…/tests/test_stripe_bootstrap_products.py", line 32, in <module>
INTERNALERROR>     from scripts import stripe_bootstrap as bootstrap
INTERNALERROR>   File "…/scripts/stripe_bootstrap.py", line 44, in <module>
INTERNALERROR>     sys.exit("The stripe SDK is required (pip install 'stripe>=11,<13')")
1 skipped, 5 warnings, 108 errors in 162.33s (0:02:42)
```

The full-tree sweep dies at **collection** on pre-existing, diff-untouched
files: `tests/test_stripe_bootstrap_products.py` (stripe SDK absent; installs
are forbidden here) and, after ignoring that one,
`tests/test_validated_claims_engine.py` (`scripts/check_validated_claims.py:643`
raises `SystemExit(1)` — its allowlist lives under the sparse-excluded
`data/`). Neither file is in the diff, so this is environmental, not a
regression. Bounded equivalent (see DEVIATIONS): I enumerated every test the
`-k` expression can select — by function name, class name, and module name
across all of `tests/` — to the closed set
{`test_cn_live_pack*.py` (command 1), `test_china_standout_track.py`,
`test_china_standouts_serialization.py`, `test_metabolism_memory_integrity.py`}
and ran the same `-k` over the latter three:

```
$ python3 -m pytest -q -p no:cacheprovider -k "china and (live_pack or standout or tradab)" \
    tests/test_china_standout_track.py tests/test_china_standouts_serialization.py tests/test_metabolism_memory_integrity.py
50 passed, 32 deselected, 4 warnings in 2.66s
```

## GAPS

- The full-tree `-k` sweep could not complete in this sparse, no-install
  environment (collection-time `SystemExit` in two untouched files). The
  candidate-set equivalent covers every test the expression can select
  (function/class/module name scan over all of `tests/`), but a rich runner
  would still be the authoritative full-tree proof.
- P8's hardcoded BASE SHA was proven blob-identical to the packet BASE for
  `scripts/build_cn_live_pack.py` only — the other five files at that SHA were
  not compared (irrelevant: P8 executes only that one file).
- Did not execute the real nightly `universe()`/metadata stack end-to-end
  (heavy data plane, sparse tree); the wiring is proven by tests + code path
  reading, not a live run.
- `repaint_disclosure.frozen_as_of` grows one entry (`score_rank`); consumers
  were not audited beyond noting the field is disclosure-only metadata on the
  armed pack (BASE always shipped `[]` there, so any consumer tolerant of the
  BASE steady state tolerates the new content).

## DEVIATIONS

- `mkdir -p research/prophet_v4/r7_program/reviews` (the directory did not
  exist) to place the mandated report file; the commit stages that one file
  only.
- Command 2 was rerun twice with targeted `--ignore`s to identify the two
  collection crashers, then once more as the candidate-set equivalent above —
  read-only test runs, no installs, no repo edits.
- No push, PR, label, or merge; reviewed files untouched.

## Verdict

STATUS: **PASS** — all eight surfaces PASS; notes recorded on surfaces 3 and 4
are non-blocking design clarifications, not defects. The two commits do what
the frozen spec says on the real publication path, fail closed without
endangering the armed pack, and pin both sides of each defect with tests.
