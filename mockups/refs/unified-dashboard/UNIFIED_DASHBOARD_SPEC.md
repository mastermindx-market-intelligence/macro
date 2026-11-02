# MarketOntology — Unified Macro Dashboard, design spec

**Figma file:** `MarketOntology Design System` — file key `ldbAfjrQmPreFZ43htLkMx`
(`https://www.figma.com/design/ldbAfjrQmPreFZ43htLkMx`)
**Pages:** `01 · Tokens` · `02 · Components` · `03 · Unified Dashboard`
**Status:** design proposal, mockup tier. Nothing in this packet touches the repo.
**Authority order:** `docs/DESIGN_DOCTRINE.md` (content law) > `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`
(visual/composition law) > `mockups/design_system/macro_reference.html` (the Archetype-D worked
example) > this document. Where they disagree, the higher source wins and this packet is wrong.

---

## 0 · The job, and the archetype

**User job.** A subscriber opens this page to answer, in plain words, at a glance: *what is the
market regime right now, and what should I do about it* — with the technical receipts one hover
or one click away, and with "watch — don't chase" available as an honest, complete answer.

**Archetype: `regime_dashboard` (D).** Primary question *"What regime am I in; what would change
that read."* L1 budget 6. Identity device: the regime VerdictHero with the capped-dial caveat
discipline. This page consumes the D skeleton from `macro_reference.html` and extends it in one
place only — §3 below.

**What makes it *unified*.** `macro.html` answers the question for one economy. This page answers
it once, for the whole estate, and then shows where that single read lands across five markets on
**one shared scale**. The unification is not a merge of five dashboards; it is one answer plus one
axis. Every per-market depth surface survives as a named landing (§8).

**Section inventory — 6 of 6 L1 sections.**

| # | Section | Job |
|---|---|---|
| 1 | VerdictHero | the answer, its stance, its caveat |
| 2 | Regime spine | where that answer lands across five markets |
| 3 | What changed | what moved since the reader last looked |
| 4 | Why — three drivers | the evidence under the verdict |
| 5 | What we're watching | what would change the read |
| 6 | Go deeper | named landings for everything demoted |

Above-fold budget at 1440×900: chrome (58) + the answer (≈330) + the spine (≈190). What changed
begins just below the fold — chrome + answer + two supporting modules, exactly at budget.

---

## 1 · Layout grid

**Desktop 1440.** Header `_site_nav` family, 58px, full-bleed, bottom hairline. Content measure
**1180**, centred (130px gutters). Section rhythm `--sp-6` (24). Panel padding `16px 18px`,
radius `--r-panel` 14, hairline `--line`.

Hero is a two-column split: copy column **fixed 660** (a ~56ch measure — the clause and the caveat
must not run the full 1180) and a **316** gauge column, pushed apart with space-between. The
remaining ~168px of slack is deliberate: the gauge sits off the right margin rather than jammed
against it.

Spine row grid (content width 1144): `name 150 · track 706 · moved 78 · stance 168`, gaps 14.
The three right-hand columns carry micro caps heads so the integers below them are self-describing.

Drivers: 2×2, gap `--gap-grid` 18, each panel FILL. Watching: 3-up, gap 18. Go deeper: wrapped chips.

**Mobile 390.** Header 52. Content 358 (16px gutters). Section rhythm 20.
The mobile composition is a **declared re-composition, not a squeeze** — see §7.

**Breakpoints inherited:** 900 (nav collapse), 860 (hero and driver grid go single-column),
640 (decision rows stack to two lines; drivers become a swipe strip). 390 is the design floor.
The page never scrolls horizontally at any width; wide content scrolls inside its own container.

---

## 2 · Typography

One family for words, one for figures — the institutional signature is weight contrast and
numeric discipline, not a second display face.

