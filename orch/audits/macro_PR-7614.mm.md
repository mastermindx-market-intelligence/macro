# Plain-language / theme / validated-claims audit — macro PR #7614

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7614 |
| title | `fix(ci): checkpoint core engine outputs before tail desks` |
| merged_at | 2026-09-21T22:29:57Z |
| head (pre-merge candidate) | `02fe114e577f181634afb41a34073ff4b7577ebf` |
| merge_commit | `a9b1f4cb07d24e29c15b45cc5d73e344dcb6e2ae` |
| base | `main` at `e2f7189ddfe85946a5b440650e1a0be25a92dca2` (post-merge snapshot) |
| branch | workstream-bound CI repair (no new code/JS/CSS surface) |
| changed files | **3 infra-only paths, +137 / −0.** `.github/workflows/daily.yml` (+9), `config/dag.yml` (+27), `tests/test_push_retry.py` (+101). Zero template / HTML / JS / CSS / data / render / user-facing runtime / agentos surface touched. |
| additions / deletions | 137 / 0 |
| labels | `merge-on-green` (sweeper arm — this is a CI repair, the label is the standing arm for ordinary work, not a release marker) |
| scope collision | none — body is explicit that "this PR addresses publication atomicity only. It does not alter the Gold calculation, data-source authority, UI methodology, or the incumbent publisher implementation. PR #7596 remains a separate, unchanged carrier for the post-rebase Gold binding repair. Do not replace or redesign it." |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --merged recent` (last 24 h: 2026-09-20T22:29Z → 2026-09-21T22:29Z) against `git ls-tree origin/main -- orch/audits/` shows the unaudited merges are exclusively infra/CI lanes: macro #7614, #7628, #7621, #7636, #7637, #7639, #7613, #7597; terminal #705, #700, #698, #696, #695, #693, #689. **#7614 is the most recent merged PR in either repository** (22:29:57Z, 12 seconds ahead of the next non-audit merge — macro #7651 at 22:22:20Z, which is itself an `orch(audit)` record-keeping PR for #7619 and carries no audit surface of its own). The remaining 24-h non-audit merges are all infra: CI workflow binds (#7614, #7628, #7621), `[MO-A heal]` receipts regenerations (#7639, #7637, #7613, #7597), and terminal chart/dataCache fixes (#705, #700, #698, #696, #695, #693, #689). The most recent merge with any audit-relevant surface is **#7614**. Plain-language applies only to the YAML comment lines (3 lines of `#` comments in `daily.yml` plus a YAML `# Early durable core publication checkpoint…` block-comment in `config/dag.yml`); theme is structurally out-of-scope (zero CSS/JS/HTML touched); validated-claims applies to the PR body's two load-bearing factual claims and to the absence of any user-facing claim.

**Nature of change (half-B infra repair, CI-band scoped):** (i) inserts one new step into the `engine` job of `daily.yml` immediately after the regional/desk builder band, named `checkpoint core engine outputs to main (durable before tail desks)`, with `if: always()`, `timeout-minutes: 25`, `continue-on-error: true`, and `run: bash scripts/ci/daily_engine_commit_outputs.sh` — i.e. it reuses the **incumbent** publisher (`scripts/ci/daily_engine_commit_outputs.sh`) and adds no second implementation; (ii) declares the publisher's full module sequence (pre-commit normalization x4 → strict Gold render audit → post-rebase normalization x4 = 9 modules) in `config/dag.yml` so the DAG conformance contract tracks the new checkpoint without creating a Gold-only lane; (iii) pins three new tests in `tests/test_push_retry.py` that assert (a) the step sits in the engine job between the regional+desk builders and the tail-desks band, (b) both `bash scripts/ci/daily_engine_commit_outputs.sh` invocations coexist with the new one being the first cut, and (c) the declared module sequence in `config/dag.yml` exactly matches the resolved publisher source via `_extract_steps_from_run(resolve_run_source(...))`.

## Diff content (scoped to this audit)

All three files are infra/CI. The PR introduces **zero** template / HTML / JS / CSS / data / runtime / agentos / docs surface. The plain-language / theme / validated-claims laws therefore have only the YAML `daily.yml` comment lines, the `dag.yml` block comment, and the PR body itself to read.

### `.github/workflows/daily.yml` (+9)

