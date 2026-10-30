# Receipt-truth review — `validation_failed` split of the plan-not-built cohort

- Reviewer lane: `lane/pro-receipt-truth-review-20261021-r1` (read-only; this file is the only write)
- BASE under review: `7e0cf6c655632be9e75188db1982504450183a43` (= HEAD of this lane; the seat branch tip)
- Diff reviewed: `git diff e5dd30c6344e4b62a0beba054ac4da97e00bab36..HEAD`
- Date: 2026-10-21 (review run 2026-10-20/21 host clock)

## Verdict

**PASS_WITH_NOTES** — the change satisfies every numbered spec point; both notes are
host/environment observations, not defects in the reviewed bytes.

## Diff surface

```
 engine/prophet_bridge.py                  |  31 +++++++--
 scripts/build_prophet.py                  |   4 +-
 templates/_prophet_receipts.html.j2       |   1 +
 templates/_us_candidate_pool_rows.html.j2 |   1 +
 tests/test_prophet_whynot_receipts.py     | 109 +++++++++++++++++++++++++++++++
 5 files changed, 141 insertions(+), 5 deletions(-)
```

Exactly the five owned files. `.github/ci/legacy-jobs.yml` is untouched — permitted
("possibly one `run:` line") and unnecessary: the `prophet-anticipation-intake` job
already runs `python -m pytest tests/test_prophet_whynot_receipts.py -q`
(`.github/ci/legacy-jobs.yml:27114`). No stray file. Deletions are 5 prose lines
(4 comment/docstring lines in the engine, 1 comment line in `build_prophet.py`);
`git diff --numstat` confirms `109 0` for the test file — no test deleted.

## `REFUSAL_ORDER` as it reads at HEAD (engine/prophet_bridge.py:414-426)

```python
REFUSAL_ORDER = (
    "plan_not_built",   # cleared every gate; only the plan build itself failed
    "already_open",     # cleared every gate; the name already has a live plan
    "validation_failed",  # cleared every gate; origination later failed its own data check
    "not_ready",        # the patience statuses that are ALMOST admitted
    "ran_too_far",      # the anti-chase refusal — must outrank the band it co-occurs with
    "stood_down",       # an explicit avoid/exit/blocked stance
    "grade_low",        # the tier cascade graded it below the actionable set
    "conviction_low",   # the board's own `band == 'low'`
    "pointing_down",    # tone refused by ruling (§6.7 A1)
    "no_trigger",       # no entry signal on the row at all
    "unknown",          # fail-closed generic — an unmapped/renamed status word
)
```

Base (`e5dd30c`) read identically minus the `validation_failed` line — a pure
insertion between `already_open` and `not_ready`.

## Spec points

1. **PASS** — `engine/prophet_bridge.py:417` seats `"validation_failed"` immediately
   after `already_open` (line 416) and immediately before `not_ready` (line 418).
   Copy at lines 460-461 is byte-equal to the frozen strings in both languages
   (programmatic substring check against all three files: EN True / ZH True).
   `REFUSAL_NEAR` at line 483 is `frozenset({"plan_not_built", "already_open",
   "not_ready"})` — the new code is absent.
2. **PASS** — keyword-only parameter at `engine/prophet_bridge.py:1507-1508`
   (`*, validation_failures: Iterable[Mapping[str, Any]] | None = None`).
   `failed_tickers` is built at lines 1573-1578 as the strip+upper-cased ticker set.
   Precedence chain at lines 1591-1600 is exactly the spec's (a) `key in open_tickers`
   → `already_open`; (b) `originated is not None and key and key not in originated
   and key in failed_tickers` → `validation_failed`; (c) `originated is not None …
   key not in originated` → `plan_not_built`; (d) `else: continue`. Both (b) and (c)
   require `key not in originated`, so rows present in `originated` never receive
   either code. `None` leaves `failed_tickers` empty, branch (b) is unreachable, and
   output is unchanged — pinned by
   `test_absent_failure_record_leaves_the_prior_output_untouched`. The intake record
   producer at `engine/prophet_bridge.py:4376-4381` emits exactly
   `{"ticker", "id", "stage", "errors"}` and is stored into
   `intake_stats["validation_failures"]` at line 5032.