| Role | EN | ZH | Size / weight |
|---|---|---|---|
| Verdict word | Inter Extra Bold | Noto Sans SC Black | 46 / −3% tracking **EN only** (36 at 390) |
| h1 | Inter Extra Bold | Noto Sans SC Black | 28 / −2% EN only |
| h2 panel titles | Inter Bold | Noto Sans SC Bold | 17 / −1% EN only |
| h3 | Inter Bold | Noto Sans SC Bold | 14 |
| md lead | Inter Medium | Noto Sans SC Medium | 15 |
| body / sm | Inter Regular | Noto Sans SC Regular | 14 / 12.5 |
| label · micro (eyebrows, table heads) | Inter Semi Bold, caps, +8% | Noto Sans SC Medium, **no caps**, +2% | 11 / 10 |
| **All figures** | IBM Plex Mono | IBM Plex Mono | num-xl 38 · num-lg 22 · num-md 15 · num-sm 12.5 · num-micro 10 |

Sizes are the shipped `--fs-*` ramp, promoted verbatim — nothing was re-tuned.

**Font-mapping decisions to record.** `--font-ui` leads with San Francisco in production and
cannot be embedded in Figma, so Inter — the stack's named carrier — is the file's proxy; the
rendered result is the non-Apple reality, which is the stricter test. Noto Sans SC stands in for
the `PingFang SC / Noto Sans CJK SC` branch. Noto Sans SC has no 800 or 600, so the ZH ramp maps
**800 → Black** and **600 → Medium**; that mapping is the spec, not an accident.

**ZH typographic law applied in the file:** tracking resets to 0–2%, uppercase is dropped
everywhere (it mangles mixed CJK/Latin), and the ZH ramp is bound as its own text-style set so a
language switch is a style swap, never a per-node override.

---

## 3 · The signature: the regime spine

The one memorable element, and the only new primitive this page asks for. Proposed name
`.mx-spine` (`.mx-*` per the namespace law; it is not in the §11.1 inventory and therefore needs
design-lane ratification before any builder uses it).

**What it is.** One horizontal scale — *Risk-off ←→ Risk-on* — reused identically by five market
rows. Each row carries: today's position (solid marker), the position it came from a month ago
(hollow marker), a thin connector between them, a signed travel figure, and a plain stance word.

**Why it earns the page.** It is the ontology made visible: markets that normally live on five
separate pages are placed on one comparable axis, so "the regime is risk-on but narrowing" becomes
a shape you can see rather than a sentence you have to trust. It replaces the generic "markets
tile grid" that every dashboard reaches for, and it is honest by construction — the footnote says
in plain words that positions are a read on a shared scale, **not price performance**.

**Encoding rules (each one is a law being obeyed, not a style choice).**
- **Position** is a measurement → neutral geometry; the marker takes its stance's ink, never a
  category hue.
- **Travel** is a measurement change, **not** a price move, so it uses muted measurement ink plus
  an explicit arrow — never `--up`/`--down`. This deliberately dodges the 红涨绿跌 flip: a travel
  figure means the same thing in both languages.
- **Stance ink** encodes health, and health never flips: Act / Get ready → `--ink-ok`;
  Watch — don't chase / Protect gains → `--ink-warn`; Stand aside / Ignore → `--muted`, no colour
  at all. Three levels, achromatic by default, colour only where it means severity.
- **Zone ticks** at 25/50/75 are notches, not labels. The axis is anchored in **words**
  (Risk-off · Neutral · Risk-on), never in a bare 0–100.
- **The subject market** (US stocks) is the only marked subject, one per spine.
- **The null row is designed.** Commodities carries a dashed rail, no marker, and a
  "Read being updated" chip. Not a blank, not an em-dash, and never falsifier vocabulary.

---

## 4 · Component inventory

Everything below already exists in the canonical inventory except where marked. All render on
page `02 · Components`, in both treatments.

