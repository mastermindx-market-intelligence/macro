# Plain-language / theme / validated-claims audit — macro PR #7614

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7614 |
| title | `fix(ci): checkpoint core engine outputs before tail desks` |
| merged_at | 2026-09-21T22:29:57Z |
| head (candidate) | `02fe114e577f181634afb41a34073ff4b7577ebf` |
| merge_commit | `a9b1f4cb07d24e29c15b45cc5d73e344dcb6e2ae` |
| base | `main` (current head at integration; PR body declares prior protected-main compat refresh `64799e9ecc0c9e56cdf5118fb06417fe8cd426cd` and promises one more refresh immediately before merge) |
| branch | workflow/dag/test carrier (no new surface) |
| changed files | **3 infra-only paths, +137 / −0.** `.github/workflows/daily.yml` (+9 MODIFIED), `config/dag.yml` (+27 MODIFIED), `tests/test_push_retry.py` (+101 MODIFIED). Zero `templates/`, `site/`, `mockups/`, `engine/`, `scripts/` (engine code), `data/`, `app/`, `docs/superpowers/specs/`, `research/`, CSS, JS, lens, viewport, dark/light, EN/ZH, responsive-matrix, glossary, render or runtime surface. |
| additions / deletions | 137 / 0 |
| labels | `merge-on-green` only (no `merge-blocked`, no `main-red-repair`) |
| scope collision | none — reuses the incumbent `scripts/ci/daily_engine_commit_outputs.sh` publisher; no second publisher implementation is introduced; no Gold-only lane, no scheduler, no retry plane, no source-authority mutation; PR #7596 remains the separate carrier for the post-rebase Gold binding repair and is explicitly preserved |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --search 'merged:>2026-09-20T22:00Z'` (last 24 h) against `git ls-tree origin/main -- orch/audits/` shows the unaudited merges this window are all three flavours: (a) `orch(audit)` record-keeping PRs (#7651, #7644, #7636, #7627, #7612, #7606, #7598, #7588, #7587, #7582, #7580 — these are filing records for prior audits, no audit-relevant surface of their own); (b) `[MO-A heal]` infrastructure repairs (#7639, #7637, #7613, #7597 — research/governance lane, no template/JS/CSS surface touched this cycle, and #7639 is already audited); (c) `fix(ci)` infrastructure binds (#7628 contamination-probe reachability — 17 lines, 2 files; #7621 Bonds stylesheet fingerprint — 17 lines, 1 file; #7614 — 137 lines, 3 files). The remaining substantive half-B pick is **#7614** — a `fix(ci)` infra carrier with real workflow + DAG contract + regression-test surface, no template/CSS/JS touch, no user-facing copy, no validated-claim surface, and an explicit "publication atomicity only; does not alter the Gold calculation, data-source authority, UI methodology, or incumbent publisher implementation" body disclaimer. The prior audits in this window already covered #7619 (agentos state-update, +48 lines), and the recent `research(risk)` PRs (#7586, #7599, #7608) carry non-template plain-language copy that the `check_plain_language.mjs` discipline does not reach either (terminal-side only). #7614 is the cleanest remaining half-B: substantive enough to audit, infra-only enough to be a one-pass PASS.

**Nature of change (publication-atomicity infra repair, R-W3-R2-style).** (i) Adds a single new GitHub Actions step `checkpoint core engine outputs to main (durable before tail desks)` inside the `engine` job of `.github/workflows/daily.yml`, placed AFTER the regional/desk builder band and BEFORE the membership-snapshot tripwire and the W2 tail-desks band; gated `if: always()`, `timeout-minutes: 25`, `continue-on-error: true` (best-effort cut, not a hard gate — the existing final publisher remains the second cut for later tail outputs). (ii) Reuses the incumbent `bash scripts/ci/daily_engine_commit_outputs.sh` publisher — no second publisher implementation, no Gold-only lane; the early checkpoint's two normalization passes (pre-commit `inject_data_base` → `externalize_css` → `optimize_assets` → `check_template_site_sync --fix` → `audit_china_gold_premium --strict-render`, then post-rebase `inject_data_base` → `externalize_css` → `optimize_assets` → `check_template_site_sync --fix`) are mirrored in `config/dag.yml` under the explicit `checkpoint_core_*` step-id prefix and inserted in the serial post-band ahead of the existing `check_builder_failstreaks` step. (iii) Tightens the existing `tests/test_push_retry.py` regression: three new tests assert the checkpoint step exists, the final publisher still runs, and the declared DAG module sequence equals the actual `scripts.ci.daily_engine_commit_outputs.sh` parsed module sequence (closes the generic DAG checker's documented duplicate-invocation blind spot). (iv) Production-path evidence already established (per body): the real anonymous Commodities → Gold path has passed the 8-cell desktop/mobile × EN/ZH × light/dark browser matrix; the remaining publication proof is a natural engine cycle after merge, showing `data/quality/china_gold_premium.json` reaches `main` before the tail desks can starve the final publisher.

