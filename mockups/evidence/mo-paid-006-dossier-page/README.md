# MO-PAID-006 PAGE R1 — official policy statements dossier card

TP-0 visual-evidence receipt for the new `Official policy statements`
dossier card introduced by the MO-PAID-006 PAGE R1 build on
`templates/international_macro.html.j2`. Theme art direction law
(TP-0 2026-08-27) requires dark and light to be TWO art directions,
not one skin; this receipt proves the card satisfies that law across
both themes, both languages, and both viewports.

## The five states

| page_id | route | state | items | stance | leadership |
|---|---|---|---|---|---|
| `euro_area` | `euro_area.html` | `covered` | 3 EC | `null` | `no rights-cleared source` |
| `united_kingdom` | `united_kingdom.html` | `covered` | 2 BoE | `{label:"restrictive", provider_label:"HM Treasury", authoritative:false}` | `no rights-cleared source` |
| `united_kingdom_no_stance` | `united_kingdom--no-stance.html` (synthetic) | `covered` | 2 BoE | `null` (no plain-word read of HM Treasury announcements right now) | `no rights-cleared source` |
| `japan` | `japan.html` | `no_coverage` | 0 | `null` | `no rights-cleared source` |
| `euro_area_outage` | `euro_area--outage.html` (synthetic) | `source_outage` | 0 | `null` | `no rights-cleared source` |

The two synthetic routes exist ONLY in the scratch dir served from
127.0.0.1 — they are not on the production site. They were created so
the `no-stance` (HM Treasury has no current assistant read) and
`source_outage` (the wire is unavailable this refresh) states have
distinct routes to capture against, exactly as the build lane's
12-test page child tests them. `euro_area.html` and `japan.html` are
real production routes and their bytes here are re-rendered from
`origin/main` (the json payloads) plus the branch's template (the
markup), so a reader can compare any captured cell against the live
page at the same composition.

## The 40-cell matrix

5 routes × 2 themes (dark/light) × 2 locales (en/zh) × 2 viewports
(desktop 1440 / mobile 390) = **40 cells**, each with:

- a full-page PNG: `cells/<page_id>-<theme>-<lang>-<viewport>.png`
- a `#official-statements` crop: `cells/crops/<page_id>-<theme>-<lang>-<viewport>.png`
- a DOM fact row in `dom.json` (`card_present`, `dossier_state`,
  `item_count`, `leadership_text`, `stance_attr`, `chip_count`,
  `rail_width`, `rail_display`, `card_background`, `list_background`,
  `chip_border_style`, `scroll_w`, `viewport_w`, `card_bbox`,
  `card_within_viewport`, `title_attr_count`)
- a manifest state in `manifest.json` (p0_evidence.v2; `applied_theme`,
  `applied_locale`, `viewport_width`, `sha256`, `bytes`, `width`,
  `height`)

| state | route | dark en / dark zh | light en / light zh |
|---|---|---|---|
| covered (EZ, 3 EC) | `euro_area.html` | desktop 1440 + mobile 390 | desktop 1440 + mobile 390 |
| covered (GB, 2 BoE, restrictive stance, non-auth) | `united_kingdom.html` | desktop 1440 + mobile 390 | desktop 1440 + mobile 390 |
| covered (GB, 2 BoE, no stance) | `united_kingdom--no-stance.html` | desktop 1440 + mobile 390 | desktop 1440 + mobile 390 |
| no_coverage (JP, 0 items) | `japan.html` | desktop 1440 + mobile 390 | desktop 1440 + mobile 390 |
| source_outage (EZ, 0 items) | `euro_area--outage.html` | desktop 1440 + mobile 390 | desktop 1440 + mobile 390 |

## DARK TREATMENT (command-center)

| mechanism | value |
|---|---|
| surface material | glass `.imd-card` (`backdrop-filter: blur(20px)`, `background: var(--imd-panel)`) |
| inner well | `.imd-dossier-list` sits on `--panel2` (cool slate) |
| link rail | 3 px rail at opacity `.45` on the left of the card (`::before`; `display:block`, `width:3px`) |
| hover affordance | flat colour change on the headline link (`.imd-dossier-headline:hover { color: var(--ink-link) }`) |
| chip border | `1px dashed var(--line)` (chip floats over the rail with a quiet dashed outline) |
| outage ink | `.imd-dossier-outage` in `--ink-warn` (semantic colour carries the message) |
| status dots | flat colour fill (no halo, no glow) |

## LIGHT TREATMENT (research workspace)

| mechanism | value |
|---|---|
| surface material | solid `--panel` with `--line` hairline border + `--card-shadow`; no glass, no blur |
| inner well | `.imd-dossier-list` transparent (no `--panel2`); items separated by `--line` hairlines |
| link rail | none (`html[data-theme="light"] .imd-dossier::before { display: none }`) |
| hover affordance | underline on hover (`.imd-dossier-headline:hover { text-decoration: underline; text-underline-offset: 2px }`) |
| chip border | `solid` (chip sits firmly on the white material; the dashed cue no longer reads as needed) |
| outage ink | `--muted` colour (light material does not need semantic warning ink for a recoverable refresh state) |
| status dots | flat colour fill |