| Component | Canon | Use here |
|---|---|---|
| PageShell / PageHeader | `_site_nav` family | header; no third header family was created |
| VerdictHero | `.mx-vh` | §1 — eyebrow, two-tone verdict word, clause, stance, live chip, as-of |
| Section header | `.mx-sec` | every panel title + LENS `?` + one as-of slot |
| Panel / Panel2 | `.panel` / `.panel2` | E1 panels; E2 for metric tiles. Nesting depth 2, never 3 |
| Metric tile | `.mtile` | driver tiles: label · tabular value · one plain note |
| DecisionRow | `.mx-chg-row` | §3 What changed |
| **Regime spine row** | **`.mx-spine` — NEW, needs ratification** | §2 |
| Callout | `.mx-callout` | the capped-score caveat |
| Stance chip | doctrine stance vocabulary | six words, nothing else |
| Freshness | `.dtp` family | live / delayed / settled / read-being-updated; one as-of per panel |
| ChartFrame | illus (`lib/illus.py`) | driver sparklines, `--ser-1` only, question captions |
| TierLock | `.mx-tier-gate` + ghost | driver 4 |
| Empty / stale / error | `.mx-empty` + `.mx-empty-why` | specimen page; stale state live on the spine |
| Depth link | `.depth` chips | §6 landings |
| Tooltip | LENS `data-tip-en/zh` | every receipt (`?`, hover rows) |

**Deliberate non-use.** No emoji as UI icons (the one 🔒 is the grandfathered lock mark and should
route to `_icons.html.j2` at build). No second accent. No Plotly. No tabs — this page has one task.

---

## 5 · Theme art direction

Dark and light share information architecture, component semantics, spacing and type scales, state
meanings, ordering, density law and every interaction. They do **not** share material treatment.
The variable collection has four modes (`Dark · EN`, `Dark · ZH`, `Light · EN`, `Light · ZH`), but
the modes only carry *colour*. The mechanisms below are applied by a separate pass, and that is the
point: **if you only switched the mode, the light frames would be wrong.**

### DARK — the command center

Graphite canvas `#0f1115`, panels `#181b21` lifted **by luminance alone**. Depth is a luminance
step (`--panel` → `--panel2`), never a shadow: the dark card effect is a **1px inner top highlight**
(`rgba(255,255,255,.03)`), i.e. a light edge, not a cast shadow. Hairlines `#3a4150` sit at the
1.6:1 container floor. The aurora is present at jewel-tone alphas (.20 / .16) behind a 120px blur
— ambient, never touching legibility. The one glow on the page is the subject marker's soft bloom
(`--link` at 55%, 14px radius, no offset) — restrained, and it marks exactly one thing. State text
prints the raw tokens, because on dark the ink rungs resolve to the raw tokens by construction.
Nothing pulses except the live chip.

### LIGHT — the research workspace

White panels `#ffffff` on a canvas that stays **perceptibly deeper** (`#f7f8fa`) — panel ≈ bg is
the flatness bug and does not occur here. Depth is earned structurally: hairline + whitespace +
a genuine **cast shadow** `0 1px 3px rgba(20,30,50,.07)`.

**Mechanisms that intentionally differ, and why:**

| # | Mechanism | Dark | Light | Why it cannot be a token swap |
|---|---|---|---|---|
| 1 | Panel depth | inner top light-edge (`INNER_SHADOW`) | cast drop shadow | Opposite effect *types*. A light edge on white is invisible; a dark drop shadow on graphite is mud. |
| 2 | Subject marker | soft bloom halo | **ring** — 2px `--link` stroke + tight `0 2px 4px` shadow | A bloom becomes a pastel stain on white. The ring carries the same "this is the subject" meaning with structure instead of light. |
| 3 | Spine rail + zones | rail reads by luminance; ticks cut through it | rail gains a **1px track border**; ticks re-key to `--panel` | Neutral segments vanish on white — the same rule that forces 1px gaps + a track border on heatmaps. |
| 4 | Aurora | alphas .20 / .16 | alphas **.09 / .08** | Same geometry, lighter ink. Dark alphas on a white canvas read as a printing error. |
| 5 | Header glass | `--panel` at 72% | `--panel` at **88%** | White at 72% over a near-white canvas disappears; the bar would lose its plane. |
| 6 | Caveat callout | 8% tint | **6%** tint, ink deepens via the rung | White amplifies tint; 8% amber on white is a highlighter smear. |
| 7 | Locked preview | ghost at .46 | ghost at **.42** (+ `saturate(.35)` in CSS) | A blur teaser on white reads as a dirty smudge unless it is desaturated and lifted. |
| 8 | State text | raw tokens (ink-mix 100%) | `--ink-*` rungs (up 62 · down 84 · warn 62 · ok 70 · act 88 · link 88) | The raw fill-grade palette fails the 4.5:1 floor as text on white. Fill-grade and text-grade are different jobs. |
| 9 | Chart ink | `--ser-1` `#5b9bf0` | light twin `#2f63c4` | A pale blue stroke disappears on white; a saturated one glares on graphite. |

