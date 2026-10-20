# Audit — mastermindx-market-intelligence/macro PR #7558

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7558](https://github.com/mastermindx-market-intelligence/macro/pull/7558) |
| title | `fix(ci): bind contract-delta to exact tested merge base` |
| merged | 2026-09-20T22:32:08Z via squash-merge to `main`. Most recent merged non-audit-record half-B PR in the 24-h window after the orch(audit) record PRs #7560/#7555/#7549/#7548/#7547/#7546/#7545/#7544/#7543/#7541/#7540/#7538/#7537/#7536/#7529/#7525/#7519/#7516 and the closeout #7476. This is a CI-infrastructure repair, not a product/UI wave. |
| head | exact head `2605c9759db246e0a38a36d6459a46b2e2cf0bf2` (capture-time head = merge head). |
| author / merger | `chriswong6031-creator` (operator, META-CEO A seat WS:CI-MERGE-CONTROL-PLANE / W-CONTRACT-DELTA bounded source repair). |
| base | `origin/main` at `8e6523e038411552dac95f571be424a0d881e99a` (protected at commit time per PR body). |
| files | **2 paths, +150 / −7** — `.github/workflows/ci.yml` (+38 / −5) and `tests/test_contract_delta.py` (+112 / −2). |
| half-B label | **half-B (CI control-plane repair, scoped to the `contract-delta` job in `.github/workflows/ci.yml`).** No product, Prophet, dashboard, theme, design-system, copy, or rendering surface changes. |
| scope | **Bind the `contract-delta` job to the immutable PR merge object GitHub actually checked out, instead of the event field `pull_request.base.sha`.** Replace `github.event.pull_request.base.sha` with the synthetic merge's first parent (current tested base), bound by the exact PR head via a fail-closed resolver. Introduced-vs-inherited finding semantics are unchanged; ordinary candidate-added debt remains red. |
| durable owner | `WS:CI-MERGE-CONTROL-PLANE / W-CONTRACT-DELTA` (referenced in PR body, sourced from #7496). |
| checks | PR body reports RED-first proof: new `test_contract_delta_merge_resolver_selects_current_tested_base` (which creates the long-lived-PR topology in a temporary git repo and reproduces the hosted shallow-checkout assumption) failed first because the resolver did not exist. GREEN: `python3 -m pytest -q tests/test_contract_delta.py tests/test_ci_plan_workflow.py tests/test_trusted_ci_production_route.py` → 58 passed; `python3 scripts/check_workflow_yaml.py --selftest` → 4/4; `python3 scripts/check_workflow_yaml.py .github/workflows` → 98 workflow files parse; `git diff --check` PASS. Fences SUCCESS on local exact head. Hosted run `35538286004` was pending at PR-body time (PR was DRAFT / HOLD); release gate is exact-head checks + independent non-author review per PR-body release boundary. |
| gating scripts | `scripts/check_plain_language.mjs` — DOES NOT EXIST in macro (terminal-side only; `ls scripts/check_plain*` → no matches). Plain-language discipline on macro is read against the standing design-doctrine rules. `scripts/check_validated_claims.py` exists but errors out with `allowlist-missing` on `data/regime/validated_claims_allowlist.json` in a sparse checkout (sparse-tree fault, NOT a wave of new unearned claims; the checker itself explains this). `scripts/check_design_system.py` and `scripts/check_runtime_style_injection.py` exist (TP-0 art-direction gate). |

## Diff content (scoped to this PR)

**`.github/workflows/ci.yml` (+38 / −5, around line ~5076)**

- The old step `fetch the PR's base commit` (`git fetch --depth=1 origin ${{ github.event.pull_request.base.sha }}`) is REPLACED by a two-step pair:
  1. `resolve the exact tested PR merge base` (NEW, `id: contract-merge`, `shell: bash`, `env: EXPECTED_PR_HEAD: ${{ github.event.pull_request.head.sha }}`).
     - `tested_merge=$(git rev-parse HEAD)`, fail-closed if `$tested_merge != $GITHUB_SHA` (ensures checkout HEAD == GITHUB_SHA).
     - Reads `git cat-file -p HEAD | sed -n 's/^parent //p'` to recover the raw commit object's `parent` headers. Comment explains: `actions/checkout@v4` with `fetch-depth: 1` marks the merge as a shallow boundary, so revision-walking formats like `%P` hide its parents — the raw commit object retains both parent OIDs.
     - Asserts exactly two parents; fails closed if not.
     - Binds `$tested_head` (second parent) to `$EXPECTED_PR_HEAD`; fails closed on mismatch.
     - Emits `base_sha=$tested_base` and `head_sha=$tested_head` to `$GITHUB_OUTPUT`.
     - Uses `::error title=contract-delta::…` annotations per the standing CI-guarded `print("::warning title=…")` line-start convention (annotations start the line).
  2. `fetch the exact tested PR merge base` (`git fetch --depth=1 origin ${{ steps.contract-merge.outputs.base_sha }}`). The comment is updated to explain why `pull_request.base.sha` is wrong on long-lived PRs (creation-era base vs current tested main).
- The downstream `differential contract-delta gate` step changes `--base ${{ github.event.pull_request.base.sha }}` → `--base ${{ steps.contract-merge.outputs.base_sha }}`. The `scripts/check_contract_delta.py` script is UNCHANGED.
- Net effect: the differential base used by `check_contract_delta.py` is now derived from the immutable synthetic merge object GitHub actually checked out, fail-closed at every gate. There is NO product, theme, copy, design-system, rendering, or user-facing change in this PR.

**`tests/test_contract_delta.py` (+112 / −2)**

- Existing test `test_contract_delta_run_step_calls_the_script_with_base` is RENAMED to `test_contract_delta_binds_to_the_exact_tested_merge_parent` and tightened: it now asserts the new `resolve the exact tested PR merge base` resolver step exists, checks `EXPECTED_PR_HEAD == "${{ github.event.pull_request.head.sha }}"`, asserts the resolver's `run` string contains `git rev-parse HEAD`, `GITHUB_SHA`, `git cat-file -p HEAD`, `sed -n 's/^parent //p'`, `"$#" -ne 2`, `"$tested_head" != "$EXPECTED_PR_HEAD"`, and `base_sha=$tested_base`. It then asserts `steps.contract-merge.outputs.base_sha` is in the job blob and `github.event.pull_request.base.sha` is NOT in the job blob (regression-guard for the prior event-field path).
- NEW `test_contract_delta_merge_resolver_selects_current_tested_base` — RED-first proof. Creates a temporary git repo, sets up the exact topology that exposed #7496: a candidate forks from an old base, main moves independently, then a two-parent synthetic merge is tested. The test:
  - Asserts `_git("show", "-s", "--format=%P", "HEAD", cwd=repo).strip() == ""` after writing the merge to `.git/shallow` — i.e. it REPRODUCES the hosted shallow-checkout assumption that hides `%P` parents.
  - Asserts `git cat-file -p HEAD` still returns both `parent` headers.
  - Runs the actual workflow resolver bash with `GITHUB_SHA=tested_merge`, `EXPECTED_PR_HEAD=pr_head`, and the real `GITHUB_OUTPUT` file.
  - Asserts the resolved output equals `{"base_sha": tested_base, "head_sha": pr_head}` and that `base_sha != creation_base` (current tested main ≠ creation-era base).
  - Re-runs the resolver with `EXPECTED_PR_HEAD=creation_base` and asserts non-zero exit + stderr contains `"second parent does not match the exact PR head"` (fail-closed binding proof).
- `import os` is added to the test module imports; no other test surfaces change.

## Plain-language findings

**Verdict: NOT APPLICABLE.** This PR contains zero user-facing copy. The two changed files are `.github/workflows/ci.yml` (CI YAML) and `tests/test_contract_delta.py` (CI test). No template, no rendered HTML, no JS, no CSS, no product copy, no error message, no toast, no empty state, no tooltip, no user-visible string is added, removed, or changed. The only English text changes are inside:
- The PR body and PR comments (operator-facing release notes; not user-facing).
- The expanded inline comment block inside `ci.yml` explaining why `pull_request.base.sha` is wrong on long-lived PRs (developer-facing CI documentation, not user-facing).
- The docstring of the new test (developer-facing test documentation, not user-facing).
- The step name `resolve the exact tested PR merge base` (developer-facing CI step label, not user-facing).

`scripts/check_plain_language.mjs` does not exist in macro (terminal-side only). Standing design-doctrine plain-language checks (banned-vocab, plain-word null disclosure, tier-2 receipts, glance-tier state + plain-word stance under hard word budgets) apply to user-facing surfaces only. PR #7558 is a CI control-plane repair, so the plain-language gate is not engaged.

The operator-facing release prose in the PR body and PR comment is technical/incident-style ("HOSTED RED → SAME-CARRIER GREEN SOURCE REPAIR") and is not subject to the user-facing plain-language laws. It correctly names the exact defect (`fetch-depth: 1` shallow-checkout + `%P` revision-walk hiding parents), the precise witness (PR #7243, head `b81777c3d701…`, run `35534642672`, all twelve `ci-pack-0..11` jobs succeeded while `contract-delta` misclassified `tests/test_unified_dashboard_b1.py`), the exact test branch lines (`~4674` vs `~5076`), the exact source head (`a9d8a9f27e59648e55096d541656fc2df28381cd`) and #7513 head (`2a5eb9491e87c228711fc0298bbf3f7f56e88662`), and the conflict-free `git merge-tree --write-tree` result (tree `cfd47ecd2367e9b2272cf74deb092e48d97f8213`, exit 0). This is the standing PR-body discipline — every `verified:` claim names its command, every `git merge-tree` is recorded by tree SHA, every job name and run ID is recorded by ID. No false claims, no over-claims, no green-by-waiver language.

## Theme findings

**Verdict: NOT APPLICABLE.** PR #7558 does not touch `templates/theme.css`, `site/theme.css`, the design-system tokens, the dark/light palette, the runtime style injection surface, or any CSS rule. The two changed files are CI YAML and CI test code. The standing TP-0 art-direction gate (DARK TREATMENT / LIGHT TREATMENT / evidence matrix per packet) does not engage because no material UI packet is added or changed.

No token substitution is performed, no `var(--token)` is added, no `color-mix(...)` overlay is added, no theme-specific degraded state is added, no responsive breakpoint is added, no shadow/glow/border-radius rule is added. The PR does not regress any existing dark/light behavior because it does not touch the rendering surface at all.

`scripts/check_design_system.py` and `scripts/check_runtime_style_injection.py` are not exercised by this PR's diff and have nothing to flag.

## Validated-claims findings

**Verdict: NOT APPLICABLE.** PR #7558 introduces no user-facing claims — no statistics, no probabilities, no forecasts, no signal names, no tier-word bands, no tier→label mappings, no neural-web lobe references, no zone or regime labels, no Prophet board mentions. The only English strings introduced are developer-facing step names, inline comments, and a docstring. None of these are user-facing claims.

`scripts/check_validated_claims.py` is engaged at the engine + dashboard + Prophet board surface, not at the CI workflow YAML surface. The script errors out in this sparse checkout with `allowlist-missing` on `data/regime/validated_claims_allowlist.json` (sparse-tree fault, not a wave of new unearned claims — the checker itself explains this). Even if it ran cleanly, the PR's diff contains no candidate text for the CI to gate against.

The PR body and comments reference prior PRs and runs by ID (#7243, run `35534642672`, #7513, head `a9d8a9f27e59648e55096d541656fc2df28381cd`, head `2a5eb9491e87c228711fc0298bbf3f7f56e88662`, merge-tree tree `cfd47ecd2367e9b2272cf74deb092e48d97f8213`, fenced SUCCESS, exact-head hosted run `35538286004`). These are operator-facing provenance records, not user-facing claims. The PR body explicitly disclaims green-by-waiver ("Do not manufacture green by wiring or waiving unrelated suites on affected product PRs") and disclaims product semantics change ("No product/Prophet semantics change in this carrier").

The release boundary is correctly framed: DRAFT / HOLD until ordinary hosted exact-head checks and independent non-author review conclude. The Closes-#7496 clause is correctly conditional ("Closes #7496 only when this source repair is actually merged and the shared gate is accepted") — no premature claim of acceptance, no premature claim of fix-landed.

## Overall verdict

**PASS — non-engaging repair.** PR #7558 is a bounded CI control-plane source repair (no product/UI surface). It binds the `contract-delta` job in `.github/workflows/ci.yml` to the immutable synthetic merge object GitHub actually checked out, fail-closed at every gate, and adds a RED-first test that recreates the hosted shallow-checkout topology in a temporary git repo to prove the resolver selects current tested main (not creation-era base), binds to the exact PR head, and fails closed on a mismatched expected head.

- **Plain-language:** NOT APPLICABLE — zero user-facing copy.
- **Theme:** NOT APPLICABLE — zero theme/CSS/design-system change.
- **Validated-claims:** NOT APPLICABLE — zero user-facing claims.

The PR correctly cites the durable owner (`WS:CI-MERGE-CONTROL-PLANE / W-CONTRACT-DELTA`), explicitly scopes itself as a bounded source repair (no new CI plane, no waiver, no runner/queue/scheduler/merge-authority change), correctly disclaims green-by-waiver and product-semantics change, and enforces the DRAFT / HOLD release boundary. No false claims, no over-claims, no operator-facing language that misrepresents the scope or status.

The 58-test local qualification, the `check_workflow_yaml.py --selftest` 4/4 pass, the 98 workflow-file parse, the `git diff --check` clean, and the conflict-free `git merge-tree --write-tree` against the only open recent PR touching `ci.yml` (#7513, separate `ci-pack` cancellation stanza at ~line 4674) are all properly recorded in the PR body. The fail-closed binding (`tested_head != EXPECTED_PR_HEAD` → `::error` + exit 1) and the shallow-checkout handling (`git cat-file -p HEAD` raw object headers, not `%P`) are both inline-commented with the reason they exist.

No audit defects found. No `DO_NOT_REDO`/`DNR` conflict. No `DEC:`/`DSC:` records cited that would be contradicted by this PR. No design-doctrine regression. No `agentos/` governance-plane write needed — this is a CI workflow YAML + test change, not a knowledge-plane write.

**Recommended action:** record this audit (`orch(audit): record macro PR #7558 plain-language/theme/validated-claims audit (2026-09-20)`) so the next audit pass picks up the next non-engaging half-B PR. Continue the audit sweep.
