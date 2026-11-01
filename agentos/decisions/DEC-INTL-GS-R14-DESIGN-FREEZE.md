---
key: INTL-GS-R14-DESIGN-FREEZE
question: >
  Is the Paper R14 "Global Surveillance · Masterpiece" page (14 boards) plus its written
  spec the frozen design for International Markets Global Surveillance Waves 2–5
  (IM13–IM18), and how are the six open decisions ORCH-D left for the seat ruled?
answer: >
  Yes, frozen at research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md
  (blob 5d9c51dc25005935a6be5846a01baa48246f9375) with reference PNGs under mockups/refs/intl-gs-r14/.
  Rulings: (1) spec §5.3 additive tokens live scoped under .intl-gs in a new
  templates/intl_workspace_surveillance.css, nothing added to theme.css; (2) the §14
  file plan is ratified (new view templates, both view lists in shell.html.j2, the asset
  tuple in build_intl.py, the stylesheet link in intl.html.j2); (3) the IM16
  market-by-capability acceptance matrix is adopted as mandatory, as the masterplan
  already requires; (4) G1: the specified-but-undrawn theme/locale variants in §13 are
  accepted as specification — no further Paper pass; the 8 evidence crops are produced
  on the real build; (5) G7: PNGs copied into the repo under mockups/refs/intl-gs-r14/;
  (6) every Wave 2+ packet owes the 8 evidence screenshots plus focus-state captures in
  both themes (§16.1) and a green evidence gate is not acceptance — the seat reviews
  the crops.