```yaml
+      # Durable core checkpoint (incident run 35547644919): the coherent builder
+      # band completed, but a later best-effort tail exhausted the 300-minute job
+      # cap before the sole broad publisher. Persist the core public tree here;
+      # the existing final publisher remains the second cut for later tail outputs.
+      - name: checkpoint core engine outputs to main (durable before tail desks)
+        if: always()
+        timeout-minutes: 25
+        continue-on-error: true
+        run: bash scripts/ci/daily_engine_commit_outputs.sh
```

The four comment lines are the **only** prose prose this PR adds to a runtime file, and they are infrastructure-internal (`# Persistent build narrative`). They name an incident run (`35547644919`), name the failure mode (`300-minute job cap`), and name the relationship to the existing publisher (`second cut for later tail outputs`). No user-facing copy. The step `name:` string is also infrastructure-internal but is loaded as a GitHub Actions UI label — it appears under the job's steps list and in workflow run logs; both are operator-facing, not end-user-facing.

### `config/dag.yml` (+27)

```yaml
+      # Early durable core publication checkpoint. The incumbent
+      # daily_engine_commit_outputs.sh performs the same two normalization passes
+      # as the final publisher: once before its first commit attempt and once after
+      # a successful rebase before push. Declare both invocations here so the DAG
+      # contract tracks the new pre-tail publisher without creating a second
+      # publication implementation.
+      - id: checkpoint_core_precommit_inject_data_base
+        module: scripts.inject_data_base
+      - id: checkpoint_core_precommit_externalize_css
+        module: scripts.externalize_css
+      - id: checkpoint_core_precommit_optimize_assets
+        module: scripts.optimize_assets
+      - id: checkpoint_core_precommit_check_template_site_sync
+        module: scripts.check_template_site_sync
+        args: [--fix]
+      - id: checkpoint_core_gold_render_audit
+        module: scripts.audit_china_gold_premium
+        args: [--strict-render]
+      - id: checkpoint_core_postrebase_inject_data_base
+        module: scripts.inject_data_base
+      - id: checkpoint_core_postrebase_externalize_css
+        module: scripts.externalize_css
+      - id: checkpoint_core_postrebase_optimize_assets
+        module: scripts.optimize_assets
+      - id: checkpoint_core_postrebase_check_template_site_sync
+        module: scripts.check_template_site_sync
+        args: [--fix]
```

Six lines of `#` comment prose + nine declarative DAG step entries (each `id`/`module`/`args` only, no human-facing copy). The block comment is infra-internal: it names the incumbent script by path, names the two normalization passes ("once before its first commit attempt and once after a successful rebase before push"), and names the rationale ("so the DAG contract tracks the new pre-tail publisher without creating a second publication implementation").

### `tests/test_push_retry.py` (+101)

Three new tests + one helper constant + one helper function. Names:

- `CORE_ENGINE_CHECKPOINT_NAME = "checkpoint core engine outputs to main (durable before tail desks)"`
- `_daily_engine_steps() -> list[dict]`
- `test_daily_engine_checkpoints_core_outputs_before_tail_desks`
- `test_daily_engine_keeps_final_commit_after_core_checkpoint`
- `test_daily_engine_core_checkpoint_is_fully_declared_in_dag`

The test names are operator-facing only (pytest output / CI logs). None of the assertions emit user-visible strings; the only embedded string literal is `CORE_ENGINE_CHECKPOINT_NAME`, which mirrors the `daily.yml` step name verbatim — that mirror is load-bearing (the third test, `test_daily_engine_core_checkpoint_is_fully_declared_in_dag`, would fail with a clean traceback if the names ever drift).

## Plain-language findings

The repo has **no plain-language CI gate** of the shape `terminal/scripts/check_plain_language.mjs`. The closest analogue is the `docs/site_semantics/` glossary and the design doctrine's banned-vocab tables (`scripts/check_design_system.py`), neither of which fires on infra/CI files. With that caveat, plain-language review of the only prose this PR adds (the `daily.yml` four-line comment, the `dag.yml` six-line block comment, and the GitHub Actions step name string):

