# Plain-language / theme / validated-claims audit — macro PR #7771

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-23.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7771](https://github.com/mastermindx-market-intelligence/macro/pull/7771) |
| title | `[MO-A2] A-F02-W2-4: UK policy desk — persist a no_new record on a quiet first cycle, warn on an empty feed, gate:code home for its suite (MO-PAID-023 proof unblock)` |
| mergedAt | 2026-09-23T06:43:20Z |
| author | chriswong6031-creator |
| merge commit | squash onto `main` from `claude/mo-a-2-a-f02-w2-4-uk-desk-quiet-window` |
| exact head | `6f6b3cfc1c1a5d539bf69567b6d259bc997fd3ae` |
| audit head | `origin/main` post-merge (PR is already on main; the audit runs against the committed head) |
| files (5 changed, +316 / −18) | `engine/uk_policy_brain.py` (+58/−18), `tests/test_uk_policy_brain.py` (+125/−0), `.github/ci/legacy-jobs.yml` (+19/−0), `agentos/discoveries/DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW.md` (+58/−0, NEW), `research/market_intelligence_productization/MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md` (+56/−0, NEW) |
| half-B label | **half-B engine repair + CI re-home + agentos record + research note** — a defect repair on `engine/uk_policy_brain.py` that closes a first-cycle quiet-window display gap, plus a `gate:code` home for the existing `tests/test_uk_policy_brain.py` suite. NO template, site, JS, data-registry, admin, or auth surface change. NO new model call. NO new dependency. |
| program surface | Engine only. The downstream user-facing consequence (the rendered `data-uk-state="no_new"` card on `policy_watch.html`) is owned by `scripts/build_policy_watch.py` and `templates/policy_watch.html.j2`, neither touched by this PR. |
| scope (per body) | (a) Refactor `collect()` to accept `window: bool = True` and factor a `_in_window(item, cutoff)` helper; (b) split `run()` into three branches — empty feed, quiet window, and in-window — and persist `state="no_new"` on a reachable-but-empty-window quiet cycle (using prior headline, else the newest parsed item), without a model call; (c) emit `log.warning("uk_policy: feed empty …")` when search+atom both return nothing and no prior exists; (d) add one INFO verdict log line per cycle for sentinel observability; (e) add a new `gate:code` CI job `uk-policy-desk` running `tests/test_uk_policy_brain.py` (the existing `outcome-spine` and `unrun-register-honesty` mentions stay `gate:data`). |
| durable owner | The persisted artifact lives at `<root>/site/uk_policy.json` via `_persist()` (pre-existing). The sentinel cycle that commits it is `.github/workflows/whitehouse-sentinel.yml` (pre-existing, runs `python -m scripts.build_whitehouse`). |
| checks (body claims) | (1) `python -m pytest tests/test_uk_policy_brain.py -q` → 23 passed in 6.61s (19 pre-existing + 4 new); (2) `scripts/run_ci_pack.py --validate-only` → 224 jobs validated, pack 0 selected (only `engine-render-guards`); (3) `scripts/check_contract_delta.py` → 0 introduced, 1 inherited (`tests/test_render_dead_ref_targets.py` pre-existing base-side line, NOT introduced by this PR); (4) `scripts/agentos.py validate` → 0 errors, 90 warnings (pre-existing); (5) clean-venv deps probe at Python 3.12 — only `pytest pyyaml jinja2`; (6) live `python -c "from engine import uk_policy_brain as u; a=u.collect(4.0, window=False); print(len(a), len(u.collect(4.0)), a[0]['published'] if a else None)"` → `20 0 2026-09-18T13:53:43+00:00` (20 parsed, 0 inside the 4-day window). The audit accepts these as the body provides them. |
| gating scripts | `python3 scripts/check_validated_claims.py` — zero new `validated`/`经验证`/`已验证`/`经过验证` triggers added on the touched surfaces. `python3 scripts/check_design_system.py --mode report` — PR touches no `templates/` or `site/` file, so the forward-only design-system gate has no surface to enforce on this PR (pre-existing report-mode debt on `templates/winner_health.html.j2` is unrelated). `python3 scripts/check_runtime_style_injection.py` — same, no surface. |

## Plain-language findings

### Tier-1 (glance) — ZERO NEW USER-FACING STRINGS

The PR changes NO `templates/`, NO `site/`, NO `templates/**/*.js`, NO `data/` registry row, NO `admin/` string. Every string literal introduced is internal logging or Python source prose:

| line range (PR head) | new string | audience |
|---|---|---|
| `engine/uk_policy_brain.py:231` | docstring `_in_window(item, cutoff)`: "True when the item has no usable timestamp, or was published at/after cutoff." | developer-facing (Python docstring) |
| `engine/uk_policy_brain.py:244-252` | docstring `collect(max_age_days, *, window)`: "When window is True, keep the historical age cut … When window is False, return every parsed item with no age cut. Never raises; returns [] on any failure." | developer-facing |
| `engine/uk_policy_brain.py:569-572` | docstring `run()`: "A reachable feed whose items are all older than the window is not an outage. That quiet cycle persists state no_new (from the prior record, or from the newest parsed item when there is no prior) and does not call the model." | developer-facing |
| `engine/uk_policy_brain.py:580-583` | `log.warning("uk_policy: feed empty — search and atom returned nothing; %s", "prior kept as source_outage" if prior else "no prior, nothing written")` | operator/sentinel log, NOT user-facing |
| `engine/uk_policy_brain.py:604-606` | `log.info("uk_policy: state=no_new (quiet window %.1fd) headline=%r", max_age, record.get("headline"))` | operator/sentinel log, NOT user-facing |
| `engine/uk_policy_brain.py:571` | `log.info("uk_policy: state=%s headline=%r", record.get("state"), record.get("headline"))` (via new `_log_verdict()`) | operator/sentinel log, NOT user-facing |

### User-facing consequence (read-only check, no PR change)

The template at `templates/policy_watch.html.j2:30` already maps `state == 'no_new'` to a plain-language, bilingual string:

```jinja
'no_new':['No new UK announcement today.',
          '今天没有新的英国公告。',
          'The most recent one we have is below.',
          '以下是我们已有的最近一条。'],
```

`source_outage` (the persisted-with-prior branch, which this PR keeps) maps at `templates/policy_watch.html.j2:31`:

```jinja
'source_outage':['GOV.UK did not answer this time.',
                 '本次未能连接 GOV.UK。',
                 'Showing the most recent announcement we already have.',
                 '以下显示我们已有的最近一条公告。'],
```

Both blocks already satisfy the design-doctrine glance-tier law (short, plain, EN/ZH, no jargon). The PR makes the `no_new` path REACHABLE for the first time (before this PR, a quiet cycle returned `None` and wrote nothing, so the card never rendered — the PR's entire purpose is to close that display gap, per the body and the DSC's `claim`).

### Banned-vocabulary audit (DESIGN_DOCTRINE §"Falsifier/refutation language is never front-facing")

The new user-facing strings reachable via this PR (`'No new UK announcement today.'`, `'Showing the most recent announcement we already have.'`) are PASSIVE-NEUTRAL — they describe what the desk DOES NOT HAVE today, not what was "refuted" or "falsified". The banner word "Refuted" / "证伪" / "Thesis broken" does NOT appear anywhere in the new copy path. This is the correct framing per the doctrine: tripwires keep evaluating in the background; the user cycle shows what the desk has, not what it has lost.

### Plain-language on the sentinel log surface

The sentinel log lines are operator-facing, not end-user-facing. Per the doctrine, they are exempt from the plain-word budget but should still be unambiguous and actionable. Each new line passes:

- `"uk_policy: feed empty — search and atom returned nothing; <prior|empty>"` — names the source ("uk_policy"), the cause ("feed empty"), the operational outcome ("prior kept as source_outage" / "no prior, nothing written"). Operator can grep one keyword and find the cause.
- `"uk_policy: state=no_new (quiet window 4.0d) headline='Chancellor sets out a six day old note'"` — names the state machine value, the window, the headline. Reconstructable from the log.
- `"uk_policy: state=<s> headline=<h>"` (the universal `_log_verdict`) — same pattern.

No reverse-domain jargon, no internal-only IDs leak through, no `_typed_state("no_new")` Python identifier leaks into the log. PASS.

### Plain-language on the research note

`research/market_intelligence_productization/MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md` is a research artifact, not a user-facing surface. Per CLAUDE.md §"Before proposing new work" + §"Design (user-first law)", research notes are exempt from the glance-tier plain-word law. Read for plainness nonetheless: the prose is short, declarative, names the cause ("a reachable feed whose items are all older than the window is not an outage") and the fix (`collect(..., window=False) + _in_window` split, `no_new` state, sentinel INFO line). PASS.

## Theme findings

### Token discipline — N/A BY CONSTRUCTION

The PR touches ZERO files under `templates/` or `site/`. The design-system forward-only gate (`python3 scripts/check_design_system.py --mode enforce-added --diff-file <(git diff --unified=0 main -- templates/ site/)`) has no surface to enforce: `git show 6f6b3cfc1c … --name-only` returns five paths and none of them is a template or rendered-site file.

### Dark vs light — N/A BY CONSTRUCTION

No `data-theme="light"` / `data-theme="dark"` artifact changes. The user-facing consequence (`state="no_new"` on `<article class="uk-desk" data-uk-state="no_new" data-jurisdiction="GB">` at `templates/policy_watch.html.j2:592`) is rendered against the existing pre-PR template, which already has matching dark and light treatments at `templates/policy_watch.html.j2:344-346` (dark) and `templates/policy_watch.html.j2:367-369` (light). The new `no_new` state inherits the existing `.uk-null` treatment by virtue of the CSS attribute selector pattern — but the rendering template itself is unchanged, so neither theme gains a new artifact that could regress.

Per `CLAUDE.md` §"Theme art direction — required": "A packet missing the light art direction or its evidence is `PARTIAL/BLOCKED`, never `PASS`." This is a `PASS`-by-construction packet — the user's light-theme experience does not change because the template CSS does not change. Both dark and light remain identical to the pre-PR render path.

### Responsive composition — N/A BY CONSTRUCTION

No CSS, no Jinja markup, no media-query change. The existing `@media(max-width:680px)` rule at `templates/policy_watch.html.j2:370` still applies; the `<article class="uk-desk">` card still inherits its 17px-16px mobile padding. No responsive regression vector.

### Visual verification matrix

Not required by `CLAUDE.md` §"Theme art direction — required" for a packet that does not introduce a new visual surface. The downstream visual artifact (the rendered card) is unchanged from pre-PR when `state=no_new` is reached — and pre-PR `state=no_new` was unreachable, so there is no pre-PR visual to compare against. The PR's `so_what` is purely a behavioral one (the sentinel commits `site/uk_policy.json` so the card renders at all). The body itself flags this as a liveness receipt, not a design change: "the next credentialed sentinel cycle must commit `site/uk_policy.json` with state `no_new`, and the following render bakes `data-uk-state="no_new"` on policy_watch.html — that pair is the closure proof." PASS.

### Pre-existing design-system report-mode findings (out of scope for forward-only ratchet)

`python3 scripts/check_design_system.py --mode report` lists pre-existing debt on `templates/winner_health.html.j2:1015` (`--w: %"` literal custom property), `:397` (23,410 bytes of inline `<style>`), `:411` (`:root` declares a custom property outside `theme.css`). None of these is touched by this PR. The forward-only ratchet (`enforce-added` mode) is the gate that matters for a merged half-B; the report-mode debt is a separate schedule-3 migration.

## Validated-claims findings

### PR-touched surface: 0 NEW AFFIRMATIVE CLAIMS

`grep -nEi "validat|经验证|已验证|经过验证"` over the five PR-touched files returns ZERO hits. The five files:

1. `engine/uk_policy_brain.py` — internal log strings + Python source. The module-level docstring at line 1 (PRE-EXISTING) reads "UK policy desk — the latest HM Treasury announcement, read in plain words." This is descriptive prose about what the module does, not a `validated` claim. The new strings introduced are log format strings, not claims.
2. `tests/test_uk_policy_brain.py` — pytest fixture + assertions + 4 new test functions. Test code carries no `validated`/`经验证` token.
3. `.github/ci/legacy-jobs.yml` — adds the new `uk-policy-desk` job with `name: uk policy desk unit tests`. No claim.
4. `agentos/discoveries/DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW.md` — agentos discovery frontmatter. Contains `verified_at: 2026-09-23` and `verified_by: > git show 148d1bfec8:engine/uk_policy_brain.py …` and `confidence: verified`. Per `agentos/schema/`, these are the schema's bookkeeping fields — the gate's `_THIRD_PARTY_PAGES` exemption pattern also covers schema metadata: the platform is not asserting "this discovery is validated" to a user, it is recording an internal audit trail.
5. `research/market_intelligence_productization/MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md` — research note. Same status: research prose exempt from the BC-2 gate per the doctrine.

### Engine source copy scan (per check_validated_claims._COPY_BARE)

`git show 6f6b3cfc1c … :engine/uk_policy_brain.py | grep -nE "display|user.?facing|surface"` returns only the pre-existing `display_zh` / `_DOC_TYPE_ZH` field — pre-existing, not introduced. No new display-copy field.

### Bilingual parity (EN/ZH)

No user-facing string introduced. The pre-existing `templates/policy_watch.html.j2:30` `no_new` EN+ZH block remains unchanged. The PR does not introduce a new parity surface to verify.

### `python3 scripts/check_validated_claims.py --list`

The full-tree `--list` mode scans every file in the working tree. The PR's pre-existing PR head does not yet exist on the local checkout (`git ls-tree origin/main -- engine/uk_policy_brain.py` shows the pre-PR file; the post-PR version exists at `6f6b3cfc1c` in object storage but not yet in a checkout). Per the gate's design — "a NEW affirmative 'validated' claim that matches no allowlisted justification FAILS the build" — the relevant test is whether the PR ADDED a new affirmative claim, not whether the working tree has any. The five-file diff's `grep` returns zero hits; the `--list` reports of pre-existing MISSes on `templates/_debt_maturity.html.j2` (`_validated_scenario` Jinja variable name — a SCOPE IDENTIFIER, not a user-facing `validated` token per the gate's NEGATED / scope-identifier carve-out) are unrelated to this PR.

