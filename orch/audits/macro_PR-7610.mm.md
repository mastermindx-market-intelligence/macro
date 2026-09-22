# Plain-language / theme / validated-claims audit — macro PR #7610

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7610 |
| title | `fix(help): make tooltip affordances keyboard and touch reachable` |
| merged_at | 2026-09-22T02:31:47Z |
| head (semantic) | `d859be36ad557ab2e8d16f4f11f4dc1ded4cc8e8` |
| merge commit | `492551a93284fb40a289fa4dde1c2e205001b6e5` |
| branch | `claude/macro-help-affordance-20260921` |
| changed files | **47, +1016 / −49.** Substantive code delta: `templates/theme.js` (+43 / −4), `site/theme.js` (+43 / −4, byte-aligned sync), `site/research_screener.html` (+1 / −1, `?v=` re-stamp), `tests/test_lens_nested_control_taps.py` (+61 / −2). Remaining 41 files are pure visual-evidence receipts under `mockups/evidence/help-affordance-r2/` (24 PNGs + `manifest.json` + `EVIDENCE.yml`) plus the versioned `mockups/evidence/prophet-p0b-zero-fouc/` re-emit (12 PNG re-stamps + 2 manifest/layout files). |
| labels | `merge-on-green` (sweeper-backed; merge commit produced by the macro merge-on-green sweeper at the listed timestamp) |
| scope collision | none — body explicitly bounds scope to one defect (15×15 mouse-era help glyphs were not keyboard/touch reachable) and explicitly disclaims any rank/score/signal/UI-architecture/claim/scheme/layout change. The shared `Lens` viewport-clamped tooltip/sheet system is preserved; the upgrade is to the existing `span.help.help-upgraded` legacy triggers only. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 30` against `git ls-tree origin/main -- orch/audits/` (the standing workflow per `macro-pr7603-audit-delivered` + `orch_audit_filename_convention`): the most recent non-audit merged PRs in the prior 24-h window were #7666 (research/risk rerun — half-D data plane, no user-facing surface), #7632 (fix/risk — half-D replay correction), #7628/#7621/#7614 (fix/ci — infra), #7619 (agentos: control-room continuity — already audited as `macro_PR-7619.mm.md`), #7614/#7613/#7597 ([MO-A heal] governance), #7608 (research/risk), #7600 (fix/alt-data — already audited). The most recent merged PR with a real half-B user-facing surface, no committed audit yet, and an explicit user-facing consequence (the 15×15 help glyph's 24-cell visual-evidence matrix that the design system + bilingual + lens selectors all need to read) is **#7610**.

**Nature of change (one-defect keyboard/touch reachability repair, half-B surface-touch).** The legacy `span.help.help-upgraded` "?" glyph is visually 15×15 but interaction-shaped as if it were still mouse-only — no `tabindex`, no `role="button"`, no visible focus ring, no 40×40 coarse-pointer hit area. On a 390×844 touch device, the visible glyph was unreachable without poking at the exact 15-px pixel. The PR defers to the lens system's existing interactive trigger contract: the `span.help.help-upgraded` base selector grows `position:relative` and `touch-action:manipulation` (so the `::before` hit slop can compute), a `:focus-visible` rule with a 2-px outline is added, a `@media (hover:none),(pointer:coarse)` rule paints an invisible 40×40 `::before` hit area, `tabindex=0` and `role=button` are set on every upgraded help glyph at upgrade time, and Enter/Space activation is wired through the existing delegated `keydown` listener (`e.target.closest('span.help.help-upgraded')`). The close (`.lens-x`) button grows from 26×26 to 40×40 with `touch-action:manipulation` and its own `:focus-visible` outline, and gets the same bilingual `aria-label` discipline (`Close` / `关闭`) driven by `data-lang` and a `langchange` listener. A new `syncUpgradedHelpLabel(el)` is called at upgrade time and re-bound to the existing `langchange` document event. **No new tooltip, no new lens, no new shared interaction owner** — the lens system is preserved verbatim (the standing comment `LENS on .lens-q owns open/close; this only translates the label.` at `templates/commodities.html.j2:1428` is unchanged). The repair is *to* the lens contract, not a new contract.

## Plain-language findings

### 1.1 Pass — bilingual `aria-label` discipline is preserved/strengthened

The PR's substantive user-facing copy change is two new `aria-label` strings driven by `data-lang`: `"More information"` / `"更多信息"` (the `span.help.help-upgraded` accessible name — the canonical pair already used by the existing `lens-q` upgrade path in `templates/commodities.html.j2:992, 1032, 1139`) and `"Close"` / `"关闭"` (the `.lens-x` close-button accessible name — a change from the prior hard-coded single-language `"Close"`, upgraded to live bilingual via the existing `data-lang` lookup and a `langchange` listener that re-syncs the `aria-label` whenever the user toggles EN/ZH). Both are canonical paired bilingual strings. No banned-glance vocabulary (`validated`, `proved`, `guaranteed`, `certified`) introduced; the only matches in the diff are `approved fixtures` JSON gap-receipt strings under `mockups/evidence/help-affordance-r2/manifest.json`'s `gaps[].reason: ...` array (evidence-system gap metadata describing absence-of-automated-capture, not promotion claims). PR body closes with the canonical anti-promotion line "Merge/green CI is not production acceptance."

## Theme findings

### 2.1 Pass with caveat — 5 design-system blocking findings are all pre-existing false positives

`python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7610.diff` reports 5 blocking findings (`templates/theme.js:5471 [color-literal] #5b9bf0`, `templates/theme.js:5479 [color-literal] #181b21`, `templates/theme.js:5479 [color-literal] #d7dce3`, `templates/theme.js:5479 [literal-custom-property] --lens-panel: var(--panel,var(--card,#181b21))`, `templates/theme.js:5479 [literal-custom-property] --lens-text: var(--text,var(--ink,#d7dce3))`). Every one is a pre-existing dark-fallback hex literal in UNCHANGED context lines within the diff hunks (verified via `git show HEAD~1:templates/theme.js` — line 5471's `#5b9bf0` and line 5479's `#181b21`/`#d7dce3` were already in `templates/theme.js` before this PR). The checker is reporting these as "added by this diff" because they fall within the line-range of the diff hunks (the hunk `@ -5467,11 +5467,16 @@` covers lines 5467–5477 of the old file and 5467–5482 of the new file, and the checker appears to flag the entire hunk-range rather than only `+`-prefixed lines). The PR adds zero hex/rgb/hsl/`color-mix` literals; the only new color tokens are `currentColor` and `var(--info,var(--blue))` etc. — all token-driven.

