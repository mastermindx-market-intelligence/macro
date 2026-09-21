---
key: orch-audit-macro-pr-7621-2026-09-21
title: 'orch(audit): record macro PR #7621 plain-language/theme/validated-claims audit (2026-09-21)'
pr: 7621
repo: mastermindx-market-intelligence/macro
merge_commit: 35a6ed64d3ab8e5d0ad5436d5da41f2c260071f8
author: chriswong6031-creator
merged_at: 2026-09-21T13:58:15Z
branch: sol/heal-bonds-stylesheet-fingerprint-20260921
base: main
files_changed: 1
additions: 17
deletions: 6
kind: test_only_ci_maintenance
verdict: PASS
date: 2026-09-21
---

# Macro PR #7621 — plain-language / theme / validated-claims audit

Audit scope: plain-language compliance, theme compliance, and validated-claims
compliance of merged macro PR #7621 (`fix(ci): bind Bonds stylesheet
fingerprint to canonical render`), per the qwen_auditor2 audit template.

This PR is **test-only** — one file, `tests/test_bonds_glance_copy.py`,
+17/−6 lines. The diff converts a hardcoded stylesheet digest expectation
into a dynamically derived one computed from the canonical Jinja render of
the `<style>` block that contains `.dtp-chip--snapshot`. The change
preserves every prior assertion (`.dtp-chip--snapshot` must appear,
`.dtp-chip--live` must not) and adds a byte-equality check between the
rendered CSS and the committed `assets/css/<digest>.css` file. No publisher,
product, data, or runtime code is touched. Scope of plain-language gating
is therefore N/A (no user-facing copy added or modified); theme compliance
is N/A in the "new theme law applies" sense (no template or stylesheet
added or modified) but the test *enforces* the prior theme-token contract;
validated-claims compliance is N/A (no `validated` word added to any
user-facing surface, and the only file modified is a test module that
asserts a contract, not a surface).

## PR metadata

| Field | Value |
|---|---|
| Repo | `mastermindx-market-intelligence/macro` |
| PR | [#7621](https://github.com/mastermindx-market-intelligence/macro/pull/7621) |
| Title | `fix(ci): bind Bonds stylesheet fingerprint to canonical render` |
| Author | `chriswong6031-creator` |
| Base → Head | `main` ← `sol/heal-bonds-stylesheet-fingerprint-20260921` |
| Merge commit | `35a6ed64d3ab8e5d0ad5436d5da41f2c260071f8` |
| Merged at | `2026-09-21T13:58:15Z` |
| Files changed | 1 (`tests/test_bonds_glance_copy.py`) |
| Additions / Deletions | +17 / −6 |
| Kind | Test-only CI maintenance (regression repair) |

**Files modified (per `gh pr view 7621 --json files`):**

- `tests/test_bonds_glance_copy.py` (modified, +17 / −6)

## PR body — capability and result

The body is short, capability-focused, and falsifiable:

- **Capability:** repair the shared CI regression blocking current `main`,
  p0b receipt repair PR #7613, and Glossary publisher repair PR #7615.
  The Bonds contract pinned historical stylesheet digest `f5ed7f7d`; the
  canonical public re-render correctly re-externalized the same stylesheet
  after its comment changed from `LIVE` to `Snapshot`, producing content
  hash `ebe31e14`; the required `.dtp-chip--snapshot` selector remained
  intact. The literal digest therefore made a healthy content-addressed
  render fail.
- **Scope:** one test file only. No publisher, product, data, or runtime
  changes.
- **Receipts:** RED reproduced on protected `main` `4eafb563cec…`; target
  test 1 passed; full Bonds glance contract 7 passed; exact hosted
  `ccw-w4-credit-desk` command 120 passed; contract-delta 0 introduced /
  1 inherited (`tests/test_render_dead_ref_targets.py`, pre-existing);
  `git diff --check` pass.
- **Pins:** Protected Skillpack `Mastermind@412deca…`; protected Macro
  `main` `4eafb563cec…`; semantic head `50b9ffd85a…`.

The body does not address user-visible copy, theme tokens, or validation
claims. That is appropriate for a test-only repair.

## Plain-language findings

**Scope decision:** the standalone `terminal/scripts/check_plain_language.mjs`
gate is a Terminal-repo instrument for user-facing surfaces; macro does not
maintain an equivalent mjs script (the macro `engine/neuralweb/chat_plain_words.py`
governs chat LLM output, not docs). For macro PRs the operative plain-
language law is the doctrine in `docs/DESIGN_DOCTRINE.md` and `CLAUDE.md`
§Design — "plain-word null disclosure + Tier-2 receipt" and the banned
internal-state/study-name vocabulary **on user-facing surfaces**. This PR
does **not** touch `templates/`, `site/`, `engine/` display-copy fields, or
any consumer-facing surface. The single file modified is
`tests/test_bonds_glance_copy.py`, which is reviewer- and CI-facing.

Plain-language gating therefore does not apply.

**Manual scan of the diff for any banned vocabulary or user-facing surface
content:** the new test code uses domain terms (`Environment`,
`StrictUndefined`, `rendered_css`, `digest`, `assets/css/`, `.dtp-chip--snapshot`,
`.dtp-chip--live`, `LIVE`, `Snapshot`) that are exclusively about the
Jinja/CSS render contract; none of these strings appear on any user-facing
page or in any message routed to users. No "validated", "proven", or
related loaded words appear in the test. No banned vocab appears.

**Plain-language verdict: N/A — no user-facing surface touched. PASS by
construction.**

## Theme findings

**Scope decision:** the macro design-system law is `docs/DESIGN_DOCTRINE.md`
plus `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` (archetype per route,
canonical components, tokens extend theme.css only, density budgets). The
theme-dark-vs-light art-direction law (TP-0, 2026-08-27) and the
`scripts/check_design_system.py` / `check_runtime_style_injection.py` /
`check_ui_visual_evidence.py` enforcers apply to substantive product
styling of user-facing surfaces.

This PR modifies no template, no stylesheet, no component, no token, and
no JavaScript. The only theme-adjacent artifact is the *assertion* inside
the test that the canonical bonds `<style>` block contains the snapshot
chip token and does not contain the live chip token — that is enforcement
of an existing theme-token contract, not a new theme decision.

**Theme verdict: N/A for new theme law. The test, if anything, is a PASS
for the prior theme contract: it still rejects `.dtp-chip--live` and
still requires `.dtp-chip--snapshot` in the canonical CSS.**

## Validated-claims findings

**Scope decision:** the operative gate is `scripts/check_validated_claims.py`
plus the user-facing law that the word "validated" (and equivalents) on
user-facing surfaces must map to a backing artifact (`validated:true`) or
a justified entry in `data/regime/validated_claims_allowlist.json`. The
checker reports 38 pre-existing `validated` claims across the macro tree —
all in files PR #7621 does **not** touch (`templates/_macro_suite_shell.html.j2`,
`templates/canada.html.j2`, `templates/hk.html.j2`, the `macro_*.html.j2`
suite, `templates/macro_suite.js`, `templates/mm_brain.js`,
`site/macro_*.html`, `site/macro_suite.js`, `site/mm_brain.js`,
`engine/market_os/macro_workspaces/consumer.py`). PR #7621 contributes
zero new claims and zero modifications to any claim-bearing file.

**Manual scan of the diff for "validated", "verified", "certified",
"endorsed", or other claim-bearing vocabulary:** none present. The test
asserts digest equality, file existence, and selector presence — these are
CI assertions, not user-facing claims.

**Validated-claims verdict: N/A for new claims. PASS by construction
(zero contribution to the pre-existing 38-claim queue).**

## Overall verdict

**PASS.**

PR #7621 is a tightly scoped, test-only CI regression repair. It converts
a hardcoded `ebe31e14` digest expectation into a dynamically derived one
computed from the canonical Jinja render of the snapshot `<style>` block,
then enforces byte-equality between that rendered CSS and the committed
`site/assets/css/<digest>.css` file. Plain-language gating is N/A (no
user-facing copy touched); theme gating is N/A (no template / stylesheet /
token / JS touched) but the test actively enforces the prior
`.dtp-chip--snapshot` / no-`.dtp-chip--live` theme-token rule; validated-
claims gating is N/A (no `validated`-word surface touched; zero
contribution to the pre-existing 38-claim checker queue).

The PR is best described as a guard-strengthening change for an already-
passing surface contract. No drift on any of the three audit axes.

`SESSION END: PROVEN_OUTCOME`