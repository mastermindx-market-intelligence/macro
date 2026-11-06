<!-- Provenance: commissioned by the GMI Industrials first-vertical Fable Meta-CEO seat
     (operation gmi-industrials-fable-ceo-e2e-20260924-chairman-001, session c6467452) as an
     independent `ROUTE: review` / `reviewer` (Opus) child under `MODE: READ_ONLY` — it measured the
     branch against freshly fetched origin/main and executed its own probes; it wrote no repository file.
     The lane reviewers' own verdicts on the same heads were unreliable in both directions (a
     FIX_REQUIRED built on a stale base, then a 0-blocker PASS), so this read-only pass is the
     program's real quality gate for every task PR. -->

**Round:** T01 independent Opus red-team, third pass, on lane round 5's head.

**Verdict:** PARTIAL — all of N1-N8 CURED with executed evidence; 0 blockers, 0 majors, 3 one-line minors (F1-F3) and 2 no-action nits. F1-F3 were cured by the SEAT in round 6 (head `8e15b3f9c557`): two false `requests`-provenance statements in CI-authority comments, a dead `exhibit_url` plus two texts calling `primaryDocument` a URL, and an unused harness `get()` stub that reported `refresh_seam_unbound` for a seam the same class binds.

---

# T01 RE-CHECK ROUND 3 (opus, READ_ONLY) — PR #7924 head 0feac39712727cfecfb5c01c5ca4c4f1be3eab62
base fresh origin/main = 29013bf2c43b7097c45ce54e7cb0feb6b3028062
`git diff --name-only origin/main...origin/claude/ind-t01-dependency-binding | wc -l` => 22 (same owned set; no foreign path)
three new commits: 61e34f2a727 (N1 N2 N6) / e013dead749 (N3) / 0feac397127 (N4 N5 N7 N8); stat = 4 files, +233 -68

## N1-N8 DISPOSITIONS
- N1 (blocker: undeclared `requests`) CURED. Install line `.github/ci/legacy-jobs.yml` industrials block: `run: pip install pytest pyyaml requests`. Counterproof in a clean venv: after `pip uninstall -y requests` the suite dies `ModuleNotFoundError: No module named 'requests'` at `engine/neuralweb/company_intelligence_reader.py:21`; reinstalled => 22 passed. Sufficiency proof: venv holding EXACTLY `pytest pyyaml requests` => `22 passed in 1.16s`.
- N2 (deliberate closure evasion) CURED. `tests/industrials_result_cash_helpers.py:411-414` is now `from scripts.refresh_event_workspaces import (RefreshError, acquire_results_filing,)`; `grep -n "__import__\|importlib" tests/industrials_result_cash_helpers.py` => no match.
- N3 (fail_sources non-causal) CURED. Harness keys on the real URLs: `submissions_url = "https://data.sec.gov/submissions/CIK0000987654.json"` (= `_SUBMISSIONS_URL.format(cik=987654)`, owner `scripts/refresh_event_workspaces.py:92,251`), `url.endswith("-index-headers.html")` (owner :317), `url.endswith(exhibit_filename)` (owner exhibit_url = f"{archive_base}/{filename}"); unmatched URL => `(404, b"")`, fail-closed, no real `requests` call. Empty fail_sources reaches the owner's real return dict (`return {"status": "ok", **prepared}`), and the two new tests pass, including the same-instance flip.
- N4 (registry iterable consumed twice) CURED. `engine/company_intelligence/financial_dossier.py:69-70` `materialized_registry = None if registry is None else frozenset(registry)`, threaded to both `_check_identity` (:86) and `_checked_identity_value` (:107). `test_registry_generator_is_materialized_once_no_contradiction` passes `iter(list(issuer_registry()))` and asserts `live_admission == "admissible"` AND `bindings.identity.status == "resolved"`.
- N5 CURED for the owned file: the `frozenset({"example.invalid"})` sentence is gone from the `validate_delivery_inputs` docstring. Two pre-existing `example.invalid` literals remain in engine/ (`engine/sector_intelligence/finance_projection.py:1785`, `engine/marketing/earnings_call_lane.py:609`) — not this PR's files, out of scope.
- N6 CURED. No `refresh_module._http_get` assignment survives; `grep -n "_http_get\|monkeypatch\|setattr" tests/industrials_result_cash_helpers.py` yields only `def fake_http_get` (:467) and the `http_get=fake_http_get` kwarg (:485).
- N7 CURED. `tests/industrials_result_cash_helpers.py:192,196,200` — get_bytes / get_bytes_strict / get_bytes_strict_bounded each `self.read_count += 1`.
- N8 CURED. `tests/industrials_result_cash_helpers.py:508-511` publish docstring names the REQUIRED keyword `stage_dir` and the pytest `tmp_path` caller; suite passes `stage_dir=tmp_path` (`tests/test_industrials_dependency_binding.py:111,116`); every write is under `stage_dir` (`:387-393`).