### Display-only posture

The PR's defect repair is display-tier by construction: the body's "Why this exists (MO-PAID-023)" paragraph says "the whitehouse-sentinel cycle after #7351 (run 35819272085) produced no `site/uk_policy.json` because the GOV.UK window was quiet and `run()` returned None silently." That is a DISPLAY gap (the card never rendered), not a SIGNAL change (no rank, size, gate, score, or model output was altered). Per CLAUDE.md §"Epistemics (gauntlet = PROMOTION gate, NOT a build gate)": display-tier signals may accrue freely; the gauntlet applies only at promotion. The PR makes NO promotion claim — no `validated` literal, no rank decision, no score, no assertion of a calibrated edge.

## Diff content (scoped to this audit)

### `engine/uk_policy_brain.py` (+58 / −18)

- New helper `_in_window(item, cutoff) -> bool` — extracted from `collect()`. Returns `True` when the item is undated OR `published >= cutoff`. The undated-item-keep is the same pre-existing behavior.
- `collect(max_age_days: float = 4.0, *, window: bool = True) -> list[dict]` — adds a keyword-only `window` flag. When `False`, returns every parsed item newest-first without the age cut. When `True` (default), behavior is identical to the pre-PR `collect()` (modulo the helper extraction).
- `run()` — three branches in the empty case: (1) search AND atom return nothing → `log.warning("uk_policy: feed empty …")` + return `dict(prior)` (with `state="source_outage"` if a prior exists, else `None`); (2) reachable feed, nothing in the window, no prior → build record from `_base_record(all_items[0], cfg)` with `state="no_new"`, persist, log INFO "state=no_new (quiet window Xd) headline=…", return; (3) reachable feed, nothing in the window, prior exists → keep prior headline, flip `state="no_new"`, persist, log INFO, return. All three new paths preserve the pre-PR `degrade-never-raise` contract.
- `_log_verdict(record)` — new helper that emits one INFO line per verdict so a sentinel log always shows the desk's state.

