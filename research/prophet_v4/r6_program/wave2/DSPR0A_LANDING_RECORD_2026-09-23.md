# DS-PR-0a landing record — re-scoped by the seat after the lane's collision census proved incomplete

Lane `pu_w2_dspr0a` (GLM, mb) produced the first cut (commits 9a1d0542, 48ae8c7b, bc3944fb, c1e87283; final review FIX_REQUIRED 2B/1M/1m). Its round-2 reviewer found that the packet's class-collision scan was empty for the wrong reason, and the seat's own census then found live token consumers as well. The seat (Fable Meta-CEO, session 48cdfd56) re-scoped the landing to the provably pixel-neutral subset in the commit that carries this record. Ruling: `research/prophet_v4/r6_program/rulings/R6-B20-02_DSPR0_SPLIT_2026-09-23.md`.

## SOURCE_SHA

origin/main at the seat commit: 5ced8909a6f09f6c1c681db0c5ce8e04f96627d9. Lane base: 1fc095fe9ab6a6958f2d57d482efb6df0c5d716b.

## WHY THE LANE'S NEUTRALITY CLAIM WAS FALSE

1. The packet's scan `git grep -n -E '\.mx-(vh|sec|…|rail)\b' …` returned 0 lines because `\b` is not a POSIX ERE atom: on this platform's `git grep -E` it matches nothing, so the scan could only ever print 0. A word-boundary census written with explicit character classes finds the names in live templates and baked pages (table below).
2. The packet assumed the §2.2 token NAMES were unconsumed. They are consumed estate-wide: pages already write `var(--r-card)` bare, or with fallbacks of 10–16px, so landing `--r-card:12px` re-renders those corners. The seat's classification of every consumer is below.

## WHAT LANDED (pixel-neutral by construction)