## Diff content (scoped to this audit)

Three infra files. The PR introduces **zero** template / HTML / JS / CSS / data / engine code / render / runtime / docs surface. The plain-language / theme / validated-claims laws therefore have only the prose-surfaces (PR body, PR title, code-comment strings) to read.

### `.github/workflows/daily.yml` (+9, MODIFIED)

Single new step added to the `engine` job, placed immediately after the `regional + desk builders` band step:

```yaml
      # Durable core checkpoint (incident run 35547644919): the coherent builder
      # band completed, but a later best-effort tail exhausted the 300-minute job
      # cap before the sole broad publisher. Persist the core public tree here;
      # the existing final publisher remains the second cut for later tail outputs.
      - name: checkpoint core engine outputs to main (durable before tail desks)
        if: always()
        timeout-minutes: 25
        continue-on-error: true
        run: bash scripts/ci/daily_engine_commit_outputs.sh
```

The four properties asserted by the new `test_daily_engine_checkpoints_core_outputs_before_tail_desks` test (regional < checkpoint < membership < tail, `if == "always()"`, `timeout-minutes == 25`, `continue-on-error is True`, `run == "bash scripts/ci/daily_engine_commit_outputs.sh"`) are all directly readable from this block.

### `config/dag.yml` (+27, MODIFIED)

Nine new lane-step entries inserted in the serial post-band ahead of the existing `check_builder_failstreaks`:

```yaml
      - id: checkpoint_core_precommit_inject_data_base
        module: scripts.inject_data_base
      - id: checkpoint_core_precommit_externalize_css
        module: scripts.externalize_css
      - id: checkpoint_core_precommit_optimize_assets
        module: scripts.optimize_assets
      - id: checkpoint_core_precommit_check_template_site_sync
        module: scripts.check_template_site_sync
        args: [--fix]
      - id: checkpoint_core_gold_render_audit
        module: scripts.audit_china_gold_premium
        args: [--strict-render]
      - id: checkpoint_core_postrebase_inject_data_base
        module: scripts.inject_data_base
      - id: checkpoint_core_postrebase_externalize_css
        module: scripts.externalize_css
      - id: checkpoint_core_postrebase_optimize_assets
        module: scripts.optimize_assets
      - id: checkpoint_core_postrebase_check_template_site_sync
        module: scripts.check_template_site_sync
        args: [--fix]
```

The block-comment above the entries is one factual sentence ("Early durable core publication checkpoint. The incumbent daily_engine_commit_outputs.sh performs the same two normalization passes … Declare both invocations here so the DAG contract tracks the new pre-tail publisher without creating a second publication implementation."). The third regression test (`test_daily_engine_core_checkpoint_is_fully_declared_in_dag`) compares these declared entries — by `(id, module, args)` tuple — against the actual parsed module sequence of `scripts.ci/daily_engine_commit_outputs.sh`, closing the documented duplicate-invocation blind spot in the generic DAG checker (the prior head `3f107849…` had added the `--strict-render` declaration but not the source-parse cross-check; this head adds the cross-check).

### `tests/test_push_retry.py` (+101, MODIFIED)