### 2.2 Pass — TP-0 24-cell evidence matrix is delivered

The PR body names the 24-cell matrix explicitly: `REST + help focus + help hover across dark/light × EN/ZH × desktop/mobile`. The `mockups/evidence/help-affordance-r2/manifest.json` records the standard axes (`themes: [dark, light]`, `locales: [en, zh]`, `viewports: desktop 1440 / mobile 390`, `force_states: [help-focus, help-hover]`, `access: anonymous`) and `outcome: captured`. The 24 PNG receipts carry the canonical `mastermind.page_evidence_receipt.v1` schema declaration in `EVIDENCE.yml`. The honesty block in `manifest.json` repeats the canonical disclaimers (`"anonymous only; no credential is entered, stored, or synthesized"`; `"this tool measures and screenshots; it scores, ranks, and judges nothing"`).

### 2.3 Pass — no theme-token, palette, runtime-style-injection, or material-design surface changed

`scripts/check_runtime_style_injection.py` is out-of-scope for this PR by construction: the diff contains no `style="..."` injection, no `style.textContent =`, no parallel palette, no duplicated light/dark branches inside JS, no inline `<style>` block. The diff modifies two CSS string-literal blocks in `templates/theme.js` (the canonical shared CSS surface) and the matching JS-side upgrade path; the modifications are token-driven and reuse the existing CSS custom property plane that the pre-PR `.lens-pop` block already establishes. No new CSS variable is declared; no new palette is introduced.

## Validated-claims findings

### 3.1 Pass — no promotion-bearing claim introduced

The PR's substantive surface change is `templates/theme.js` (CSS string-literal + JS upgrade path). Grepping `templates/theme.js` for `validated` returns zero matches. The PR introduces no user-facing `validated`, `proved`, `guaranteed`, `certified`, or any promotion-bearing synonym. No MISS row is generated against this PR's diff. The only `validated`/`guaranteed`/`certified`/`proved` strings present in the diff are the three `"approved fixtures"` strings in `mockups/evidence/help-affordance-r2/manifest.json`'s `gaps[].reason: ...` array — gap-receipt metadata, not promotion claims. The honesty block carries the canonical disclaimers.

## Overall verdict

**VERDICT: PASS — clean half-B keyboard/touch reachability repair, with 5 design-system checker findings that are all false positives (context-proximity, not new color literals).**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | Two new bilingual `aria-label` strings (`More information` / `更多信息`, `Close` / `关闭`) wired to existing `data-lang` + `langchange` re-sync discipline. No user-facing visible-on-page prose added; no banned-glance vocabulary; only `approved fixtures` JSON gap-receipts (not claims). |
| theme | PASS with caveat (5 false-positive design-system findings) | `check_design_system.py --mode enforce-added` reports 5 blocking findings, but all are pre-existing dark-fallback hex literals in unchanged context lines (lines 5471/5479, verified via `git show HEAD~1:templates/theme.js`). PR adds zero new color literals. TP-0 24-cell evidence matrix IS delivered. No `style="..."` injection, no JS-injected style system, no new CSS variable declared. |
| validated-claims | PASS | Zero `validated`/`proved`/`guaranteed`/`certified` in changed surface. PR body explicitly disclaims promotion. |
| merge hygiene | PASS | 47 files, +1016 / −49 (substantive code delta is `templates/theme.js` +43/−4 + `site/theme.js` +43/−4 + `site/research_screener.html` +1/−1 + `tests/test_lens_nested_control_taps.py` +61/−2 = **+148 / −11**; the remainder is the 24-cell `mockups/evidence/help-affordance-r2/` evidence receipts and the versioned `mockups/evidence/prophet-p0b-zero-fouc/` re-emit). `templates/theme.js` and `site/theme.js` are byte-aligned (canonical `scripts/check_template_site_sync.py` gate confirmed 99 pairs OK at merge time); `site/research_screener.html` `?v=` re-stamp refreshes the Caddyfile `?v=*` exclusion. Two new parametrised tests with docstrings self-documenting design intent. `merge-on-green` label armed and the sweeper squash-merged at the listed timestamp. |

**Non-blocking follow-up (out of this lane's owned path):** `scripts/check_design_system.py --mode enforce-added` flags context lines inside diff hunks as "added by this diff" even when those lines are unchanged. For this PR, that produces 5 spurious blocking findings — all pre-existing dark-fallback hex literals at unchanged positions. The fix would be to filter the patch to only `+`-prefixed lines before scanning; a separate tool-investigation PR could land that. Until then, every reviewer of a PR that touches any line adjacent to `var(--info,var(--blue,#5b9bf0))`/`var(--panel,var(--card,#181b21))`/`var(--text,var(--ink,#d7dce3))` in `templates/theme.js` will see the same 5 spurious findings.

**No blocking issue found. The 5 reported design-system findings are confirmed false positives. No retry. No scope expansion. Audit complete.**