- `templates/theme.css` `:root`: `--sp-1`, `--sp-4`, `--sp-5`, `--sp-6`, `--sp-7`, `--sp-8`, `--gap-grid`, `--t-med`, `--t-slow`, `--ease-std`, `--ease-lift`, `--shadow-hover`, `--ser-1`…`--ser-4`, `--ink-tier`; light overrides for `--ser-*` and `--ink-tier`; `--ink-prov: var(--prov-ink)` in both provenance blocks (`--prov-ink` unchanged).
- `templates/theme.css` primitives, verbatim from the specimen: `.mx-tbl` (+ `th`, `td`, `tr:hover td`), `.mx-tblbox`, `.mx-tabset` (+ `button`, `[aria-selected]`), `.mx-rail` (+ `li`, `::before`, `::after`, `.done`, `.now`). Two references to deferred tokens carry value-equal fallbacks so the rules stay valid until DS-PR-0c lands: `var(--t-fast,.16s)` and `var(--r-pill,999px)` (the lane's repair of the checker's radius-literal finding).
- `site/theme.css`: byte-identical paired copy (`check_template_site_sync --fix`).
- `mockups/design_system/specimen.html`: header rewritten; the proposed block now holds only the deferred tokens (`--sp-2`, `--sp-3`, `--r-ctl`, `--r-btn`, `--r-card`, `--r-panel`, `--r-pill`, `--t-fast`) and the deferred zh estate rule; the four landed primitive families are deleted from the specimen; `.mx-vh`/`.mx-sec`/`.mx-callout`/`.mx-disc` stay specimen-local.
- `templates/dashboard.html.j2`: NOT changed (the lane's deletion of the page-local `--sp-*` line is reverted; with `--sp-2`/`--sp-3` deferred, that page must keep its local definers).

## DEFERRED TO DS-PR-0c (token + class reconciliation; each item changes rendered output and owes the two-theme evidence matrix)

| Item | Why deferred (origin/main census) |
|---|---|
| `--sp-2`, `--sp-3` | bare consumers: 1 and 2 sites outside any local definer |
| `--r-ctl` | 29 files; 7 bare; fallbacks of 2/3/4/5/6/10px and `var(--r)` (21 sites) |
| `--r-btn` | 7 files; 2 bare (`dashboard.html.j2:6547, 6593`) |
| `--r-card` | 24 files; 9 bare (dashboard ×5, `_curve_panel`, `_risk_envelope_band.css.j2`, `market_structure` ×2); fallbacks of 10/11/13/14/16px (9 sites) |
| `--r-panel` | fallbacks of 12/13px and `var(--mq-radius)` (8 sites) |
| `--r-pill` | 3 bare |
| `--t-fast` | 2 consumers with `.14s` fallbacks |
| `.mx-sec` | page-local rules + markup: `bonds.html.j2` (7), `dashboard.html.j2` (6), `_unified_dashboard_hero.html.j2` (5 → `site/intl.html`, `site/macrodata/global_regime_fragment.json`), `sanctions_map.html.j2` (4), `site/us_stocks.html` (1) |
| `.mx-vh`, `.mx-callout` | `bonds.html.j2` (4 + 4, with light overrides at :348), hero (1 callout) |
| `.mx-disc` | `templates/risk_envelope_live.js` (1) |
| zh estate rule (`h1,h2,h3,.eyebrow,.mx-vh-word`) | changes tracking/uppercase on every zh page |
| `dashboard.html.j2:1903` `--sp-8:32px`→`--sp-7` | moves with `--sp-2`/`--sp-3` |

DS-PR-0b (unchanged from the packet): `html body` var() rebinds of the vector-polish block and component radii; `.eyebrow`→`--fs-label`; `_icons` stroke 1.8; specimen duplicate-rule cleanup.

## TOKEN CONSUMER CENSUS (origin/main; consumers of `var(--x…)` outside theme.css/specimen; classification: local-def = the consuming file defines the token itself; fb=canon = fallback equals the §2.2 value; BARE/fb≠canon = landing changes the computed value)

```
--sp-1  fb=canon×14 | --sp-2  BARE×1 fb=canon×33 | --sp-3  BARE×2 fb=canon×27 local-def×2 | --sp-4  fb=canon×15 local-def×2
--sp-5  fb=canon×4 local-def×2 | --sp-6  fb=canon×4 | --sp-7  fb=canon×2 | --sp-8  fb=canon×3 | --gap-grid none
--r-ctl  BARE×7 fb≠canon×21 fb=canon×62 local-def×16 | --r-btn  BARE×2 fb=canon×13 | --r-card  BARE×9 fb≠canon×9 fb=canon×34
--r-panel  fb≠canon×8 fb=canon×11 local-def×5 | --r-pill  BARE×3 fb=canon×52 local-def×11 | --t-fast  fb≠canon(.14s)×2 fb=canon×1
--t-med/--t-slow/--ease-std/--ease-lift/--shadow-hover/--ser-1..4/--ink-prov  none | --ink-tier  local-def×1 (tier_preview.css)
local definers: seo_base.html.j2 + dashboard.html.j2 (--sp-1..6, --sp-8); options.html.j2 (--r-ctl, --r-panel, --r-pill); tier_preview.css (--ink-tier)
```
Landed set = every token whose consumers are all `local-def` or `fb=canon` or none.

## CLASS COLLISION CENSUS (origin/main; `git grep -o -E '(^|[^A-Za-z0-9_-])mx-(vh|sec|tbl|tblbox|tabset|callout|disc|rail)([^A-Za-z0-9_-]|$)' -- templates app scripts site`, excluding theme.css/specimen)

Hits exist only for `mx-sec`, `mx-vh`, `mx-callout`, `mx-disc` (files listed in the deferral table). `mx-tbl`, `mx-tblbox`, `mx-tabset`, `mx-rail`: 0 hits.

## GATES (seat, this checkout, at the commit carrying this record)

- `git diff origin/main -- templates/theme.css templates/dashboard.html.j2 > /tmp/pr7849_seat.diff` (77 lines) then `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7849_seat.diff` → exit 0; `design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25311)`.
- `python3 scripts/check_runtime_style_injection.py` → exit 0; `runtime style injection guard OK (197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)`.
- `python3 -m scripts.check_template_site_sync --fix` → `1 site copy restored from templates/ (101 pairs checked)`; `cmp templates/theme.css site/theme.css` → exit 0.
- `python3 -m pytest tests/test_check_design_system.py tests/test_public_chrome.py -q` → `104 passed`.

## ACCEPTANCE GREPS (observed at this commit)

| Grep | Observed |
|---|---:|
| `grep -c -E '^\s*--sp-1:4px; --sp-4:16px; --sp-5:20px; --sp-6:24px;' templates/theme.css` | 1 |
| `grep -c -E '^\s*--r-ctl:8px;' templates/theme.css` | 0 |
| `grep -c -E '^\s*--t-fast:' templates/theme.css` | 0 |
| `grep -c -E '^\.mx-tbl\{' templates/theme.css` | 1 |
| `grep -c -E '^\.mx-(vh\|sec\|callout\|disc)' templates/theme.css` | 0 |
| `grep -c -E '^\s*--ink-prov:' templates/theme.css` | 2 |
| landed primitives referencing a deferred token without fallback | 0 |
| `grep -c -F 'PROPOSED — DS-PR-0c' mockups/design_system/specimen.html` | 1 |
| `grep -c -E '^\.mx-(tbl\|tblbox\|tabset\|rail)' mockups/design_system/specimen.html` | 0 |
| `git diff origin/main -- templates/dashboard.html.j2 \| wc -l` | 0 |

## PIXEL-NEUTRALITY ARGUMENT

Every landed token has no live consumer, or only consumers whose fallback equals the landed value, or only consumers inside a file that defines the token itself (where the local declaration wins on specificity). Every landed primitive family has zero live class usages. No existing declaration was changed. Therefore no rendered pixel changes at landing; the `?v=` re-stamp of theme.css is not owed by this PR.

## EVIDENCE

Lane commits 9a1d0542357a, 48ae8c7b8c26, bc3944fb90dc, c1e872834fb0; seat re-scope commit = the commit carrying this record (see PR #7849).
