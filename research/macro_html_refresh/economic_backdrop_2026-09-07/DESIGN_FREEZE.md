# Economic backdrop row — DESIGN FREEZE (2026-09-07)

Operation `macro-briefing-economic-backdrop-design-20260907-sol-001`.
Artifacts: `section.html.j2` (macro `economic_backdrop(cards)`), `section.css.j2` (raw-CSS
partial, included inside an existing `<style>` block, `_risk_radar_card.css.j2` shape).
Design-only child: nothing outside this directory was written, and no rendering, browser,
git or network action was performed.

Governing inputs read: `docs/DESIGN_DOCTRINE.md`, `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`,
`templates/theme.css` (tokens, `.panel`/`.card`, `.dtp`, ink rungs, focus ring),
`templates/dashboard.html.j2` (the `body.page-macro` token block at :1783–1875, the
`.panel > h2` rail idiom, `.card` at :404, the `.sx` mount sequence at :8487/:8687),
`templates/_risk_radar_card.css.j2` (partial convention + the `.rrx` rail it must not
imitate). **Two required inputs could not be read — see §9 GAPS.**

---

## 1. The job, and what earns its place

Question the row answers: *"what is the economy actually doing right now — growth,
prices, financing — and where do I go to check it?"* Three cards, fixed order
**Growth → Inflation → Financial conditions**, never re-sorted by tone or score, because
a row whose order moves is a scoreboard, and a scoreboard is out of scope.

Per card, in reading order: **topic label → state sentence → the caveat → at most two
facts → one calculation cut + data status → one deep link.** That is the whole budget.
Nothing else is admitted: no dial, no bar, no sparkline, no second timestamp, no
per-card disclaimer stack. There is no illustrative chart because none of these three
reads is a shape question — an added chart here would be space-filling, which
DESIGN_SYSTEM §9.13 removes rather than styles.

## 2. Hierarchy — the state is the headline, the topic is the label

The instinctive layout makes "Growth" the card title. That is backwards: the reader
already knows the three topics; what they do not know is the read. So the topic drops to
an eyebrow-grade `h3` (11px/600 caps, `--ink-3`) — semantically a real heading so the
page outline never loses the card — and the **state sentence is the largest, darkest
thing in the card** (`--fs-md` 15px/600, `--ink-1`). The caveat note follows at
`--fs-sm`/`--ink-2`; facts sit below a rule at 13px with tabular figures; the footer meta
is the quietest line on the card at `--fs-label`/`--ink-3`. Four ink grades, one
direction of travel — answer, qualification, evidence, provenance.