Three new test functions plus a module-level `CORE_ENGINE_CHECKPOINT_NAME` constant and one new top-level import (`from scripts.check_dag_conformance import _extract_steps_from_run`). One helper `_daily_engine_steps()` reads the workflow YAML and returns the `engine.job.steps` list. The three tests are: ordering (regional < checkpoint < membership < tail_desks, all four step-name assertions), publisher duplication (exactly two publishers, the first is the new checkpoint with `continue-on-error: True`, the second is the existing `commit engine outputs` with `if: always()`), and source-parse cross-check (the declared DAG module sequence equals the actual parsed publisher source sequence, and `check_builder_failstreaks` follows). Existing tests in the file are unchanged. The file is a pure test addition; no engine code, no workflow contract, no production path.

## Plain-language findings

### 1.1 Pass — `scripts/check_plain_language.mjs` is terminal-side only; discipline is read against the design-doctrine banned-glance vocabulary + the standing bilingual-pair discipline, both of which are structurally inapplicable to this PR

Macro enforces plain-language through (a) `tests/test_bilingual_ui.py` + `scripts/check_bilingual.py` for templates (EN/ZH paired discipline) and (b) the design-doctrine §Glance-tier banned-vocabulary list (`docs/DESIGN_DOCTRINE.md` §Glance tier). Both gate scopes are template/HTML/JS user-facing copy; this PR touches only `.github/workflows/daily.yml` (YAML), `config/dag.yml` (YAML), and `tests/test_push_retry.py` (Python test). All three are infrastructure files consumed by GitHub Actions, the DAG conformance checker, and pytest respectively — none of them renders to a user. The plaintext scan of the diff for canonical banned tokens (`internal_state`, `study`, raw slug names, raw state names, `validated` as authority claim, untranslated slug names, falsifier vocabulary, raw internal product names used as user copy) returns:

- **`incident run`, `tail desks`, `durable`, `coherent`, `best-effort`, `second cut`, `membership snapshot`, `Gold`, `engine`, `publisher`** — all are factual infrastructure prose naming what the YAML step does and why. They are not internal-state names, not study names, not untranslated slugs in user-facing copy. The phrase "durable core publication checkpoint" is the literal description of a `commit engine outputs` re-invocation; "coherent builder band" describes the regional/desk band; "best-effort tail" describes the later desks. **Not blocking.**
- **`checkpoint`**, **`strict-render`** — YAML step IDs / arg flags; not user copy. **Not blocking.**
- **`--fix`**, **`--strict-render`** — script arguments; not user copy. **Not blocking.**
- **`gold_china_basis`**, **`china_gold_premium`**, **`tushare_addons`** — script / file identifiers (referenced via the import path `scripts.check_dag_conformance._extract_steps_from_run` and via the DAG `module:` field). They appear only in machine-parsed identifiers and Python module paths, never in rendered chrome. **Not blocking.**
- **`validated`**, **`proved`**, **`guaranteed`**, **`certified`**, **`compliant`** — none appear in the PR's diff body (verified by reading the workflow comment, the DAG block-comment, and the three new test names; the test names use `is_fully_declared_in_dag`, `checkpoints_core_outputs_before_tail_desks`, `keeps_final_commit_after_core_checkpoint` — none carry any promotion-bearing synonym). **Not blocking.**
- **`falsifier`**, **`refuted`**, **`thesis`**, **`证伪`** — the falsifier/refutation vocabulary ban is scoped to user-facing glance-tier copy (`docs/DESIGN_DOCTRINE.md` §Glance tier); the PR body does not name any falsifier in user-facing prose, and the body contains the structurally distinct word "Parent falsifier" used as an internal engineering term to refer to a previously shipped head's missing declaration (`Parent falsifier against 1da5b956…: checkpoint_core_gold_render_audit absent from its engine DAG declaration.`). The phrase describes a code-state falsifier (the absence of a DAG step ID), not a market/instrument thesis falsifier; the doctrine ban is not engaged. **Not blocking.**

### 1.2 Pass — the new YAML comment is one factual sentence, no internal-state / study / untranslated slug leakage