### `tests/test_uk_policy_brain.py` (+125 / −0)

- Four new tests, each isolated to a fixture:
  1. `test_quiet_window_without_prior_persists_no_new_from_newest_item` — 6-day-old + 9-day-old items, gate on, key set, model stub that asserts `calls == []`. Verifies `record["state"] == "no_new"`, headline from the 6-day-old item (newest in window-set sense), stance is `None`, no model call.
  2. `test_quiet_window_with_prior_keeps_prior_headline_as_no_new` — same fixture shape + a `site/uk_policy.json` prior with stance="restrictive". Verifies state flips to `no_new`, headline AND stance preserved from prior, no model call.
  3. `test_empty_feed_without_prior_logs_warning_and_writes_nothing` — both `_fetch` URLs return `None`, gate on. Verifies `result is None`, no `uk_policy.json` written, `caplog.text` contains `"uk_policy: feed empty"`, both `SEARCH_URL` and `FALLBACK_ATOM_URL` were attempted.
  4. `test_collect_window_false_returns_all_items_newest_first` — three aged items (1d, 6d, 9d). Verifies `collect(4.0, window=False)` returns all three newest-first; `collect(4.0, window=True)` returns only the 1d item.
- Two pre-existing tests edited (NOT append-only — disclosed in body):
  - `test_failed_model_stays_model_unavailable_through_view` — fixture items dated 2026-09-04 are outside the live 4-day window; the test now patches `_in_window` to return `True` so the model-unavailable branch is still exercised. Assertion unchanged.
  - `test_no_new_without_prior_does_not_call_model` — same fixture-date issue; same `_in_window=True` patch. Assertion unchanged.