Copy is passed through, not authored here: state labels are the existing owner-supplied
source labels (`Accelerating momentum, broad strength` / 动能加速，广度强劲, etc.), and
`note` renders the supplied contradiction sentence. No falsifier/refutation vocabulary
appears anywhere (#3821). The action word is `Investigate` / 查看详情 — never a trade verb.

## 3. Composition and geometry

Section header sits on the **canvas** (design system §3) and carries the page's shared
regime rail via `.ebd-h::before`, so the row joins the existing section rhythm instead of
introducing a second header idiom. The three cards are canonical **`.panel` (E1)**
surfaces — one panel = one answer — not `.card`, because `.card` on this page is
`--panel2`, the E2 member plane; three `--panel2` tiles floating on the canvas with no
parent panel is precisely the light-mode flatness bug. `.panel` keeps a scoped compact
padding (14/16/13 vs the estate's 16/18) to hold the row inside its height budget; that
is the only geometry the composition class overrides.

**Height budget at 1440 (computed, browser proof still owed — §9).** Card content:
label 14 + gap 6 + state 20 + gap 6 + note 2×19=38 + rule/pad 10 + facts 30 + rule/pad 10
+ footer 20 = **154**; plus 27px vertical padding = **181**; plus header row 22 and its
12px margin = **215** ≤ 240, leaving ~25px of headroom.
The longest supplied state (`Disinflating headline, broad/sticky underlying`, 45 chars)
measures ≈322px at 15px Inter against ≈368px of card content width at 1440 — it stays on
one line, so the longest-state line-height debt is **0px**, inside the ≤12px allowance.
That single measurement is the row's tightest assumption and is the first thing to check
in the render.

**Responsive.** 3 columns ≥900px; **single-column stack below 900**, which is this page's
own collapse point (`.span4 → .span12`). 768 deliberately stacks: a third-width card there
is ~236px, which pushes the longest state onto two lines and squeezes the fact pair below
a legible measure — the commission permits three columns at 768 *only if readable*, and it
is not. At 390 all three cards render in full (no truncation, no hiding, no ellipsis) and
the deep link becomes a real 44px-high target. `minmax(0,1fr)` + `min-width:0` +
`overflow-wrap:break-word` everywhere: the page never scrolls horizontally.

## 4. DARK TREATMENT — command centre

Cards are the page's existing graphite `--panel` (#14171e) on the deepened `--bg`
(#0a0c11). **Depth is luminance:** the card/canvas gap does the separating work, so the
hairline stays at the page's quiet `--hair` (72% of `--line`) and the existing `--ms`
shadow (inset top sheen + contact + ambient) supplies the material edge. No new glow, no
bloom, no accent wash — the only lit element in the row is the link ink.

The **tone spine** (3px, left edge) renders as a vertical gradient fading downward,
reusing the page's own `.panel > h2::before` rail idiom, so it reads as instrument
hardware rather than a coloured stripe. Inside the card, the fact strip is separated by a
**hairline rule only**: on graphite a third luminance plane inside a 30px-tall strip
muddies the read and costs instrument calm, and the rule alone is already legible.

## 5. LIGHT TREATMENT — research workspace

White `--panel` on the page's cool `#e8ebf1` canvas. White-on-canvas measures only
~1.19:1, so **the edge carries the card, not the fill**: the raised light `--hair` (90% of
a 16%-ink `--line`) plus the page's light `--ms` two-stop contact/ambient shadow. This is a
different mechanism from dark, not a recolour of it — dark leans on the luminance gap and
under-uses its border; light has no luminance to spend and must draw the boundary.

Three further mechanisms are authored specifically for light:

- **Spine renders solid**, not gradient. A fade-to-transparent rail on white reads as a
  printing defect / smudge rather than as hardware.
- **Fact strip becomes a drawn `--panel2` band** (radius, hairline, inset) instead of a
  rule. On white a bare rule leaves the two figures floating; the band is the light
  equivalent of the depth dark gets for free, and it is the light-safe container idiom
  (design system §12: tint step + hairline).
- **Unavailable card recesses to `--panel2` with no shadow.** In dark the graphite fill
  already says "card"; in light a white card with no content reads as a hole in the sheet,
  so the empty state sits *below* the plane of its siblings.
- **Link hover thickens the underline** rather than brightening the ink; on white a
  brightened link is just a paler link.

Everything else is identical by construction: information architecture, order, type and
spacing scales, state meanings, tone semantics, budgets, breakpoints, focus behaviour and
copy. Two art directions, one semantic system.

**Colour discipline.** The row is achromatic except for two reserved meanings: `--warn`
(health/severity) on the spine, and `--link`-derived ink on the action. No direction hue
touches this row at all — `tone` is an attention grade, not a market call — so 红涨绿跌
has nothing to flip here, and the ZH reader sees no inverted meaning. Deliberately: the
spine is 3px and neutral-by-default so it is not confused with `.rrx`, the risk alert,
which is 4px and always coloured.

## 6. Keyboard, no-JS, screen reader

- Zero JavaScript. The receipt is a native `<details>`; with JS disabled the row is fully
  readable and the receipt still opens.
- Tab order per card: receipt `<summary>` → deep link. Both carry the estate focus ring
  (2px `--link` mix, offset 2–3px). Nothing is hover-only: the receipt opens on click, tap
  and Enter/Space.
- `<section aria-labelledby>` → `h2`; each card `<article aria-labelledby>` → its `h3`, so
  the outline reads Economic backdrop → Growth / Inflation / Financial conditions.
- Three identical "Investigate" links in one row are indistinguishable in a screen-reader
  link list, so each carries a visually-hidden topic suffix (`.ebd-sr`). This is the one
  markup element not in the data contract; it is composed from `title`, adds no field.
- No translated text in `title=` (house law). The only Tier-2 copy is the `<details>`
  receipt body, dual-emitted `.l-en`/`.l-zh` like every other string.
- `prefers-reduced-motion` kills the only two transitions (link ink, chevron rotate).

## 7. State matrix

| State | Spine | Card | State line | Facts | Footer | Link |
|---|---|---|---|---|---|---|
| **Normal** (`tone:neutral`) | achromatic `--hair-strong` | `--panel`, solid hairline | supplied label, `--ink-1` | up to 2, with each fact's own period | `Calculated <asof>` · availability | active |
| **Caveated** (`tone:warn`) | `--warn` | unchanged | unchanged — the words carry the read, never a coloured verdict | unchanged | unchanged | active |
| **Stale / partial** (`tone:warn` + stale availability) | `--warn` | unchanged | last known state, qualified by the supplied `note` | facts keep their own periods | availability caption states the health failure; the calc cut is NOT re-dressed as freshness | active |
| **Unavailable** (`tone:unavailable`) | muted, **dashed border** | dark: graphite; light: recessed `--panel2` | `Read unavailable` / 暂无法读取 at `--ink-2` | omitted entirely | `Source check needed` / 需核对来源 | **still active — the workspace still opens** |

Rules this encodes: a known-last state never wears present-tense success while source
health has failed (the qualification is in the supplied `note` and in the availability
caption, both always visible); one unavailable card never deletes the row — the other two
render normally and the footer keeps its bottom alignment via `margin-top:auto`; a missing
fact's reason arrives **in its value slot**, never as a naked dash, which is why the value
slot uses tabular UI type rather than the page's mono numeral face (mono is for figures,
never words).

**Clocks are never conflated.** Each fact prints its own reference period beside its own
label (July CPI can legitimately sit under a September calculation cut); the card prints
exactly ONE calculation-cut footer, and nothing in this row claims live, today's, fresh or
complete. There is no second as-of anywhere in the section, and no stacked micro-caveats.

## 8. Boundaries honoured

No new global nav, scoreboard, dial, state store, forecast, auth, live painter, source
registry or semantic map. No hero/ticker/existing-card/Risk-disclosure/Release-Radar/Macro-
Command change. No new `:root` family, font stack or runtime-injected stylesheet; all
values are theme/page tokens or `--ebd-*` derivations of them. No new component system:
`.panel` is the card, `.ebd-*` are scoped composition classes only. `.ebd-*` was grepped
against `templates/` — zero pre-existing occurrences, so no page-local shadowing.
The macro computes nothing: an enum guard on `tone`, contract-matching `[:3]`/`[:2]` caps,
and presence checks are its only logic.

## 9. Proof still owed (this design is PARTIAL until the parent renders it)

1. **Evidence matrix — 12 cells, none captured here** (no browser, no Bash in this child):
   dark/light × EN/ZH × 1440 / 768 / 390, whole-page, mounted after the ticker.
2. **The height claim is arithmetic, not a measurement.** Verify ≤240px at 1440 including
   the heading, and verify the longest state stays on one line (the ≈322px vs ≈368px
   assumption in §3). If it wraps, the correction is a 14.5px state, not truncation.
3. **Light `--panel2` fact band on the unavailable card**: it is overridden to `--panel` so
   the band does not disappear into the recessed card — confirm the strip still reads when
   both rules apply (only reachable if a payload ships `unavailable` with facts, which the
   contract says it will not).
4. **Two commissioned reference inputs were unreadable in this session** (paths outside the
   allowed working directory; the tool denied them and cannot be retried here): the
   installed `frontend-design` SKILL.md, and the two committed baselines
   `home-1440-dark-en.png` / `home-1440-light-en.png` in the foreign review worktree. The
   design was therefore anchored on the *source of the geometry* — the shipped
   `body.page-macro` token block, `.panel`/`.card` rules and section-header idiom — plus
   the doctrine and the master design system. A reviewer who can see the baselines should
   check two things specifically: that the compact panel padding matches the neighbouring
   cards' optical density, and that the 3px spine does not read as a second risk rail
   beside the 57px public risk rail already on that page.
