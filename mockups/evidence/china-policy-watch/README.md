# China Policy Watch — W5 r3 evidence

Fixture-rendered `templates/china_policy_watch.html.j2` (no live `data/` bake).
Playwright seeds `localStorage` (`theme`, `lang`, clears `themeAuto`), calls
`setTheme`/`setLang`, re-reads `html[data-theme]` / `html[data-lang]`, and
refuses a cell on mismatch.

## DARK TREATMENT

Command center: luminance depth, instrument glass (`--mx5-glass-bg` at 55%
with inset highlight and 32px shadow), restrained `--sh-glow` on the
State-Hand gauge, aurora wash in the pressure accent. Backdrop is a quieter
inner panel (hairline + 3% white lift), not a second peer card. Chips and
pills sit on translucent fills.

## LIGHT TREATMENT

Research workspace: cool canvas, white material (`--mx5-glass-bg` 82% with
8% shadow and a white inset hairline — shadow instead of glow). Aurora is
dialed to 6%/4%. The nested China-macro backdrop uses a white sheet
(`rgba(255,255,255,.72)`) plus a 6% cool drop shadow so it reads as paper
on the desk, not a token-swapped dark panel. Stance badges keep the same
semantic hues; light relies on fill + hairline rather than glow.

## Intentional differences

| Mechanism | Dark | Light |
|---|---|---|
| Card depth | glow + 32px shadow | hairline + 8–24px shadow |
| Backdrop | 3% white lift | white sheet + inset hairline |
| Aurora | 13% accent bloom | 6% / 4% wash |
| Needle glow | drop-shadow on `--sh-accent` | theme.css light pointer, same accent |

Token substitution alone is not the light design — the backdrop sheet, the
inset hairline, and the shadow-not-glow stack are the light-specific
mechanisms.

## L1 section count

DOM `.pw > .cnx-card[data-l1]`: **6** → `['hero', 'thesis', 'pboc', 'sectors', 'tape', 'ledger']`

Demotion landings:

| Removed L1 | Landing |
|---|---|
| FX & reserves | Nested **China macro backdrop** inside PBoC card (`data-landing="china-macro-backdrop"`) + counted China-desk link |
| NBS latest prints | Same backdrop (stance line + per-tile direction words) |
| NPC 2026 targets | Chip row on the policy-thesis card (`data-landing="npc-2026"`) |
| Sector rows 9–13 | `#pw-sector-all` disclosure, linked as **See all N →** |

## 390 h-scroll

`{"clientWidth": 390, "scrollWidth": 390, "pageScroll": false, "tableClient": 312, "tableScroll": 1056}`

Zero page h-scroll is required; the capped table scrolls inside `.pw-table-scroll`.

## Rest cells

8 full-page: dark/light × EN/ZH × 1440/390 (`full-*-*.png`).

## State shots

`.sh-pop` open dark+light; LENS `?` host open dark+light via hover-intent
(`state-*.png`). Tips use `button.lens-q` hosts (S1 390 tap trap — not row
hosts). Desktop LENS is hover-intent; a click toggles it closed.

## Before/after crops

Both lanes (EN+ZH, dark desktop): FX MoM, margin tell, buyback tell, tape tag
row, sector-table cap, subtitle. Before = `origin/main` template.

## Honest differences vs live

- Fixture VM, not the VPS bake.
- `live_config.js` is absent in this sparse tree; live quote hydration omitted.
- Shared site nav renders; some nav JS 404s are expected and do not change
  the desk cards under test.
