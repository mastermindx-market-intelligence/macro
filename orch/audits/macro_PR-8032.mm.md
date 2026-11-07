# macro PR #8032 — plain-language / theme / validated-claims audit

**Auditor:** orchestrator child (REMOTE USEFUL-IDLE, one pass).
**Mode:** half-B audit on a merged PR per qwen_auditor2 convention.

## PR metadata

| Field | Value |
|---|---|
| Repo | `mastermindx-market-intelligence/macro` |
| PR | [#8032](https://github.com/mastermindx-market-intelligence/macro/pull/8032) |
| Title | `fix(macro): stale-source next action drops banned copy; its tests stop reading the day's data` |
| Author lane | `claude/heal-macro-suite-stale-source` |
| Merged at | 2026-09-25T19:06:51Z (within the last-24h window of 2026-09-26) |
| Merge commit | `1f2b713e37eb724933cd161cfeadfa337779ad9c` |
| Files changed (5) | `lib/macro_suite_view.py` (+6/-5), `site/macro_liquidity_regime.html` (+1/-1), `tests/test_macro_command_copy_law.py` (+24/0), `tests/test_macro_command_panels.py` (+9/-1), `tests/test_macro_suite_pages.py` (+5/-3) |
| Type | half-B (user-facing copy repair + test hardening; no engine, no schema, no design tokens) |

## Plain-language findings

This PR is a plain-language *fix* by construction — it removes two banned terms from the user-facing reading path and replaces them with the §5-approved equivalents already used in the shell template. Two strings change in `lib/macro_suite_view.py`:

| Branch | EN before → after | ZH before → after | Why |
|---|---|---|---|
| `WAIT_FOR_SOURCES` | "wait for the next accepted print." → **"wait for the next reading."** | "请等待下一次已接受的读数。" → **"请等待下一次读数。"** | spec §5 bans "accepted print"; "reading" / "读数" is the glossary word |
| `WATCH_BOUNDARY` | "Watch the **axis** closest to changing this state." → **"Watch the reading closest to changing this state."** | "关注最接近改变当前状态的**坐标轴**。" → **"关注最接近改变当前状态的读数。"** | spec §5 bans "axis" / "坐标轴"; matches the shell-template sentence the source comment now cites |

`site/macro_liquidity_regime.html` (+1/-1) carries the rebuilt WAIT_FOR_SOURCES sentence into the committed artifact; the paired test `test_11_thirteen_other_suite_pages_byte_identical` requires every other suite page to stay byte-identical, which the diff honors (zero other HTML bytes changed).

A new parametrised test, `test_every_next_action_branch_is_clean_whatever_state_the_data_is_in`, runs *all four* next-action branches (`WAIT_FOR_SOURCES`, `TREAT_AS_UNSETTLED`, `WATCH_BOUNDARY`, `WATCH_ONLY`) through the page-level plain-language guard `guard.find_violations`. The old page test (`test_all_fifteen_built_pages_are_clean_outside_details`) only ever saw whichever branch the nightly data selected, so a stale source flipping the verdict to `WAIT_FOR_SOURCES` exposed "accepted print" and broke every full-suite PR. The new test pins the verdict to the source code, not the data — correct direction.

`_boundary_view` in `tests/test_macro_suite_pages.py` now also neutralises `availability.state = "CURRENT"` so the boundary-distance tests exercise the boundary rule itself rather than the contradiction / stale-source precedence above it.

`test_fragments_carry_the_authenticity_marker` (in `tests/test_macro_command_panels.py`) is re-shaped to accept either the `mc-move` block *or* the typed empty state per `money.html` tab — because stale data legitimately renders the typed empty state in both money tabs. The offer-link-with-no-figure case still fails. That is a sensible relaxation, not a regression.

**Verdict (plain-language): PASS by construction.** The PR exists *because* the old copy violated §5; the new copy is the §5-approved glossary word ("reading" / "读数"), the change is mirrored in ZH, and a new test guards all four branches so the verdict no longer depends on the nightly data. No new plain-language strings are introduced; the prose sentence in the new test docstring is internal test commentary and not user-facing.

## Theme findings

No theme surface is touched. Diff stat covers source, one rendered HTML page, and three test files — zero CSS, zero `theme.css`, zero token-table, zero JS, zero design-system ratchet surface. `scripts/check_design_system.py --mode enforce-added` would not flag any added blocking rule from this PR (no new template, no new tokens, no new color usage).

The single HTML change is to plain `<p class="mq-next-text">` text inside an existing section. EN and ZH spans are both present. No new class names, no structural changes, no media-query effects. ZH parity is preserved (the change is mirrored 1-for-1 in the `l-zh` span).

**Verdict (theme): PASS** — no theme surface touched, no light/dark art direction impact.

## Validated-claims findings

The PR does not introduce any `validated`-style claim. It is a copy repair + test hardening, not a promotion or a tier-2 evidence assertion. The new test docstring writes "the red hit every full-suite PR" and "exposed 'accepted print', which had been banned all along" — both are internal CI reasoning, not user-facing prose.

No new strings contain the banned vocabulary the validated-claims gate polices (no "validated", no new numeric claim, no new score, no new escalation). The runner allowlist `data/regime/validated_claims_allowlist.json` is sparse-tree-absent in this checkout, but the PR touches none of its keys by construction (the diff has zero `data/regime/` paths).

**Verdict (validated-claims): PASS** — no new user-facing claim, no allowlist impact.

## Overall verdict

**PASS on all three dimensions** — plain-language (banned vocabulary removed and locked by a branch-exhaustive test), theme (no theme surface touched), validated-claims (no new claim, no allowlist touch).

**Notes for follow-up:**

- The PR body says the four originally-red tests now pass; the new test also passes for all four branches and on the old copy would fail on `WAIT_FOR_SOURCES` ("accepted print") and `WATCH_BOUNDARY` ("axis") — i.e. the test is RED-first in spirit even though it is added green.
- Spec §5 is referenced but the spec file is not in this sparse checkout; the PR body and the in-source comment are sufficient evidence that the banned terms are the ones the spec covers.
- The `_boundary_view` helper still hard-codes `"CURRENT"` for `availability.state` — fine for the boundary test, but if a future case wants to test a *non-CURRENT* boundary case it would need a richer helper. Not a defect of this PR; flag only.
- The PR is recorded disk-only under REMOTE USEFUL-IDLE MODE (no new PR opened, no `merge-on-green` armed). Follow-up audits / live-verification receipts are owned by the merge sweep; this audit is the deliverable.