3. **PASS** — `scripts/build_site.py` is not in the diff. Its only call site
   (`scripts/build_site.py:4871`) passes `reconstructed_plans` and no
   `validation_failures`. The sole new-argument caller is
   `scripts/build_prophet.py:3157-3162`.
4. **PASS** — both templates gained exactly one map line each
   (`templates/_prophet_receipts.html.j2:51`, `templates/_us_candidate_pool_rows.html.j2:16`)
   carrying both language strings, byte-equal to the engine copy. `pvr_copy` mirrors
   `REFUSAL_COPY` exactly (pre-existing `test_template_copy_mirrors_the_engine_copy_exactly`,
   passing) and `_why` shared-key wording equality is pinned by the new
   `test_candidate_pool_copy_words_shared_codes_identically` (passing).
5. **PASS on this host where the environment allows** — all six spec'd cases exist
   and pass by name (verbose run quoted below). `tests/test_prophet_whynot_receipts.py`
   + `tests/test_prophet_plan_relation.py`: **158 passed, 2 skipped**.
   `tests/test_prophet_bridge.py -k 'refus or receipt or whynot'`: **7 passed, 113 deselected**.
   The combined required batch reports `22 failed, 256 passed, 7 skipped` — every one
   of the 22 is environmental on this host (Note N1), zero assertion failures.

## Test evidence

```
$ python3 -m pytest -q -p no:cacheprovider tests/test_prophet_whynot_receipts.py tests/test_prophet_plan_relation.py
158 passed, 2 skipped in 48.28s

$ python3 -m pytest -q -p no:cacheprovider tests/test_prophet_bridge.py -k 'refus or receipt or whynot'
7 passed, 113 deselected in 1.38s

$ python3 -m pytest -q -p no:cacheprovider tests/test_prophet_whynot_receipts.py tests/test_us_board_gate.py tests/test_prophet_card_shared.py tests/test_prophet_plan_relation.py
22 failed, 256 passed, 7 skipped in 96.86s   # all 22 environmental — see N1

$ python3 -m pytest -q -p no:cacheprovider tests/test_us_candidate_lanes.py -k "refusal_family or off_board_reasons_are_all_declared"
2 passed, 174 deselected

$ python3 -m pytest -q -p no:cacheprovider tests/test_prophet_journey_reconcile.py::test_declared_reason_vocabulary_superset_engine_runtime_union
1 passed
```

Six new cases, verbose names all PASSED:

```
tests/test_prophet_whynot_receipts.py::test_cleared_row_in_the_failure_record_headlines_validation_failed PASSED
tests/test_prophet_whynot_receipts.py::test_an_open_plan_outranks_the_failure_record PASSED
tests/test_prophet_whynot_receipts.py::test_an_originated_row_earns_no_receipt_even_if_the_record_names_it PASSED
tests/test_prophet_whynot_receipts.py::test_absent_failure_record_leaves_the_prior_output_untouched PASSED
tests/test_prophet_whynot_receipts.py::test_validation_failed_is_ordered_and_excluded_from_near PASSED
tests/test_prophet_whynot_receipts.py::test_candidate_pool_copy_words_shared_codes_identically PASSED
```

(Spec's "precedence a>b>c" is covered across `test_an_open_plan_outranks_the_failure_record`
(a over b) and the QUIET/plan_not_built contrast inside
`test_cleared_row_in_the_failure_record_headlines_validation_failed` (b over c);
a seventh regression test,
`test_cleared_row_absent_from_the_failure_record_keeps_plan_not_built`, also passes.)

## Attack surfaces

- **Ordering regressions in `REFUSAL_ORDER` consumers — dismissed.** In-engine, the
  only order-sensitive consumers are `_refusal_codes`' sort (lines 1368-1369), whose
  index map is rebuilt from the same tuple each call (relative order of existing codes
  preserved by pure insertion), and the group loop (line 1610). External consumers are
  dynamic: `engine/us_candidate_lanes.py:240` splats `*REFUSAL_ORDER` into
  `declared_reasons()`, and `scripts/prophet_journey_reconcile.py:173` imports the
  tuple from the engine (ImportError fallback `()` at 177) — no second copy exists.
  Both pinning tests pass on this host (see evidence).
