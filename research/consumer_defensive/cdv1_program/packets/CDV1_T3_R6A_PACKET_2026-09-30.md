# CDV-1 T3 R6a — one bounded follow-up to merged Task 3 (new branch `claude/cdv1-t3-r6a-followup`)

LANE `cdv1_t3_r6a_followup` — BUILD the Task 3 follow-up R6a. Task 3 merged as PR #8232 (`ddf03116`). This lane changes one module and its suite, opens ONE DRAFT PR, and stops. The seat owns readiness, labels, review and merge.

This packet is complete on its own. Each rule below is a seat ruling. The source is the seat's record of the fourth independent review of PR #8232, notes 1–4 and 6–8, plus the platform gap that review listed. Nothing here reopens Task 3's accepted rulings R6.1–R6.10.

## C0 GATE (first actions; quote the outputs under EVIDENCE)
1. Run `git fetch origin main` and `git rev-parse HEAD origin/main`. HEAD must equal `origin/main` (a detached HEAD). If not, STOP with STATUS BLOCKED.
2. `git ls-remote origin refs/heads/claude/cdv1-t3-r6a-followup` must print nothing. If the branch exists, STOP with STATUS BLOCKED.
3. `git grep -n "strftime\|def compare_eps\|def owner_lookup\|def _unavailable" -- engine/earnings_narrative/economic_interpretation.py` must show all four names.
4. `git grep -n "assert len(calls) >= " -- tests/test_earnings_economic_interpretation.py` must print the floors (50 and 35 on the seat's read).

## MISSION
Close seven gaps the fourth review of Task 3 found, none of which produces a wrong payload today:
- five test pins the suite should have;
- EPS growth that depends on the caller's decimal context and can be rounded twice;
- clock text that depends on the C library's `strftime`.

The module change moves `CODE_REVISION`, which is the sha256 of the module's own bytes. That is expected: no payload is stored in production before Task 5.

## HARD LAWS (violations are seat-reportable)
- Never `git add -A`; add named files only. Never force-push, rebase, amend, or use bare `git stash`/`pop`.
- The only `gh` acts permitted are `gh pr list --head claude/cdv1-t3-r6a-followup` and ONE `gh pr create --draft` (DELIVERY). Never `gh pr ready|merge|edit|review|comment`, never add labels, and do not poll CI.
- Never print, copy or open credentials (`~/.glm`, `~/.minimax`, `~/.codex/auth*`, `ext/glm_shim/.token`, any `.env`).
- Never write outside OWNED FILES. Never write under `data/` or `site/`: this is a SPARSE tree, and a write there truncates committed artifacts. Never run `python3 scripts/worktree_sparse.py full`.
- Do not stop to ask questions and never end on a status note. Record blocks under GAPS and finish the packet.
- No test uses the network. Every number is a synthetic test value.
- Trailer on EVERY commit: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Push with `git push origin HEAD:refs/heads/claude/cdv1-t3-r6a-followup` (no force). Treat "Everything up-to-date" as FAILURE when a commit was expected.

## FILES
OWNED (the only files you may change):
- `engine/earnings_narrative/economic_interpretation.py`
- `tests/test_earnings_economic_interpretation.py`

FROZEN: every other file, including `tests/earnings_economic_interpretation_fixtures.py`, `tests/earnings_economic_fixtures.py`, Tasks 1 and 2, `.github/ci/**` and `research/**`. No CI change is needed, because the `earnings-economic-dossier` job already runs this suite. Existing tests may be extended. Never delete or weaken an existing test: if one contradicts a ruling below, report it under GAPS.

## MEASURED INTERFACES (seat reads of `origin/main`)
- `CODE_REVISION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()` (line 147).
- `_compare_eps(current, prior, *, precision, uncertainty)` (line 410) computes `rate = (current_value / prior_value - Decimal("1")) * Decimal("100")`. It then applies `rate.quantize(Decimal(1).scaleb(-precision_value))` under the AMBIENT decimal context and wraps `ArithmeticError` as `EconomicInterpretationError("EPS growth arithmetic is not defined")`. The payload path `_comparison` calls it with `precision=2`. The public `compare_eps` wraps it.
- Measured failure: under a caller's `decimal.localcontext(decimal.Context(prec=5, rounding=decimal.ROUND_DOWN))`, `compare_eps('3.07', '2.93', precision=2)` returns `'4.77'` and still reports `ROUND_HALF_EVEN`. Exact half-even rounding is `'4.78'`. Separately, under the default context, 3 of about 6,500 fuzzed comparable results with 28–30-digit operands differ from exact half-even rounding (double rounding at 28 digits).
- `_parse_instant` / `_parse_date` (lines 210–232): a regex form check, then `strptime` / `date.fromisoformat`, then a `strftime` round trip. The round trip, and the output formatting at every other `strftime` call (lines 702, 755, 768, 783, 786 and 885), depend on the platform's C library: glibc does not zero-pad `%Y` below year 1000.
- `owner_lookup(group, metric=None)` (line 526) returns `"reconciliation"` when `type(metric) is str and metric == "pg_core_reconciliation_context"`. `test_each_lookup_tests_the_type_before_it_reads_the_value` (line 377) varies only the first argument of each lookup.
- `format_value_and_unit(value, unit)` reads `value` through `_parse_decimal`, which admits exactly `str`, `int`, `float` and `Decimal` by identity.
- `test_unavailable_payload_echoes_only_an_exact_string_revision` (line 1799) makes one revision bad at a time.
- `test_every_other_argument_is_refused_when_it_is_not_exact` (line 1325) ends `assert len(calls) >= 50`. The fourth review counted 55 calls present.
- The suite already has the helpers `_Raiser`, `_Liar`, `_Str`, `_opaque`, `_baseline`, `_build_with`, `_is_exact_json` and imports `Fraction`.

## SEAT RULINGS R6a.1–R6a.7 (binding)

**R6a.1 — pin every lookup parameter (note 1).** Add tests that vary the parameters the existing test does not reach, with the suite's four hostile kinds (`list`, `raiser`, `liar`, `str_subclass`).
- For `owner_lookup`, vary `metric` with `group="demand"`. The liar and the `str` subclass carry `"pg_core_reconciliation_context"`. Each result equals `owner_lookup("demand")` and is never `"reconciliation"`. Positive control: `owner_lookup("demand", "pg_core_reconciliation_context") == "reconciliation"`.
- For `format_value_and_unit`, vary `value` with `unit="percent"`. Each raises `EconomicInterpretationError`. Positive control: `format_value_and_unit(Decimal("1"), "percent")` is not `None`.

**R6a.2 — both revisions bad (note 2).** For each of the eight kinds the existing test uses, make BOTH `semantic_revision` and `code_revision` bad at once. The payload is `unavailable` with `quality.reason == "unsupported interpretation version"`, and both `build` fields are `None`.

**R6a.3 — nested key order is not compared (note 3; R6.4).** Build a supported payload. Reverse the key order of one nested mapping (for example `quality`, or the first observation) and validate it: accepted. Reverse the TOP-level key order of the same payload: refused with `EconomicInterpretationError`.

**R6a.4 — the empty-dict message (note 4; R6.6).** `validate_economic_interpretation(<a valid payload>, workspaces={}, source_texts=…, fiscal_scope=…)` raises `EconomicInterpretationError` whose message is exactly `workspaces must map generation ids to workspaces`. Pin it with `match=r"^workspaces must map generation ids to workspaces$"`.

**R6a.5 — floors at the count present (note 8).** Raise every `assert len(calls) >= N` in the suite to the number of calls actually present. Quote each before and after count; the counts come from running the test with a temporary print, never from reading the code. Do not change which calls are made.

**R6a.6 — EPS growth under an explicit local context (notes 6 and 7).**
- Inside `_compare_eps`, do all arithmetic under `decimal.localcontext(_EPS_WORK_CONTEXT)`, where `_EPS_WORK_CONTEXT = decimal.Context(prec=100, rounding=decimal.ROUND_HALF_EVEN, Emax=999999, Emin=-999999, traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow])`.
- Round the result once, under `_EPS_RESULT_CONTEXT`: the same context but with `prec=28`.
  - With a precision: `rate.quantize(Decimal(1).scaleb(-precision_value, context=_EPS_RESULT_CONTEXT), context=_EPS_RESULT_CONTEXT)`.
  - With `precision=None`: `_EPS_RESULT_CONTEXT.plus(rate)`.
- The formula, the returned keys, every refusal and every message stay as they are. A result with more than 28 digits is still refused, as today's default context refuses it.
- No ambient context value can reach the result: not its precision, its rounding, its traps or its exponent limits.
- A 100-digit working precision leaves at least 70 guard digits below any 28-digit result, so no false tie can arise from operands of up to 70 significant digits. State that bound as a known limit in the PR body. Do not use `fractions.Fraction` in the module: exact rationals of operands with extreme exponents are unbounded in cost.

**R6a.7 — clock text without the C library (the platform gap).**
- Add `_format_instant(value: datetime) -> str`, returning `f"{value.year:04d}-{value.month:02d}-{value.day:02d}T{value.hour:02d}:{value.minute:02d}:{value.second:02d}Z"`.
- Add `_format_date(value: date) -> str`, returning `f"{value.year:04d}-{value.month:02d}-{value.day:02d}"`.
- `_parse_instant` and `_parse_date` compare the value against these helpers instead of `strftime`.
- Every other formatting call uses them too. After the change, `git grep -n strftime -- engine/earnings_narrative/economic_interpretation.py` prints nothing.
- `strptime` and `date.fromisoformat` stay; both are implemented in Python. Accepted and refused strings stay the same on macOS. On Linux, years 0001–0999 are now accepted as they already are on macOS.

## TESTS (add to `tests/test_earnings_economic_interpretation.py`; each asserts a class and a message or a value)
1. R6a.1: the two lookup pins and their positive controls.
2. R6a.2: both revisions bad, for the eight kinds.
3. R6a.3: nested order accepted, top-level order refused.
4. R6a.4: the exact empty-dict message.
5. R6a.5: the raised floors.
6. R6a.6, in several parts:
   - Each case below returns identical results under the default context, under `Context(prec=5, rounding=ROUND_DOWN)`, under `Context(prec=50, rounding=ROUND_CEILING)`, and under a context with every trap cleared:
     - `compare_eps("3.07", "2.93", precision=2)["value"] == "4.78"`;
     - `compare_eps("1.64", "1.50", precision=2)["value"] == "9.33"`;
     - the `nonpositive_prior` case and one overflow refusal (`"1E+999999"` over `"1E-999999"`), which still raises `EconomicInterpretationError`.
   - A fixed-seed fuzz of at least 2,000 pairs, run under the default context. Operands have 1–30 significant digits and exponents −10 to 10, precisions are 0–6, and every prior is positive. Each comparable value must equal an exact oracle: `Fraction` arithmetic in the test, rounded half-even with Python's `round()` of a `Fraction`, and printed with exactly `precision` decimals. Keep a negative rate that rounds to zero as `-0.00`, as `Decimal.quantize` does. Quote the pair count and the number of cases where the old implementation differed.
   - At least one literal pinned case where today's implementation, under the default context, differs from the oracle. The seat's probe found one: `current="86599450252.21717677831864229"`, `prior="7.86759076908354901062539863897E-8"`, `precision=6`. Today's code gives `"110071116805563916092.505878"`; the exact half-even value is `"110071116805563916092.505877"`. Verify it with a throwaway probe outside the repository (a copy of today's `_compare_eps` beside the oracle), then write it into the test with a one-line comment. (The seat's fuzz of 39,995 comparable pairs found 2 such cases for today's code and 0 for the R6a.6 design.)
   - A result with more than 28 digits (for example `"1E+40"` over `"1"` at precision 2) is still refused with the same message.