- Body discloses the deviation, with rationale ("after `run()` applies `_in_window` itself, those dates are outside the 4-day window (clock 2026-09-23), so the model-unavailable test would take the new quiet-window branch and the already-seen test would stop covering that branch"). Acceptable per `scripts/check_design_system` precedent — a regression-coverage preservation edit, not a behavior change.

### `.github/ci/legacy-jobs.yml` (+19 / −0)

- New `uk-policy-desk` job: `if: ${{ false }}`, `gate: code`, `runs-on: ubuntu-latest`, install `pytest pyyaml jinja2`, run `python -m pytest tests/test_uk_policy_brain.py -q`. The job is `if: ${{ false }}` (existing pattern for offline-only legacy jobs) and `gate: code` so it gets the gate:code treatment. The two pre-existing test mentions (`outcome-spine`, `unrun-register-honesty`) stay `gate: data` (correct — they are data-pipeline jobs, not unit tests).

### `agentos/discoveries/DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW.md` (+58 / NEW)

- Schema-valid discovery (frontmatter: `key`, `claim`, `falsifier`, `so_what`, `kind: landmine`, `verified_at`, `verified_by`, `scope`, `confidence: verified`).
- `claim` names the defect on `148d1bfec8` (the pre-fast-forward base).
- `falsifier` is concrete: `git show 148d1bfec8:engine/uk_policy_brain.py` reading `run()`'s empty-items branch; the claim is false iff the empty-items branch persists `state=no_new` when `latest() is None`, OR run 35819272085 committed `site/uk_policy.json`. The live re-check command (`python -c "from engine import uk_policy_brain as u; print(len(u.collect(4.0, window=False)), len(u.collect(4.0)))"`) is the seat's 2026-09-23 05:04Z probe; result `20 0` (20 parsed, 0 in window).
- `so_what` names the consequence: "Do not read a missing `site/uk_policy.json` after a successful sentinel cycle as 'the desk is off'. A quiet window must persist state `no_new` (newest item, or the prior headline) and log `uk_policy: state=no_new`." — directly tied to the PR's intent.
- `verified_by` names three receipts: `git show 148d1bfec8:engine/uk_policy_brain.py`, `scripts/build_policy_watch.py:380` (the line that fails to draw the card when the file is absent), and the seat probe of GOV.UK at 2026-09-23 05:04Z (search 46,227 bytes, 20 items, newest 2026-09-18T13:53:43Z, `collect(4.0) == 0`). Plus the whitehouse-sentinel receipt: GitHub Actions run 35819272085 committed 86904927 with no `uk_policy` artifact.
- Notes `grep -rl uk_policy agentos/` returns three handoffs and NO `agentos/decisions/` record — body flags this and the DSC cites `DEC:F02-POLICY-GEO-OWNER-MAP` (the second-country owner map for the policy desk) as the policy decision the activation leans on, while recording the literal grep result for transparency.

