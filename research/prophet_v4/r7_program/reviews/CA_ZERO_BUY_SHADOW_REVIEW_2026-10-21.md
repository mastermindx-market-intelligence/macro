# CA zero-buy shadow liveness — adversarial review of PR #9930 (commit fbfd71df2fa)

- **Reviewer seat**: lane/pro-regional-cazb-review-20261021-r1 (REGIONAL packet, seat ruling F1, ROUTE review / C1 / routine-bounded / READ_ONLY)
- **Range reviewed**: `a580ce7e780..fbfd71df2fa` (single commit; HEAD of this lane = BASE, verified `git rev-parse HEAD` = `fbfd71df2fac9c1c0275adbf57db9d37338c5d61`, clean tree)
- **Frozen spec**: (a) no watch-only rows written to the board ledger on a zero-buy night; (b) `write_shadow` and the track-ledger emit each run exactly once on a zero-buy night; (c) non-empty-buy path byte-identical to parent behavior; (d) nothing fabricates rows.
- **Verdict: `STATUS: PASS_WITH_NOTES`** — all six attack surfaces PASS; the two NOTEs and the environmental test-infra caveats are below, none touch the diff.

```
$ git diff --stat a580ce7e780..HEAD
 scripts/build_canada.py    |  24 ++++--
 tests/test_board_shadow.py | 186 +++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 204 insertions(+), 6 deletions(-)
```

## Surface 1 — Zero-buy path: PASS

Diff hunk 1 replaces the parent's unconditional early return with a guard that fires only on a MISSING board object:

```python
# scripts/build_canada.py:693-695 (HEAD)
    if setups is None or not isinstance(setups, dict):
        return [_skip_row]
    rows = setups.get("buy") or []
```

With a real board dict and `rows == []`, control now falls through the whole block. Tracing every ledger-relevant sink:

- **Board ledger receives no rows, watch-only or otherwise.** The ONLY writer of the board ledger in this function is `board_ledger.append_board(calls, market="CA", asof=asof)`, and it is reachable solely through the `elif` arm at `scripts/build_canada.py:763-764`, guarded at `:759` by `if not rows:` (which only logs: "zero official buys for %s — append skipped (%d watch calls)"). Although the watch strip (`:743-755`) still populates `calls` with watch rows on a zero-buy night, that list is never handed to `append_board`. `board_ledger.scorecard("CA")` (`:782`) and `board_ledger.grade("CA")` (`:784`) are read projections.
- **Track-ledger emit runs exactly once.** Single straight-line block `:790-805`: one `_tl.from_board_ledger_grade(...)` (`:797`) followed unconditionally by one `_tl.atomic_write(... ca_track_ledger.json)` (`:803`) inside one `try`. No branch sits between them, so one invocation of the first implies exactly one of the second. It writes `ca_track_ledger.json`, not the board ledger.
- **`write_shadow` runs exactly once.** Single call site in the function: `board_shadow.write_shadow(calls, market="CA", asof=asof)` at `scripts/build_canada.py:816`, in its own fail-soft `try` (`:814-818`). `engine/board_shadow.py:949` is untouched pre-existing code; the diff's contribution is removing the early return that used to suppress this call.
- **Health output on zero-buy is the honest SKIP row alone** (`health = [] if rows else [_skip_row]`, `:756`) — identical health shape to the parent's SKIP return; no new ERROR row unless a downstream step raises (fail-open-LOUD, same as non-empty nights).
- Dynamic proof: T1/T2/T5 assert `seen == {"scorecard": 1, "grade": 1, "track": 1, "shadow": 1}` and `appends == []` (test_board_shadow.py:2401, 2433-2434, 2494-2499); all pass on HEAD (69/69).

## Surface 2 — Non-empty path: PASS

Parent (`a580ce7e780`, lines 685-688):

```python
    rows = (setups or {}).get("buy") or []
    if not rows:
        return [{"en": "Board ledger (no ranked names to log)", "zh": "榜单账本（无可记录个股）",
                 "status": "SKIP", "rows": 0, "last": "—"}]
```

For truthy `rows`, the parent never entered that return, so the only HEAD deltas that can touch the non-empty path are:

