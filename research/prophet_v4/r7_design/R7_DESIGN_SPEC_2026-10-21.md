# R7 design spec — Prophet Opportunity workspace (award-grade)

Date: 2026-10-21. Paper file: PROPHET. Page: `08 · R7 award-grade · Opportunity workspace · DRAFT` (27 artboards).
Status: **design reference only.** Not implemented, not browser-proven and not production-proven. Production tokens
are unchanged; the four R7 tokens exist only in the Paper token set. Sample names, prices and dates are illustrative,
and every board says so in its own footnote.

Authority order used: `docs/DESIGN_DOCTRINE.md` > masterplan §6/§13 (`Prophet_End_to_End_Masterplan_Fable_2026-10-20.md`)
> `templates/theme.css` > live templates (vocabulary only) > Paper. **Read §16 OQ1 before implementing:** merged PR #9566
(2026-10-18) restored the Chairman's compact chart-first card at `/us_stocks.html` and states that draft #9495 must keep
that compact layout.

## 1. Signature idea — the decision line

Every opportunity is read through the same five slots, always in this order:

**Company · Current decision · Timing · What ends it · Lens**

- **One spine, every width.** At 1440 the slots are the ledger's columns; a 40px panel2 spine names them once. At 768 and
  390 the same five slots stack inside each card as label/value pairs, with a fixed 84px label column. In Setup detail
  they are the page's five sections. Compare transposes them: slots become rows and names become columns. A reader learns
  the order once and finds the same answer in the same place on every surface.
- **States replace content, never slots.** Unavailable, stale, not assessed, older-signal-only, revoked and reconstructed
  all render inside the same slot geometry. No slot is ever removed and no row changes height on a state change, so CLS
  from state is 0 by construction.
- **Lens is a filter, not a score.** The three lenses (Early leadership / Quality earnings / Cycle capture) re-key the
  board. Each lens fills Timing and What ends it with its own native evidence (entry window / report checkpoints / cycle
  milestones). A lens without a native entry rule says `Entry not assessed`. It never borrows another lens's stance.
- **Frozen versus live.** A saved list shows `When you saved` beside `Tonight`, so history stays dated (§6.2).
  Corrections sit beside the original and never overwrite it.
- **Hue only for meaning.** Stance is carried by shape plus label, never colour alone:

  | Glyph | Stances |
  |---|---|
  | filled ok dot | Buy |
  | half warn dot | Near |
  | muted ring | Wait |
  | dashed muted ring | Unavailable / Not assessed / Entry not assessed / Entry revoked / Older signal only |

  Surfaces stay achromatic. No container carries a coloured edge (Chairman rule 2026-10-18).

## 2. Artboard set and proof exports

All 27 artboards were screenshot-reviewed in Paper and exported to `proofs/` (PNG, 1x).

| Proof | Artboard | Surface | Width | Theme | Locale |
|---|---|---|---|---|---|
| 01 | R7-01 | Today (ledger, lens switcher, receipt shelf) | 1440 | light | EN |
| 02 | R7-02 | Today | 1440 | dark | EN |
| 03 | R7-03 | Today | 1440 | light | ZH |
| 04 | R7-04 | Today | 1440 | dark | ZH |
| 05 | R7-05 | Today (cards) | 390 | light | EN |
| 06 | R7-06 | Today | 390 | dark | EN |
| 07 | R7-07 | Today | 390 | light | ZH |
| 08 | R7-08 | Today | 390 | dark | ZH |
| 09 | R7-09 | Today, stress reflow | 320 | light | EN |
| 10 | R7-10 | Setup detail | 1440 | light | EN |
| 11 | R7-11 | Setup detail | 1440 | dark | EN |
| 12 | R7-12 | Setup detail | 390 | light | EN |
| 13 | R7-13 | Setup detail | 390 | dark | EN |
| 14 | R7-14 | Lens: Early leadership | 1440 | light | EN |
| 15 | R7-15 | Lens: Quality earnings | 1440 | light | EN |
| 16 | R7-16 | Lens: Cycle capture | 1440 | light | EN |
| 17 | R7-17 | Compare (transposed decision line) | 1440 | light | EN |
| 18 | R7-18 | Compare, grouped by slot | 390 | light | EN |
| 19 | R7-19 | Saved list (when you saved vs tonight) | 1440 | light | EN |
| 20 | R7-20 | Save to list sheet | 390 | light | EN |
| 21 | R7-21 | Save outcomes (waiting / saved / rejected / uncertain) | 390 | light | EN |
| 22 | R7-22 | State: decision unavailable | 390 | light | EN |
| 23 | R7-23 | State: stale quote, entry revoked, reconstructed plan | 390 | light | EN |
| 24 | R7-24 | State: refusal receipt (passed names) | 390 | light | EN |
| 25 | R7-25 | Save to list dialog | 1440 | light | EN |
| 26 | R7-26 | Board states (loading / healthy empty / outage) | 390 | light | EN |
| 27 | R7-27 | Today (two-column cards) | 768 | light | EN |

Variants (HTML sketches, never Paper writes):
- `variants/decision-strip/1–3.html`. Adopted: 1, the ledger spine.
- `variants/lens-switcher/1.html`. Adopted: segmented, one row.
- `variants/receipt-shelf/1.html`. Adopted: a disclosure list on the see-all landing.

## 3. Token additions (add-only)

Paper token set hash before: b80d0392. Hash after: 640746f9.

| Paper token | Light | Dark | Production mapping |
|---|---|---|---|
| `--mx-*-line-quiet` | #E2E6EC | #272C35 | **new** `--line-quiet` in `templates/theme.css` (light + dark blocks); in-row hairlines, receipt dividers |
| `--mx-*-focus` | #2758E6 | #7AA7E0 | **no new production token**: focus = `outline: 2px solid var(--ink-link); outline-offset: 2px` (`--ink-link` already defined, theme.css ~l.382) |

Everything else binds to existing tokens:
- surfaces: bg / panel / panel2;
- text: text / muted;
- dividers: line;
- semantic: ok / warn / up / down;
- ink: ink-up / ink-down / ink-warn / ink-link;
- spacing, radius and type: the existing `--sp-*`, `--r-*` and `--fs-*` steps.

The ledger shadow is light-only: `0 1px 2px rgba(28,36,48,.06)`. Dark has no shadow; depth comes from luminance.

## 4. Type

Inter, with PingFang SC for ZH. Numerals are tabular (`font-feature-settings: 'tnum'`) on every node.

Each role has exactly one weight: 400 regular, 500 medium, 600 semibold. The MASTERMINDX wordmark stays at 700 as an
existing brand asset. In the Paper file, 76 nodes were normalised from 700 to 600.

| Role | Size / line height | Weight |
|---|---|---|
| Page h1 (one per page) | 28/36 | 600 |
| Section h2 | 17/24 or 18/26 (panel titles) | 600 |
| Ticker | 17/22 (ledger), 17/24 (card) | 600 |
| Decision stance | 17/22 | 600 |
| Slot value | 14/20 | 500 or 600 |
| Body | 14/22 | 400 |
| Meta / slot label / caption | 12.5/18 | 400, muted |
| Chart axis and level labels | 11.5/16 | 400 or 500, muted |
| Micro (counts in pills) | 10–11 | 500 |

**ZH parity:** same sizes, line heights raised.

| Size | 10 | 11–12 | 12.5–13 | 14 | 15–17 | 18 | 19–20 | 22–24 | 28 |
|---|---|---|---|---|---|---|---|---|---|
| ZH line height | 16 | 18 | 20 | 22 | 24 | 26 | 28 | 32 | 38 |

ZH uses no letter-spacing and no italics. Figures keep the Latin tabular numerals.

**No-split rule:** a date, a price range or a ticker+qualifier never breaks across lines.
- EN dates: `Oct 20`.
- Price ranges: an en dash followed by U+2060 (word joiner).
- ZH date parentheticals: U+2060.
- Production: wrap these in `<span class="nowrap">` (add the utility to theme.css if absent).

Laws enforced in the file:
- no ALL-CAPS;
- no monospace labels;
- no "→";
- no middot meta strings;
- no emoji;
- typographic apostrophe ’ throughout.

## 5. Geometry

**1440 ledger (R7-01..04, R7-14..16)**
- Board: padding-inline 64, gap 24.
- Ledger panel: r14, 1px line, light shadow.
- Spine: 40 tall, panel2.

| Column | Width |
|---|---|
| select | 36 |
| Company | 252 |
| Current decision | 200 |
| Timing | 312, includes a 104×36 mini chart |
| What ends it | 196 |
| Lens | 156 |
| actions | flex |

- Rows: min-height 88, 1px line-quiet dividers.
- L1 shows at most 8 rows, then `See all N candidates`.
- Lens boards widen the lens column to carry checkpoints: 252/200/200/196/268, with 88px checkpoint labels.

**Setup detail 1440 (R7-10/11)**
- Header decision line.
- Timing panel with the levels chart.
- What-ends-it panel.
- Checkpoints.
- Provenance footnote.