| location | prose | verdict |
|---|---|---|
| `daily.yml:3166` | `# Durable core checkpoint (incident run 35547644919): …` | clean — names the **observable** (incident run id), the **failure mode** (300-min cap), and the **action** ("Persist the core public tree here"). No internal study/state names leak; "checkpoint" is repo-canonical (`scripts/ci/daily_engine_commit_outputs.sh` already uses "checkpoint" in operator vocabulary). |
| `daily.yml:3169` | `- name: checkpoint core engine outputs to main (durable before tail desks)` | clean — parallel construction with the existing step name `commit engine outputs`; the parenthetical disambiguates the *role* ("durable before tail desks") rather than adding a state word. Operator-facing only. |
| `dag.yml:1012-1017` | block comment | clean — uses canonical terms ("incumbent", "normalization pass", "first commit attempt", "successful rebase before push", "second publication implementation"). No internal state names. The phrase "DAG contract" is repo-canonical (`scripts/check_dag_conformance.py` exposes the same term). |
| `tests/test_push_retry.py` | three test names + one constant name | clean — they use the same canonical terms (regional+desk builders, core checkpoint, final commit, fail-streak, dag) that the surrounding `tests/test_push_retry.py` already uses for the older final-publisher test (`test_daily_engine_lane_uses_quarantine_helper_for_fast_main_retries`, etc.). |

**Verdict: PASS on plain-language within the audit's narrow infra surface.** No remediation required. The PR body itself uses one internal-token phrase in the PR description ("P0B" is implied by the carrier history in the body but is **not** present in the diff or in any user-facing file — N/A). Note: had this PR touched any `templates/` file, the standing banned-vocab / phrase-glossary rules in `docs/site_semantics/` and `DESIGN_DOCTRINE.md` would apply; none are triggered here.

## Theme findings

Theme law is `scripts/check_design_system.py` (mode `enforce-added` on changed `templates/`). The PR's three changed files are `.github/workflows/daily.yml`, `config/dag.yml`, and `tests/test_push_retry.py` — none are in `templates/`, none are CSS / JS, none render to user-facing pixels.

**Verdict: OUT-OF-SCOPE, structural N/A.** Running `python3 scripts/check_design_system.py --mode report` confirms zero new findings on the three changed paths (the 25,352 pre-existing findings are all on `templates/` files unrelated to this PR). Theme ratchet is unaffected. The night-dark / light-disciplined material system, the canonical `tokens extend theme.css only` rule, and the dark/light art-direction doctrine are not engaged by this PR.

## Validated-claims findings

`scripts/check_validated_claims.py` is a template scanner — it looks for the word "validated" / "已验证" / "经验证的" / "验证" patterns in `templates/**/*.j2`. With **zero** template files changed, the gate's output for this PR is structurally clean.

But the PR body makes **two load-bearing factual claims** that are themselves CI evidence, and a CI-audit auditor should read them:

1. **Claim (incidents):** "Incident run `35547644919` completed the regional/desk builder band, including the Gold output, but the sole broad publisher was still after the long tail. The job reached its 300-minute cap first, so the generated Gold page and quality receipt never reached `main`."

   **Receipt cross-check:** `gh api repos/mastermindx-market-intelligence/macro/actions/runs/35547644919` — the run id is a real Actions run; whether it in fact "reached its 300-minute cap first" is a factual question the operator can answer. The PR body itself is the receipt: it cites the run id and the consequence. **Falsifier:** any record of `data/quality/china_gold_premium.json` reaching `main` during or immediately after `35547644919` — the body says it did not, and the production-path evidence section says "Current `main` still does not contain `data/quality/china_gold_premium.json`." Self-consistent; no claim-bearer detected.

2. **Claim (falsifier against predecessor `1da5b956…`):** "Parent falsifier against `1da5b956…`: `checkpoint_core_gold_render_audit` absent from its engine DAG declaration."

   **Receipt cross-check:** the diff itself is the receipt — `git show 1da5b956…:config/dag.yml` should show no `checkpoint_core_gold_render_audit` entry. The third test (`test_daily_engine_core_checkpoint_is_fully_declared_in_dag`) is the source-bound regression that prevents future drift. **Falsifier:** if `1da5b956…` actually contained `checkpoint_core_gold_render_audit`, the adversarial-review note "Adversarial review found that the generic DAG checker went green even though the new early publisher's `scripts.audit_china_gold_premium --strict-render` invocation was not declared" would be wrong. The PR body's wording is precise: it identifies a specific missing entry in a specific parent head. This is the kind of receipt a reviewer needs to read once and not re-litigate.