## NEW FINDINGS (round 3)
- F1 minor — stale dependency comment in a SHARED CI-authority file. `tests/test_ci_pack.py:3755-3756`: "pyyaml is the only non-stdlib transitive need (engine.earnings_narrative.promotion -> yaml)". False at this head: `requests` is also required (proven above) and the job block's own install comment says so. Fix: amend that line to name requests.
- F2 minor — dead variable + wrong docstring in the harness. `tests/industrials_result_cash_helpers.py:433` `exhibit_url = f"https://example.invalid/{exhibit_filename}"` is assigned and never read (only `exhibit_filename` is used). The run_refresh docstring (:419-424) claims the submissions entry "points at https://example.invalid/<synthetic>.htm"; the real `primaryDocument` field is the bare filename and the owner derives the archive URL, so the doc misdescribes the fixture T02 will extend. Fix: delete :433, restate the docstring as "primaryDocument is the bare exhibit filename; the seam derives https://www.sec.gov/Archives/...".
- F3 minor — `_PublicationHarness.get()` (:502-503) still returns an unconditional `{"status": "unavailable", "reason": "refresh_seam_unbound"}` with no `needed:` key. Pre-existing (61665615:471, unchanged by the three cures) and unused by the suite (`grep harness.get` => no hit), but it now CONTRADICTS `run_refresh`, which proves the seam IS bound. Fix: delete the stub or give it the same causal shape.
- F4 nit — any non-empty `fail_sources` 503s the submissions URL regardless of the name, and only `failed[0]` is reported as `source`. Blessed by ruling R5 step 2, so not a finding against the lane; recorded so T02 does not read `source` as a validated source identity.
- F5 nit (MiniMax item) — `tests/test_industrials_dependency_binding.py:201` `__import__("tests.industrials_result_cash_helpers", fromlist=["FIXTURE_NAMES"])` hides nothing: the same module is statically imported at :8-15 and is a declared `paths:` entry, so the closure test sees it either way.

## ITEM PASS/FAIL
1. PASS — `grep -n "__import__\|importlib" tests/industrials_result_cash_helpers.py` (no match); plain in-function import; clean venv `pytest pyyaml requests` => 22 passed; uninstall-requests counterproof fails at company_intelligence_reader.py:21.
2. PASS (CI diff) — `git diff origin/main...origin/claude/ind-t01-dependency-binding -- .github/ci/legacy-jobs.yml` = 1 file, +77, ONE hunk @@ -16876,3 +16876,77 @@ appending only `industrials-result-cash`.
3. PASS — `python3 -m pytest tests/test_industrials_dependency_binding.py -k "empty_fail_sources or causal_not_coincidental or registry_generator" -v` => 3 passed; full suite 22 passed.
4. PASS — N4/N5/N6/N7/N8 evidence above.
5. PASS with F1-F3 — writes only under stage_dir; unmatched URL fails closed 404; no foreign paths; no module-level side effects beyond FIXTURE_DIR.glob; helper API `case`(=load_case :53)/`load_case`/`cell`/`comparison`/`dossier_inputs`/`publication_harness`/`issuer_registry`/`shared_identity` all present.

## CLOSURE PROOF (item 2, executed)
`python3 -c "curated_exclusive_closure_findings('.github/ci/legacy-jobs.yml')"` (the exact function the test and check_contract_delta call):
  TOTAL_JOBS_WITH_MISSES: 0
  INDUSTRIALS_MISSES: NONE
  CLOSURE_N: 39  DECLARED_N: 40  OVER_DECLARED_LITERALS: []
  GLOB_PATTERNS: ['tests/fixtures/industrials_result_cash/**']  (matches no closure .py — it is the fixture corpus the suite reads via FIXTURE_DIR.glob; required so a fixture edit selects the job, NOT over-declaration)
`python3 -m pytest tests/test_ci_pack.py -k "curated_exclusive_scopes_cover_their_own_import_closure or every_workflow_test_path_exists"` => `2 passed, 119 deselected in 267.40s`
Declared literals == closure exactly (39/39), so neither under- nor over-declared.

## VERDICT
FIX_REQUIRED (no blocker, no major): N1-N8 all CURED. Three minors (F1 stale pyyaml-only comment in tests/test_ci_pack.py:3755-3756; F2 dead exhibit_url + wrong docstring at helpers:433/:419-424; F3 contradictory refresh_seam_unbound stub at helpers:502-503) plus two nits. None blocks T02/T04 branching on the harness API, which is stable; F1 is the one worth fixing before merge because it is a false dependency statement in a shared CI-authority file.
Repository working tree untouched: `git status --porcelain | wc -l` => 0 after every sandbox operation.