Both treatments were judged as designs, at both languages and both widths — the eight cells in §10.

### The 红涨绿跌 flip

Direction tokens swap in the ZH modes, so the verdict's "RISK-ON" half prints **red** in Chinese
and green in English, and the gauge arc follows. Health tokens do **not** flip: `准备行动` stays
green in both languages because it means *safe to move*, not *up*. Quadrants flip; the spine's
travel indicators are deliberately outside the flip (§3). This is visible in
`dashboard_dark_zh_1440.png` against `dashboard_dark_en_1440.png`.

---

## 6 · Glance-tier copy (EN, with ZH twins)

Every string below is Tier 1 and is inside budget: title ≤4 words, subtitle ≤14 words, row ≤1 line,
footer ≤1 sentence. ZH is written native-shaped and budgeted in characters, not translated clause
for clause.

### Hero
| Slot | EN | ZH |
|---|---|---|
| Eyebrow | Global markets · Regime read | 全球市场 · 状态判读 |
| Verdict (2 words) | **RISK-ON, NARROWING** | **偏多，但在收窄** |
| Clause (11 words) | Buyers are still showing up — but fewer stocks are carrying the move. | 买盘仍在——但真正推动上涨的个股在减少。 |
| Stance | Watch — don't chase | 观察，勿追 |
| Gauge caption | One score, anchored in words — capped this week (see note) | 唯一评分，配文字锚点——本周封顶（见注） |
| Caveat | Read the score with care: one input is rebuilding, so it is capped at 62 — the uncapped blend reads 71. | 读数注意：一项输入正在重建，综合分被封顶为 62——未封顶为 71。 |

The verdict word is **two-tone**: "RISK-ON," takes `--ink-up`, "NARROWING" takes `--ink-warn`. The
state and its qualifier print in different inks so the headline can never contradict its own
stance — a single green word above "Watch — don't chase" is the failure this prevents.

The caveat sits **beside** the headline, never behind a hover: a cap that changes how the number
should be read is the one sanctioned second reading of a headline quantity. 62 is printed once,
in the gauge; 71 appears only inside the caveat; the gauge draws the capped arc solid and the
uncapped remainder as a 26% ghost, so the caveat is visible as well as stated.

### Spine
Heading **Where this shows up** / 这一状态体现在哪里 · caption *One scale, five markets — where
each sits, and which way it moved.* / 同一标尺，五个市场——各自位置，以及本月的移动方向。
Column heads: MARKET · WHERE IT SITS TODAY · MOVED · WHAT TO DO (市场 · 今日位置 · 本月移动 · 该怎么做).

| Market | Position | Moved | Stance |
|---|---|---|---|
| US stocks / 美股 | 72 | ← −6 | Protect gains / 保护收益 |
| Hong Kong / 香港 | 61 | → +5 | Watch — don't chase / 观察，勿追 |
| China A-shares / A股 | 58 | → +9 | Get ready / 准备行动 |
| Government bonds / 国债 | 38 | ← −4 | Stand aside / 暂时观望 |
| Commodities / 大宗商品 | — | — | Read being updated / 判读更新中 |

