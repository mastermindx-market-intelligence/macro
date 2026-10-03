# Audit — mastermindx-market-intelligence/macro PR #7472

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7472](https://github.com/mastermindx-market-intelligence/macro/pull/7472) |
| title | `[MO-B F09 W8-1 follow-on] Direct unit tests for _resolve_cash_runway (7 tests; Grok h_7451_rv1 minor 1)` |
| merged | 2026-09-20T03:49:19Z (24-h window: 2026-09-19 03:49 UTC → now) |
| head | code head `2a8e783e3e1923b131f6629fff9f3b35fe465e07`; merge head `51dcfdefc1` on `origin/main`. Three commits: `2b3cea5e` (MiniMax build, 7 tests, +165), `f6698fe0` (seat tightening after Grok `h_w8t_rv1`, +20), `2a8e783e` (import-failure test pins None for every value key after Grok `h_w8t_rv2b`, +3). Base main ⊇ `e338508d` (#7451). |
| files | 1 changed (+188 / −0): `tests/test_cash_runway.py` (one file, one new class appended after the last existing test). No engine / script / template / fixture / CSS / CI-manifest change. |
| half-B label | **half-B (MO-B F09 W8-1 follow-on).** Tag `[MO-B F09 W8-1 follow-on]` carries the canonical Meta-CEO B tranche marker; this child is the third commit on packet **B-F09-3** (MO-PAID-059 / MO-DELTA-018), raised by Grok `h_7451_rv1` minor 1 — no direct test for `scripts.build_stock_library._resolve_cash_runway`. Test-only child: nothing in the engine, producer, template, or CSS surface moves. |
| owner | Meta-CEO B seat (m_w8_1_test contract; executor = MiniMax lane `m_w8_1_test` on m1; seat gate = 026851bd at 2026-09-20T02:40Z). |
| base | `origin/main` at `e338508d` (verified merge-base via `git merge-base origin/main HEAD`; post-#7451 merge of #7451 itself). |
| live proof | GREEN `python3 -m pytest -q tests/test_cash_runway.py tests/test_debt_maturity.py` → **107 passed, 1 skipped** (was 100 + 1 at #7451 → +7). `python3 scripts/check_contract_delta.py --base origin/main` → **0 introduced, 0 inherited**. RED proof at 2a8e783e in seat-run: (A) throwaway edit of the resolver's fault branch (`"status": "not_loaded"` → `"not_applicable"` at `scripts/build_stock_library.py:159`), `pytest -k resolve_cash_runway` → 2 failed / 5 passed (loader-fault and import-failure tests); (B) extra key injected into the not_loaded dict → not_loaded test fails (1 failed); (C) non-None `cash_usd` on the shared fault return fails the import-failure test; all reverted, `git status --porcelain` clean. |

The PR is a follow-on test-only child of #7451. It widens the test surface from "engine entry-point" (TestExtractCashRunway, 16+ tests) to "resolver entry-point" (TestResolveCashRunway, 7 tests) without rewriting r1, without force-pushing, without merging `origin/main` mid-flight. The disciplined follow-on shape.

## Diff content (exact)

**Tests (1 MODIFIED file, +188)**

`tests/test_cash_runway.py` — one new class `TestResolveCashRunway` appended after the last existing test, plus one module-level constant `_RESOLVER_KEYS` (the closed 14-key shape of every `_resolve_cash_runway` return dict). Seven test methods, each named in the order Grok's review cited:

1. `test_resolve_cash_runway_not_applicable_for_crypto_and_etf` — crypto ticker (`BTC-USD`) and ETF sector (`ETF / macro`) short-circuit to `{"schema": "cash_runway.v1", "status": "not_applicable"}` without calling the loader (a `fake_loader` raises `AssertionError` if invoked). Verifies the structural-non-filer branch never reads disk.
2. `test_resolve_cash_runway_unresolved_shape` — loader returns `(None, None, "unresolved")`; asserts the dict has exactly the 14-key `_RESOLVER_KEYS` shape and that every value key (other than `schema` / `status` / `as_of`) is `None`.
3. `test_resolve_cash_runway_not_loaded_keeps_cik` — loader returns `("0000320193", None, "not_loaded")`; asserts `cik == "0000320193"` is preserved (the resolver does NOT drop the CIK on the cache-miss path).
4. `test_resolve_cash_runway_confirmed_no_filings_calls_extract_with_none` — patches `engine.cash_runway.extract_cash_runway` directly on the module so the resolver's local `from engine.cash_runway import extract_cash_runway as _cr_extract` resolves to the fake (recorded_args captures `facts`, `cik`, `as_of`, `ladder`); asserts `facts is None`, `cik == "0000320193"`, `as_of == cr_asof`, `ladder is None`. Uses a try/finally restore rather than `monkeypatch.setattr` per the executor's stated deviation.
5. `test_resolve_cash_runway_loaded_passes_facts_and_ladder` — same shape as #4 but with a non-None `facts_marker` and a `ladder_sentinel`; asserts both are passed through, plus the returned dict's `status` equals the sentinel's `status` field.
6. `test_resolve_cash_runway_loader_fault_degrades_to_not_loaded_with_warning` — loader raises `RuntimeError("boom")`; asserts the dict degrades to `not_loaded` (NEVER `not_applicable`), CIK is `None`, every other value key is `None`; asserts via `capsys.readouterr().out` that the captured stdout contains the exact GitHub-annotation prefix `::warning title=stock-library cash-runway producer fault::` AND the ticker `AAPL`. This pins the standing GH-annotation line-start rule (`scripts/check_gh_annotation_line_start.py` doctrine; `capsys` + `line.startswith("::")` shape).
7. `test_resolve_cash_runway_import_failure_degrades_to_not_loaded` — `monkeypatch.setattr(bsl, "_dm_load", None)` simulates the loader-import-failed module-level state; asserts `status == "not_loaded"` AND `status != "not_applicable"`, CIK is `None`, AND (per the r2 Grok `h_w8t_rv2b` MAJOR fix) every value key in the dict is `None`. This is the r2-only test that protects against the silent-degrade-to-not-applicable defect (a candidate SEC filer must NEVER be classified as a structural non-filer; `not_applicable` is reserved for crypto `-USD` suffix and `ETF / macro` sector).

No imports of new modules. The test file already imported `scripts.build_stock_library` transitively (via the r1 fixtures); each test imports it inside the test body so `monkeypatch.setattr(bsl, "_dm_load", …)` resolves to the right module object. The precedent for the import-failure test shape (`tests/test_debt_maturity.py::test_debt_maturity_import_failure_never_kills_the_stockdata_build`) is named in the PR body.

No fixture, engine, script, template, CSS, or CI-manifest change. The test additions run with the existing test runner; no new pytest fixtures, no new conftest additions, no new markers.

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-side only). Plain-language discipline here is read directly against the standing design-doctrine rules (glance-tier = state + plain-word stance under hard word budgets; no internal-state names; no raw slugs; per-signal "so what do I do"; honest-null grammar). Test files are not user-facing, so the doctrine is moot — but the test names ARE a downstream-coupling surface (a future maintainer grepping `_resolve_cash_runway` reads them), and the file contains string literals inside assertions that the doctrine touches.

**Verdict: PASS (and N/A on user-facing copy).**

1. **No user-facing surface.** The diff touches `tests/test_cash_runway.py` only. No template bytes change; no `_debt_maturity.html.j2`, `theme.css`, or Jinja change. The glance-tier / word-budget / ZH-parity / honest-null grammar rules do not apply.
2. **Test names are plain-language compliant.** All seven method names follow `<unit>_<scenario>_<expected>`: not_applicable_for_crypto_and_etf, unresolved_shape, not_loaded_keeps_cik, confirmed_no_filings_calls_extract_with_none, loaded_passes_facts_and_ladder, loader_fault_degrades_to_not_loaded_with_warning, import_failure_degrades_to_not_loaded. Grep across the diff for snake_case English sentence fragments: zero ambiguous / jargon-laden names. The closest to jargon is `extract_with_none` (the "with_none" suffix is the convention for "passing None as the first argument" — a standard pytest idiom; not a leaked engine identifier).
3. **No internal-state / study / rank names leaked into assertions or docstrings.** Grep across the new 188 lines for `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | validated | 已验证 | 经验证 | 经过验证 | thesis | refut | invalid`: **zero matches.** The test docstrings describe the contract under test in one line ("When the loader finds no CIK the status is unresolved with a 14-key shape." / "A loader RuntimeError degrades to not_loaded with a warning and no CIK." / "A None loader (import failure) degrades to not_loaded, never not_applicable.") — they name the resolver and its return-status taxonomy, which are the resolver's contract surface, not internal study names.
4. **Assertion strings are closed-schema identifiers, not raw slugs.** The only string literals in the new lines are:
   - `::warning title=stock-library cash-runway producer fault::` — the CI GitHub-annotation prefix the resolver's `except` arm must emit (CI-guarded; the test asserts `line.startswith("::")`).
   - `"AAPL"`, `"BTC-USD"`, `"SPY"`, `"Technology"`, `"ETF / macro"` — tickers and sectors, the canonical short forms the resolver routes on.
   - `"0000320193"` — the test's chosen canonical CIK (AAPL's actual SEC CIK, publicly known).
   - `"schema"`, `"status"`, `"cik"`, `"cash_usd"`, `"cash_display"`, `"ocf_usd"`, `"capex_usd"`, `"free_cash_flow_usd"`, `"monthly_burn_usd"`, `"runway_months"`, `"runway_display"`, `"near_term_cover_pct"`, `"period"`, `"as_of"` — the 14 closed-schema keys, the same names the engine emits and the template reads (already audited in the #7451 macro_PR-7451.mm.md report).
   - `"cash_runway.v1"`, `"not_applicable"`, `"not_loaded"`, `"unresolved"`, `"confirmed_no_filings"`, `"loaded"`, `"loaded_sentinel"`, `"sentinel_no_filings"` — closed-enum return statuses. `loaded_sentinel` / `sentinel_no_filings` are test-local sentinels (returned by `fake_extract`); they never appear in user copy or engine output.
   No raw slugs, no user-visible jargon, no leaked acronyms.
5. **No ZH parity required.** Tests do not run under the bilingual renderer (they are pure-Python pytest cases against the resolver; no Jinja, no `t('…', '…')` blocks). The doctrine's EN/ZH rule does not apply.
7. **No promoted-verb framing in docstrings.** Grep across the new 188 lines for `validated | 已验证 | 经验证 | 经过验证 | proven | certified | approved | gauntleted | promoted`: **zero matches.** The docstrings describe the contract ("When the loader finds no CIK the status is unresolved with a 14-key shape."); they do not claim the resolver is validated or proven.
8. **Honest-null grammar in the import-failure docstring.** Test 7's docstring explicitly carries the honest-null disclosure of why `not_applicable` is forbidden here: *"A candidate SEC filer must never silently degrade to not_applicable, which is reserved for structural non-filers (crypto tickers, ETF/macro sectors). When the loader itself is None the module-level import failed; the ticker is still a real filer identity, so the degraded state must be not_loaded."* This is the doctrine-correct form: name the structural-non-filer scope, name what "None loader" means, name why the degraded state must be `not_loaded`. The same discipline Test 6 enforces on the producer-fault path (degrade to `not_loaded`, emit a CI annotation naming the ticker, never silently classify as `not_applicable`).

The PR is plain-language compliant across all 188 new lines. No debt introduced.

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27): dark and light are TWO art directions, not one skin; 8-cell evidence matrix (dark × light × EN × ZH × desktop 1440 × mobile 390) required for any user-facing material change; "the same CSS still renders once the tokens swap" is precisely the failure this law exists to stop.

**Verdict: N/A (no user-facing surface in this PR).**

### CSS discipline — N/A

`tests/test_cash_runway.py` adds 188 lines of pure-Python test code. No `templates/` change, no `theme.css` change, no `style.textContent` runtime injection. The `scripts/check_design_system.py --mode enforce-added --diff-file <(git diff origin/main...HEAD)` run returns **0 blocking finding(s)** (estate-wide pre-existing non-blocking census is 18,972, unchanged by this PR). The diff introduces zero CSS bytes; zero token additions; zero breakpoint literals; zero color literals; zero shadow literals.

### 8-cell evidence matrix — N/A

The 8-cell evidence matrix is required for any **user-facing material change**. A test-only follow-on that adds 188 lines of pytest cases against an already-merged resolver (`_resolve_cash_runway`) is not a user-facing material change: it does not introduce new copy, new numbers, new null states, new light/dark overrides, or new template selectors. The matrix required for the new `.dmw-runway` block in #7451 still stands (already flagged `MISSING` in the macro_PR-7451.mm.md report); this PR neither closes nor widens that gate — it is orthogonal. The parent section (`<section id="debt-maturity">`) carries the matrix from the ladder's earlier recapture waves (the ladder panel's captures pre-date this PR); the new `.dmw-runway` block specifically remains un-captured, but that capture obligation is the parent PR's, not this follow-on's.

### Runtime style injection — N/A

`scripts/check_runtime_style_injection.py` does not apply: the diff contains no `style=` setStyle, no inline `style.textContent`, no JS-mounted DOM, no parallel token family. Test additions do not touch the rendered surface; they only exercise the Python resolver.

## Validated-claims findings

The standing macro law: the word "validated" and friends (`verified`, `proofed`, `certified`, etc.) are CI-enforced via `scripts/check_validated_claims.py`; context/data/detection/tagging artifacts stay display-tier until they clear the gauntlet.

**Verdict: PASS.**

1. **No artifact promotion occurred.** The diff is test-only. The engine module (`engine/cash_runway.py`) was already audited in #7451 as display-tier; this PR does not modify it. The producer module (`scripts/build_stock_library.py` `_resolve_cash_runway`) was also already audited in #7451; this PR does not modify it. The 7 new tests exercise existing contract behaviour; they do not promote any tier, rank, gate, or score. The closed 14-key resolver return shape (`_RESOLVER_KEYS`) is itself a `display-tier` shape — every key is either a USD number, a USD-formatted string, a closed-enum status, or a derived ratio — so testing the shape does not advance the gauntlet.
2. **No `validated` / `已验证` / `经验证` / `经过验证` framing in test docstrings or assertions.** Grep across the new 188 lines for `validated | 已验证 | 经验证 | 经过验证`: **zero matches.** The test names and docstrings describe the contract under test ("A loader RuntimeError degrades to not_loaded with a warning and no CIK.") — they do not claim the underlying resolver, the engine, or the test itself is validated.
3. **`scripts/check_validated_claims.py --list` returns no new MISS for the diff.** Re-running the checker on the touched file surface (only `tests/test_cash_runway.py`; the script scans `templates/` not `tests/`) confirms the estate's MISS list is unchanged by this PR. The pre-existing `MISS templates/_macro_suite_shell.html.j2:17` and other surfaces are untouched by this PR; no new MISS appears anywhere.
4. **No new doctype:validation hints, no `data-validated` attributes, no A7 claim.** The diff adds zero HTML bytes; it adds zero JSON bytes; it adds zero data attributes. The 14-key resolver shape is exercised via Python dict-equality and per-key `is None` assertions — these are structural / value tests, not authority claims.
5. **The CI-annotation assertion pins the doctrine-correct receipt, not a validation claim.** Test 6 asserts that the resolver's `except` arm emits the exact GitHub-annotation prefix `::warning title=stock-library cash-runway producer fault::` to stdout. The annotation is a **producer-fault receipt** ("the resolver degraded to not_loaded rather than fabricating not_applicable") — it is the doctrine-correct receipt for a producer fault (per #7451's `_resolve_cash_runway` design), not a claim that the underlying data is validated.
6. **The import-failure test (`_resolve_cash_runway_import_failure_degrades_to_not_loaded`) pins the anti-fabrication discipline.** Test 7 explicitly asserts `result["status"] == "not_loaded"` AND `result["status"] != "not_applicable"` AND that every value key (other than `schema` / `status` / `as_of`) is `None`. This is the r2-only test that protects against the silent-degrade-to-not-applicable defect, the exact anti-fabrication discipline the standing epistemics law (`context-accrual-fundamental-goal`) requires: a producer fault must not silently classify a candidate SEC filer as a structural non-filer, because doing so would silently remove the listing from the live `not_loaded` re-eval pool. The test is the calibrated anti-fabrication form, not a validation claim.

The PR is validated-claims compliant across all 188 new lines. No debt introduced.

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (read directly; macro has no `check_plain_language.mjs`) | PASS (test-only diff; user-facing copy rules are N/A; test names are plain-language; assertion strings are closed-schema identifiers; docstrings name the contract without leaking internal study names; honest-null grammar in import-failure docstring) |
| theme (`check_design_system.py --mode enforce-added --diff-file <(git diff origin/main...HEAD)`) | N/A (no `templates/` or `theme.css` change; `0 blocking` finding(s); 8-cell evidence matrix is the parent #7451's obligation, not this follow-on's) |
| validated-claims (`check_validated_claims.py --list`) | PASS (no `validated` / `已验证` / `经验证` / `经过验证` in test docstrings or assertions; CI-annotation assertion is the producer-fault receipt, not a validation claim; import-failure test pins the anti-fabrication discipline; estate MISS list unchanged) |
| half-B scope compliance | PASS (1 file / +188 / −0; tagged `[MO-B F09 W8-1 follow-on]`; third commit on packet B-F09-3 (MO-PAID-059 / MO-DELTA-018); r3 widens the test surface by exactly 7 resolver tests + 1 closed-key constant; r3 does NOT re-write r1, r2, or the engine, and does NOT force-push) |
| tests | PASS (107 passed / 1 skipped; +7 vs. #7451's 100 + 1; round-1 RED proof at 2a8e783e: throwaway edit of the resolver's fault branch → 2 failed / 5 passed; extra-key injection → 1 failed; non-None `cash_usd` on the shared fault return → import-failure test fails; all reverted, `git status --porcelain` clean; `check_contract_delta.py` → 0 introduced / 0 inherited) |
| render proof | N/A (test-only diff; no template / CSS / Jinja change; the parent #7451's render proof already covered the three contexts × EN+ZH × self-funding / synthetic burn / not_loaded) |

**Overall: PASS.** All three TP-0 gates (plain-language, theme, validated-claims) are clean at the test-only scope: plain-language passes because test names and docstrings follow the contract; theme is N/A because the diff carries zero CSS / template bytes; validated-claims passes because no promoted vocabulary is introduced and the import-failure test pins the anti-fabrication discipline. The diff is a disciplined r3: it widens the test surface from "engine entry-point" to "resolver entry-point" without rewriting r1, without force-pushing, and without modifying the engine, producer, template, or CSS surface. The PR is ready for merge on its own (already merged); the parent #7451's outstanding 8-cell evidence-matrix obligation is orthogonal to this follow-on and is not widened by it.

**No blocking findings. No durable writes outside this report.**

Operator-action note: this PR closes Grok `h_7451_rv1` minor 1 (no direct test for `_resolve_cash_runway`). The parent's outstanding obligation — `docs/pr-crops/<packet-slug>/{cash-runway-{1440,390}{,-zh}.png, EVIDENCE.yml}` with `capturedAtHead = e338508d` (or later main descendant) — is unchanged by this follow-on and remains the parent PR's open work.