**768 (R7-27)**
- Mobile nav state (production switches at max-width 900px, `navigation-refresh.css` ~l.1405).
- Gutter 20, two-column card grid, gap 12, card width 358.
- Lens switcher on one row.
- Long lens values wrap; they never truncate.

**390 card (R7-05..08)**
- Panel, 1px line-quiet, r12, padding 14/16/16, gap 12, light shadow.
- Header: 20px r5 checkbox, ticker 17/24 600 stacked over the name, 104×36 mini chart docked right.
- Five slot rows with an 84px label column.
- Full-width 40px r10 `Open setup` button.
- Mobile nav: 56.

**320 stress (R7-09)**
- Mini chart moves below the decision.
- Every button is full width.
- No horizontal scroll and no truncated decision text.

**Levels chart**

| Mark | Style | Meaning |
|---|---|---|
| Price line | text ink, 1.75 | daily closes |
| Last close | dot with a 2px panel halo | latest close |
| Entry zone | panel2 band | entry zone |
| Dotted `1.5 4` | muted, 1.25 | chase boundary |
| Dash-dot `10 4 2 4` | muted, 1.25 | entry-method stop |
| Dashed `6 4` | muted, 1.25 | base invalidation |

- Level ink is neutral muted (#5D6B7E) at 1.25. Levels are told apart by dash pattern plus a right-edge price label, never by hue.
- 390 chart: 318×188.
- Caption, mandatory: "Daily closes, <from> to <to>. Lines are the plan’s own levels; none of them is a target."

## 6. Component inventory with states

| Component | Anatomy | States (all drawn unless marked spec) |
|---|---|---|
| Decision line (ledger row / card) | select · Company (ticker, name, sector, quote + change) · decision (glyph, stance, reason, read-at) · timing · what ends it · lens · action | Buy · Near · Wait · Entry not assessed · Not assessed · Unavailable · Older signal only · Entry revoked (stale) · Reconstructed plan · selected (checked) · focus-visible · hover (no information added) |
| Stance glyph | 12px SVG, shape-coded | filled ok / half warn / muted ring / dashed ring; Met/Formed = small ok dot; Rejected + outage = neutral circled X; Uncertain = warn ring with "!" |
| Lens switcher | segmented radiogroup: All candidates · Early leadership · Quality earnings · Cycle capture, each with a count | selected · focus · disabled-with-reason (spec) |
| Ordering note | one muted sentence above every list | always present: "Ordered by original priority — not a current entry recommendation." (lens variants name their own key) |
| Receipt shelf / Passed on tonight | count line + `See all N passed names`; receipt = disclosure button (ticker, title, sector) → What passed (Met/Formed rows) · What didn’t verify · consequence · reassurance · Open research | collapsed · expanded · focus-visible |
| Levels chart + caption | §5 | default · quote stale (last dot hollow, caption names the stale clock) · no plan (chart without levels + sentence) |
| Mini chart | 104×36 price line + entry band | default · no data (muted sentence, same box) |
| Setup detail panels | Timing · What ends it · Checkpoints · Provenance | assessed · entry revoked · reconstructed · not assessed |
| Compare | transposed decision line, max 3 names; 390 grouped by slot, "In the order you picked" | 2–3 selected · fewer than 2 (spec, OQ10) · mixed lenses ("Not ranked…" note) |
| Save to list sheet/dialog | list choice, new list, consequence sentence, Save | idle · waiting (polite live region) · saved read-back · rejected (assertive, "Not saved") · uncertain (polite, "Save not confirmed yet", asked-at time) |
| Saved list | per name: When you saved vs Tonight, change note, correction beside the original | unchanged · changed · corrected (original kept) · tonight unavailable |
| Board states | loading (true-geometry skeleton, `aria-busy`, no shimmer) · healthy empty (sentence + why + count judged) · outage (what failed, what still works, Reload, Last checked; counts unknown, not zero) | all three drawn in R7-26 |
| Sample-data footnote | one muted sentence at board foot | required on every illustrative board |

## 7. EN/ZH copy rules

- **Register.** EN uses plain verbs, sentence case and the second person for the user's own lists. ZH uses a neutral
  written register (您 only for user-owned objects) with full-width punctuation.
- **Separators.** In headings, both locales use a spaced em dash `—`, as the live ZH strings do (OQ9).
- **Market direction ink.**
  - EN: up = green, down = red.
  - ZH: up and down swap through the existing `html[data-lang="zh"]` rule (theme.css ~l.277).
  - Health, stance and save-state ink never flip.
- **Stance words are closed vocabulary:**

  | EN | ZH |
  |---|---|
  | Buy | 买入 |
  | Near | 临近 |
  | Wait | 等待 |
  | Entry revoked | 入场已撤回 |
  | Not assessed | 未评估 |
  | Unavailable | 暂不可用 |
  | Older signal only | 仅有旧信号 |
  | Entry not assessed | 入场未评估 |
  | Not supplied | 未提供 |

  Slot labels:

  | EN | ZH |
  |---|---|
  | Company | 公司 |
  | Current decision | 当前决策 |
  | Timing | 时机 |
  | What ends it | 失效条件 |
  | Lens | 策略 |

  Lens names:

  | EN | ZH |
  |---|---|
  | Early leadership | 早期领涨 |
  | Quality earnings | 优质财报 |
  | Cycle capture | 周期捕捉 |

- **Forbidden copy.**
  - No targets, reward-to-risk, probability, conviction, sizing or "position" language.
  - Saving "doesn’t create a plan or a position".
  - No score words in Compare ("Not ranked…").
- **Complete register.** Appendix A covers every string on every board in both locales:
  - 457 EN rows (367 present, 78 locale-invariant or numeric, 8 superseded during iteration, 4 drawn-only-in-EN with ZH supplied);
  - 99 ZH-only drawn strings, all matched to a row's ZH after whitespace and joiner normalisation (0 unmatched).

## 8. Responsive rules (implementation)

1. Use a container query on the board's own width, not the viewport.
   - **≥1136:** ledger, with these tracks:

     | Column | Track |
     |---|---|
     | Company | `minmax(200px,252px)` |
     | decision | `minmax(176px,200px)` |
     | timing | `minmax(200px,312px)` |
     | what ends | `minmax(168px,196px)` |
     | lens | `minmax(132px,156px)` |
     | actions | `1fr` |

     The mini chart renders only when the timing track is ≥280px.
   - **768–1135:** two-column card grid, gap 12.
   - **<768:** single column.
   - **<360:** stress rules (chart below decision, full-width buttons).
2. The site header follows the existing navigation family only. Its mobile state is ≤900px; there is no third header.
3. Compare at 768: 140px label column plus 3×186px. At 390 it groups by slot.
4. Text wraps and never truncates. A long lens value may take three lines (CRDO at 768 is the accepted example).
5. Touch targets are ≥40px (card button 40, dialog buttons 44). The checkbox is 20px visual inside a 40px hit area.

## 9. Contrast (WCAG 2.x, computed from token hex)

**Light** (ratio against panel #FFFFFF / bg #F7F8FA / panel2 #EEF1F6):

| Ink | panel | bg | panel2 | Allowed use |
|---|---:|---:|---:|---|
| text #1C2430 | 15.62 | 14.70 | 13.80 | all text |
| muted #5D6B7E | 5.43 | 5.11 | 4.79 | secondary text, level lines |
| ink-link / focus #2758E6 | 5.79 | 5.45 | 5.12 | links, focus ring, checked fill (white tick 5.79) |
| ink-up #1E6D47 | 6.30 | 5.93 | 5.56 | positive change text |
| ink-down #B23C3D | 5.82 | 5.48 | 5.14 | negative change text |
| ink-warn #7D5922 | 6.32 | 5.95 | 5.58 | warn text |
| ok #2F8A52 | 4.30 | 4.05 | 3.80 | glyph fill only (≥3:1 non-text) |
| warn #B9791A | 3.61 | 3.40 | 3.19 | glyph only (≥3:1 non-text) |
| up #1F9A55 / down #CF4040 | 3.61 / 4.71 | 3.40 / 4.43 | 3.19 / 4.16 | marks only; use ink-* for text |
| line #C9CCD1 / line-quiet #E2E6EC | 1.61 / 1.25 | — | — | dividers (not information-bearing) |

**Dark** (ratio against panel #181B21 / bg #0F1115 / panel2 #1E222A):

| Ink | panel | bg | panel2 | Allowed use |
|---|---:|---:|---:|---|
| text #D7DCE3 | 12.51 | 13.71 | 11.56 | all text |
| muted #8B93A1 | 5.57 | 6.11 | 5.15 | secondary text, level lines |
| link / focus #7AA7E0 | 6.92 | 7.59 | 6.40 | links, focus, checked fill (tick must be #0F1115: 7.59; white would be 2.49) |
| up #45B873 / down #E06464 | 6.86 / 5.07 | 7.52 / 5.56 | 6.34 / 4.69 | change text and marks |
| warn #E0A030 / ok #3DA564 | 7.59 / 5.56 | 8.31 / 6.09 | 7.01 / 5.13 | glyphs and text |
| line #3A4150 / line-quiet #272C35 | 1.69 / 1.23 | — | — | dividers |

Result:
- Every text pair used on the boards is ≥4.5:1 in both themes.
- Every information-bearing non-text mark (glyphs, focus ring, checkbox border = muted) is ≥3:1.
- The light checkbox border was changed from line (1.61) to muted (5.43) for 1.4.11.

## 10. Accessibility and interaction

- One h1 per page and h2 per panel. The ledger is a real `<table>`:
  - a caption naming the ordering;
  - `scope="col"` headers that match the five slot labels;
  - row headers on Company.
- Cards are `<article>` elements whose heading is the ticker and name. Slot labels are `<dt>` and values are `<dd>`.
- Stance is always a text label. Glyphs are `aria-hidden`.
- Charts carry a text alternative: the caption plus a visually-hidden list of level values. No information exists only on
  hover. Mini-chart detail opens by keyboard or touch through `Open setup`.
- The lens switcher uses `role="radiogroup"` with arrow-key movement. Counts are part of each option's accessible name.
- The receipt is a `<button aria-expanded>` disclosure.
- Save outcomes:

  | State | Announcement |
  |---|---|
  | waiting, uncertain | `aria-live="polite"` |
  | rejected | `role="alert"` (assertive) |
  | saved | announces the read-back text |

  Focus returns to the invoking control on close.
- Focus: 2px ring in the link ink with a 2px offset, never removed, never clipped by overflow.
- Reduced motion: every transition goes to 0ms. The skeleton never shimmers.

## 11. Motion and Core Web Vitals

- **Motion budget.** The only motion is a 120ms opacity/transform on sheet open and close and on disclosure expand, and
  only when the user acts. No entrance animation, no count-up and no shimmer.
- **CLS ≤0.1, designed to 0.**
  - The skeleton has the final geometry.
  - States swap content inside fixed slot geometry.
  - The mini chart reserves 104×36.
  - The sheet overlays rather than pushing content.
- **LCP ≤2.5s.** The LCP element is the h1 or the first ledger row, which is text. Charts are inline SVG under 3KB each,
  no web-font flash beyond the existing Inter strategy, and no new image assets.
- **INP ≤200ms.** The lens switch filters already-rendered rows (CSS/attribute toggle, no re-render of the chart SVGs).
  The compare checkbox only toggles state; the compare view renders on demand.

## 12. Acceptance checklist mapped to masterplan §13

**§13 rows**

| # | §13 row | Where | Status |
|---|---|---|---|
| 1 | Candidate outside the featured shelf | R7-01/14–16 `See all N`, R7-26 | Drawn |
| 2 | Intake accepted, then the clock fails | R7-22 (assessment didn’t publish), R7-26 outage | Drawn |
| 3 | Quote with no native assessment | R7-01 `Not assessed` row, R7-22 | Drawn |
| 4 | Qualified entry | R7-01 Buy row, R7-10/12 setup detail | Drawn |
| 5 | Stale / expired / future-clock fact | R7-23 (stale quote revokes entry); expired + future-clock = same revoked state | Drawn (stale); spec (future-clock) |
| 6 | Quote/basis mismatch | Revoked state with reason "Quote and plan use different bases" | Spec only |
| 7 | Corrected / retracted source | R7-19 correction kept beside the original; retracted = same pattern, "Withdrawn on <date>" | Drawn (corrected); spec (retracted) |
| 8 | Selected-card study and back | Selection persists through Open setup and Back; restore focus and scroll | Spec only |
| 9 | Exact / related / no Plan | R7-10 "No open same-security model record found…"; R7-23 reconstructed | Partial; related-Plan copy spec |
| 10 | Save succeeds | R7-20/21/25, R7-19 read-back | Drawn |
| 11 | Save ambiguous | R7-21 uncertain | Drawn |
| 12 | Research watch vs position | R7-18/19/20 "Saving doesn’t create a plan or a position" | Drawn |
| 13 | Holding vs new entry | R7-01 footnote "not your holdings or fills"; dedicated holding row | Spec only |
| 14 | Healthy empty vs outage | R7-26 | Drawn |
| 15 | EN/ZH and light/dark | R7-01..08, R7-10..13 | Drawn (Today + Setup) |
| 16 | Track record | Not on this page; link target only | Spec only |

**§13.1 checks**
1. A non-featured candidate is one action away (`See all 16 candidates`, lens counts).
2. Strategy, horizon and leading risk are the Lens, Timing and What ends it slots.
3. Research-worthy but not enterable: `Entry not assessed`, the refusal receipt and `Older signal only`.
4. Historical setup vs quote vs decision vs holding:
   - read-at lines;
   - "Source date is not a quote timestamp";
   - When you saved vs Tonight;
   - the holdings footnote.
5. Save and retrieve the original: R7-19.
6. Compare without commensurability: "Not ranked…" (R7-17/18).
7. Record vs P&L: no P&L appears anywhere; the footnote says "System model plan — not your holdings or fills".
8. Unavailability vs uncertainty vs negative:

   | Case | Glyph | Example |
   |---|---|---|
   | Unavailable / not assessed | dashed ring | |
   | Uncertain save | warn "!" | |
   | Negative | neutral X | Rejected / Not saved |

**§6.2 truth rules**
- A quote is not a Buy (R7-22/23).
- Missing ≠ Wait: R7-22 states it.
- History is dated: read-at lines and saved dates.
- Unavailable is not a stage (R7-19/22).
- Independent invalidation is always visible: What ends it never collapses.
- Stale facts revoke entry (R7-23).
- Waiting never instructs: Wait rows carry no action verb beyond Open setup.
- Sample labels are on every board.
- Ordering is labelled on every list.

**§6.4 persistence:** four save states, a read-back time, and a check before any re-save so nothing is saved twice.

**§6.5:** see §8–§11 above.

**Commission checks**
- No container edge accent anywhere on the page (audited: 0).
- No middots, "→", ALL-CAPS or Menlo in content.
- No straight apostrophes.
- All fills are bound to tokens.

## 13. Template-by-template implementation map

All changes are proposals for a routed builder; none are made here. Line numbers are as of origin/main at session start.

- **`templates/theme.css`**
  - Add `--line-quiet` (light #E2E6EC, dark #272C35).
  - Add a `.nowrap{white-space:nowrap}` utility if it is absent.
  - Make no other token changes. Focus reuses `--ink-link`.
- **`templates/_prophet_workspace.css.j2`** (13 lines; overlay pointer-events safeguard)
  - Keep the safeguard.
  - Add the decision-line CSS: the container query (§8), slot grid tracks, stance glyph classes, state classes, chart line-dash classes and the skeleton.
- **`templates/_us_board_cards.html.j2`** (315 lines; setup-detail body near l.288)
  - This is **the compact chart-first card protected by #9566**.
  - Add the five-slot block beneath the chart with fixed slot geometry, the state copy and the stance glyph.
  - Do not widen or heighten the card beyond the #9566 envelope (OQ1).
- **`templates/_us_prophet_plan_cards.html.j2`** (included at `dashboard.html.j2` ~l.17164)
  - Plan card states: Entry revoked, Reconstructed from the <date> plan, Older signal only.
- **`templates/dashboard.html.j2`**
  - `#us-standouts` (~l.16664) gets the h2 `Tonight’s US opportunities`, the lens radiogroup with counts, the ordering note, `See all N`, and the Passed on tonight count.
  - The row macros (~l.16799, 17484, 17625, 17683) adopt the slot order.
  - The includes at ~l.16384 / 17097 / 17341 are unchanged.
- **`templates/_prophet_setup_detail.html.j2`** (121 lines)
  - Timing panel with the levels chart (§5) and the mandatory caption, the What ends it panel, the checkpoints table, the provenance footnote, and the revoked / reconstructed / not-assessed variants.
- **`templates/_prophet_receipts.html.j2`** (236 lines)
  - Refusal receipt disclosure (§6) on the see-all landing.
  - Today shows only the count and a link (L1 budget).
- **`templates/_us_candidate_pool*.html.j2`**
  - All candidates landing: the full ledger (≥1136) or cards, with the same ordering note.
- **`templates/plans.html.j2`**
  - Exact / related / no Plan copy; the reconstructed-plan banner.
- **`templates/watchlist.html.j2`** (~l.827), **`watchlist.js`**, **`watchstore.js`**
  - The four save states.
  - Read-back from the account store.
  - A list check before any re-save (idempotent).
  - Live regions per §10.
  - Saved list "When you saved / Tonight" columns, with the correction kept beside the original.
  - `watchlist_risk.js`: read-only consumer; verify that no risk/position wording is added.
- **`engine/prophet_bridge.py` `REFUSAL_COPY`** with **`tests/test_prophet_whynot_receipts.py`** (import ~l.47, asserts ~l.313–315)
  - The proposed title change must land together with its pinned test (OQ5).
  - EN: "Passed the board’s checks — tonight’s plan data didn’t verify".
  - ZH: "已通过榜单检查 — 今晚的计划数据未能核实".
- **Leave untouched:** `templates/_prophet_card.html.j2` (shared by other surfaces), the navigation family files and `navigation-refresh.css`.
- **Tests to extend:** `tests/test_us_board_*`, `tests/test_grade_us_board.py`. New guards:
  1. Five slot labels present per row or card in EN and ZH.
  2. No `border-left`/`box-shadow inset` accent on Prophet containers.
  3. A state change keeps the slot count.
  4. `Entry not assessed` / `Unavailable` never co-occur with a Buy glyph.
  5. Stale quote implies no Buy.
  6. Sample-data footnote present when fixture data renders.

## 14. Open design questions

1. **OQ1 (blocking for implementation): ledger vs #9566 compact card.**
   - #9566 restored the Chairman's compact chart-first cards and binds #9495 to that layout.
   - Recommended default: carry the R7 semantics, states, copy, tokens and type into the compact card (390/768 card anatomy), and use the 1440 ledger only on the All candidates landing.
   - Needs a seat or Chairman ruling before Today at 1440 becomes a ledger.
2. **OQ2: native entry glyph for Quality earnings and Cycle capture.** These lenses have no native entry rule today, so they show `Entry not assessed`. Should a future native rule get its own stance words, or reuse Buy/Near/Wait?
3. **OQ3: health-bad token.** Outage uses a neutral circled X and plain text. A dedicated health-bad ink would need a production token, which is out of scope here.
4. **OQ4: shelf chevrons.** The passed-names shelf uses a disclosure chevron. Should the today-page count link carry one too, or stay plain text?
5. **OQ5: REFUSAL_COPY wording.** The change spans engine and tests (§13) and needs the bridge owner's agreement.
6. **OQ6: regional extension.** HK and CA reuse the decision line. HK grade semantics wait behind #7288 (seat ruling F19).
7. **OQ7: light up/down tokens below AA as text.** Change text must use ink-up/ink-down. Should production add lint for this?
8. **OQ8: light warn/orange are non-text only.** Confirm that no template uses `--warn` as text colour in light.
9. **OQ9: ZH dash convention.** Spaced em dash `—` vs the ZH double dash `——` in headings. The live strings use the former.
10. **OQ10: compare with fewer than two selected.** Proposed copy: "Pick 2 or 3 names to compare." with the button disabled and the reason given. Not drawn.
11. **OQ11: coverage gaps.**
    - Dark is drawn only for Today and Setup; ZH only for Today; 768 only for Today light EN.
    - The remaining cells follow the same tokens and rules but are not drawn.

## Appendix A. EN/ZH copy register (every string drawn on page 08)

Generated from the Paper text census of all 27 artboards (scratch `register.json`). No-break characters are shown as ordinary spaces. Status key:

- **present**: drawn in EN, with ZH drawn or specified.
- **invariant**: a ticker, number or symbol that is identical in both locales.
- **superseded**: replaced during iteration and no longer on any board; kept for traceability.
- **EN-drawn**: drawn only on an EN board, with the ZH supplied here.

Each row is grouped under the first surface that carries it, and the same string recurs on its other surfaces. R7-02/04/06/08/11/13 (dark) reuse the strings of their light twins. R7-27 (768) reuses R7-05.

Coverage check: 457 EN rows; 99 ZH strings drawn on ZH boards, of which 0 lack a matching register ZH after whitespace and joiner normalisation.

### R7-01

| EN | ZH | Status | Also on |
|---|---|---|---|
| MASTERMINDX | MASTERMINDX | present | R7-05, R7-18 |
| United States ▾ | 美国 ▾ | present | — |
| China ▾ | 中国 ▾ | present | — |
| Hong Kong ▾ | 香港 ▾ | present | — |
| Canada ▾ | 加拿大 ▾ | present | — |
| International ▾ | 国际 ▾ | present | — |
| Other Assets ▾ | 其他资产 ▾ | present | — |
| Research ▾ | 研究 ▾ | present | — |
| Search tickers | 搜索代码 | present | — |
| Prophet | Prophet | present | — |
| Today | 今晚 | present | R7-05, R7-10, R7-12, R7-18, R7-22, R7-23, R7-24 |
| All candidates | 全部候选 | present | R7-05, R7-18 |
| Plans | 计划 | present | R7-05, R7-18, R7-26 |
| Saved lists | 已保存列表 | present | R7-05, R7-18, R7-26 |
| Tonight’s US opportunities | 今晚的美股机会 | present | R7-05 |
| Which names have a real, current opportunity, and what would end it. | 哪些股票有真实、当前的机会，以及什么会让它失效。 | present | R7-05 |
| Board built Oct 20, after the close | 榜单建于 10月20日收盘后 | present | R7-05, R7-10, R7-12, R7-18, R7-22, R7-23, R7-24, R7-26 |
| Quotes as of 16:00 ET, Oct 20 | 报价截至 10月20日 16:00（美东） | present | R7-05, R7-10, R7-12, R7-18, R7-22 |
| 3 of 16 | 16 只中有 3 只 | invariant | R7-05 |
| have an entry ready now. | 现在可以入场。 | present | R7-05 |
| 7 | 7 只 | invariant | R7-05 |
| are setting up or waiting. | 正在形成或等待。 | present | R7-05 |
| 6 | 6 只 | invariant | R7-05 |
| can’t be judged tonight, and each one says why. | 今晚无法判断，每只都写明了原因。 | present | R7-05 |
| All | 全部 | present | R7-05 |
| 16 | (same as EN) | invariant | R7-05 |
| Early leadership | 早期领涨 | present | R7-05, R7-10, R7-14, R7-17, R7-18, R7-23 |
| 8 | (same as EN) | invariant | R7-05 |
| Quality earnings | 优质财报 | present | R7-05, R7-17, R7-18 |
| 5 | (same as EN) | invariant | R7-05 |
| Cycle capture | 周期捕捉 | present | R7-05, R7-17, R7-18, R7-22 |
| 3 | (same as EN) | invariant | R7-05, R7-14, R7-15 |
| Compare | 对比 | present | R7-05, R7-10, R7-12, R7-22, R7-23 |
| 2 selected | 已选 2 只 | present | R7-05 |
| Company | 公司 | present | R7-10, R7-17, R7-18, R7-19 |
| Current decision | 当前决策 | present | R7-05, R7-10, R7-17, R7-18, R7-22, R7-23 |
| Timing | 时机 | present | R7-05, R7-10, R7-12, R7-17, R7-18, R7-22, R7-23 |
| What ends it | 失效条件 | present | R7-05, R7-10, R7-17, R7-18, R7-22, R7-23 |
| Lens | 策略 | present | R7-05, R7-10, R7-17, R7-18, R7-22, R7-23 |
| NVDA | (same as EN) | invariant | R7-05, R7-10, R7-19 |
| NVIDIA Corporation | 英伟达公司 | superseded | — |
| Semiconductors. Quote $225.07, up 0.22% at 16:00 ET | 半导体。16:00（美东）报价 $225.07，上涨 0.22% | superseded | — |
| Buy | 买入 | present | R7-05, R7-10, R7-17, R7-18, R7-19 |
| Entry is ready now | 现在可以入场 | present | R7-05, R7-10, R7-17, R7-18, R7-19 |
| Assessed Oct 20 close | 评估于 10月20日收盘 | present | R7-05, R7-10, R7-17, R7-18, R7-19 |
| Entry zone $220.50 to $225.10 | 入场区间 $220.50 至 $225.10 | superseded | — |
| Inside the zone today | 今日位于区间内 | superseded | — |
| Base invalidation | 筑底失效位 | present | R7-05, R7-10, R7-12, R7-17, R7-18, R7-23 |
| Close below $212.40 | 收盘跌破 $212.40 | present | R7-05, R7-10, R7-12 |
| Stage: Ready | 阶段：就绪 | present | R7-05, R7-10 |
| Open setup | 查看形态 | present | R7-05, R7-17, R7-18, R7-19 |
| NVIDIA | 英伟达 | present | R7-05, R7-10, R7-19 |
| Semiconductors | 半导体 | present | R7-05, R7-10, R7-17, R7-19, R7-23 |
| $225.07 | (same as EN) | invariant | R7-05, R7-10 |
| +0.22% | (same as EN) | invariant | R7-05, R7-10 |
| Entry zone | 入场区间 | present | R7-10, R7-12, R7-17, R7-18, R7-23 |
| $220.50–225.10 | (same as EN) | invariant | R7-10 |
| Price is inside the zone | 价格在区间内 | present | R7-05, R7-10, R7-12, R7-17, R7-18 |
| ANET | (same as EN) | invariant | R7-05, R7-19 |
| Arista Networks | Arista Networks | present | R7-05, R7-19 |
| Computer networking | 计算机网络 | present | R7-05 |
| $142.18 | (same as EN) | invariant | R7-05 |
| −0.41% | (same as EN) | invariant | R7-05 |
| Near | 临近 | present | R7-05, R7-19, R7-22 |
| Entry may be near | 入场可能临近 | present | R7-05 |
| $136.80–140.20 | (same as EN) | invariant | — |
| 1.4% above the zone | 高于区间 1.4% | present | R7-05 |
| Close below $129.60 | 收盘跌破 $129.60 | present | R7-05 |
| Stage: Turning | 阶段：转折 | present | R7-05 |
| VKTX | (same as EN) | invariant | R7-05 |
| Viking Therapeutics | Viking Therapeutics | present | R7-05 |
| Biotechnology | 生物科技 | present | R7-05 |
| $35.56 | (same as EN) | invariant | R7-05 |
| −3.24% | (same as EN) | invariant | R7-05 |
| Wait | 等待 | present | R7-05, R7-19 |
| Wait for a pullback | 等待回调 | present | R7-05 |
| $30.20–32.40 | (same as EN) | invariant | — |
| 9.8% above the zone | 高于区间 9.8% | present | R7-05 |
| Close below $27.90 | 收盘跌破 $27.90 | present | R7-05 |
| Stage: Trend | 阶段：趋势 | present | R7-05 |
| CRDO | (same as EN) | invariant | R7-05, R7-23 |
| Credo Technology | Credo Technology | present | R7-05, R7-23 |
| $88.14 | (same as EN) | invariant | R7-05, R7-23 |
| Last quote 11:42 ET | 最后报价 11:42（美东） | present | R7-05, R7-23 |
| Entry revoked | 入场已撤回 | present | R7-05, R7-23 |
| Price ticks are stale | 价格数据过期 | present | R7-05, R7-23 |
| Returns when quotes refresh | 报价刷新后恢复 | present | R7-05, R7-23 |
| $84.10–86.90 | (same as EN) | invariant | R7-23 |
| Can’t confirm on a stale quote | 报价过期，无法确认 | present | R7-05, R7-23 |
| Close below $79.80 | 收盘跌破 $79.80 | present | R7-05, R7-23 |
| Stage: Ready, Oct 20 | 阶段：就绪（10月20日） | present | R7-05, R7-23 |
| PFE | (same as EN) | invariant | R7-05, R7-16, R7-22 |
| Pfizer | 辉瑞 | present | R7-05, R7-16, R7-22 |
| Pharmaceuticals | 制药 | present | R7-05 |
| $28.67 | (same as EN) | invariant | R7-05 |
| +0.10% | (same as EN) | invariant | R7-05 |
| Not assessed | 未评估 | present | R7-05, R7-14, R7-15, R7-22 |
| No earnings assessment yet | 尚无财报评估 | present | R7-05 |
| A current quote is not a decision | 有最新报价不等于有决策 | present | R7-05 |
| Next report | 下次财报 | present | R7-05, R7-15, R7-17, R7-18 |
| Not supplied | 未提供 | present | R7-05, R7-10, R7-15, R7-17, R7-18, R7-23 |
| Invalidation | 失效位 | present | R7-05, R7-15, R7-17, R7-18 |
| Maturity not assessed | 成熟度未评估 | present | R7-05 |
| LFUS | (same as EN) | invariant | R7-05, R7-16, R7-22 |
| Littelfuse | 力特 | present | R7-05, R7-16, R7-22 |
| Electronic components | 电子元件 | present | R7-05, R7-22 |
| $429.22 | (same as EN) | invariant | R7-05, R7-22 |
| +1.05% | (same as EN) | invariant | R7-05, R7-22 |
| Unavailable | 暂不可用 | present | R7-05, R7-19, R7-22 |
| Tonight’s assessment didn’t publish | 评估未发布 | present | — |
| Last published Oct 17 | 最近发布于 10月17日 | present | R7-05, R7-19, R7-22 |
| Next milestone | 下一里程碑 | present | R7-05, R7-17, R7-18, R7-22 |
| Not yet supplied | 尚未提供 | present | R7-05, R7-22 |
| Funding check | 资金检查 | present | R7-05, R7-22 |
| Unknown tonight | 今晚未知 | present | R7-05, R7-22 |
| Stage not assessed | 阶段未评估 | present | R7-05, R7-14, R7-22 |
| See all 16 candidates | 查看全部 16 只候选 | present | R7-05 |
| Ordered by original priority — not a current entry recommendation. | 按建立时优先级排序 — 并非当前入场建议。 | present | R7-05 |
| Passed on tonight | 今晚未纳入 | present | R7-05, R7-24 |
| 4 of 20 | 20 只中的 4 只 | invariant | R7-05 |
| Watch — don’t chase. Each rejoins the board when its setup completes. | 观望，不要追。形态走完，它们会自己回到榜上。 | present | R7-05, R7-24 |
| SMCI | (same as EN) | invariant | R7-05, R7-24 |
| Ran too far — waiting for a pullback | 涨得太急 — 等回调 | present | R7-05, R7-24 |
| MOS | (same as EN) | invariant | R7-05, R7-24 |
| Still heading down | 方向仍朝下 | present | R7-05, R7-24 |
| HOOD | (same as EN) | invariant | R7-05, R7-24 |
| No entry trigger yet | 暂无买点 | present | R7-05, R7-24 |
| ALAB | (same as EN) | invariant | R7-05, R7-24 |
| Passed the board’s checks — tonight’s plan data didn’t verify | 已通过榜单检查 — 今晚的计划数据未能核实 | present | R7-05, R7-24 |
| See all 20 passed names | 查看全部 20 只未纳入标的 | present | R7-05 |
| Re-drawn nightly. System model plan — not your holdings or fills. | 每晚重绘。系统模型计划——并非您的实际持仓或成交。 | present | R7-05 |
| Sample names and prices for design review, not live signals. | 示例名称与价格，仅供设计评审，并非实时信号。 | present | R7-05, R7-10 |
| Assessment didn’t publish | 评估未发布 | present | R7-05, R7-19, R7-22 |

### R7-02

| EN | ZH | Status | Also on |
|---|---|---|---|
| EN | 中文 | invariant | — |

### R7-05

| EN | ZH | Status | Also on |
|---|---|---|---|
| Showing 6 of 16 | 显示 16 只中的 6 只 | present | — |
| Entry zone $220.50–225.10 | 入场区间 $220.50–225.10 | present | — |
| Entry zone $136.80–140.20 | 入场区间 $136.80–140.20 | present | — |
| Entry zone $30.20–32.40 | 入场区间 $30.20–32.40 | present | — |
| Entry zone $84.10–86.90 | 入场区间 $84.10–86.90 | present | R7-23 |

### R7-10

| EN | ZH | Status | Also on |
|---|---|---|---|
| NVIDIA setup and timing | 英伟达的形态与时机 | present | R7-12 |
| Why this setup is on tonight’s board, when it is ready, and what would end it. | 这个形态为何在今晚的榜单上、何时就绪，以及什么会让它失效。 | present | R7-12, R7-22, R7-23 |
| Save to list | 保存到列表 | present | R7-12, R7-22, R7-23 |
| Price closed at $225.07, inside the entry zone. The entry read is the owner’s assessment at that date; a later quote inside the zone does not renew it. | 收盘价 $225.07，位于入场区间内。入场判断是数据所有方在该日期的评估；之后区间内的报价不会使其续期。 | present | R7-12 |
| Chase boundary | 追高边界 | present | R7-12 |
| Entry-method stop | 入场方法止损位 | present | R7-12 |
| Aug 25 | 8月25日 | present | R7-12 |
| Sep 22 | 9月22日 | present | R7-12 |
| Oct 20 | 10月20日 | present | R7-12 |
| Daily closes, Aug 25 to Oct 20. Lines are the plan’s own levels; none of them is a target. | 8月25日至10月20日每日收盘价。各条线是计划自身的价位，均不是目标价。 | present | R7-12 |
| Price levels | 价位 | present | R7-12 |
| Entry zone · low/high | (same as EN) | superseded | — |
| $231.80 | (same as EN) | invariant | R7-12 |
| Above it, the setup has run. Not a target. | 高于此位，说明行情已走出。不是目标价。 | present | R7-12 |
| $216.30 | (same as EN) | invariant | R7-12 |
| Belongs to the entry method, not the base | 属于入场方法，而非筑底形态 | present | R7-12 |
| What ends the setup | 形态的失效条件 | present | R7-12 |
| Entry stop and base invalidation are different. Chase boundary is not a target. | 入场止损位与筑底失效位不同。追高边界不是目标价。 | present | R7-12 |
| Why it is here | 为何在榜单上 | present | — |
| Entry conditions | 入场条件 | present | — |
| Above 200-day trend | 位于 200 日趋势线上方 | present | R7-24 |
| Met | 已满足 | present | R7-24 |
| Weekly confirmation | 周线确认 | present | R7-24 |
| Base formation | 筑底形态 | present | R7-24 |
| Formed | 已形成 | present | R7-24 |
| Source stage | 来源阶段 | present | — |
| Ready | 就绪 | present | R7-14, R7-17 |
| Selection is not entry permission. Setup type is not an assigned strategy. | 入选不等于可以入场。形态类型不是指定的策略。 | present | — |
| Strategy lens | 策略视角 | present | — |
| Stage | 阶段 | present | — |
| Holding horizon | 持有期限 | present | — |
| Targets and holding period are not available in this view. No reward-to-risk ratio or success probability is calculated. | 此视图不提供目标价和持有期。不计算盈亏比或成功概率。 | present | — |
| Plan connection | 计划关联 | present | — |
| No open same-security model record found. No plan or position is created here. | 未找到同一证券的未平模型记录。此处不会创建计划或仓位。 | present | — |
| View in Plans | 在计划中查看 | present | — |
| Source dates | 来源日期 | present | R7-23 |
| Signal date | 信号日期 | present | R7-23 |
| Oct 9 | 10月9日 | present | R7-23 |
| Plan as of | 计划截至 | present | R7-23 |
| Oct 20 close | 10月20日收盘 | present | — |
| Quote timestamp | 报价时间 | present | R7-23 |
| 16:00 ET, Oct 20 | 10月20日 16:00（美东） | present | R7-23 |
| Source as-of | 来源截至 | present | R7-23 |
| Source date is not a quote timestamp. Missing clocks remain missing. | 来源日期不是报价时间。缺失的时间保持缺失。 | present | R7-23 |
| Evidence & source details | 证据与来源详情 | present | — |
| Original source, receipts and check results | 原始来源、凭证与检查结果 | present | — |

### R7-12

| EN | ZH | Status | Also on |
|---|---|---|---|
| $225.10 | (same as EN) | invariant | — |
| $220.50 | (same as EN) | invariant | — |
| $212.40 | (same as EN) | invariant | — |
| $220.50 – 225.10 | (same as EN) | invariant | — |

### R7-14

| EN | ZH | Status | Also on |
|---|---|---|---|
| 2 of 8 | 8 只中有 2 只 | invariant | — |
| 4 | (same as EN) | invariant | — |
| 2 | (same as EN) | invariant | — |
| What is emerging early, what is supporting it, and what opportunity remains? | 什么正在早期出现、什么在支撑它、还剩下什么机会？ | present | — |
| An entry window lasts 2 to 15 sessions. It is not a holding period. | 入场窗口持续 2 至 15 个交易日。它不是持有期。 | present | — |
| Where the 8 names stand tonight | 今晚这 8 只标的所处位置 | present | — |
| Bottoming | 筑底 | present | — |
| 1 | (same as EN) | invariant | R7-15 |
| Turning | 转折 | present | — |
| Trend | 趋势 | present | — |
| Not assessed is not a stage. It means tonight’s assessment didn’t publish for that name. | 未评估不是阶段。它表示该标的今晚的评估未发布。 | present | — |
| Entry window is open | 入场窗口已打开 | present | R7-17, R7-18 |
| Not there yet | 尚未触发 | present | — |
| The move already started | 行情已经启动 | present | — |
| Ready, Oct 20 read | 就绪（10月20日读数） | present | — |
| Window open, quote stale | 窗口已打开，报价过期 | present | — |
| Not a stage | 不是阶段 | present | — |
| Unavailable is not a stage | 暂不可用不是阶段 | present | — |
| COHR | (same as EN) | invariant | — |
| Coherent | Coherent | present | — |
| Optical components | 光学元件 | present | — |
| $96.40 | (same as EN) | invariant | — |
| +0.62% | (same as EN) | invariant | — |
| VRT | (same as EN) | invariant | R7-17, R7-18, R7-19 |
| Vertiv | 维谛技术 | present | R7-17, R7-18, R7-19 |
| Electrical equipment | 电气设备 | present | R7-17, R7-18, R7-19 |
| $118.42 | (same as EN) | invariant | R7-17, R7-18 |
| +1.36% | (same as EN) | invariant | R7-17, R7-18 |
| $114.60–119.30 | (same as EN) | invariant | R7-17, R7-18 |
| Close below $109.80 | 收盘跌破 $109.80 | present | R7-17, R7-18 |
| See all 8 in Early leadership | 查看早期领涨中的全部 8 只 | present | — |
| 4 of 11 | 11 只中的 4 只 | invariant | — |
| See all 11 passed in Early leadership | 查看早期领涨中全部 11 只未纳入标的 | present | — |

### R7-15

| EN | ZH | Status | Also on |
|---|---|---|---|
| ADBE | (same as EN) | invariant | R7-16, R7-17, R7-18, R7-19 |
| Adobe | 奥多比 | present | R7-16, R7-17, R7-18, R7-19 |
| Software | 软件 | present | R7-17, R7-18, R7-19 |
| $356.20 | (same as EN) | invariant | R7-17, R7-18 |
| +0.84% | (same as EN) | invariant | R7-17, R7-18 |
| Entry not assessed | 入场未评估 | present | R7-17, R7-18, R7-19 |
| No entry rule in this lens | 此策略没有入场规则 | present | R7-17, R7-18 |
| Read Oct 20 close | 读取于 10月20日收盘 | present | R7-17, R7-18, R7-19 |
| Dec 10 | 12月10日 | present | R7-17, R7-18 |
| Checkpoints re-read after it | 之后重新读取检查点 | present | R7-17, R7-18 |
| No exit rule in this lens yet | 此策略尚无退出规则 | present | R7-17, R7-18 |
| Reported | 已报告 | present | R7-17, R7-18 |
| Improved | 改善 | present | R7-17, R7-18 |
| Consensus | 一致预期 | present | R7-17, R7-18 |
| Revised up | 上修 | present | R7-17, R7-18 |
| Guidance | 指引 | present | R7-17, R7-18 |
| Raised | 上调 | present | R7-17, R7-18 |
| Open research | 查看研究 | present | R7-17, R7-18, R7-19, R7-24 |
| COST | (same as EN) | invariant | R7-16 |
| Costco | 好市多 | present | R7-16 |
| Consumer staples retail | 必需消费品零售 | present | — |
| $912.35 | (same as EN) | invariant | — |
| −0.27% | (same as EN) | invariant | — |
| Dec 11 | 12月11日 | present | — |
| Not qualified | 来源不合格 | present | — |
| $25.18 | (same as EN) | invariant | — |
| +0.40% | (same as EN) | invariant | — |
| Oct 28 | 10月28日 | present | — |
| Mixed | 好坏参半 | present | — |
| Held | 维持 | present | — |
| NKE | (same as EN) | invariant | R7-16 |
| Nike | 耐克 | present | R7-16 |
| Footwear and apparel | 鞋类与服装 | present | — |
| $71.06 | (same as EN) | invariant | — |
| −1.12% | (same as EN) | invariant | — |
| Older signal only | 仅有旧信号 | present | R7-22 |
| Not assessed in this lens | 未在此策略中评估 | present | — |
| Legacy signal, Sep 30 | 旧信号，9月30日 | present | — |
| Dec 18 | 12月18日 | present | — |
| UNH | (same as EN) | invariant | R7-16, R7-19 |
| UnitedHealth | 联合健康 | present | R7-16, R7-19 |
| Managed care | 管理式医疗 | present | R7-19 |
| $512.40 | (same as EN) | invariant | — |
| +0.18% | (same as EN) | invariant | — |
| Date not confirmed by a source | 日期未经来源确认 | present | — |
| Checkpoints not read | 检查点未读取 | present | — |
| An older signal is not a checkpoint | 旧信号不是检查点 | present | — |
| Unavailable is not a checkpoint result | 暂不可用不是检查点结果 | present | — |
| Checkpoints | 检查点 | present | — |
| 3 of 5 | 5 只中有 3 只 | invariant | — |
| have their checkpoints read. | 已读取检查点。 | present | — |
| No name in this lens has an entry rule yet. | 此策略中尚无标的有入场规则。 | present | — |
| Has the company’s economic reality or expectation path improved enough to deserve attention? | 公司的经营实况或预期路径是否已改善到值得关注？ | EN-drawn | — |
| This lens has no entry or exit rule yet. Checkpoints are research, not a Buy. | 此策略尚无入场或退出规则。检查点是研究，不是买入。 | present | — |
| How the 5 names read tonight | 今晚这 5 只标的的读数 | present | — |
| Consensus and guidance are read only when the source qualifies. Otherwise they show Not qualified. | 只有来源合格时才读取一致预期与指引，否则显示“来源不合格”。 | present | — |
| See how checkpoints are read | 查看检查点如何读取 | present | — |
| Ordered by next report date — not a recommendation. | 按下次财报日期排序 — 并非推荐。 | present | — |
| Checkpoints read | 已读检查点 | present | — |

### R7-16

| EN | ZH | Status | Also on |
|---|---|---|---|
| 2 of 3 | 3 只中有 2 只 | invariant | — |
| can’t be judged tonight, and it says why. | 今晚无法判断，并写明了原因。 | present | — |
| Is the economic turn real, can the company finance the path, and can original equity participate? | 经济拐点是否真实？公司能否为这条路径融资？原有股东能否分享？ | EN-drawn | — |
| This lens has no entry or exit rule yet. A cycle research horizon is not a holding period. | 此策略尚无入场或退出规则。周期研究期限不是持有期。 | present | — |
| How the 3 names read tonight | 今晚这 3 只标的的读数 | present | — |
| Funding, dilution and the per-share path are read only when the source qualifies. Otherwise they show Not qualified. | 只有来源合格时才读取融资、摊薄与每股路径，否则显示“来源不合格”。 | present | — |
| Ordered by next milestone date — not a recommendation. | 按下一里程碑日期排序 — 并非推荐。 | present | — |
| MU | (same as EN) | invariant | R7-17, R7-18, R7-19 |
| Micron | 美光 | present | R7-17, R7-18, R7-19 |
| Memory semiconductors | 存储半导体 | present | R7-18, R7-19 |
| $118.40 | (same as EN) | invariant | R7-18 |
| +1.92% | (same as EN) | invariant | R7-18 |
| Dec 17 | 12月17日 | present | R7-17, R7-18 |
| Quarterly report; turn re-read after it | 季度财报；之后重新读取拐点 | superseded | — |
| Failure case | 失败情形 | present | R7-17, R7-18 |
| Industry turn | 行业拐点 | present | R7-17, R7-18 |
| Confirmed | 已确认 | present | R7-17, R7-18 |
| Funding | 融资 | present | R7-17, R7-18 |
| Covered | 已覆盖 | present | R7-17, R7-18 |
| Per-share path | 每股路径 | present | R7-17, R7-18 |
| Recovering | 恢复中 | present | R7-17, R7-18 |
| DOW | (same as EN) | invariant | — |
| Dow | 陶氏 | present | — |
| Commodity chemicals | 大宗化工 | present | — |
| $52.85 | (same as EN) | invariant | — |
| −0.62% | (same as EN) | invariant | R7-17 |
| Jan 29 | 1月29日 | present | — |
| Early | 早期 | present | — |
| Needs capital | 需要资金 | present | — |
| $248.60 | (same as EN) | invariant | — |
| Quarterly report | 季度财报 | present | R7-17, R7-18 |

### R7-17

| EN | ZH | Status | Also on |
|---|---|---|---|
| Compare 3 names | 对比 3 只标的 | present | R7-18 |
| The same decision line, side by side. Each column keeps its own lens and its own date. | 同一条决策线并排呈现。每一列保留各自的策略和日期。 | present | — |
| Back to Today | 返回今晚 | present | R7-18 |
| Add a name | 添加标的 | present | R7-18 |
| Save 3 to a list | 将 3 只保存到列表 | present | R7-18 |
| $104.75 | (same as EN) | invariant | — |
| Has its own entry rule | 有自己的入场规则 | present | R7-18 |
| Checkpoints only; no entry rule yet | 仅检查点；尚无入场规则 | present | R7-18 |
| Lens checkpoints | 策略检查点 | present | R7-18 |
| Remove | 移除 | present | R7-18, R7-19 |
| Not ranked. Each column is read under its own lens and its own date, so a checkpoint in one lens is not a score against another. | 不做排名。每一列按各自的策略和日期读取，一个策略中的检查点不能作为与另一策略比较的分数。 | present | — |

### R7-18

| EN | ZH | Status | Also on |
|---|---|---|---|
| The same decision line, read slot by slot. Each name keeps its own lens and its own date. | 同一条决策线，逐栏读取。每只标的保留各自的策略和日期。 | present | — |
| Not ranked. Each name is read under its own lens and its own date, so a checkpoint in one lens is not a score against another. | 不做排名。每只标的按各自的策略和日期读取，一个策略中的检查点不能作为与另一策略比较的分数。 | present | — |
| In the order you picked | 按您选择的顺序 | present | — |
| Stage 3 of 4 · Ready | (same as EN) | superseded | — |
| Next step | 下一步 | present | — |
| Saving doesn’t create a plan or a position. | 保存不会创建计划或仓位。 | present | R7-21 |

### R7-19

| EN | ZH | Status | Also on |
|---|---|---|---|
| October watch | 十月观察 | present | R7-20, R7-25 |
| Each name keeps the decision it had when you saved it, shown beside tonight’s decision. A saved name is a research watch, not a plan or a position. | 每只标的保留您保存时的决策，并与今晚的决策并列显示。已保存的标的是研究观察，不是计划或仓位。 | present | — |
| Read back from your account at 21:42 ET, Oct 20 | 10月20日 21:42（美东）从您的账户读回 | present | — |
| Decisions as of the Oct 20 close | 决策截至 10月20日收盘 | present | — |
| Saved VRT, ADBE and MU to October watch | 已将 VRT、ADBE 和 MU 保存到十月观察 | present | — |
| Read back from your account at 21:42 ET. Saving doesn’t create a plan or a position. | 21:42（美东）从您的账户读回。保存不会创建计划或仓位。 | present | — |
| When you saved | 保存时 | present | — |
| Tonight | 今晚 | present | — |
| What changed | 变化 | present | — |
| Not there yet, get ready | 尚未触发，做好准备 | present | — |
| Saved Oct 6 | 10月6日保存 | present | — |
| Moved to Ready in the Oct 17 read. | 在 10月17日的读数中转为就绪。 | present | — |
| Networking equipment | 网络设备 | present | — |
| Saved Oct 13 | 10月13日保存 | present | — |
| The Oct 13 read was corrected on Oct 15. What you saved is kept as it was, with the correction beside it. | 10月13日的读数已于 10月15日更正。您保存的内容保持原样，更正并列显示。 | EN-drawn | — |
| See history | 查看历史 | present | R7-22 |
| No entry signal yet | 尚无入场信号 | present | — |
| Saved Oct 9 | 10月9日保存 | present | — |
| Tonight’s assessment didn’t publish, so there is no current decision. Unavailable is not a stage. | 今晚的评估未发布，因此没有当前决策。暂不可用不是阶段。 | EN-drawn | — |
| Saved Oct 20 | 10月20日保存 | present | — |
| No change since you saved. | 保存后没有变化。 | present | — |
| Quality earnings lens | 优质财报策略 | present | — |
| Cycle capture lens | 周期捕捉策略 | present | — |
| 6 names saved | 已保存 6 只 | present | — |
| Tonight’s decisions are redrawn nightly. What you saved stays as it was when you saved it. | 今晚的决策每晚重绘。您保存的内容保持保存时的样子。 | present | — |
| Sample names, dates and decisions for design review, not live signals. | 示例名称、日期与决策，仅供设计评审，并非实时信号。 | present | — |
| 6 names saved, 3 changed | 已保存 6 只，3 只有变化 | present | — |

### R7-20

| EN | ZH | Status | Also on |
|---|---|---|---|
| Save 3 names to a list | 将 3 只标的保存到列表 | present | R7-25 |
| VRT, ADBE, MU | VRT、ADBE、MU | present | R7-21, R7-25 |
| 6 names | 6 只 | present | — |
| Semis cycle | 半导体周期 | present | R7-25 |
| 7 names, MU is already in it | 7 只，MU 已在其中 | present | R7-25 |
| New list | 新建列表 | present | R7-25 |
| Name it on the next step | 下一步命名 | present | R7-25 |
| Saving keeps each name’s decision as it stands tonight, so you can see later what changed. It doesn’t create a plan or a position. | 保存会保留每只标的今晚的决策，便于您之后查看变化。它不会创建计划或仓位。 | present | R7-25 |
| Save to October watch | 保存到十月观察 | present | R7-25 |
| Cancel | 取消 | present | R7-21, R7-25 |
| 3 names | 3 只 | present | R7-25 |

### R7-21

| EN | ZH | Status | Also on |
|---|---|---|---|
| After Save to October watch | 点击“保存到十月观察”之后 | present | — |
| The sheet stays open and reports what your account said. Four outcomes; none of them is called a failure, and none repeats the save on its own. | 面板保持打开，并报告您账户的答复。共四种结果；没有一种称为失败，也没有一种会自行重复保存。 | present | — |
| Waiting for the account | 等待账户 | present | — |
| Saving to October watch | 正在保存到十月观察 | present | — |
| Waiting for your account to confirm. You can close this; the save carries on, and nothing is saved twice. | 正在等待您的账户确认。您可以关闭此面板；保存会继续进行，不会重复保存。 | present | — |
| Close | 关闭 | present | — |
| Read back from the account | 已从账户读回 | present | — |
| Saved to October watch | 已保存到十月观察 | present | — |
| Read back from your account at 21:42 ET. VRT, ADBE and MU are in the list with tonight’s decisions kept as they stand. | 21:42（美东）从您的账户读回。VRT、ADBE 和 MU 已在列表中，今晚的决策按原样保留。 | present | — |
| Open October watch | 打开十月观察 | present | — |
| Done | 完成 | present | — |
| Refused by the account | 账户拒绝 | present | — |
| Not saved | 未保存 | present | — |
| Your account says October watch was deleted on another device. Choose another list for VRT, ADBE and MU. | 您的账户显示“十月观察”已在另一台设备上删除。请为 VRT、ADBE 和 MU 选择其他列表。 | present | — |
| Nothing was added anywhere. | 没有添加到任何列表。 | present | — |
| Choose another list | 选择其他列表 | present | — |
| No answer from the account | 账户无应答 | present | — |
| Save not confirmed yet | 保存尚未确认 | present | — |
| Your account didn’t answer in time. Before saving again we check the list, so nothing is saved twice. | 您的账户未及时应答。再次保存前我们会先检查列表，因此不会重复保存。 | present | — |
| Asked at 21:42 ET | 请求于 21:42（美东） | present | — |
| Check again | 再次检查 | present | — |

### R7-22

| EN | ZH | Status | Also on |
|---|---|---|---|
| Littelfuse setup and timing | 力特的形态与时机 | present | — |
| Why there is no decision tonight | 今晚为何没有决策 | present | — |
| Tonight’s assessment for LFUS didn’t publish, so there is no decision, timing or exit to show. The quote still updates; a fresh quote is not a Buy. | LFUS 今晚的评估未发布，因此没有可显示的决策、时机或退出。报价仍会更新；最新报价不等于买入。 | superseded | — |
| Tonight’s assessment | 今晚的评估 | present | — |
| Didn’t publish | 未发布 | present | — |
| Last published | 最近发布 | present | — |
| Oct 17 | 10月17日 | present | — |
| Next board | 下次榜单 | present | — |
| After the close, Oct 21 | 10月21日收盘后 | present | — |
| Unavailable is not a stage. It doesn’t mean Wait, and it doesn’t mean the setup ended. | 暂不可用不是阶段。它不代表等待，也不代表形态已结束。 | present | — |
| Last published read | 最近发布的读数 | present | — |
| Kept as published on Oct 17. Tonight’s quote doesn’t renew it. | 按 10月17日发布的原样保留。今晚的报价不会使其续期。 | present | — |
| Decision then | 当时的决策 | present | — |
| Assessed | 已评估 | present | — |
| Oct 17 close | 10月17日收盘 | present | R7-23 |
| This is history, not tonight’s view. It is here so you can see what changed. | 这是历史记录，不是今晚的视图。放在这里是为了让您看到变化。 | present | — |
| Also without a decision tonight | 今晚同样没有决策 | present | — |
| No earnings assessment yet. A current quote is not a decision. | 尚无财报评估。有最新报价不等于有决策。 | present | — |
| CAT | (same as EN) | invariant | — |
| Caterpillar | 卡特彼勒 | present | — |
| An earlier model flagged it on Oct 9. Tonight’s method hasn’t assessed it, so it has no stage, timing or exit. | 较早的模型曾在 10月9日标记它。今晚的方法尚未评估它，因此它没有阶段、时机或退出。 | present | — |
| Unavailable, Not assessed and Older signal only are kept apart from Wait. Each says why, and none borrows a stage. | 暂不可用、未评估和仅有旧信号与等待分开显示。每一项都写明原因，且都不借用阶段。 | present | — |
| Tonight’s assessment for LFUS didn’t publish, so there is no decision or timing, and the funding check can’t be read. The quote still updates; a fresh quote is not a Buy. | LFUS 今晚的评估未发布，因此没有决策或时机，资金检查也无法读取。报价仍会更新；最新报价不等于买入。 | present | — |

### R7-23

| EN | ZH | Status | Also on |
|---|---|---|---|
| Credo Technology setup and timing | Credo Technology 的形态与时机 | present | — |
| Last quote 11:42 ET, Oct 20 | 最后报价 10月20日 11:42（美东） | present | — |
| Why the entry is revoked | 入场为何撤回 | present | — |
| The last price tick arrived at 11:42 ET, so we can’t confirm that price is inside the entry zone. The setup itself hasn’t changed. | 最后一笔价格数据在 11:42（美东）到达，因此无法确认价格是否在入场区间内。形态本身没有变化。 | present | — |
| Last quote | 最后报价 | present | — |
| 11:42 ET, Oct 20 | 10月20日 11:42（美东） | present | — |
| Expected | 预期 | present | — |
| Setup stage | 形态阶段 | present | — |
| Ready, Oct 20 | 就绪（10月20日） | present | — |
| A stale quote never shows as Buy. When quotes refresh, the entry comes back only if price is inside the zone. | 过期报价永远不会显示为买入。报价刷新后，只有价格在区间内时入场才会恢复。 | present | — |
| Plan | 计划 | present | — |
| Reconstructed from the Oct 17 plan | 依据 10月17日计划重建 | present | — |
| Tonight’s plan file didn’t arrive. These levels are the Oct 17 plan as published; nothing was recalculated or extended. | 今晚的计划文件未送达。这些价位是 10月17日计划的原样；没有重新计算或延伸。 | present | — |
| Rebuilt | 重建于 | present | — |
| 21:10 ET, Oct 20 | 10月20日 21:10（美东） | present | — |
| The plan stays labeled until tonight’s plan verifies. It never fills in a level the original didn’t have. | 在今晚的计划核实之前，此计划会一直带有标注。它绝不会补上原计划没有的价位。 | present | — |
| See the Oct 17 original | 查看 10月17日原件 | present | — |
| Oct 17 close, rebuilt | 10月17日收盘，已重建 | present | — |
| $85.62 | (same as EN) | invariant | — |

### R7-24

| EN | ZH | Status | Also on |
|---|---|---|---|
| 20 names | 20 只 | present | — |
| Astera Labs, Semiconductors | Astera Labs，半导体 | present | — |
| What passed | 已通过的检查 | present | — |
| What didn’t verify | 未能核实的内容 | present | — |
| Tonight’s plan data | 今晚的计划数据 | present | — |
| Because the plan data didn’t verify, we show no entry zone, timing or exit for ALAB tonight. | 由于计划数据未能核实，今晚不显示 ALAB 的入场区间、时机或退出。 | present | — |
| This is not a rejection of the setup and not a Wait. It rejoins the board when its plan data verifies; the next build is after the close, Oct 21. | 这不是否定该形态，也不是等待。计划数据核实后它会重新回到榜单；下次构建在 10月21日收盘后。 | present | — |
| Showing 4 of 20. Plan data refusals are listed first, then the rest by original priority. | 显示 20 只中的 4 只。计划数据未核实的排在最前，其余按建立时优先级排序。 | present | — |
| Show 16 more | 再显示 16 只 | present | — |

### R7-25

| EN | ZH | Status | Also on |
|---|---|---|---|
| Entry zone, low to high | 入场区间（由低到高） | present | — |

### R7-26

| EN | ZH | Status | Also on |
|---|---|---|---|
| Before and around tonight’s board | 今晚榜单建成前后 | present | — |
| Loading keeps the final shape, so nothing moves when the board fills. An empty board says how many were judged and why none is ready. An outage says what failed and what still works. | 加载时保持最终版式，榜单填入时不会跳动。空榜单会说明判断了多少只、为何都未就绪。故障时会说明哪里失败、哪些仍可用。 | present | — |
| Loading | 加载中 | present | — |
| Loading tonight’s board | 正在加载今晚的榜单 | present | — |
| Built, nothing ready | 已建成，暂无就绪 | present | — |
| No entry is ready tonight | 今晚没有可入场的标的 | present | — |
| 0 of 13 have an entry ready now. 9 are setting up or waiting. 4 can’t be judged tonight, and each one says why. | 13 只中目前 0 只可入场。9 只正在形成或等待。4 只今晚无法判断，每只都写明了原因。 | present | — |
| See all 13 candidates | 查看全部 13 只候选 | present | — |
| Build didn’t finish | 构建未完成 | present | — |
| Tonight’s board didn’t build | 今晚的榜单未能建成 | present | — |
| The build after the close stopped before it finished, so tonight has no decisions, timing or exits to show. Counts are unknown, not zero. | 收盘后的构建在完成前中断，因此今晚没有可显示的决策、时机或退出。数量未知，并非为零。 | present | — |
| What still works | 仍可使用 | present | — |
| Oct 19 board | 10月19日榜单 | present | — |
| History, not tonight’s view | 历史记录，并非今晚的视图 | present | — |
| Last checked 21:42 ET | 最后检查于 21:42（美东） | present | — |
| Reload | 重新加载 | present | — |
| Sample counts and times for design review, not live data. | 示例数量与时间，仅供设计评审，并非实时数据。 | present | — |