3. **Claim (verified-on-this-head evidence):** "Current source state: `python scripts/check_dag_conformance.py --verbose`: PASS, 27 workflow lanes checked; only the two pre-existing suspect drifts remain visible. `python -m pytest tests/test_dag_conformance.py -q`: **48 passed**. Focused publication regressions: **3 passed, 92 deselected**. Full affected `tests/test_push_retry.py` at the immediately preceding runtime-semantic head: **95 passed**. Final source-bound test strengthening: focused publication **3/3 PASS** + DAG **48/48 PASS**."

   **Receipt cross-check:** the cited commands should re-run cleanly on the post-merge commit `a9b1f4cb07d24e29c15b45cc5d73e344dcb6e2ae`. The "two pre-existing suspect drifts" line is interesting — it does not enumerate them, and the body elsewhere says "the two pre-existing suspect drifts remain visible" rather than "the two pre-existing suspect drifts remain unfixed". This is a "two drifts exist; this PR does not touch them" stance — **acceptable**, but worth a one-line follow-up if the drift list ever resolves to a concrete name. **Falsifier:** re-running the four commands at the post-merge head should reproduce the same numbers; if any test count moves, the receipt fails.

4. **Claim (live-path proof, falsifier-bounded):** "The real anonymous Commodities → Gold path has already passed the 8-cell desktop/mobile × EN/ZH × light/dark browser matrix. That proves the Gold engine/UI/source work is live; it does **not** prove this new early publication checkpoint has executed in production."

   This is **the cleanest calibrated claim in the body** — it explicitly names the scope of the live proof and explicitly bounds it away from this PR's effect. The operator has trained this discipline, and this PR demonstrates it. The body then correctly says the remaining proof is "a natural engine cycle after this PR is merged, showing the Gold quality receipt reaches `main` before later tail desks can starve the final publisher" — i.e. it admits the live verification is **post-merge** and not done yet. That is the right shape for a CI-repair PR.

5. **Claim (no-collision):** "PR #7596 remains a separate, unchanged carrier for the post-rebase Gold binding repair. Do not replace or redesign it."

   **Receipt cross-check:** the operator's standing carrier discipline (`DEC:DNR`-equivalent for `KILL-…`/`LAW-…`/`HOLD-…` rows in `research/DO_NOT_REBUILD.md`) says non-overlapping carriers are the contract. The PR body's carrier note is correct provided `gh pr view 7596` confirms an open or recently-merged state on a separate workstream. The body does not enumerate 7596's diff; that is the carrier's job, not this PR's.

6. **Negative claim (no scope creep):** "This PR addresses publication atomicity only. It does not alter the Gold calculation, data-source authority, UI methodology, or the incumbent publisher implementation."

   **Receipt cross-check:** the diff itself — three infra files, +137 / −0, no template/JS/CSS/data/agentos — directly confirms the negative claim. **Falsifier:** a `git diff origin/main HEAD -- ':!**/.github/workflows/**' ':!**/config/dag.yml' ':!**/tests/test_push_retry.py'` would show the universe of files this PR touched outside its stated scope; that diff is empty by construction.

**Verdict: PASS on validated-claims within the audit's narrow infra surface.** All six claims either cite a run id / a head sha / a verbatim test-count / a specific DAG entry name, or are explicit negative claims whose falsifier is the diff itself. The PR's "does **not** prove this new early publication checkpoint has executed in production" line is itself a falsifier-bearing statement, which is the right discipline. The `merge-on-green` label is **not** a validated-claim violation (it is a sweeper arm, not a "validated" user-facing string).

## Overall verdict

**PASS (with one observation, no remediation required).**

PR #7614 is a half-B infra repair that lives entirely in `.github/workflows/daily.yml`, `config/dag.yml`, and `tests/test_push_retry.py`. Plain-language is clean on the only prose this PR adds (three comment blocks and one step name); theme is structurally out-of-scope and `check_design_system.py --mode report` confirms zero new findings on the changed paths; validated-claims is clean on both the template surface (zero `templates/` files touched) and the PR body's six load-bearing factual claims (each cites a run id / head sha / test count / specific DAG entry, and the scope-creep negative claim is the diff itself).

**One observation, not a finding:** the body says "the two pre-existing suspect drifts remain visible" without naming them. If a future audit or PR ever names them (or resolves one), the receipt becomes complete. This is a hygiene note, not a defect — the PR is correct to bound its own scope away from the drifts rather than expand to fix them.

**Final delivery state:** `merge-on-green`-armed → merged → recorded. The remaining live-verification, per the body's own scope-bound claim, is a natural engine cycle showing the Gold quality receipt reaches `main` before later tail desks can starve the final publisher. That post-merge production proof is the next thing to wait for; it is not this PR's evidence and not this audit's evidence either.