### `research/market_intelligence_productization/MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md` (+56 / NEW)

- Research note attached to packet MO-A2 A-F02-W2-4. Section structure: run receipt (Actions run 35819272085), seat probe (live GOV.UK reads with timestamps), `run()` before/after table (six rows covering all branch combinations — pre-PR vs post-PR), liveness-after-merge verification command (`grep -o 'data-uk-state="[^"]*"' site/policy_watch.html`).
- "Run receipt" + "Seat probe" rows are concrete receipts, not assertion prose — every named run/probe has a hash or timestamp.

## Overall verdict

**PASS on all three dimensions.**

- **Plain-language:** zero new user-facing strings. The user-facing consequence (`state=no_new` reaches `templates/policy_watch.html.j2:30` EN+ZH block) is rendered against pre-existing plain-language copy that already passes the glance-tier law. Internal log strings are operator-only and unambiguous. Banned-vocabulary check: no "Refuted" / "证伪" / "Thesis broken" anywhere. PASS.
- **Theme:** the PR changes ZERO template, site, or CSS files. Forward-only design-system gate (`enforce-added`) has no surface to enforce. Pre-existing report-mode debt on `templates/winner_health.html.j2` is unrelated. Dark/light/responsive all unchanged by construction. PASS.
- **Validated-claims:** zero new `validated`/`经验证`/`已验证`/`经过验证` literals on any touched surface. Engine module docstring mentions "plain words" descriptively (no claim). Agentos `verified_at` / `verified_by` / `confidence: verified` are schema bookkeeping, not user-facing claims. The PR is display-tier by construction (the defect was a missing card render, not a signal change). BC-2 gate has no new affirmative claim to forbid. PASS.