## Mechanisms that intentionally differ

The two treatments are NOT the same CSS with tokens substituted. They
differ in six observable ways:

1. **Surface material.** Dark uses a glass card (`rgba(16,22,30,.62)`,
   `backdrop-filter: blur(20px)`). Light uses a solid card with a
   hairline border and a real shadow (`box-shadow: var(--card-shadow)`).
   Both produce the same outline shape and a `backdrop-filter` reset on
   light (`backdrop-filter: none`).
2. **Inner well.** Dark places the item list on `--panel2` (cool slate);
   light drops the well entirely and relies on `--line` hairlines between
   items for separation.
3. **Link rail.** Dark carries a 3 px rail at `.45` opacity on the
   left of the card. Light removes it — `display: none` — because a
   hairline-bordered card on a white material does not need a quiet
   accent strip; the rail would compete with the card's border.
4. **Hover affordance.** Dark hover = colour change. Light hover =
   underline. These are the language of the two art directions: dark
   is an instrument (colour shift = state), light is a document
   (underline = emphasis).
5. **Chip border.** Dark = `dashed`. Light = `solid`. The dashed cue
   works against the glass material (it reads as a soft outline). On
   white, a dashed edge looks like a rendering bug.
6. **Outage ink.** Dark = `--ink-warn` (semantic warning colour is
   needed to read through the dark glass). Light = `--muted` (a
   recoverable refresh state on white does not need semantic warning
   ink — `--muted` is the same colour voice the rest of the page uses
   for as-of labels).

## Reference baseline

- `.uk-desk` policy watch HTML (`templates/uk-desk.html.j2`, lines
  332-337) — the prior dossier plane the international_macro card
  replaced in this lane. The new card inherits the
  `.imd-dossier-headline:hover { color: var(--ink-link) }` (dark) /
  `text-decoration: underline` (light) hover contract but no longer
  uses the rail.
- This page's own `.imd-card` (the international_macro hero card) —
  the dossier card IS `.imd-card .imd-dossier` so it inherits the
  page's panel/glass material directly; the light treatment overrides
  the inherited glass to solid via the `.imd-dossier` selector and a
  `data-theme="light"` keyed rule.

## Degraded states per theme

| degraded state | dark | light |
|---|---|---|
| `source_outage` (`.imd-dossier-outage`) | `--ink-warn` on `--panel2` with `dashed var(--line)` border | `--muted` on transparent with `dashed var(--line)` border |
| `no_coverage` (`.mx-empty.imd-dossier-empty`) | `mx-empty` shipped default (existing token plane) | `mx-empty` shipped default (existing token plane) |
| `stance absent` on GB (`[data-dossier-stance="none"]`) | dashed chip on glass + `An assistant's read of HM Treasury's latest announcement — context, not a verdict.` plain-word caveat below |
| EZ + `europe_news` present (`a.imd-dossier-more`) | link to `#europe-news` (`Full Europe official press wire`) below the read line |

## DOM-record summary

40/40 cells pass `card_present: true`. `dossier_state` matches the
fixture for every cell. Leadership literal is exact in both languages
across all 40 cells (en: `Leadership statements: no rights-cleared
source.` 20/20; zh: `领导层表态：暂无获准转载的来源。` 20/20).

`rail_display` (computed `::before`) DIFFERS across themes as
required: dark = `block` (rail is drawn), light = `none` (rail is
hidden). `chip_border_style` differs as required on the GB-with-stance
cells: dark = `dashed`, light = `solid`.

All 20 mobile cells satisfy `scroll_w <= viewport_w` — the card sits
inside the 390-px viewport with no horizontal overflow. All 40 cells
satisfy `card_within_viewport` (the card's right edge ≤ viewport
width). `title_attr_count` is 0 on every cell — the dossier slice
never relies on a hover tooltip to communicate.

## What was NOT captured

- Hover/focus states are not captured. The card's CSS has a single
  headline hover (`color: var(--ink-link)` dark /
  `text-decoration: underline` light) and a focus-visible outline
  (`outline: 2px solid var(--link); outline-offset: 2px`); neither is
  required as a separate interaction state beyond the headline hover,
  which is observable in the dark/light treatment contrast above.
- The EZ `a.imd-dossier-more` (link to `#europe-news`, "Full Europe
  official press wire") is conditional on BOTH `europe_news` (the
  fetched wire packet) AND `D.cc == 'EZ'`. The capture here did not
  feed an `europe_news` packet, so the link is absent on every EZ
  cell. The link's CSS is the standard `.imd-dossier-more` rule; its
  presence/absence is pinned by build-lane test 12
  (`tests/test_international_macro_dossier_page.py`).

## Reproduction

```sh
# 1. Render 5 fixture pages into a scratch site from the branch's template.
SCR=$(mktemp -d)
python3 "$SCR/render_pages.py" "$SCR"

# 3. Capture the 40 cells.
python3 "$SCR/capture.py" "$SCR"
```

No credentials. No network beyond the local fixture server.