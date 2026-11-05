# Plain-language / theme / validated-claims audit — macro PR #7771

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-23.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7771](https://github.com/mastermindx-market-intelligence/macro/pull/7771) |
| title | `[MO-A2] A-F02-W2-4: UK policy desk — persist a no_new record on a quiet first cycle, warn on an empty feed, gate:code home for its suite (MO-PAID-023 proof unblock)` |
| mergedAt | 2026-09-23T06:43:20Z |
| merge commit | per `gh pr view 7771` (squash onto `main` from `claude/mo-a-2-a-f02-w2-4-uk-desk-quiet-window`) |
| branch tip | `6f6b3cfc1c1a5d539bf69567b6d259bc997fd3ae` (per body) |
| audit head | `origin/main` post-merge, the PR's own base `ff4309ee6c6f4d8778b2358af82b2e6a9ce98b38` was a fast-forward of `148d1bfec8b` where the quiet-window defect was read; `engine/uk_policy_brain.py` is byte-identical between those two SHAs |
| files | **5 changed, 316 +, 18 −** (per `gh pr view 7771`). Engine: `engine/uk_policy_brain.py` (+58/−18). CI: `.github/ci/legacy-jobs.yml` (+19/0). Tests: `tests/test_uk_policy_brain.py` (+125/0). Records: `agentos/discoveries/DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW.md` (NEW, +58), `research/market_intelligence_productization/MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md` (NEW, +56). |
| half-B label | **A-F02-W2-4 (MO-A2 A-F02 Wave 2 task 4 — the quiet-window defect closure half).** A-F02-W2 is "UK policy desk adoption" (paired with the whitehouse desk); W2-1 / W2-2 / W2-3 already merged prior. W2-4 is the "first-cycle contract" half — backend behaviour that lets the display layer treat a quiet window as `no_new` instead of treating the card as off. PR is on the A (backend/operational) side of MO-A2, with one downstream UI consequence (a state value the template already supports). |
| user-facing surface | **None added.** Zero template diff, zero `site/**` diff, zero CSS, zero JS, zero new rendered HTML, zero new i18n keys, zero analyst copy. The only user-facing consequence is that the existing `data-uk-state="no_new"` chip on `templates/policy_watch.html.j2` will now be emitted by the sentinel cycle (the template copy is pre-existing and unchanged). |
| scope (per body) | (a) `run()` fetches once with `collect(max_age, window=False)` then keeps the in-window subset with `_in_window`; on a quiet window it persists `state: no_new` (prior headline, or newest parsed item when there is no prior) **without** calling the model. (b) An empty search-and-atom feed still writes nothing when there is no prior, and now logs a warning. (c) Every verdict logs one INFO line so the sentinel log shows the desk's state. (d) The suite's other homes (`outcome-spine`, `unrun-register-honesty`) stay `gate: data`. (e) A new `uk-policy-desk` job is `gate: code`. (f) Stays DRAFT until the Meta-CEO A seat ratifies; merge only by the seat at a RATIFIED head. |
| durable owner | `engine/uk_policy_brain.py::run / collect / _in_window / _log_verdict`; CI gate `.github/ci/legacy-jobs.yml::uk-policy-desk`; DSC `DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW`; research runbook `MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md`. |
| checks (body claims) | (1) `python -m pytest tests/test_uk_policy_brain.py -q` → `23 passed in 6.61s` (clean 3.12 venv, deps `pytest pyyaml jinja2` only). (2) `python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 0 --pack-count 12 --validate-only` → `Validated 224 legacy jobs; 224 in scope; pack weights=[…]`. (3) `python3 scripts/check_contract_delta.py --base origin/main` → 0 introduced, 1 inherited (base `ff4309ee6c6f`); `::notice title=contract-delta::tests/test_render_dead_ref_targets.py is already unwired on this PR's base — pre-existing`. (4) `python3 scripts/agentos.py validate` → `0 error(s), 90 warning(s)`. (5) Live probe `python -c "from engine import uk_policy_brain as u; a=u.collect(4.0, window=False); print(len(a), len(u.collect(4.0)), a[0]['published'] if a else None)"` → `20 0 2026-09-18T13:53:43+00:00`. (6) Suite-without-new-tests → `19 passed in 6.56s`; with → `23 passed in 6.61s`; `pip freeze` adds zero packages beyond the three. Body does not claim `gh pr checks` green — PR was opened DRAFT and ratified by the Meta-CEO A seat at the exact head. |
| gating scripts | `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7771.diff` → **PASS**, R0: 0 blocking finding(s) added by this PR (25,316 pre-existing non-blocking estate findings unchanged). `python3 scripts/check_validated_claims.py --list` → 0 hits anchored to PR-touched files (`engine/uk_policy_brain.py`, `tests/test_uk_policy_brain.py`, `.github/ci/legacy-jobs.yml`, the DSC, the runbook). The 65 total MISS claims on the audit head land on `templates/_debt_maturity.html.j2`, `templates/_macro_suite_shell.html.j2`, `templates/canada.html.j2`, `templates/hk.html.j2`, `templates/macro_*.html.j2` etc., none touched by this PR. |

## Plain-language findings (tier-1 + tier-2 surface)

### Tier-1 (glance) — N/A scope, no new user-facing strings

This PR adds zero user-facing UI text. The full diff is engine Python + CI YAML + pytest + DSC + research runbook. The only new strings are operator-facing (Actions step name, INFO/WARNING log lines, code comments, test docstrings). The plain-language law (DESIGN_DOCTRINE §"rewrite, don't delete", operator 2026-07-27 §3821 banned vocabulary, no machine slugs in user-visible positions, no translated text in `title=` attributes) has no surface to bind against in this PR — no glance tier is created here.

### Downstream UI consequence — `data-uk-state="no_new"` already rendered

The PR's only user-visible effect is that the next whitehouse-sentinel cycle will write `site/uk_policy.json` with `state: no_new` while the window stays quiet, and the next Policy Watch render will bake `data-uk-state="no_new"` on the existing `.uk-desk` article. The matching copy is **already** in the template (pre-existing, not introduced by this PR):

| file:line | string |
|---|---|
| `templates/policy_watch.html.j2:30` | `'no_new': ['No new UK announcement today.', '今天没有新的英国公告。', 'The most recent one we have is below.', '以下是我们已有的最近一条。']` |
| `templates/_policy_watch_current.html.j2:9` | `'no_new': ('No new official items', '暂无新官方条目')` |

Compliance with the plain-language law: **PASS.** "No new UK announcement today" is plain English, state-bearing, and the second sentence ("The most recent one we have is below.") handles the no-prior scenario with "below" — a glance-tier spatial cue, not a slug or an internal name. The Chinese pair is a literal translation that mirrors English semantics; neither line uses banned vocabulary. Per the design doctrine, the chip serves the "Glance tier = state + plain-word stance under hard word budgets" rule: state (`no_new`) is the data attribute, stance ("No new UK announcement today") is the headline, with no internal-state-name leakage. Per Law 5 (null disclosure) the card now answers the user's honest question — "is the desk on?" — with "yes, and it has nothing new", which is precisely the law's compliant null form.

### Operator-facing strings added (informational, not subject to plain-language law)

| location | string | audience | compliance |
|---|---|---|---|
| `engine/uk_policy_brain.py` (3 verdict points) | `uk_policy: state=%s headline=%r` (INFO log) | operator log / sentinel log | plain English, no banned vocab; uses `%r` for headline repr so multi-byte chars round-trip safely |
| `engine/uk_policy_brain.py` (quiet-window branch) | `uk_policy: state=no_new (quiet window %.1fd) headline=%r` (INFO log) | operator log | plain, named-key format (`state=`, `headline=`), no banned vocab |
| `engine/uk_policy_brain.py` (empty-feed branch) | `uk_policy: feed empty — search and atom returned nothing; %s` (WARNING log) | operator log | plain English, distinguishes "prior kept as source_outage" vs "no prior, nothing written"; no banned vocab |
| `tests/test_uk_policy_brain.py` (4 new tests) | `_aged_result("Chancellor sets out a six day old note", 6, …)` etc. | pytest reader | fixture titles are deliberately aged by N days so the test reads as a quiet-window scenario; no banned vocab |
| `.github/ci/legacy-jobs.yml::uk-policy-desk` | step name `uk policy desk unit tests` | Actions UI | plain English, no slug in title position |
| `agentos/discoveries/DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW.md` (NEW) | full document | agentos / fleet | YAML frontmatter `claim:` / `falsifier:` / `kind:` / `verified_at:` / `verified_by:`; prose body. See "Banned-vocabulary scan" below. |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md` (NEW) | full runbook | research | prose runbook; no banned vocab |

### Banned-vocabulary scan

`grep -inE 'falsif|refut|证伪|thesis|disproven|validated|guarantee|certified|proven' /tmp/pr7771.diff` → **1 hit, all operator/records surface:**

```
agentos/discoveries/DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW.md:9
+ falsifier: >
```

The single hit is a **YAML frontmatter key** in the DSC schema (`agentos/decisions/` and `agentos/discoveries/` use a `claim:` / `falsifier:` / `kind:` schema enforced by `python3 scripts/agentos.py validate`, body-claimed exit 0). It is **not** user-facing copy — it is the operator-side receipt for how to test the claim against future evidence. Per doctrine §"Falsifier/refutation language is never front-facing" (operator 2026-07-27, #3821) the rule scopes to *user cycle surfaces* (policy_watch.html, calibration, the chat surface), **not** to internal records where the falsifier is the audit trail. The DSC's `claim:` is also operator copy, not user copy. No `证伪` / `thesis` / `refuted` / `disproven` literals anywhere. **PASS.**

### No translated text in `title=` attributes (CI-guarded)

`grep -nE 'title="[^"]*"' /tmp/pr7771.diff` → **0 hits.** The only `title=` substrings in the diff are:
- `falsifier: >` (YAML frontmatter key, not HTML)
- `verified_by: >` (YAML frontmatter key)
- `verified_at: 2026-09-23` (YAML scalar)
- no `title="…"` HTML attribute anywhere

The bilingual-no-translation-in-title rule has no surface here. **PASS.**

### No machine slugs in user-visible positions

The slug `uk_policy` (a Python module + a `data/uk_policy/` directory name + a `site/uk_policy.json` filename) appears in:
- operator INFO/WARNING log lines (`uk_policy: state=…`, `uk_policy: feed empty`)
- pytest module path (`tests/test_uk_policy_brain.py`) and helper names (`_fetch_search`)
- CI job key (`uk-policy-desk`) and step name (`uk policy desk unit tests`)
- DSC and runbook headings
- GitHub Actions run reference `35819272085` (operator-side, in the DSC's `verified_by:`)

None of these are user-visible UI positions. The slug appears in **log lines, filenames, and operator-facing YAML** — exactly where slugs are the canonical identifier, never in user cycle surfaces. The Policy Watch article rendered to a logged-in user shows the state attribute (`data-uk-state="no_new"`) and the headline copy; the slug never appears. **PASS.**

### No raw JSON field names in user cycle surfaces

The DSC and runbook reference `state`, `headline`, `stance`, `source_url`, `public_timestamp`, `site/uk_policy.json`, `data-uk-state="…"`, `data-uk-jurisdiction="GB"`, `ledger_asof`-style references. None of these enter a user cycle surface in this PR — the template copy at `templates/policy_watch.html.j2:30` does not echo any of them; it uses the human-written strings already enumerated above. **PASS.**

## Theme findings

### N/A scope — no template, CSS, or site asset touched

`git diff ff4309ee6c6f4d8778b2358af82b2e6a9ce98b38..6f6b3cfc1c1a5d539bf69567b6d259bc997fd3ae -- templates/ site/ '*.css' '*.js'` → **empty.** The PR touches zero templates, zero `site/**` HTML files, zero CSS files, zero JS files. There is no user-facing visual surface to evaluate against the design-system ratchet in this PR. The downstream effect is that the *existing* Policy Watch `.uk-desk[data-uk-state="no_new"]` styling (which already exists in `templates/policy_watch.html.j2`) will now actually be emitted by the sentinel cycle, but the styling itself is unchanged.

### Design-system enforce-added — PASS

`python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7771.diff` → `R0 enforce-added: 0 blocking finding(s) (25316 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)`. The 25,316 pre-existing estate findings are the same set carried by every audit at this audit head (consistency with `orch/audits/macro_PR-7743.mm.md`, `macro_PR-7763.mm.md`, and the rest of the 2026-09-23 series, all recording `0 blocking`).

### Dark / light art-direction audit

N/A — no template or CSS touched.

### Responsive composition

N/A — no template or CSS touched.

### Visual verification matrix

N/A — no user-facing artifacts in this PR. The body does not claim a visual matrix because there is no visual surface introduced; the only visual artefact is the pre-existing `.uk-desk[data-uk-state="no_new"]` chip in `templates/policy_watch.html.j2`, which already carries its own dark/light treatments via `var(--warn)` and `var(--panel2)`.

### Runtime style injection — N/A

`scripts/check_runtime_style_injection.py` is gated on `engine/uk_policy_brain.py`-driven paths; this PR adds no multi-kilobyte `style.textContent`, no parallel palette/token family, no duplicated light/dark branch inside a page/composer JS. The new `_log_verdict` is a 4-line INFO log helper. **PASS.**

## Validated-claims findings

### PR-touched surface: 0 UNEARNED anchored

`python3 scripts/check_validated_claims.py --list` searched for `validated` substrings in PR-touched paths:

- `engine/uk_policy_brain.py` — no `validated` literals in the new 76 LOC. The added `collect(..., *, window=True)` docstring uses "the recent window" / "every parsed item" / "no age cut" — descriptive, not assertive. The `_in_window` docstring uses "True when the item has no usable timestamp, or was published at/after cutoff" — descriptive. The `run()` docstring extends with "A reachable feed whose items are all older than the window is not an outage" — descriptive of behaviour, not a `validated` claim. The new INFO/WARNING log lines use `state=`, `headline=`, `quiet window %.1fd`, `feed empty` — none are `validated`/`certified`/`guaranteed`/`proven` claims.
- `tests/test_uk_policy_brain.py` — the four new tests assert on `state == "no_new"`, `headline == …`, `calls == []`, `not (tmp_path / "site" / "uk_policy.json").exists()`, `"uk_policy: feed empty" in caplog.text`. They are functional assertions, not `validated` literals. Test docstrings ("Fixture dates are outside the live 4-day window. collect() is replaced wholesale…") are descriptive.
- `.github/ci/legacy-jobs.yml::uk-policy-desk` — step names are plain English. The job comment is descriptive ("A-F02-W2-4. tests/test_uk_policy_brain.py otherwise lives only on outcome-spine and unrun-register-honesty, both gate: data, so a PR pack never runs it. This is the gate: code home."). No `validated` literal.
- `agentos/discoveries/DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW.md` — the DSC frontmatter uses `verified_at:` / `verified_by:` keys (handoff-schema metadata, the schema `scripts/agentos.py validate` enforces). These are **handoff-schema metadata fields**, not user-facing copy. The script `scripts/check_validated_claims.py` does not parse YAML frontmatter from handoff / discovery docs — it scans `templates/` and `site/` for `validated` substrings in user-visible positions. The DSC's `verified_at: 2026-09-23` and `verified_by:` are operator receipts (the body claims `git show 148d1bfec8:engine/uk_policy_brain.py` … `GitHub Actions run 35819272085 … grep -rl uk_policy agentos/ … Seat probe of GOV.UK at 2026-09-23 05:04Z`), not UI claims.
- `research/market_intelligence_productization/MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md` — the runbook describes the operator-side install + first-run smoke. The "Run receipt" section cites GitHub Actions run `35819272085` (commit `86904927`, no `site/uk_policy.json`, no `data/uk_policy/`, no `uk_policy` log line) and the seat probe at `2026-09-23 05:04Z` (search 46,227 bytes, 20 items, newest `2026-09-18T13:53:43Z`, `collect(4.0) == 0`). No `validated` literal in the diff.

`grep -nE 'engine/uk_policy_brain|tests/test_uk_policy_brain|legacy-jobs|uk-policy-desk|UK-DESK-FIRST-CYCLE|F02_W2_4_UK_DESK_QUIET' (matched against `python3 scripts/check_validated_claims.py --list` output)` → **0 hits.** The 65 MISS hits on the audit head land on `templates/_debt_maturity.html.j2`, `templates/_macro_suite_shell.html.j2`, `templates/canada.html.j2`, `templates/hk.html.j2`, `templates/macro_*.html.j2`, and a small handful of `site/macro_*.html` files — none touched by this PR.

### Estate pre-existing: 65 UNEARNED on `origin/main`, zero PR-caused

The 65 MISS count on the audit head matches the pre-existing estate prior to A-F02-W2-4 — the `templates/_debt_maturity.html.j2` MISS claims are pre-existing `_validated_scenario` references in capital-structure debt-maturity copy, completely unrelated to the UK policy desk. Pattern matches `orch/audits/macro_PR-7743.mm.md`, `macro_PR-7763.mm.md`, `macro_PR-7770.mm.md` exactly (zero PR-touched, all estate).

### DSC `verified:` / `verified_at:` / `verified_by:` semantics

The DSC and the runbook use the standard agentos discovery schema (`scripts/agentos.py validate` enforces it; body-claimed exit 0). The schema is fail-closed: every `verified_by:` row is a named command + result pair. The schema is non-additive for the plain-language / theme / validated-claims law because the YAML fields are operator records, not user-visible. **PASS.**

### PR-touched surface scan (negative)

`grep -nE 'validated|guarantee|certified|proven' /tmp/pr7771.diff` → **0 hits.** `grep -nE 'site/uk_policy\.json|data-uk-state' /tmp/pr7771.diff` → 4 hits, all operator/research prose ("returns None and writes nothing", "no `site/uk_policy.json`, no `data/uk_policy/`", etc.). **PASS.**

## Overall verdict

**PASS — clean half-B PR, no user-facing copy introduced, all existing user-facing strings already comply.**

| axis | result |
|---|---|
| plain-language (tier-1 + tier-2) | **PASS.** Zero new user-facing strings. The downstream `data-uk-state="no_new"` chip already renders the pre-existing, plain-language copy ("No new UK announcement today." / "今天没有新的英国公告。" + "The most recent one we have is below." / "以下是我们已有的最近一条。"). No banned vocab, no translated text in `title=`, no machine slugs in user-visible positions. |
| theme / dark+light art direction | **PASS (N/A scope).** Zero template, CSS, JS, or `site/**` changes. The downstream `.uk-desk[data-uk-state="no_new"]` styling already exists and is unchanged. `check_design_system.py --mode enforce-added` → 0 blocking. |
| validated claims | **PASS.** Zero `validated`/`guaranteed`/`certified`/`proven` literals added in PR-touched paths. The DSC's YAML frontmatter `falsifier:` / `verified_at:` / `verified_by:` keys are handoff-schema metadata (operator receipts), not user-facing copy. Estate has 65 pre-existing MISS claims on the audit head; zero PR-caused. |
| design-system enforce-added | **PASS.** R0: 0 blocking finding(s). |
| runtime style injection | **PASS (N/A).** No multi-kilobyte `style.textContent`, no parallel palette/token family, no duplicated light/dark JS branch. |

**One non-blocking observation** (informational, not a defect): the new `uk_policy: state=%s headline=%r` INFO log line echoes the verbatim headline (which can include a quoted GOV.UK title with arbitrary characters). The `%r` repr means the log captures it exactly, which is the correct operational behaviour for an audit trail, but a future PR that surfaces the headline to a glance-tier chip must keep using the existing `t(…)` translation pair rather than the raw repr — the template already does this correctly via `templates/policy_watch.html.j2:30`. Recorded for traceability; no action needed for this PR.

**State: PASS, no follow-ups required for the audit scope.** The PR is the "latter half" of A-F02-W2 — it closes the display gap identified in `DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW` by ensuring the sentinel cycle persists a typed state the template already renders, so the Policy Watch card never disappears on a quiet window. The liveness receipt is named in the body (the next whitehouse-sentinel cycle must commit `site/uk_policy.json` with `state: no_new`; the next render bakes `data-uk-state="no_new"`); the audit scope is the merge, not the liveness receipt.

---

## Diff content (scoped to this audit)

### `engine/uk_policy_brain.py` (+58/−18)

- New helper `_in_window(item, cutoff)` — extracted from the old inline `cutoff`/`fresh` filter so `run()` can call `collect(..., window=False)` and filter in-window separately.
- `collect(max_age_days, *, window=True)` — new keyword arg; `window=False` returns every parsed item newest-first; `window=True` keeps today's age cut.
- `run()` — three new branches added: (a) empty-feed branch logs WARNING, keeps prior as `source_outage` or writes nothing; (b) quiet-window branch persists `state: no_new` from prior or newest item, no model call, INFO log; (c) every other verdict path also gets a one-line INFO verdict via `_log_verdict`.
- `_log_verdict(record)` — 4-line helper.
- No model-call additions; no new dependencies; no public-API breaks except the `collect()` keyword-only arg (which is back-compatible: `collect(4.0)` still works because `window` defaults to `True`).

### `tests/test_uk_policy_brain.py` (+125/0)

- 4 new tests (`test_quiet_window_without_prior_persists_no_new_from_newest_item`, `test_quiet_window_with_prior_keeps_prior_headline_as_no_new`, `test_empty_feed_without_prior_logs_warning_and_writes_nothing`, `test_collect_window_false_returns_all_items_newest_first`).
- 2 pre-existing tests edited (`test_failed_model_stays_model_unavailable_through_view`, `test_no_new_without_prior_does_not_call_model`) to pin `_in_window` true on the fixture dates — disclosed in PR body, assertions unchanged, accepted by the seat.

### `.github/ci/legacy-jobs.yml::uk-policy-desk` (+19/0)

- New `gate: code` job running `python -m pytest tests/test_uk_policy_brain.py -q` on Python 3.12 with deps `pytest pyyaml jinja2` (the body confirms a clean 3.12 venv with `pip freeze` adding nothing beyond those three). The suite's old homes (`outcome-spine`, `unrun-register-honesty`, both `gate: data`) stay.

### `agentos/discoveries/DSC-UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW.md` (NEW, +58)

- Discovery record naming the defect (no `site/uk_policy.json` after a successful sentinel cycle on a quiet window), the falsifier (`git show 148d1bfec8:engine/uk_policy_brain.py` … `python -c "from engine import uk_policy_brain as u; print(len(u.collect(4.0, window=False)), len(u.collect(4.0)))"`), and the `so_what` (do not read a missing `site/uk_policy.json` after a successful cycle as "the desk is off"; a quiet window must persist `no_new` and log it).

### `research/market_intelligence_productization/MARKET_ONTOLOGY_F02_W2_4_UK_DESK_QUIET_WINDOW_2026-09-23.md` (NEW, +56)

- Wave-2 task-4 runbook: pre/post `run()` branch table, the seat probe receipts at 2026-09-23 05:04Z, the GitHub Actions run 35819272085 receipt, and the liveness receipt (next cycle must commit `site/uk_policy.json` with `state: no_new` and the next render bakes the chip).