rationale: >
  The seat inspected the scanner (dark/EN/1440) and Brazil dossier boards directly:
  the six-question scaffold, the four clocks, the return identity, rights tiers,
  attention stances, selected/featured states carried by 1.5px rings, neutral surface
  hierarchy and the existing site-nav family are all present; no accent stripe or
  colored edge appears. The spec reads column widths from Paper, carries a contrast
  table with three forbidden combinations, and separates selected/focus/hover states
  that the drawing merged. Where Paper and production disagree (Inter vs system font,
  light ink-ok hex, focus offset 2px vs 3px, the scanner Q6 footer's "2px offset" copy)
  production tokens and the spec are authoritative, never the PNG glyphs.
alternatives:
  - option: Commission a second Paper pass to draw every theme/locale variant of all six boards.
    why_not: >
      The scanner already proves all eight combinations; the remaining variants are
      mechanical applications of §13 and are verified on the real build anyway.
  - option: Add the new tokens to theme.css.
    why_not: >
      theme.css carries a same-diff receipt (ci-pack-9) and is shared by every page;
      a scoped stylesheet keeps the blast radius to the surveillance views.
evidence:
  - "Seat look at mockups/refs/intl-gs-r14/scanner__dark__en__1440.png and dossier__dark__en__1440.png (2026-10-21 04:2xZ)"
  - "research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md §1 design bar, §5 token diff, §13 matrices, §14 homes, §15 contrast, §17 gaps"
  - "ORCH-D return (Opus orchestrator abd45165af1bdea65): 14 artboards, 540 Paper tool calls, PNGs exported from Paper, no git acts"
  - "docs/DESIGN_DOCTRINE.md — no accent stripe rule (Chairman 2026-10-18)"
affects:
  - "research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md"
  - "mockups/refs/intl-gs-r14/*"
  - "templates/intl_workspace_surveillance.css (to be created by Wave 2)"
  - "templates/intl/shell.html.j2, scripts/build_intl.py, templates/intl.html.j2 (Wave 2 file plan)"
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-seat-d7c4f490
decided_at: 2026-10-21
amended_at: 2026-10-22
review_by: 2026-11-21
---

## Scope

This freezes the design reference for Waves 2–5 of WS:INTL-GLOBAL-SURVEILLANCE. It does
not build, merge or publish anything, and it does not reopen the Wave 0 or Wave 1
contracts. A later material invalidator (a §14 hard acceptance test that the design
cannot satisfy, or a Chairman design ruling) reopens it; a new session does not.

## Amendments A1 / A1.1 / A1.2 (2026-10-22, seat d7c4f490)

# Seat ruling — DEC:INTL-GS-R14-DESIGN-FREEZE amendment A1 (2026-10-22, seat d7c4f490)

Trigger: #9949 @ dcbcf989 CI RED. pack-3 design-governance (`check_design_system.py --mode enforce-added`)
blocks 80 findings, all in the `.intl-gs{}` §5.3 token block of `templates/intl_workspace_surveillance.css`
(rule 4 `literal-custom-property` + rule 1 `color-literal`). pack-5 `international-workspace-browser`:
`test_frozen_files_unchanged_vs_origin_main` ×5 fails because pack checkouts are `fetch-depth: 1` and
`origin/main` does not exist there (main has not touched the five frozen files since 556d3333).

Facts that bind (scripts/check_design_system.py on main):
- theme.css is the sole token root; rule 4 fires on ANY literal-valued custom property outside theme.css,
  in any selector, and `SANCTIONED_LITERAL_FILES` never exempts it. `is_derived_value` admits only
  `var(--x)` chains, `calc/min/max/clamp(` with unitless numbers, and the inert keywords; `color-mix(`,
  `%`, `px`, hex and any word of 2+ letters are literals. Rule 1 also flags `color-mix(` as a colour literal
  outside sanctioned files. Rule 9 keeps a scoped (non-`:root`) DERIVED block legal — that is the sanctioned
  way for a surface to extend the palette.
- Spec R14 L10: doctrine/theme.css win on disagreement. Spec L202 / DEC ruling (1) forbade adding
  `--sp-*/--ser-*/--returns-*` to theme.css in Wave 2 (blast radius, ci-pack-9 same-diff receipt). Both stay.
- Estate precedent: theme.css L277 swaps `--up/--down` under `html[data-lang="zh"]`; theme.css L557–565
  already supplies the ZH font stack; `--r-card:12px`/`--r-ctl:8px` exist; `--ser-4:#e08b45` == theme
  `--orange`, `--ser-1:#5b9bf0` == theme `--info`, `--ser-2:#d4a017` == theme `--q2` (dark).
- `--sp-*` has ZERO consumers in the PR (css/j2/js grep). `--returns-*`/`heatbg` classes have no
  consumer in the foundation macros (vocabulary for W2A/W2B/W3 views).
- Checker quirk: `CUSTOM_PROP_RE` matches `.x--mod::before{content:""` as a custom property
  (`--mod:` + `:before…`). Pseudo-elements must never directly follow a `--modifier` token in a selector.

RULING (binds the fix lane; reviewer checks it verbatim; the spec file gets the same text as §5.3 amendment A1):

```css
/* === INTL-GS §5.3 TOKENS — amendment A1 (2026-10-22): pure theme derivations, no literals === */
.intl-gs{
  --r-panel:var(--r-card); --r-btn:var(--r-ctl);
  --r-pill:calc(var(--r-card) * 100);   /* pill = any radius ≥ half-height; theme has no pill token */
  --ser-1:var(--info); --ser-2:var(--q2); --ser-3:var(--ok); --ser-4:var(--orange);
  --ink-tier:var(--ink-link);           /* tier_preview.css's own default outside the prophet gate */
}
/* returns heat — FILL ONLY, never text ink; follows --up/--down so light theme and ZH red-up
   hold BY CONSTRUCTION (theme.css L277 swaps --up/--down under html[data-lang="zh"]) */
.intl-gs__heat--up-soft{fill:var(--up);fill-opacity:.14;}
.intl-gs__heat--up-mid{fill:var(--up);fill-opacity:.26;}
.intl-gs__heat--up-strong{fill:var(--up);fill-opacity:.42;}
.intl-gs__heat--down-soft{fill:var(--down);fill-opacity:.14;}
.intl-gs__heat--down-mid{fill:var(--down);fill-opacity:.26;}
.intl-gs__heat--down-strong{fill:var(--down);fill-opacity:.42;}
.intl-gs__heatbg{position:relative;isolation:isolate;}
.intl-gs__heatbg::before{content:"";position:absolute;inset:0;background:var(--heat-ink);opacity:var(--heat-a);z-index:-1;pointer-events:none;}
.intl-gs__heatbg--up-strong{--heat-ink:var(--up);--heat-a:.42;}
.intl-gs__heatbg--down-strong{--heat-ink:var(--down);--heat-a:.42;}
```
Proven: `scratchpad/ratchet/prove.py` runs this exact block through `check_design_system.py --mode enforce-added`
on a scratch root → `blocking=0`, rc 0.

DELETED (not moved): the `--sp-1…8` scale (no consumers; spacing stays literal px in rules like the rest of the
estate); every `--returns-*` custom property; the light-theme `.intl-gs` override block; all four
`html[data-lang="zh"] .intl-gs` / `html[data-theme="light"][data-lang="zh"] .intl-gs` blocks; the `--font-zh`
block (theme.css already carries the ZH stack); the scoped `--ink-tier` hex pair (T2 note) — replaced by the
derivation above. theme.css stays untouched; the frozen-files list keeps theme.css.

Visual deltas accepted by the seat: panel radius 14→12, button radius 10→8, series-3 sky→`--ok` green,
tier ink violet→link ink, heat tints become opacity steps of `--up/--down`. All eight evidence crops are
re-captured at the new head; §15 contrast re-run for `--ink-tier` on panel (text ink, AA expected).

pack-5 fix: the browser job adds, before its pytest step, the same fail-closed base fetch the
design-governance job uses (`git fetch origin ${{ github.base_ref || 'main' }}` → error + exit 1 on failure);
`test_frozen_files_unchanged_vs_origin_main` compares each frozen path against
`git merge-base origin/main HEAD` (not the main tip) and FAILS CLOSED with a clear message when `origin/main`
does not resolve. Proven in a `git clone --depth 1` of the lane branch + the fetch step. No network in tests.

## Amendment A1.1 (2026-10-22, seat) — radii fallbacks restored
Defect found by ORCH-2 at FX5 head 0f7d22b1: theme.css defines NO `--r-card`/`--r-ctl`/`--r-pill` at :root (DS-PR-0
pending, comment L2105-2110), so the A1 derivations are invalid at computed-value time and every radius rendered 0.
Ruling: the A1 block bytes stay; every border-radius declaration carries the estate idiom fallback, exactly one of
`var(--r-panel,12px)` / `var(--r-btn,8px)` / `var(--r-pill,999px)`; no direct `--r-card`/`--r-ctl` use in intl-gs
files; test L197 allows exactly those three pairs (mutant: a fourth pair goes red); spec §5.3 A1 gets the A1.1 note;
crops re-captured with corner zooms; delta re-review r8. The A1 sentence "drop literal fallbacks" is withdrawn for
radii only. Ratchet: rule 3 accepts `var(--r-…`, rule 4 is custom-property-only, so blocking stays 0.

## Amendment A1.2 (2026-10-22, seat) — light-theme series inks are theme derivations
F2 (r7 R3) accepted: light series-1/2/4 now equal theme light `--info`/`--q2`/`--orange` (#285fff/#b07d05/#c4781f)
because the lane's light override block (a parallel palette) was deleted under A1. Series inks are chart strokes/fills,
not text; §15 contrast applies to legend text, which stays `--text`/`--muted`. Not a gap; one line in the review record
and PR body. No re-crop, no lane.

Effect on ruling (1): the scoped block under `.intl-gs` in templates/intl_workspace_surveillance.css now holds ONLY
theme derivations (`--r-panel:var(--r-card)`, `--r-btn:var(--r-ctl)`, `--r-pill:calc(var(--r-card) * 100)`,
`--ser-1..4` = `--info/--q2/--ok/--orange`, `--ink-tier:var(--ink-link)`); `--sp-*`, `--returns-*`, `--font-zh`, the
light override and the four ZH blocks were deleted; theme.css untouched; radius declarations carry the estate fallback
pairs `var(--r-panel,12px)` / `var(--r-btn,8px)` / `var(--r-pill,999px)` until DS-PR-0 lands `--r-card/--r-ctl` at
:root; light series inks are the theme's light tokens.
