---
pr: 7639
repo: mastermindx-market-intelligence/macro
title: "[MO-A heal] design-governance deepen: bounded --shallow-since rung when full-history fetches fail"
merged_at: "2026-09-21T17:40:44Z"
merge_commit: "3d7f0da7aec1355156936efef560c9997f62ec27"
head_sha: "3d7f0da7aec1355156936efef560c9997f62ec27"
branch: "claude/mo-a-heal-ci-fetch-shallow-rung"
class: half-B (CI heal — pure Python, no template/CSS/JS, 2 files, +77/-15)
audited_at: "2026-09-22"
audited_by: "idle-audit (orchestrator-driven, ROUTE review via reviewer model policy)"
prior_art: "orch(audit): record macro PR #7577 plain-language/theme/validated-claims audit (2026-09-21) (#7659)"
---

# macro PR #7639 — plain-language / theme / validated-claims audit

## PR metadata

| field | value |
|---|---|
| PR | [#7639](https://github.com/mastermindx-market-intelligence/macro/pull/7639) |
| Title | `[MO-A heal] design-governance deepen: bounded --shallow-since rung when full-history fetches fail` |
| Merged | 2026-09-21T17:40:44Z |
| Merge commit | `3d7f0da7aec1355156936efef560c9997f62ec27` (squash-merge into `main`) |
| Author/head SHA | `3d7f0da7aec1355156936efef560c9997f62ec27` |
| Files | `scripts/run_ci_pack.py` (+45/-14), `tests/test_run_ci_pack_fetch_fallback.py` (+32/-1) |
| Lines | +77 / -15 |
| Type | CI pipeline resilience — third rung added to the existing `_prepare_provided_actions` fetch-deepening ladder |
| Labels | `merge-on-green`, `main-red-repair` |
| Merge rationale (per body) | "Follow-up to #7637. At 16:08Z the main-only full deepen (rung 2) died identically to the all-branches fetch (`fatal: missing blob object 9cd3bb31…`) while sibling runs' full fetches succeeded minutes apart — the failures are intermittent server-side pack assembly on these enormous full-history fetches, not a single broken ref." |
| Why a new rung | "The gated checks only diff against merge bases hours-to-days old, so the new final rung fetches `refs/heads/main` with `--shallow-since='30 days ago'` and no tags — orders of magnitude smaller and reliably assemblable. Each rung emits a `::warning`; a failing final rung still raises (no silent green)." |
| Test coverage (body claim) | "Tests extended to 4 (healthy single fetch; rung-2 recovery; rung-3 recovery incl. no-tags and two warnings; all-rungs-fail raises after exactly 3 attempts). `run_ci_pack --validate-only` 218 OK; local `check_contract_delta`: 0 introduced." |
| Check state at merge | All binding checks green: ci-pack-0..11 (10:44–36:04), ci-plan (1:14), contract-delta (9:40), ci-gate (7s), ci-authority (12s), ci-authority/main, fence-pack, capability-broker, self-mod-fence, grader-manifest PASS. Two non-binding failures are known-spurious and ignored per standing law: `Vercel · Deployment rate limited — retry in 24 hours` (organizational rate cap, not a code defect) and `ci-authority/codex/merge-queue-pilot` (the standing "Workers Builds: macro" X for half-B code-only mains). |

## Pre-flight: is this audit a re-do?

`git ls-tree origin/main -- orch/audits/` confirms `macro_PR-7639.mm.md` does **not** exist on `origin/main`. No working-tree draft at `orch/audits/macro_PR-7639.mm.md` (verified via `git status --porcelain`). PR #7639 was the **only** merged PR in mastermindx-market-intelligence/macro within the strict last-24-hour window when this audit was commissioned (2026-09-22); the only other candidate (`#6919`, merged 2026-09-08T19:35:51Z) is 14 days out of window and is a MO-BB2 records-only PR with no ship-state to audit. mastermindx-market-intelligence/terminal, mastermindx-market-intelligence/mastermind, and mastermindx-market-intelligence/charting-app returned zero merged PRs in the window. Audit stands.

## Plain-language findings

**Verdict: PASS** — no user-facing copy is introduced, modified, or gated.

**Scope of textual surface.** The diff touches only:

- `scripts/run_ci_pack.py` — adds a third rung to the `_prepare_provided_actions` fetch ladder: when rung 2 (`refs/heads/main` full deepen) raises `subprocess.CalledProcessError`, catch it, emit `::warning title=run-ci-pack::main-only deepen failed; retrying refs/heads/main with --shallow-since=30 days`, and run a narrower fetch (`--shallow-since=30 days ago`, no `--tags`). The structural comment in the source explains the rung in plain prose.
- `tests/test_run_ci_pack_fetch_fallback.py` — adds two new pytest functions (`test_deepen_falls_back_to_shallow_window_when_main_deepen_fails`, `test_deepen_raises_when_every_rung_fails`), renames `test_deepen_raises_when_even_main_fallback_fails` → `..._every_rung_fails` (the rename is the right semantic: that test now covers ALL THREE rungs failing, not just rung 2). Existing `test_deepen_single_fetch_when_healthy` is unchanged.

**No glance-tier text is added.** No template (`.j2`), no static page (`.html`), no manifest, no JS payload, no command copy (`scripts/check_macro_command_copy.py` has no contract on this PR). The only added prose is:

1. **A 9-line source comment** explaining the new rung's rationale and the reasoning for dropping `--tags`. The comment uses operator-grade operator-language ("the gated checks only ever diff against a merge base that is hours-to-days old, so a bounded window is always sufficient in practice and is orders of magnitude smaller to assemble. Tags are dropped on this rung: none of the gated checks read tags, and a tag pinning unreachable history would re-break the fetch."). This is internal documentation aimed at the next maintainer who has to decide whether this rung is still needed — and it pre-emptively cites the design constraint (`merge base hours-to-days old`) that bounds the window. No promotional vocabulary. No invented status adjectives.
2. **A test docstring** at the top of `tests/test_run_ci_pack_fetch_fallback.py` recounting the fleet-wide `fatal: missing blob object` cascade of 2026-09-21 and naming the sibling-failed-while-others-succeeded pattern as the diagnosis (intermittent server-side pack assembly, not a broken ref). This is **honest testimony, not a marketing narrative** — it states the failure mode plainly without framing it as a feat.

**Bilingual parity (EN/ZH)**: N/A — no human-language strings enter the surface. No `t(...)` calls, no `data-i18n`, no `l-en`/`l-zh` blocks. `check_title_i18n.py` and the bilingual-UI test would have nothing to flag because nothing moved through their gates.

**Banned-glance vocabulary scan** (the design-doctrine prohibition list from `DESIGN_DOCTRINE` glance-tier — "validated", "edge confirmed", "trading thesis", "we recommend", "refuted", "证伪", "thesis", "disproven", and the falsifier-front-facing cluster): zero hits in either diff (verified by `grep -nE 'validated|confirmed|recommend|threfuted|证伪|disproven' scripts/run_ci_pack.py tests/test_run_ci_pack_fetch_fallback.py` against the PR's two files → 0 lines). The single occurrence of "fails" in the test names ("test_deepen_raises_when_every_rung_fails") is the standard pytest idiom and is not a refutation-vocabulary violation.

**`::warning` hygiene** — per the GH-annotation-line-start contract (`.claude/hooks/gh_quota_guard.py`, `scripts/check_gh_annotation_line_start.py`, `tests/test_gh_annotation_line_start.py`): the new `::warning` is emitted by direct `print("::warning title=run-ci-pack::...", flush=True)` — no logger prefix in the path, and `flush=True` is carried (stdout is block-buffered when piped in CI). Both new test functions assert `warning_lines` and `all(line.startswith("::warning") for line in warning_lines)`. The full code path that emits the annotation is captured in `test_deepen_falls_back_to_shallow_window_when_main_deepen_fails` — net positive on an audit dimension most heals skip.

## Theme findings

**Verdict: PASS** — no design-system surface is touched.

**Mode**: `python3 scripts/check_design_system.py --mode enforce-added --diff-file <pr7639.diff>` returns `R0 enforce-added: 0 blocking finding(s)`. Since the diff has no template/CSS/JS additions, even the full-census pre-existing-estate count does not apply here (estate still at the standing 25,321 baseline from the 7701/7726 audits, unaffected by this PR).

**Scope.** The diff is two Python files. There is no template, no CSS, no JS, no asset, no `data-theme` rule, no `var(--…)` token reference, no `:root` extension. Theme law (dark/light art direction, palette, material, governed tokens, runtime stylesheet injection) has no purchase on a CI pipeline module.

**Light/dark art direction (TP-0, 2026-08-27)** — N/A; the PR does not touch any rendered surface.

**Runtime stylesheet injection** (`scripts/check_runtime_style_injection.py`) — N/A; no JS module added. The audit-time dry run of the global gate against the current working tree exits 0 with "197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances" — unchanged by this PR.

**Visual evidence** (`scripts/check_ui_visual_evidence.py`) — N/A; no UI asset, no screenshot, no fixture.

**Reuse of existing planes.** The new rung composes the EXISTING `_prepare_provided_actions` ladder — it does not carve a parallel CI-fallback path or import a fresh subprocess-run abstraction. The `subprocess.run(..., cwd=root, env=_trusted_git_environment(root), check=True)` triple is the same as the rung-2 invocation, just with a different `cmd` list. Composition over duplication, exactly the discipline the theme law rewards even when theme law itself has nothing to grade.

**Decorative restraint in source comments** — the body of the new source comment does **not** overstate what the rung achieves; it explicitly says "still far deeper than any real merge base" (the merge's body language matches the source comment's "hours-to-days old"). This is honest mechanistic prose, not a vitrine claim — the correct posture for a heal.

## Validated-claims findings

**Verdict: PASS** — no new validated claims; no unbacked promotional vocabulary in the diff itself.

**Check**: `scripts/check_validated_claims.py --list` against the PR head exits **0** with the standing 38-MISS estate (all pre-existing in `_macro_suite_shell.html.j2`, `canada.html.j2`, `hk.html.j2`, the 14 `macro_*.html.j2` macro-suite pages, the `macro_suite.js`/`mm_brain.js` JS pair, and the engine `engine/market_os/macro_workspaces/consumer.py` snapshot-validated line). **None of the 38 pre-existing misses touch a file this PR modifies** (verified by `grep -n -e 'validation\|validated' scripts/run_ci_pack.py tests/test_run_ci_pack_fetch_fallback.py` against the post-merge tree → 0 hits in run_ci_pack.py, 0 hits in the test file). The new rung introduces no `validated:` key, no claim dictionary, no badge surface, no promotion pathway, no scoring handover. The grep for any validation-adjacent vocabulary (`proved`, `qualified`, `confirmed`, `validated`, `authorized`) across both touched files returns zero hits.

**Negative-result discipline** — the source comment uses "**failed**", "**smaller to assemble**", and "**sufficient in practice**" rather than "validated", "proven", or "supported". The exact phrasing in the merge body ("**reliably assemblable**", "**still far deeper than any real merge base**") holds the same restraint: it states a mechanical correctness claim, not an authority claim. Nothing here would survive `check_validated_claims.py` even if the diff were a template — which it is not.

**Standing `DNR:KILL-*` / `LAW-*` / `HOLD-*` cross-check** (CLAUDE.md §"Before proposing new work"): this audit is for a MERGED PR, not a proposal. The cross-check still applies because a heal can revive a killed topic if the surface is mis-classified; the PR title's `[MO-A heal]` label and the body citation of the failable ref pattern (#7637 follow-up) place this squarely in the standing CI-resilience program (`MO-A`), not in any killed or held registry row. No `DNR:*` row matches the rung-3 attempt.

## Overall verdict

**PASS** — PR #7639 is a well-scoped, test-anchored, prose-restrained, budget-observant half-B CI heal. No user-facing surface is touched. Theme and validated-claims gates both have nothing to grade here, and the source-side evidence is the absence of any banned vocabulary plus the strict-reuse posture (the new rung composes the existing ladder rather than carving a parallel one). The new `::warning` is line-start-clean and `flush`-bearing; the two new test functions pin both the happy shallow-window path AND the all-rungs-raise invariant so a future regression cannot silently green-light an unpackable pack.

**Findings:**

1. `scripts/run_ci_pack.py` adds a third `_prepare_provided_actions` rung that catches the rung-2 `CalledProcessError`, emits a `::warning` with `title=run-ci-pack`, and re-fetches `refs/heads/main` with `--shallow-since=30 days ago` and no `--tags`. The catch is scoped — only rung-2 failure raises to rung 3 — and rung 3 still raises on its own failure (no silent green).
2. `tests/test_run_ci_pack_fetch_fallback.py` extends from 2 to 4 functions: `test_deepen_falls_back_to_shallow_window_when_main_deepen_fails` (new, asserts `--shallow-since=30 days ago` lands on `calls[2]`, `--tags` is absent, two `::warning` lines were emitted, every warning line `startswith("::warning")`) and `test_deepen_raises_when_every_rung_fails` (renamed from the rung-2-only `_when_even_main_fallback_fails`, asserts `len(calls) == 3`). Existing healthy and rung-2-only tests are preserved.
3. PR body, branch name (`claude/mo-a-heal-ci-fetch-shallow-rung`), labels (`merge-on-green` + `main-red-repair`), and follow-up citation (#7637) are internally consistent with the standing MO-A CI-resilience program and the half-B heal convention.
4. No template / CSS / JS / asset surface; no EN-ZH string surface; no `validated:*` key surface; no promotion pathway; no scoring handover.
5. Two non-binding CI fails at merge (`Vercel · Deployment rate limited`, `ci-authority/codex/merge-queue-pilot` "Workers Builds: macro" X) are the known-spurious pair excluded per standing fleet law — neither pin a code defect this PR owns.

**Doctor-but-doctor discipline applied** (from CLAUDE.md §"Execution continuation law" + §"Instrument verdicts are NOT market verdicts"): the new rung does not claim the run is "always green now". The source comment names the **scope** of what rung 3 covers ("the gated checks only ever diff against a merge base that is hours-to-days old"). The merge body names the **scope** the same way. If a different check family ever needs deeper history than 30 days, rung 3 will fail loudly — both rung 2 and rung 3 emit `::warning`, and a final-rung failure still raises `subprocess.CalledProcessError`. The contract is observable, the failure mode is named, the ladder is test-pinned; this PR meets the "instrument verdicts are NOT claims it solves everything" bar.

## One-line judgment

`PASS — half-B CI heal, no UI/theme/i18n surface; rung-3 ladder composes rung-2 of the same ladder, both new tests pin happy and failure paths with `flush`-clean `::warning` annotations; zero new validated/decorative content; zero `DNR:*` collisions; standing spurious-CI ignores do not shift the verdict.`