Footnote (once): *Positions are this week's read on a shared scale — not price performance.* /
位置是本周在同一标尺上的判读，并非价格涨跌幅。

### What changed — since 09-08
| Date | Name | Clause | Stance |
|---|---|---|---|
| 09-12 | Breadth / 市场广度 | participation narrowed again — fewer than half of big US stocks are above their 50-day line | Watch — don't chase |
| 09-11 | Policy rate / 政策利率 | the market moved its landing spot for the policy rate down to 3.88% | Ignore — already in the read |
| 09-10 | China / 中国 | onshore buying picked up for a third straight week | Get ready |
| 09-08 | Oil / 原油 | crude gave back the summer's gain; energy stopped leading | Stand aside |

### Drivers
Band label *Why — the three things moving this read* / 为什么 — 推动本次判读的三件事.
Each panel opens with a bold one-word judgment, then a plain sentence:
**Holding.** / 企稳。 · **Cooling, slowly.** / 缓慢降温。 · **Narrowing.** / 正在收窄。 ·
**Supportive.** / 偏支持。 (locked). Every sparkline caption is a question the chart answers
("Is growth holding?", "Are more stocks joining?") — a chart without one is decoration.

### Watching
Band label *What we're watching next* / 接下来我们在盯什么. Three conditions, each phrased as
**if → what it would change**, never as a verdict about a thesis:
*More than six in ten big stocks back above their 50-day line …would turn this read to Act, and we
would say so here first.* Footer, once: **Windows, not certainties — re-drawn nightly.** /
是窗口，不是定论——每晚重新校准。

### Page footer
*Re-drawn nightly. Windows and stances are our read of the evidence, not advice.* /
每晚重新校准。窗口与立场是我们对证据的判读，不构成投资建议。

### Plain-word compliance
- **Stance on every panel.** Hero, every spine row, every changed row. "Watch — don't chase" is
  used as the honest headline answer, which is the whole point of the vocabulary.
- **Banned vocabulary: none present.** No internal state names, no study or ruling IDs, no
  `n=`/z-scores/IC/FDR/percentile ranks, no raw slugs, no untranslated statistics, no "validated".
- **No falsifier language anywhere.** Nothing is "refuted", nothing is 证伪. A market with no
  current read says **"Read being updated"**; conditions are **windows**, re-drawn nightly.
- **Numbers arrive with meaning.** "47% — was 66%", "→ +9" under a head that reads MOVED,
  "3.88%" inside a sentence that says what moved and who moved it.
- **One-integer law.** Breadth is counted once (47%, was 66%) in its driver tile; the What-changed
  row quotes it in words ("fewer than half", "two-thirds") and prints no competing integer. The
  policy rate 3.88% appears exactly once. The score 62 appears once, with 71 only as its caveat.
- **One as-of per panel**, one session stamp in the header, one footnote per panel.

---

## 7 · Mobile 390 — the declared reduction

Not the desktop stack squeezed. What each section becomes, and where what is lost goes:

| Section | Desktop | 390 | Landing for what is dropped |
|---|---|---|---|
| 1 Hero | 2-col, 46px word, gauge right | word wraps to 2 lines at 36px; gauge moves **below** the answer, full width; meta chips wrap | nothing dropped — the answer is inside one swipe |
| 2 Spine | 4-column table | **stacked cards**: row 1 name + stance, row 2 the same shared rail + travel figure. The scale survives; the table geometry does not | column heads become the card's own structure |
| 3 What changed | 1-line rows | **two-line stack** (date+name+stance, then the clause); 3 rows shown | "See all 4 changes →" |
| 4 Drivers | 2×2 grid | **swipe strip**, cards at ~86% width with a `1 / 3` counter; the clipped second card is the affordance | horizontal snap, all three reachable |
| 5 Watching | 3 cards | **one disclosure row** — title, count `3`, chevron, plus a one-line preview of the first condition | the row is the landing; the windows footnote stays visible |
| 6 Go deeper | 6 chips | 6 chips, wrapped, shortened labels | — |