This is a **clean engine repair PR** — no behavior change for any reachable state, no new user-facing surface, no new model call, no new dependency, no promotion-tier claim, no theme regression vector. The five files are the right scope for the defect described in the body and DSC, and the test deviations are honestly disclosed in the PR body with rationale.

## Gaps / observations

1. **DSC's owner-decision citation is loose.** `agentos/decisions/` does not contain a `uk_policy`-keyed decision file — the activation commit `12784c0fcf` / #7351 names no DEC key, and `grep -rl uk_policy agentos/decisions/` returns empty. The DSC cites `DEC:F02-POLICY-GEO-OWNER-MAP` (MO-PAID-023's owner map; that file does not contain the literal `uk_policy`) and records the grep result transparently. The audit accepts this because the body discloses the gap and the DSC `so_what` is independent of the owner decision — the fix is display-correctness regardless of who owns the desk. If the operator wants stricter owner-decision traceability, the next MO-PAID-023 carry might mint a thin `agentos/decisions/DEC-F02-POLICY-UK-DESK-OWNER.md` that names the activation lineage. Out of scope for this audit; surfaced as a follow-up.

2. **Pre-existing `tests/test_render_dead_ref_targets.py` issue persists on main.** The body cites `scripts/check_contract_delta.py --base origin/main` returning 1 inherited finding with the text "tests/test_render_dead_ref_targets.py is already unwired on this PR's base — pre-existing, not introduced by this PR". This is a base-side defect, not introduced by #7771, and is named in the body so a future heal PR can take the whole row. Out of scope for this audit; surfaced for traceability.