1. `health: list[dict] = []` → `health: list[dict] = [] if rows else [_skip_row]` (`:756`): with `rows` truthy this evaluates to `[]` — identical value.
2. `if _ledger_advance_enabled():` → `if not rows: <log> elif _ledger_advance_enabled():` (`:759-763`): with `rows` truthy, `not rows` is False and the `elif` evaluates the exact same predicate as the parent's `if`; the append body (`:764-773`) and the off-nightly `else` (`:774-776`) are unchanged.

Everything downstream (scorecard attach `:782-783`, grade `:784-787`, track-ledger emit `:790-807`, shadow write `:814-818`, outer fail-open-LOUD `:819-823`) is byte-identical. No second shadow write exists anywhere in the file (grep: `write_shadow(` has exactly one call site, `:816`), and ledger-write ordering is untouched. Dynamic confirmation: the 64 pre-existing tests in `tests/test_board_shadow.py` pass on HEAD (69/69 with the five new ones) — including the non-empty armed/off-nightly append tests.

**NOTE (N1, theoretical)**: for a truthy non-dict `setups` (e.g. a list), the parent raised `AttributeError` at `.get` (outside the try); HEAD returns the SKIP row. Strictly safer. For a non-dict `Mapping` carrying real buys, parent proceeded and HEAD would SKIP — unreachable from the real caller: `vm["setups"] = setups` is a plain dict built by the canada library (`scripts/build_canada.py:1482`) and the only call site passes `vm.get("setups")` (`:1505`); on library-build failure `vm.get("setups")` is `None`, which both parent and HEAD treat as SKIP.

## Surface 3 — Test realism: PASS

Harness: `/tmp/cazb_parent/` (outside the repo, never committed) — HEAD's `scripts/ engine/ lib/ config/ collectors/ tests/conftest.py tests/test_board_shadow.py` copied, then `git show a580ce7e780:scripts/build_canada.py` written over `scripts/build_canada.py`. Verified the harness's build_canada.py differs from HEAD by exactly the reviewed hunks (`git diff --no-index --stat`: `1 file changed, 18 insertions(+), 6 deletions(-)`), and the parent early return is present at its line 685. (First harness pass also failed `test_k1_hk_zero_authority_byte_identity` with `ModuleNotFoundError: No module named 'collectors'` — a copy-completeness artifact, fixed by copying `collectors/`; not a parent-behavior signal.)

Parent run (`cd /tmp/cazb_parent && MM_DATA_GUARD=off python3 -m pytest -q -p no:cacheprovider tests/test_board_shadow.py`):

```
FAILED tests/test_board_shadow.py::test_ca_zero_buy_armed_nightly_keeps_shadow_track_and_scorecard_alive
FAILED tests/test_board_shadow.py::test_ca_zero_buy_zero_watch_still_writes_empty_shadow
FAILED tests/test_board_shadow.py::test_ca_zero_buy_shadow_failure_is_contained
FAILED tests/test_board_shadow.py::test_ca_zero_buy_off_nightly_still_writes_shadow
4 failed, 65 passed in 1.02s
```

T1's failure carries the lane's exact reported text:

```
E       AssertionError: write_shadow must run exactly once; got 0
```

HEAD run: `69 passed in 1.37s` (zero failures). 65 + 4 = 69 — the only parent/HEAD delta is the four liveness tests. T3 (`test_ca_missing_board_object_is_skip_only_and_inert`) passes on BOTH parent and HEAD by design: it pins the unchanged missing-board contract (`setups=None` → SKIP on parent via `rows == []`, on HEAD via the explicit None/non-dict guard), so it is a boundary-pinning test, not the defect-catcher; the defining regression test T1 fails on parent exactly as reported. Not a both-pass BLOCKING case.

## Surface 4 — tests/test_prophet_board_since.py on HEAD: PASS (2 failures, both pre-existing, both outside the diff)

From mandated command 1 (`2 failed, 123 passed in 1.75s`):