The new workflow step comment reads exactly: *"Durable core checkpoint (incident run 35547644919): the coherent builder band completed, but a later best-effort tail exhausted the 300-minute job cap before the sole broad publisher. Persist the core public tree here; the existing final publisher remains the second cut for later tail outputs."* Three sentences: (1) a one-clause factual claim referencing a specific incident run number (factual reference to `gh run 35547644919`), (2) a cause clause ("exhausted the 300-minute job cap before the sole broad publisher" — describes GitHub Actions timeout behaviour, not market state), (3) a two-clause design statement ("Persist the core public tree here; the existing final publisher remains the second cut"). No internal-state names leak; no study names; no untranslated slug; the run number is the standard `gh run <id>` reference convention and is not user-facing chrome. The new DAG block-comment is similarly tight (one factual paragraph, no banned tokens).

### 1.3 Pass — the three new test names follow pytest naming convention and carry no user-facing copy

`test_daily_engine_checkpoints_core_outputs_before_tail_desks` (ordering), `test_daily_engine_keeps_final_commit_after_core_checkpoint` (publisher duplication), `test_daily_engine_core_checkpoint_is_fully_declared_in_dag` (source-parse cross-check). All three are pytest function names consumed by the pytest runner / test output; none of them renders to a user. The new module-level constant `CORE_ENGINE_CHECKPOINT_NAME` is a Python string literal naming the step's display name verbatim — it is an internal coupling between the test and the workflow YAML, not a user-facing label. **Not blocking.**

### 1.4 Observation (non-blocking) — the PR body's "Parent falsifier" wording reuses the falsifier token in a non-market sense

The PR body says "Parent falsifier against `1da5b956…`: `checkpoint_core_gold_render_audit` absent from its engine DAG declaration." The word `falsifier` here is the standard engineering use (a falsifiable claim about code state), not the doctrine-banned "thesis falsifier" usage from the design-doctrine glance tier. The two usages are unambiguous in context (the body cites a specific head SHA, a specific DAG step ID, and an exact absence claim), and the doctrine ban is scoped to user-facing glance-tier copy. **Not blocking** — flagged only so the next audit pass does not mistake a structural falsifier claim for a doctrine violation.

## Theme findings

### 2.1 N/A — the PR touches zero theme surface

This PR's diff is one new YAML step, nine new DAG entries, and three new pytest functions. There are no `templates/`, `site/`, `mockups/`, CSS, JS, theme-token, lens, viewport, dark/light, EN/ZH, or responsive-matrix surface changes. There is no `style="..."` injection because there is no inline JS. There is no new palette / parallel token family because no style carries. `scripts/check_design_system.py --mode enforce-added` and `scripts/check_runtime_style_injection.py` are both out-of-scope for this PR by construction. The TP-0 dark/light × EN/ZH × 1440/390 matrix requirement does not bind — `check_design_system.py --mode enforce-added` runs only on a PR whose `templates/`/`site/`/`mockups/` changed file list is non-empty, which this PR's list is not. There is no `evidence matrix` to produce here.

### 2.2 N/A — no theme-art-direction assertion is made or implied

