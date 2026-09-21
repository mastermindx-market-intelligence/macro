# Plain-language / theme / validated-claims audit — macro PR #7639

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7639 |
| title | `[MO-A heal] design-governance deepen: bounded --shallow-since rung when full-history fetches fail` |
| merged_at | 2026-09-21T17:40:44Z |
| head | `3d7f0da7aec1355156936efef560c9997f62ec27` (squash-merge commit) |
| merge_commit | `3d7f0da7aec1355156936efef560c9997f62ec27` |
| base | `main` at the time of the squash (post-#7637 merge) |
| branch | `claude/mo-a-heal-ci-fetch-shallow-rung` |
| changed files | **2 infra paths, +77 / −15.** `scripts/run_ci_pack.py` (+45 / −14 MODIFIED), `tests/test_run_ci_pack_fetch_fallback.py` (+32 / −1 MODIFIED). Zero template / CSS / JS / data / product-runtime / render / docs / agentos / `orch/audits/` surface touched. |
| additions / deletions | 77 / 15 |
| labels | (none external; standard macro merge path; the body documents 4 new tests and `run_ci_pack --validate-only 218 OK; check_contract_delta: 0 introduced`) |
| scope collision | none — body is explicit that the heal extends the existing fetch-fallback ladder inside `run_ci_pack.py` only; no schema field, no pack index, no contract JSON, no template, no user-facing surface |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --merged recent` against `git ls-tree origin/main -- orch/audits/` shows the previous-idle-audit-window's unaudited merges are: (a) `orch(audit)` record-keeping PRs (#7651, #7644, #7636, #7627, #7612 — filing records for prior audits, no audit-relevant surface of their own); (b) `fix(ci)` infrastructure binds (#7628 "keep contamination probe reachable", #7621 "bind Bonds stylesheet fingerprint", #7614 "checkpoint core engine outputs" — no user-facing template/lens/render change); (c) `[MO-A heal]` infrastructure repairs that preceded this one (#7637 "fall back to main when all-branches fetch fails" — already-merged predecessor, no template/JS/CSS surface touched). The remaining recent merge with a real audit-relevant surface (CI governance code + test additions) and without a committed audit on `origin/main` is **#7639** — a half-B scope: a single new rung appended to the existing fetch-depth-0 fallback ladder inside `scripts/run_ci_pack.py`, +77 lines total, no template/HTML/JS/render surface, no new signal/rank/score, no new authority, no new theme surface. Plain-language applies to the prose in the GitHub annotation `::warning title=` strings and to the in-code comments that surface in PR review and in `git log`; theme is structurally out-of-scope (zero CSS/JS touched); validated-claims discipline applies to the absence of any user-facing `validated`/`proved`/`guaranteed` claim and to the test assertions which read literal subprocess argv rather than any authority-promotable assertion.

**Nature of change (half-B infra ladder extension, second MO-A heal in the same morning):** extends `_prepare_provided_actions()` in `scripts/run_ci_pack.py` (the fetch-depth-0 fetch ladder that drives all design-governance pack-runs) from a one-fallback ladder (all-branches → main-only full) to a two-fallback ladder (all-branches → main-only full → main-only `--shallow-since=30 days ago` no-tags). Each rung emits a `::warning title=run-ci-pack::…` line to stdout (CI-guarded: bare `print(..., flush=True)` per the standing house-law on GitHub annotation line-start). The new final rung is bounded — `--shallow-since='30 days ago'` no `--depth=2147483647`, no `--tags` — so the server-side pack assembly can succeed where the unbounded main-only full fetch dies on intermittent "fatal: missing blob object 9cd3bb31…" errors (measured 2026-09-21 16:08Z, the proximate cause). The body argues the boundedness is safe because "the checks behind this contract only ever diff against a merge base that is hours-to-days old" — so a 30-day window is "far deeper than any real merge base" and "orders of magnitude smaller to assemble." A failing final rung still raises (no silent green). Test surface extended from 3 → 4 (healthy single fetch; rung-2 recovery [pre-existing]; new rung-3 recovery including no-tags + two warnings; new all-rungs-fail raises after exactly 3 attempts).

## Diff content (scoped to this audit)

Both files are CI-infrastructure code + tests. The PR introduces **zero** template / HTML / JS / CSS / data / workflow / render / runtime surface. The plain-language / theme / validated-claims laws therefore have only the in-code prose strings and the GitHub annotation titles to read.

### `scripts/run_ci_pack.py` (+45 / −14, MODIFIED)

Single functional change inside `_prepare_provided_actions()`: wraps the existing main-only `git fetch --depth=2147483647 …` call in `try` / `except subprocess.CalledProcessError:` and, on failure, prints a `::warning` and re-runs with `git fetch --no-recurse-submodules --shallow-since='30 days ago' origin +refs/heads/main:refs/remotes/origin/main` (no `--depth`, no `--tags`).

The two PR-added prose surfaces are:

1. The in-code comment block (1 paragraph, 5 sentences) immediately above the new `subprocess.run(...)`. It narrates the proximate failure (16:08Z the main-only full deepen died identically with "fatal: missing blob object 9cd3bb31…"), the diagnosis (intermittent server-side pack assembly on enormous full-history fetches, "not one broken ref"), the safety argument (checks diff against a hours-to-days-old merge base, so a bounded window is sufficient), and the deliberate tag-drop ("none of the gated checks read tags, and a tag pinning unreachable history would re-break the fetch").
2. The GitHub annotation: `::warning title=run-ci-pack::main-only deepen failed; retrying refs/heads/main with --shallow-since=30 days`.

Plain-language scan: the comment uses concrete dates, concrete refspecs, concrete error strings, and concrete sufficiency arguments; no internal-state names leak; "main-only deepen", "bounded window", "tag pinning unreachable history" are the canonical terms used by every other rung in the same ladder (the pre-existing first-fallback block uses identical phrasing: "all-branches deepen failed; retrying with refs/heads/main only"). The `::warning` annotation matches the standing house-law on `print("::warning title=…::…", flush=True)` (bare `print`, `flush=True` load-bearing, line starts with `::`, no logger prefixing — verified line-start by the existing `tests/test_gh_annotation_line_start.py` discipline).

No banned-glance vocabulary in the PR-added prose: zero matches for `internal_state`, `study`, raw slug names, raw state names, `validated` as authority claim, `signal`, `score`, `rank`, `gate` (in the product-promotion sense), `threshold`, `proved` (in the implicit-authority sense), `guaranteed`, `certified`, `compliant` against the diff. The word `gate` appears in the file at lines 84, 98, 102, 397, 428, 460, 1357 — all pre-existing `GATE_VALUES = ("code", "data")` / `gate: code` pack-routing context, well outside the diff range (the diff lives at lines 2985-3035 of the post-PR file). **No new gate-promotion is asserted or implied.**

### `tests/test_run_ci_pack_fetch_fallback.py` (+32 / −1, MODIFIED)

Two test functions modified/added:

1. **Renamed** `test_deepen_raises_when_even_main_fallback_fails` → `test_deepen_raises_when_every_rung_fails`; assertions extended to verify exactly 3 subprocess calls (`len(calls) == 3`) instead of the prior 2.
2. **Added** `test_deepen_falls_back_to_shallow_window_when_main_deepen_fails`: drives the new rung-3 happy-path. Asserts `len(calls) == 3`, `--shallow-since=30 days ago` is in call 2's argv, `+refs/heads/main:refs/remotes/origin/main` is in call 2's argv, `--tags` is NOT in call 2's argv (the deliberate tag-drop is regression-tested), exactly 2 `::warning` lines were emitted (one for rung-2, one for rung-3), all of them start with `::warning` (the standing line-start discipline).

Plain-language scan: test names are literal descriptions of the behavior they exercise (`falls_back_to_shallow_window_when_main_deepen_fails`, `raises_when_every_rung_fails`). No narrative copy, no user-facing strings, no asserts on human-readable labels. The `capsys` capture and `caplog` discipline is consistent with the standing `tests/test_gh_annotation_line_start.py` test surface.

## Plain-language findings

### 1.1 Pass — the diff carries zero banned-glance vocabulary and the two prose surfaces (in-code comment + `::warning` annotation) match the canonical phrasing of the surrounding code

`grep -inE "internal_state|study|raw_slug|signal|rank|score|threshold|validated|proved|guaranteed|certified|compliant"` against the added lines of both files returns ZERO matches. The word `gate` exists in the surrounding `scripts/run_ci_pack.py` (pre-existing `GATE_VALUES` pack-routing context, lines 84 / 98 / 397 / 460 — far outside the diff range at lines 2985-3035). The word `validated-claims` exists at line 428 (pre-existing test-category declaration, also outside the diff). Neither is asserted, claimed, or implied as a product gate by the new code.

The new in-code comment block follows the same template as the pre-existing first-fallback block (the one introduced by #7637 earlier in the same morning): opens with a dated timestamp + the exact error string, names the diagnosis ("intermittent server-side pack assembly… not one broken ref"), gives the safety argument in concrete terms ("hours-to-days-old merge base… bounded window… orders of magnitude smaller to assemble"), and explains the deliberate constraint-drop ("Tags are dropped on this rung: none of the gated checks read tags, and a tag pinning unreachable history would re-break the fetch"). This is plain-language operator-memo prose, not product copy — the consumer is the next engineer reading `git blame`, not a dashboard user.

The new `::warning title=run-ci-pack::main-only deepen failed; retrying refs/heads/main with --shallow-since=30 days` annotation matches the `::warning title=run-ci-pack::all-branches deepen failed; retrying with refs/heads/main only` annotation on rung-2 (introduced by #7637). The two annotations read as a single ladder when grepped together. `flush=True` is present (load-bearing per the house law). The annotation text is plain-English, names the rung that failed, names the next rung, and gives the literal CLI flag the next rung uses — exactly the level of detail an Actions-summary reader needs to diagnose without opening the file.

### 1.2 Pass — test names are literal descriptions and assertions are concrete (no narrative)

`test_deepen_falls_back_to_shallow_window_when_main_deepen_fails` and `test_deepen_raises_when_every_rung_fails` are both literal descriptions of the behavior they exercise (the first tests the new rung-3 happy-path; the second tests the no-fallback-works case). Assertions check concrete argv (`--shallow-since=30 days ago`, `+refs/heads/main:refs/remotes/origin/main`, `--tags not in calls[2]`), concrete call counts (`len(calls) == 3`), and concrete stdout (`warning_lines == 2`, `line.startswith("::warning")`). No narrative copy is asserted. The `noqa: ANN001, ANN003` on `fake_run(cmd, **kwargs)` is the canonical type-annotation waiver used throughout the existing test file (verified: the pre-existing first-fallback test uses the identical waiver at the identical signature — not introduced by this PR).

### 1.3 N/A — the macro EN/ZH bilingual-pair discipline is structurally inapplicable

`tests/test_bilingual_ui.py` and `scripts/check_bilingual.py` gate templates/HTML/JS user-facing copy only. The PR touches only `scripts/run_ci_pack.py` and `tests/test_run_ci_pack_fetch_fallback.py` — neither is rendered by the macro product, neither carries any human-language surface. The omission is by-design and matches every other CI-infrastructure PR merged into the repo.

### 1.4 Observation (non-blocking) — the new rung deliberately drops `--tags` without an explicit merge-base read

The in-code comment justifies the tag-drop ("none of the gated checks read tags, and a tag pinning unreachable history would re-break the fetch"). This is a correct empirical claim about the current check set (`gated checks only diff against a merge base that is hours-to-days old`), but it relies on the existing check set staying tag-free. If a future check is added that reads tags, rung-3 will silently fail to assemble the tag and the gate will red on a `git describe`-style assertion. Not in scope for this PR — but worth flagging as a "future-proofing observation" in any future audit when a tag-reading check is added.

## Theme findings

### 2.1 N/A — the PR touches zero theme surface

This PR's diff is two Python files (`scripts/run_ci_pack.py` + its test). There are no `templates/`, `site/`, `mockups/`, CSS, JS, theme-token, lens, viewport, dark/light, EN/ZH, or responsive-matrix surface changes. There is no `style="..."` injection because there is no inline JS. There is no new palette / parallel token family because no style carries. `scripts/check_design_system.py --mode enforce-added` and `scripts/check_runtime_style_injection.py` are both out-of-scope for this PR by construction. The TP-0 dark/light × EN/ZH × 1440/390 matrix requirement does not bind — `check_design_system.py --mode enforce-added` runs only on a PR whose `templates/`/`site/`/`mockups/` changed file list is non-empty, which this PR's list is not. There is no `evidence matrix` to produce here.

### 2.2 N/A — no theme-art-direction assertion is made or implied

The PR body, the in-code comment, the `::warning` annotation, and the test names all restrict their scope to CI-infrastructure / git-fetch-ladder / rung-3 surface. None claim a dark/light, EN/ZH, or material-design effect. The body closes with the explicit disclaimer that the new rung is "still far deeper than any real merge base" and that "A failing final rung still raises" — both negative/operational statements, no design implication. **No theme assertion exists to fail.**

### 2.3 N/A — token substitution alone is not how this PR achieves anything in the design system layer

This PR is template-free, CSS-free, JS-free — there are no design-system tokens to substitute. The standing rule "Token substitution alone is never proof of a light design" is not engaged because there is no token substitution. The "substance may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" rule does not engage because no JS payload is changed. Both rules structurally have nothing to read in this diff.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` is satisfied by structural scope; no user-facing template surface is touched

`scripts/check_validated_claims.py --list` enumerates every affirmative user-facing claim keyed by `[file:line]` plus an allow/deny label. The allow list lives in `data/regime/validated_claims_allowlist.json` and reads `templates/*.j2` (the template surface). This PR modifies only `scripts/run_ci_pack.py` and `tests/test_run_ci_pack_fetch_fallback.py`. Both files are OUT of the gate scope (the gate reads templates, not CI infrastructure or tests). There is no `MISS` row in the gate's output against this PR's diff (the gate does not even see the files — verified manually: `python3 scripts/check_validated_claims.py` enumerates thousands of `templates/` entries; the two files in this PR never appear).

### 3.2 Pass — no use of the word "validated" or any promotion-bearing synonym in either PR-added file

`grep -inE "validated|proved|guaranteed|certified|compliant"` against the added lines of both files returns ZERO matches. The PR does not assert a deploy, a release-candidate build, a release, an authority promotion, a signal upgrade, a rank uplift, a threshold tightening, or any other promotion-bearing claim. The body closes with two operational disclaimers ("orders of magnitude smaller, reliably assemblable, still far deeper than any real merge base" + "A failing final rung still raises") — both are scope-bounded operational statements, not authority claims.

### 3.3 Pass — the `validated-claims` check-category name that appears in the surrounding file (line 428) is pre-existing and out of the PR's diff range

`scripts/run_ci_pack.py` carries a `validated-claims` check-category declaration at line 428 (verified above). This is a pre-existing reference in the legacy-job taxonomy used by `scripts/check_validated_claims.py` to know what to scan; the string sits in the `JOB_CATEGORY_TO_CHECK` lookup table and is named after the gate, not asserting that any product claim has been validated. The reference is at line 428 — well outside the diff range (2985-3035) — and the PR does not modify, rename, or extend that lookup. **Not blocking.**

### 3.4 Pass — the body explicitly disclaims any production-promotion or authority-bearing implication

The PR body closes with two operational statements: "orders of magnitude smaller, reliably assemblable, still far deeper than any real merge base" (a sufficiency argument for the bounded window) and "A failing final rung still raises" (a no-silent-green promise). The body does not claim the ladder is now "complete", "proven", or "validated" — it explicitly notes the heal is "intermittent server-side pack assembly on these enormous full-history fetches, not one broken ref", which is a diagnostic statement, not a promotion. The PR does not assert a deploy, a release-candidate build, a release, an authority promotion, a signal upgrade, a rank uplift, a threshold tightening, a context-gate change, or a policy/ledger change. No `promotion: PROMOTED` row; no `authority_changed: true` row; no score/rank/threshold/context-gate/policy/ledger changes (matches the standing discipline: CI-infrastructure PRs never carry promotion claims).

## Overall verdict

**VERDICT: PASS — clean half-B CI-ladder extension, merge is correct.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | The PR-added prose (1 in-code comment block + 1 `::warning` annotation + 2 test names) is operator-memo-level copy, not user-facing chrome. Banned-glance vocabulary returns zero matches in the added lines. The in-code comment matches the canonical phrasing template used by the pre-existing rung-1 fallback (introduced by #7637 earlier the same morning). The `::warning` annotation matches the standing house-law on bare `print("::warning title=…::…", flush=True)` with line-start and flush load-bearing. Test names are literal descriptions of behavior. Bilingual EN/ZH parity is structurally inapplicable to CI-infrastructure code. The one future-proofing observation (tag-drop relies on the existing check set staying tag-free) is non-blocking. |
| theme | N/A — structurally no theme surface | PR touches zero `templates/`, `site/`, `mockups/`, CSS, JS, theme-token, lens, viewport, dark/light, EN/ZH, responsive-matrix surface. `check_design_system.py --mode enforce-added` and `check_runtime_style_injection.py` are out-of-scope by construction. The TP-0 two-art-directions rule and the runtime-style-injection rule both have nothing to read in this diff. No theme assertion is made or implied; the body closes with two operational disclaimers ("still far deeper than any real merge base" + "A failing final rung still raises"). |
| validated-claims | PASS | `check_validated_claims.py --list` does not enumerate `scripts/run_ci_pack.py` or `tests/test_run_ci_pack_fetch_fallback.py` (gate reads templates only — diff is out-of-scope by construction). No `validated`, `guaranteed`, `certified`, `proved` (in implicit-authority sense), or other promotion-bearing synonym appears in any PR-added line. The pre-existing `validated-claims` check-category name at `scripts/run_ci_pack.py:428` is a gate-name reference, far outside the diff range (2985-3035), unmodified. PR body explicitly disclaims any promotion-bearing implication — closes with operational sufficiency ("still far deeper than any real merge base") and no-silent-green ("A failing final rung still raises") statements. No signal / rank / score / threshold / context-gate / policy / ledger change. |
| merge hygiene | PASS | Single-act ladder extension (1 new rung + 1 new test + 1 renamed test). `run_ci_pack --validate-only` reports 218 OK; `check_contract_delta: 0 introduced`. The new rung fails closed (a failing rung-3 raises — no silent green). Tags deliberately dropped (the regression test `assert "--tags" not in calls[2]` pins this). Existing pack index, contract JSON, schema, and template surface are untouched. The PR body documents the proximate failure with a concrete timestamp + exact error string + sibling-runs-evidence, satisfying the "diagnostic before heal" discipline. |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The new rung deliberately drops `--tags` on the empirical claim that "none of the gated checks read tags". This is correct today but couples the rung-3 safety argument to the existing check-set composition. If a future check is added that reads tags (e.g. a `git describe`-style version assertion), rung-3 will silently fail to assemble the tag. Worth pinning with an explicit test or with a comment in any future tag-reading check that documents the assumption. Out-of-scope for this PR.
2. The `--shallow-since='30 days ago'` literal is a magic number; if the gated checks' merge-base recency ever exceeds 30 days (highly unlikely on macro at the current merge cadence, but not structurally impossible on a slow-merge repo), rung-3 will silently miss the merge base and the gate will red on a `git rev-parse` step. A `check_fetch_window.py` regression that asserts `min(merge-base-age) < shallow-since-window` would close this. Out-of-scope for this PR.
3. The new rung is rung-3 of an all-branches → main-only-full → main-only-shallow ladder. If a future fetch failure mode survives all three rungs (e.g. the 30-day window itself becomes un-assemblable for the same intermittent reason), the next rung would need to be `git ls-remote origin +refs/heads/main:refs/remotes/origin/main` (zero-pack, refspec-only). Not in scope — flagging for the next MO-A heal cycle. The current rung-3 raises on failure (no silent green), so the next failure will be visible immediately.

**No blocking issue found. No retry. No scope expansion. Audit complete.**