1. `test_ca_laggards_strip_is_name_visible_disclosed_gap_floor_off` — `tests/test_prophet_board_since.py:390`: `assert "{% if setups.laggards %}" in text` where `text = (_ROOT / "templates" / "canada.html.j2").read_text(...)`. Pure template-text assertion on `templates/canada.html.j2`.
2. `test_us_board_cards_template_only_ever_included_with_buy_derived_items` — `tests/test_prophet_board_since.py:628`: `assert dash.count('include "_us_board_cards.html.j2"') == 1` got 2, on `templates/dashboard.html.j2`. Pure template-text assertion.

Neither failure touches the diff: `git diff --stat a580ce7e780..HEAD` shows the range changes exactly two files (`scripts/build_canada.py`, `tests/test_board_shadow.py`) — the two templates and `tests/test_prophet_board_since.py` are byte-identical between parent and HEAD, so their outcomes are necessarily identical on the parent (pre-existing). The test module also imports no `scripts.build_canada` / `board_shadow` (imports at `tests/test_prophet_board_since.py:7-19` are `engine.prophet_board_since` and stdlib/pandas; the mention of `_canada_board_ledger` at `:494` is a comment), so no behavioral coupling exists.

## Surface 5 — Collision with #7018 / #8444: PASS

`git diff --stat a580ce7e780..HEAD` lists only `scripts/build_canada.py` and `tests/test_board_shadow.py`. `templates/dashboard.html.j2` (the #7018 territory, hunks 865-940 / JS 189-220) is untouched; `sol/` does not appear in the diff (#8444 untouched). None of the packet's forbidden paths (`.claude/`, `engine/news_impact/`, `scripts/build_turn_watch.py`, `data/prophet/ledger*.jsonl`) appear.

## Surface 6 — Secrets / network / deps / data-assumptions: PASS

- Grep of all added lines for `key|secret|token|password|http|urllib|requests|socket|subprocess|import |pip ` (case-insensitive): zero hits. The diff adds no imports at any level — both hunks edit bodies of the existing function; the test additions use the file's existing module-level imports plus function-local `engine`/`scripts` imports already in idiom.
- No network at import time: no module-level statements changed anywhere.
- No `data/` assumption: the new tests stub `config.load` to `{"storage": {"site_dir": str(tmp_path)}}` (via `_stub_canada_health_read_side`, tests/test_board_shadow.py:2229-2232) and stub every engine writer; nothing reads or writes `data/`. `_board_asof`'s `store.read` fallback is pre-existing and only reached when `latest["date"]` is absent (tests always pass `{"date": ASOF}`).

## Mandated pytest commands (verbatim counts)

1. `python3 -m pytest -q -p no:cacheprovider tests/test_board_shadow.py tests/test_prophet_board_since.py`

   ```
   2 failed, 123 passed in 1.75s
   ```

   (the 2 failures = surface 4, both pre-existing template-text assertions.)

2. `python3 -m pytest -q -p no:cacheprovider -k "canada and (board or shadow or ledger)" tests`

   Exact form dies at collection on environment-broken modules unrelated to the diff:

   ```
   INTERNALERROR>   File ".../scripts/stripe_bootstrap.py", line 44, in <module
   INTERNALERROR>     sys.exit("The stripe SDK is required (pip install 'stripe>=11,<13')")
   INTERNALERROR> SystemExit: The stripe SDK is required (pip install 'stripe>=11,<13')
   5 warnings, 212 errors in 186.37s (0:03:06)
   ```

   With only `tests/test_stripe_bootstrap_products.py` ignored, collection then dies on a second pre-existing sparse-environment module (`scripts/check_validated_claims.py:643` raises `SystemExit(1)` without its allowlist data): `5 warnings, 218 errors in 201.58s (0:03:21)`. Neither `scripts/stripe_bootstrap.py` nor `scripts/check_validated_claims.py` is in the diff. No package installs are permitted in this lane, so the adapted run keeps the identical `-k` expression and scopes collection to the provably complete module union (all modules with `def test_*canada*` names, all `tests/*canada*.py`, `tests/test_board_shadow.py`; the residual class-name gap — `class *Canada*` intersected with board/shadow/ledger test names — is empty by `comm`):

   ```
   25 failed, 52 passed, 8 skipped, 1159 deselected in 13.96s
   ```

   All 25 failures are in `tests/test_stock_dashboard_first_frame.py` and share one cause (`--tb=line`, 25/25 identical):

   ```
   E   FileNotFoundError: [Errno 2] No such file or directory: '.../mockups/evidence/prophet-p0b-zero-fouc/inputs/canada-owner-fixture.json'
   ```

   the sparse-worktree omission of `mockups/` (the harness itself prints "Sparse worktree … mockups not checked out" on each). That module and `mockups/` are untouched by the diff; `tests/test_board_shadow.py`, `tests/test_canada_build.py`, `tests/test_canada_canonical_board.py` and every other canada board/shadow/ledger module in the union passed.

## NOTES (non-blocking)

- **N1** — see Surface 2: non-dict truthy `setups` now SKIPs instead of raising; non-dict Mapping with real buys would SKIP instead of proceeding. Both unreachable from the sole caller (`scripts/build_canada.py:1482`, `:1505`); strictly-safer direction.
- **N2** — the "track: 1" stub count instruments `track_ledger.from_board_ledger_grade`, while `track_ledger.atomic_write` is stubbed to an un-counted no-op (`tests/test_board_shadow.py:2215-2222`). Exactly-once for the file write itself rests on the straight-line `:797→:803` sequence (no branch between), not on a direct counter. Acceptable; noting for the record.
- The zero-buy log line at `:760-762` fires in place of the off-nightly log when `_ledger_advance_enabled()` is False and rows are empty (T5 covers the armed/False matrix; append is withheld either way).

## GAPS

- The exact-form command 2 could not complete in this environment (stripe SDK absent; claims allowlist data absent from the sparse checkout; installs forbidden). The adapted run preserves the exact `-k` selection over a grep-provably-complete module union; collection of unrelated non-canada modules was not exercised beyond the two quoted INTERNALERROR modules.
- `test_prophet_board_since.py` was not executed against a parent harness (logical byte-identity proof via `git diff --stat` used instead, as the packet's surface-4 standard allows).
- No live/nightly-path execution of `scripts/build_canada.py` itself (out of READ_ONLY scope); liveness evidence is the T1-T5 suite plus static call-site tracing.

## DEVIATIONS

- Command 2 adapted as described (two `--ignore`-form attempts quoted verbatim, then the module-union form); disclosed here rather than silently substituted.
- Parent-version test harness materialized under `/tmp/cazb_parent/` (outside the repo, never committed, removed from nothing — repo tree untouched), per the packet's blessed `git show` method.
- `MM_DATA_GUARD=off` used for the /tmp parent-harness runs only (non-git copy; guard inapplicable). All in-repo runs used default guard settings; `git status` clean except the report file.

## RETURN

```
STATUS: PASS_WITH_NOTES
RESULT:
  S1 zero-buy: PASS — append_board unreachable on empty rows (build_canada.py:759-764); track emit once (:797-803); write_shadow once (:816); health = SKIP row alone (:756)
  S2 non-empty: PASS — only the early return removed; health ternary and elif evaluate identically for truthy rows (:756, :759-763); NOTE N1 non-dict inputs (unreachable)
  S3 realism: PASS — parent: 4 failed / 65 passed with exact "write_shadow must run exactly once; got 0"; HEAD: 69 passed
  S4 prophet_board_since: PASS — 2 failures, both template-text asserts (tests/test_prophet_board_since.py:390, :628) on files byte-identical to parent; pre-existing
  S5 collision: PASS — diff touches exactly scripts/build_canada.py + tests/test_board_shadow.py; dashboard.html.j2 and sol/ absent
  S6 hygiene: PASS — no imports/secrets/network/deps added; tests pin site_dir to tmp_path; no data/ assumptions
EVIDENCE: /tmp/cazb_parent harness (git show parent build_canada.py; 18+/6- no-index check); pytest tails quoted above per command; git diff --stat a580ce7e780..HEAD (2 files, 204+/6-)
GAPS: exact-form command 2 blocked by env (stripe SDK, sparse allowlist) — adapted same -k over complete union; no live nightly-path run (READ_ONLY)
DEVIATIONS: command-2 adaptation disclosed; /tmp parent harness; MM_DATA_GUARD=off on /tmp harness only
```