7. R6a.7:
   - `_format_instant(datetime(999, 1, 2, 3, 4, 5)) == "0999-01-02T03:04:05Z"` and `_format_date(date(999, 1, 2)) == "0999-01-02"`.
   - `_parse_instant("0999-01-02T03:04:05Z", "x")` returns that instant, and `_parse_date("0999-01-02", "x")` that date.
   - Today's refused forms are still refused. Include `"2026-9-30T00:00:00Z"`, `"2026-09-30T00:00:00+00:00"`, `"2026-02-30T00:00:00Z"` and `"0000-01-01T00:00:00Z"`.

## MUTANTS (each: edit, run the suite, quote the failing test NAME, `git checkout -- <file>`, prove `git diff --quiet`)
- (m1) Delete `type(metric) is str and` in `owner_lookup`.
- (m2) In `_unavailable`, echo `code_revision` unchanged when `semantic_revision` is also not an exact `str`.
- (m3) Compare nested key order in replay.
- (m4) Remove the empty-dict refusal from the workspaces reader.
- (m5) Drop the local context, so the ambient context is used.
- (m6) Set the work context's precision to 28.
- (m7) Quantize under the work context instead of the result context.
- (m8) Drop the `:04d` from `_format_instant`'s year.
- (m9) Restore the `strftime` round trip in `_parse_date`. This mutant can only fail on Linux. If it survives on this host, say so and do not count it.