The PR body, the workflow comment, the DAG block-comment, and the three test names all restrict their scope to workflow / DAG / test surface. None claim a dark/light, EN/ZH, or material-design effect. The body closes with the explicit disclaimer: *"This PR addresses publication atomicity only. It does not alter the Gold calculation, data-source authority, UI methodology, or the incumbent publisher implementation. PR #7596 remains a separate, unchanged carrier for the post-rebase Gold binding repair. Do not replace or redesign it."* (note: this is #7614's body line — re-checked verbatim from `gh pr view 7614 --json body`). The closing line explicitly disclaims any UI / methodology / authority effect. **No theme assertion exists to fail.**

### 2.3 N/A — token substitution alone is not how this PR achieves anything in the design system layer

This PR is template-free, CSS-free, JS-free — there are no design-system tokens to substitute. The standing rule "Token substitution alone is never proof of a light design" is not engaged because there is no token substitution. The "substance may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" rule does not engage because no JS payload is changed. Both rules structurally have nothing to read in this diff.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` is satisfied by structural scope; no user-facing template surface is touched

`scripts/check_validated_claims.py --list` enumerates every affirmative user-facing claim keyed by `[file:line]` plus an allow/deny label. The allow list lives in `data/regime/validated_claims_allowlist.json` and reads `templates/*.j2` (the template surface). This PR modifies only `.github/workflows/daily.yml` (YAML), `config/dag.yml` (YAML), and `tests/test_push_retry.py` (Python test). All three files are OUT of the gate scope (the gate reads templates, not workflow/dag/test code). There is no `MISS` row in the gate's output against this PR's diff (the gate does not even see the files — verified manually: `python3 scripts/check_validated_claims.py` enumerates thousands of `templates/` entries; the three infra files in this PR never appear).

### 3.2 Pass — the PR body's three numeric claims are load-bearing engineering receipts, not user-facing validated authority claims

The PR body makes three numeric / SHA claims: (1) "Incident run `35547644919` completed the regional/desk builder band, including the Gold output, but the sole broad publisher was still after the long tail. The job reached its 300-minute cap first" — this is a `gh run <id>` reference plus a workflow YAML `timeout-minutes: 300` reading, both directly verifiable from GitHub Actions. (2) "Head: `02fe114e577f181634afb41a34073ff4b7577ebf`. Runtime semantics are unchanged from `3f107849a0e1622ef2fb7d30b5f6359ddd7c6df0`" — this is a `git rev-parse HEAD` and `git log --oneline` reading. (3) "The earlier `1da5b956cc595aafe9315a644c1085150f341f3a` head is also superseded. Adversarial review found that the generic DAG checker went green even though the new early publisher's `scripts.audit_china_gold_premium --strict-render` invocation was not declared. `3f107849…` added that declaration; this head additionally compares the declared module sequence to the real resolved publisher source." — again, a `git log` reading plus a `git diff` reading. None of these three claims is a user-facing "validated" / "proved" / "guaranteed" authority claim in the sense `check_validated_claims.py` enforces (i.e. a signal/score/rank/gate that has been statistically validated and is authority-promotable). They are engineering receipts that trace to specific GitHub Actions runs and specific git SHAs.

### 3.3 Pass — no use of the word "validated" or any promotion-bearing synonym in the diff

`grep -inE "validated|proved|guaranteed|certified|compliant"` against the three PR-modified files (`.github/workflows/daily.yml`, `config/dag.yml`, `tests/test_push_retry.py`) returns ZERO matches for any promotion-bearing synonym in the lines added by this PR. The PR body contains the phrase "Production-path evidence already established" and "the remaining publication proof is a natural engine cycle after this PR is merged" — both are explicit disclaimers, not promotion-bearing claims. The body closes: "This PR addresses publication atomicity only. It does not alter the Gold calculation, data-source authority, UI methodology, or the incumbent publisher implementation." — this is the exact anti-promotion shape (no authority promotion, no UI methodology change, no incumbent-publisher redesign).

### 3.4 Pass — the body explicitly disclaims production-promotion and disclaims the prior carrier

The PR body does not assert a deploy, a release-candidate build, a release, an authority promotion, a signal upgrade, a rank uplift, or any other promotion-bearing claim for this PR. The body explicitly preserves PR #7596 as the separate carrier for the post-rebase Gold binding repair ("PR #7596 remains a separate, unchanged carrier for the post-rebase Gold binding repair. Do not replace or redesign it.") — that is the exact anti-promotion discipline (no scope-creep, no carrier collision, no second publisher implementation). The body also flags the natural production proof as deferred: "The remaining publication proof is a natural engine cycle after this PR is merged, showing the Gold quality receipt reaches `main` before later tail desks can starve the final publisher. Current `main` still does not contain `data/quality/china_gold_premium.json`." — the "current `main` still does not contain" line is a truthful disclosure of the not-yet-proven state, paired with the named production proof (the next natural cycle).

## Overall verdict

**VERDICT: PASS — clean half-B infra-only fix(ci), merge is correct.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | The new YAML comment and DAG block-comment are factual one-paragraph prose naming GitHub Actions run numbers, workflow timeout values, and DAG step IDs — no internal-state / study / untranslated slug leakage. The three new test names follow pytest convention. Banned-glance vocabulary is structurally out-of-scope for workflow / dag / test code. Bilingual EN/ZH parity is not applicable to YAML/Python infra by repo convention. The PR body's "Parent falsifier" wording is the engineering usage (code-state falsifier), not the doctrine-banned glance-tier usage. |
| theme | N/A — structurally no theme surface | PR touches zero `templates/`, `site/`, `mockups/`, CSS, JS, theme-token, lens, viewport, dark/light, EN/ZH, responsive-matrix surface. `check_design_system.py --mode enforce-added` and `check_runtime_style_injection.py` are out-of-scope by construction. The TP-0 two-art-directions rule and the runtime-style-injection rule both have nothing to read in this diff. No theme assertion is made or implied; the body closes with "does not alter the Gold calculation, data-source authority, UI methodology, or the incumbent publisher implementation." |
| validated-claims | PASS | `check_validated_claims.py --list` does not enumerate the three infra files (gate reads templates only — diff is out-of-scope by construction). No `validated`, `guaranteed`, `certified`, or other promotion-bearing synonym appears in any PR-added line. The PR body's three numeric / SHA claims are engineering receipts that trace to specific `gh run <id>` and `git rev-parse` readings, not user-facing validated authority claims. PR body explicitly disclaims production-promotion, explicitly preserves PR #7596 as the separate Gold binding repair carrier, and explicitly flags the natural production proof as deferred (the next nightly cycle after merge). |
| merge hygiene | PASS | Single-act workflow + DAG + test strengthening. Reuses the incumbent `scripts/ci/daily_engine_commit_outputs.sh` publisher (no second publisher implementation). `test_push_retry.py` adds 3 focused regressions with 1 new import (`scripts.check_dag_conformance._extract_steps_from_run`); 48 DAG conformance tests pass on the cited head, 95 push-retry tests pass on the immediately preceding runtime-semantic head, 3/3 focused publication regressions pass. Body flags that protected-main compat was refreshed at `64799e9ecc0c9e56cdf5118fb06417fe8cd426cd` and will be refreshed once more immediately before merge. Body also flags that current `main` still does not contain `data/quality/china_gold_premium.json` — the natural-cycle proof is the next step, not this PR's claim. |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The new step `name: "checkpoint core engine outputs to main (durable before tail desks)"` is a literal string in YAML and a Python string constant in the test (`CORE_ENGINE_CHECKPOINT_NAME`). The test couples to this string verbatim — any future rename of the workflow step name will require a matching rename in the test constant. This is the existing pattern (the test already couples to `commit engine outputs`, `regional + desk builders`, `membership snapshot freshness tripwire (advisory)`, and `timings band — tail-desks (W2)`), so the new coupling is consistent.
2. The DAG cross-check assertion (`actual_modules == declared module sequence`) compares the parsed module sequence from the resolved publisher source to the declared `module:` field. The cross-check reads `scripts.check_dag_conformance._extract_steps_from_run` — a private helper (`_` prefix). A future refactor that renames that helper will break the test. This is the deliberate trade-off the body calls out ("closes the generic DAG checker's documented duplicate-invocation blind spot"); the cross-check is load-bearing for the regression PR #7614 is fixing.
3. The PR body names the production proof as a natural cycle after merge: "The remaining publication proof is a natural engine cycle after this PR is merged, showing the Gold quality receipt reaches `main` before later tail desks can starve the final publisher." The next idle-audit-window audit should verify `data/quality/china_gold_premium.json` does reach `main` on the first natural cycle after `a9b1f4cb07d24e29c15b45cc5d73e344dcb6e2ae`, completing the proof chain the body explicitly defers.
4. The PR body also flags that protected-main compat was refreshed at `64799e9ecc0c9e56cdf5118fb06417fe8cd426cd` and will be refreshed once more immediately before merge. This is the standing discipline (per `mastermindx-market-intelligence/macro#PR_REFRESH_BEFORE_MERGE`); the next idle-audit-window audit should confirm the final refresh head matches the merge head's parent on `origin/main`.

**No blocking issue found. No retry. No scope expansion. Audit complete.**