- **Leak into near-miss/`REFUSAL_NEAR` rendering — dismissed.** Line 483 excludes the
  code; the group's `"near"` flag (line 1622) is therefore False; the shelf template
  applies the WAIT rail only via `g.near`
  (`templates/_prophet_receipts.html.j2:145`, `is-near` class). The new test also
  asserts `group["near"] is False`.
- **Failed-then-originated under a different id — dismissed.** Matching is by ticker;
  `originated` membership exempts a row from both codes (lines 1594, 1597), regardless
  of id. `test_an_originated_row_earns_no_receipt_even_if_the_record_names_it` pins it.
- **Case/whitespace normalization mismatch — dismissed.** Row side:
  `str(row.get("ticker") or "").strip()` then `.upper()` (lines 1584, 1591). Record
  side: `str(failure.get("ticker") or "").strip().upper()` (line 1576). Identical
  normalization; empty tickers are dropped from the set (lines 1577-1578).
- **Template key drift (EN present, ZH missing) — dismissed.** Byte-level substring
  check of the frozen EN and ZH strings returned True for both templates and the
  engine; `pvr_copy` ↔ `REFUSAL_COPY` byte-equality and `_why` shared-key wording are
  both test-pinned.
- **Widened admission / lowered threshold / renamed refusal / deleted test —
  dismissed.** The diff inserts one elif into the cleared-row chain of a display-tier
  function and passes one kwarg through; `_refusal_codes`, every gate, and every
  threshold are untouched. No existing refusal key was renamed (all base keys still
  present in `REFUSAL_COPY`). Test file numstat `109 0` — additions only.
- **Colored left-edge accent in templates — dismissed.** Each template diff is one
  map-entry line; grep for `border|::before|background|left|stripe|edge` over the
  template diffs returns nothing.
- **The word "verified" introduced anywhere — dismissed.** `git diff
  e5dd30c..HEAD | grep -n "verified"` returns no match; the new copy reads
  "didn't verify", not the forbidden word.

## Findings

- **N1 (NOTE, environmental — not a defect in the reviewed bytes).** 22 failures in
  the required combined batch on this host: 20 ×
  `bs4.exceptions.FeatureNotFound: Couldn't find a tree builder with the features you
  requested: html5lib` (missing venv parser), 1 × `ModuleNotFoundError: No module named
  'rjsmin'`, 1 × `FileNotFoundError: .../site/tier_preview.js` (sparse worktree excludes
  `site/`). Zero assertion failures; none exercise the changed code paths. The packet
  forbids `pip install`, so the two suites could not be made green here. CI runs the
  receipts suite at `.github/ci/legacy-jobs.yml:27114`.
- **N2 (NOTE).** `engine/prophet_bridge.py:1575` — a non-Mapping entry in
  `validation_failures` is silently skipped, degrading that ticker's wording to
  `plan_not_built`. Nothing drops out of disclosure (the row still gets a receipt) and
  the producer (lines 4376-4381) only ever emits dicts, so this is defensive
  degradation consistent with the module's doctrine, not a live path. Recorded for
  completeness only; no repair requested.

## Gaps

- `tests/test_us_board_gate.py` and `tests/test_prophet_card_shared.py` could not be
  run to green on this host (N1: missing `html5lib`/`rjsmin`, `site/` excluded by the
  sparse profile). Their 22 failures were classified root-cause-by-root-cause instead;
  no assertion failure exists among them.
- No rendered-site visual proof (no build was run; render path is out of scope for a
  read-only lane). Template correctness is covered by the byte-equality and
  shared-key tests quoted above.

## Deviations

- In addition to the packet's five suites, two external `REFUSAL_ORDER`-consumer
  suites (`test_us_candidate_lanes.py` vocabulary pins,
  `test_prophet_journey_reconcile.py` vocabulary union) were run read-only to close
  the ordering-regression attack surface empirically. No other departure.
