# R7 design worklog — Prophet Opportunity workspace (award-grade)

Seat: orchestrator child (Opus, fable-mode) of Prophet end-to-end seat 69eb9a1c.
Paper file: PROPHET (01M3NT5Y3G5HTJHVR0K5W2MDJM). Base page: p-A-0 (read-only).
Target page: `08 · R7 award-grade · Opportunity workspace · DRAFT` (new).

## Before-mutation node counts (get_basic_info, 2026-10-21)

| page | name | nodeCount | artboards |
|---|---|---:|---:|
| p-1-0 | PROPHET (user active) | 3850 | 19 |
| p-B-0 | REF · REJECTED · R6 text-row direction | 2631 | 23 |
| p-A-0 | 07 · R6 successor · Opportunity workspace · DRAFT | 10121 | 36 |
| p-9-0 | 06 · R6 · Flagship candidate | 497 | 8 |
| p-8-0 | REF · Quote + Assessment Reviews | 3291 | 10 |
| p-7-0 | REF · Setup, Evidence + Playbooks | 3156 | 23 |
| p-6-0 | 05 · SOURCE ONLY · US Live Baseline | 1549 | 1 |
| p-5-0 | 04 · Shared Contracts + State Coverage | 1568 | 8 |
| p-4-0 | 03 · Screener | 2666 | 8 |
| p-3-0 | 02 · R2 · Today, Setup + Plans | 3972 | 21 |
| p-2-1 | 01 · Regional · HK + Canada | 2623 | 19 |

Token contentHash before: b80d0392.

## Log
- 02:5xZ skills loaded (fable-mode, mastermind-design-system, frontend-design); Paper guide + fonts read; before counts recorded.

## Design brief (written before any Paper write)

**Signature: the decision line.** Every opportunity is one line read in a fixed order
with fixed names: Company / Current decision / Timing / What ends it / Lens
(ZH 公司 / 当前决策 / 时机 / 失效条件 / 策略). The five names never change and never reorder.
- Today: one ledger panel; its header row is the five names (the spine); each row is one line.
- Setup detail: the line sits on top, enlarged and pinned; the sections below carry the same five headings in the same order.
- Compare: the line transposed. Slots become rows, names become columns, read across a row.
- Save to list: the line frozen at save time (Original decision) over the live line (Current decision now). This is the only place two lines stack.
- Lens views: the lens slot becomes the page filter; Timing and What ends it carry lens-native facts (Early: window + stage, Earnings: next report, Cycle: next milestone + funding).
- States never remove a slot; they replace its content with a labelled absence (Unavailable / Not assessed / Not supplied). Geometry is fixed, so state change has zero layout shift.

**Palette = existing tokens + three additions.**
- Light research workspace: canvas #F7F8FA, white material #FFFFFF, quiet fill #EEF1F6, text #1C2430, muted #5D6B7E, outer border #C9CCD1, ink-up #1E6D47, ink-down #B23C3D, ink-warn #7D5922, link #2758E6, ok #2F8A52. Controlled shadow 0 1px 2px rgba(28,36,48,.06).
- Dark command center: bg #0F1115, panel #181B21, panel2 #1E222A, text #D7DCE3, muted #8B93A1, line #3A4150, up #45B873, down #E06464, warn #E0A030, link #7AA7E0, ok #3DA564. No shadow; luminance depth only.
- Additions: --mx-light-line-quiet #E2E6EC and --mx-dark-line-quiet #272C35 for row dividers; --mx-focus-ring 2px solid link + 2px offset, complete outline.

**Type.** Inter EN, PingFang SC ZH. Weights 400/500/600 only (PingFang tops out at 600, so EN never out-weighs ZH). tabular-nums on every price, percent and date.
- Scale (existing fs tokens): label 12.5/18 (ZH 12.5/20); body 14/20 (ZH 14/22); ticker and stance 17/22 600; h1 28/36 (ZH 28/38).
- No caps, no mono, no middle-dot meta, no arrow-suffixed links.

**Stance glyphs** (shape + word, never colour alone). Ready = filled dot (ok); near = half dot (warn); wait/watch = ring (muted); stand aside = slashed ring; unavailable/not assessed = dashed ring. Lens is never hued.

**Chart.** One 104x36 mini line per row in the Timing slot:
- price line in text ink (neutral, so there is no ZH flip problem);
- entry zone as a quiet band;
- base invalidation as a dashed muted rule.
Every mark is data.

**Self-critique against defaults (R6 baseline).**
- The R6 card kit (12 identical rounded cards, filled BUY pills) becomes a ledger whose columns align across rows.
- ALL-CAPS labels (ENTRY ZONE) become sentence-case slot names.
- "View setup ->" becomes "Open setup".
- "Priority 80" leaves Tier 1; the order is labelled instead.
- Middle-dot meta becomes typographic levels.
- Residual risk is trait 3 (broadsheet hairlines). The mitigation keeps:
  - radius hierarchy (panel 14, controls 8);
  - generous 88px rows carrying a chart;
  - light material with shadow, dark with luminance depth.