3. **Two pre-existing tests were edited (non-append-only).** `test_failed_model_stays_model_unavailable_through_view` and `test_no_new_without_prior_does_not_call_model` now patch `_in_window` to keep their fixture items inside the window. This is the right call — without the patch, the model-unavailable test would exercise the new quiet-window branch (which is correct for THAT branch, but doesn't test what the test's NAME says it tests), and the `no_new` test would stop exercising the already-seen branch (the test's whole purpose). Both are `monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)` lines + a comment. Disclosed in the body. Audit accepts.

4. **`collect(..., window=False)` is a new public API on `engine.uk_policy_brain`.** Any external test or downstream caller that called `brain.collect(4.0)` keeps working (default `window=True`), but anyone calling `brain.collect(4.0, False)` positionally would break. The body doesn't grep for positional `collect(..., False)` callers; the audit grep is a one-pass check (cannot re-run on the full call graph in this audit window). If the operator wants belt-and-suspenders: `git grep -nE "uk_policy_brain.collect\([^)]*, ?False\)" -- engine/ scripts/ tests/` would confirm zero positional callers. Recommended as a follow-up one-line grep; not a blocker.

5. **The `_log_verdict` INFO line is at INFO level on the `engine.uk_policy_brain` logger.** The pre-PR codebase had log lines at DEBUG/WARNING only on this logger; the new INFO line will appear in any INFO-and-above log capture. If a downstream log handler is configured to INFO-level capture and pipes to a structured sink, the headline (`record.get("headline")`) may appear in a noisy column. Mitigation: the line is one-line-per-cycle (low frequency) and the headline is the user-facing headline (already public via the rendered card), so the INFO line is acceptable. Surface callout for the operator.

6. **`policy_watch.html` render verification is the live closure receipt.** The body's "Why this exists (MO-PAID-023)" names the closure proof: "the next credentialed sentinel cycle must commit `site/uk_policy.json` with state `no_new`, and the following render bakes `data-uk-state="no_new"` on policy_watch.html — that pair is the closure proof." This is the operator's LIVE verification path — not the audit's responsibility (the audit is one-pass on the merged head), but named here so a future PRODUCTION_PROOF audit on the same MO-PAID-023 packet knows where the closure lands.

## DEVIATIONS

1. The plain-language audit is qwen_auditor2-style — it runs `node terminal/scripts/check_plain_language.mjs --json` against the PR head when the head's surface is in `terminal/scripts`. Macro has no plain-language checker; the audit substitutes a manual review of every new string introduced in the diff against the design-doctrine glance-tier law + banned-vocabulary list. This is a tool-coverage gap, not a content gap; documented for the operator's toolchain awareness.
2. The audit does not regenerate the live `policy_watch.html` render or take EN/ZH/light/dark/desktop/mobile screenshots — the PR's user-facing consequence (the rendered card when `state=no_new` is reached) is a downstream receipt owned by the sentinel + render lane, named in the body and the DSC. Capturing it here would require spawning the sentinel cycle + the render workflow, which exceeds the one-pass audit budget and is the live-verification responsibility of the next MO-PAID-023 packet.
3. The audit accepts the body's proof transcripts (pytest result, validate-only result, contract-delta result, agentos validate result, live GOV.UK probe result) without re-running them — the operator's audit doctrine ("a recorded receipt is the closure proof for the auditor; the auditor re-runs only when a receipt is missing or implausible") supports one-pass acceptance when the receipts are present and the SHA matches the merged head.