Touch: every chip and row ≥40px effective. No hover-only affordance survives — the LENS `?` opens
on tap. Mobile L1 is effectively 5 (watching is demoted to a link row), one under the desktop
budget, which is the rule.

---

## 8 · Demotion landings

Everything the live macro surface carries that this page does not show at L1 has a named home:
breadth internals → *Breadth & participation*; the rate path and curve → *Rates & the curve*;
the China desk → *China desk*; sector temperature and rotation → *Sector rotation*; every raw
table → *Full data tables*; methodology, study IDs, base rates, window specs → *How we read this*
and the LENS receipts. Demoted, never deleted.

---

## 9 · Accessibility and motion

Text ≤18px clears 4.5:1 on the surface it actually sits on — which is why state text uses the
`--ink-*` rungs in light and why the lock's plan line uses the measured `--ink-tier`
(`#9b86ff` dark / `#5b3fc4` light), never raw violet. Component boundaries (chip outlines, the
gauge track, the segmented rail) clear 3:1. One h1 per page; every panel heads with an h2; the
band labels are real h2s styled as eyebrows so the outline never loses a section.

Motion is a status channel: the live dot pulses, settled states rest, hover lift is
`translateY(-1px)` at `--t-med` on clickable containers only, tabs and toggles never move, and one
breathing CTA at most (here: none — the gate's CTA is static). `prefers-reduced-motion` must kill
all of it **by name, including the `::before/::after` sweeps**, or the sweeps ship dead.

---

## 10 · Evidence matrix — 8 cells, all captured

| File | Frame | Node |
|---|---|---|
| `dashboard_dark_en_1440.png` | Dashboard · Dark · EN · 1440 | `4:2` |
| `dashboard_light_en_1440.png` | Dashboard · Light · EN · 1440 | `19:2` |
| `dashboard_dark_zh_1440.png` | Dashboard · Dark · ZH · 1440 | `20:2` |
| `dashboard_light_zh_1440.png` | Dashboard · Light · ZH · 1440 | `20:553` |
| `dashboard_dark_en_390.png` | Dashboard · Dark · EN · 390 | `15:2` |
| `dashboard_light_en_390.png` | Dashboard · Light · EN · 390 | `19:321` |
| `dashboard_dark_zh_390.png` | Dashboard · Dark · ZH · 390 | `20:321` |
| `dashboard_light_zh_390.png` | Dashboard · Light · ZH · 390 | `20:872` |
| `components_dark.png` / `components_light.png` | Components — DARK / LIGHT | `23:64` / `23:250` |
| `tokens_dark_en.png` / `tokens_dark_zh.png` | Palette — Dark · EN / Dark · ZH | `3:116` / `3:231` |

---

## 11 · Open items for ratification

1. **`.mx-spine` is a new primitive.** It is not in the §11.1 canonical inventory. It needs
   design-lane ratification and, if accepted, it lands in `theme.css` **and** the specimen in the
   same PR that first uses it, with both themes, both languages and 390 shown.
2. **Reference Integrity.** If this composition is ever proposed as a replacement for a live
   surface, it owes the full RIG treatment first: a capability disposition for every feature of
   the page being replaced (`RETAIN / IMPROVE / RELOCATE / REMOVE / BLOCKED_DATA`), design lineage
   citations, and independent Product-Regression and Visual/Taste critics who see the work before
   they see this rationale. This packet is design intent under review, not law and not precedent.
3. **All numbers are illustrative.** They are internally consistent under the one-integer law, and
   nothing here is live data.
4. **Locked-content ghost.** Figma has no `saturate()` on a node, so the light ghost is approximated
   by opacity alone; the CSS implementation must ship `blur(5px) saturate(.35) opacity≈.42`.
5. **Fonts.** Inter and Noto Sans SC are the file's proxies for the production stacks (§2). The
   600/800 → Medium/Black mapping for CJK is a decision, and should be checked against the real
   PingFang SC rendering before it is treated as settled.