## WORK ORDER (short steps; commit and push after each)
1. The tests for R6a.1–R6a.5, then commit `test(earnings): pin five Task 3 rules the suite left open`.
2. R6a.6 and its tests, quoted failing first against today's module (RED), then commit `fix(earnings): compute EPS growth under an explicit decimal context`.
3. R6a.7 and its tests, then commit `fix(earnings): format interpretation clocks without strftime`.
4. The mutants and the runs below.

## RUNS (quote each rc line under EVIDENCE)
- A clean venv outside the repository tree, on CPython 3.12 like CI:
  - `uv venv --python 3.12 <dir>` (uv is `/opt/homebrew/bin/uv`; the host's `python3` is 3.14 and must not be used);
  - `uv pip install --python <dir>/bin/python pytest pyyaml`, exactly the `earnings-economic-dossier` job's packages;
  - quote `<dir>/bin/python --version`.
- The suite: `bash -c 'ulimit -s hard; <dir>/bin/python -m pytest tests/test_earnings_economic_interpretation.py -q -p no:cacheprovider'`.
- The whole job line: run exactly the `run:` command of the `earnings-economic-dossier` job in `.github/ci/legacy-jobs.yml`, under `bash -c 'ulimit -s hard; …'`, with `-p no:cacheprovider` added. Quote its summary line and its wall time; the job's limit is 20 minutes.
- `python -m pyflakes` on the two owned files (pyflakes in a second venv).
- `python scripts/check_contract_delta.py --base origin/main` (quote the summary).
- `git diff --name-only origin/main...HEAD`, which lists only the two owned files.
- `git grep -n strftime -- engine/earnings_narrative/economic_interpretation.py`, which prints nothing.

## DELIVERY
After the final push, run `gh pr list --head claude/cdv1-t3-r6a-followup`. If it lists no PR, open exactly ONE with `gh pr create --draft --base main --head claude/cdv1-t3-r6a-followup --title 'fix(earnings): exact EPS growth rounding, runtime-independent clock text and five pins (CDV-1 Task 3 R6a)' --body-file <file>`.

The body has these sections:
- what changed, per R6a item;
- the RED and GREEN receipts;
- the mutants;
- the known limit of R6a.6;
- the change of `CODE_REVISION`;
- GAPS.

The body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## COMMON RULING (binding)
- **Short steps, pushed as they land.** Push an unfinished step as `wip(...)` rather than holding it.
- **Real probes.** A test must be able to fail against a plausible wrong implementation. Never restate the code in a test, and never assert on source text.
- **One rule, one place.** If a rule seems to need a special case, report it under GAPS instead.

Before the final push: `git fetch origin main`. If `origin/main` moved, `git merge --no-ff origin/main` (never rebase). On a conflict keep both sides and never discard main's side. A conflict outside OWNED FILES means STOP with STATUS BLOCKED, naming the conflict. After any merge, re-run the RUNS.

## GAPS RULE
If an R6a item contradicts Task 3's accepted rulings, the measured behavior above, or another R6a item, or cannot be met, implement everything else and report that item under GAPS with its reason. The seat rules on it. Never silently drop or reinterpret an item.

## NOT DONE UNLESS
- Every RUNS line is quoted with its rc, and both the suite and the whole job line pass in the clean 3.12 venv.
- The seven test groups exist, and R6a.6's RED is quoted against today's module.
- Mutants m1–m8 each fail a named test and are restored.
- `strftime` is gone from the module, and only the two owned files differ from `origin/main`.
- Every commit carries the trailer and is pushed, with no force and no amend, and ONE DRAFT PR exists.

## RETURN (final message, exactly these sections)
- **STATUS:** COMPLETE | PARTIAL | BLOCKED.
- **RESULT:** the PR number; the head sha; each R6a item with its line refs; the old and new floor counts; the fuzz pair count and the number of old-versus-oracle differences.
- **EVIDENCE:**
  - the C0 outputs;
  - the quoted rc lines for RED, GREEN, the whole job line (with wall time), pyflakes and contract-delta;
  - each mutant with its failing test name;
  - the `strftime` grep.
- **GAPS.**
- **DEVIATIONS:** each with its R6a id, or "none".

Then EXACTLY ONE final stdout sentinel line `<LABEL>: <STATUS> <sha>`.
