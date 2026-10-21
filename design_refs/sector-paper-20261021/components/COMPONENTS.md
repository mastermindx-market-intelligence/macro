# Sector Intelligence paper — shared component spec sheets (SIC-P-COMP)

One content contract per shared component used by the Sector Intelligence completion
boards. The code round-trip (Paper boards + later integration lanes) builds against
these sheets so no lane invents a local visual language. Production token source of
truth: `templates/theme.css` (dark default at `:root`, light override at
`html[data-theme="light"]`, zh direction swap at `html[data-lang="zh"]`). All values
shown in the static specimen are placeholder copy, not recorded output.

## Shared laws (bind every component below)

- **No colored container edge, any edge.** No semantic `border-left/right/top/bottom`,
  no inset box-shadow stripe, no pseudo-element rail (Chairman rule 2026-10-18,
  `docs/DESIGN_DOCTRINE.md` §3). Containers: neutral surface, even 1px `var(--line)`
  borders, typography, labelled semantic ink. Neutral hairline dividers between rows
  (`border-*: 1px solid var(--line)`) keep their job.
- **Focus outlines stay complete.** Every interactive element shows
  `outline: 2px solid var(--ink-link, var(--link)); outline-offset: 2px` on
  `:focus-visible`. Nothing may remove it.
- **Touch:** every interactive element is ≥ 44px tall on coarse pointers / ≤ 640px.
- **Stance is not direction** (theme.css:86, DA-002). Stance/health/status inks come
  from the status plane (`--ink-ok/--ink-warn/--ink-act/--ink-info/--muted`), never
  `--up/--down`.
- **zh 红涨绿跌 flips `direction-delta` only.** Direction color lives in
  `--ink-up/--ink-down`, which re-resolve under `html[data-lang="zh"]` automatically
  (theme.css:277). Every other component stays status-plane and never flips.
  `health-badge` never flips in any locale. Violet is lock-only estate-wide
  (theme.css:2236) — and no violet token exists yet (see gaps).
- **Never unknown-as-zero.** A missing value renders an em-dash plus an
  "unavailable"/"abstained" word, never `0`, `0.0%`, or an empty cell that reads as
  zero. A finite negative or underpowered result is reported as exactly that.
- **One as-of stamp per panel, one merged footnote per panel** (doctrine Law 4).
- **No emoji.** Icons are the monoline 24-grid inline-SVG set
  (`templates/_icons.html.j2` idiom: `stroke="currentColor"`, `fill="none"`, round
  caps, ≤3 strokes, no fill except a deliberate dot).
- State vocabulary (closed set): `fresh`, `stale`, `incompatible_generation`,
  `partial`, `corrected`, `abstained`, `error`, `empty`, `loading`, `locked`.
- **Horizontal rails show that they scroll** (VTC-012): a fade mask at the open edge
  plus a partially visible last item, keyboard-scrollable (arrow keys on the focused
  rail); never a hard clip that reads as the end of the list.
- **Range and slider tracks use `--line`** for the track in both themes, with the
  filled portion in `--text`; never a near-black track on the dark theme (VTC-012).
- **Retry and other secondary buttons use the button tokens** (`--panel2` fill,
  1px `--line` border, `--text` label); never a black fill in either theme (VTC-012).

## DESIGN-SYSTEM-GAP register

Tokens `templates/theme.css` lacks; listed here, never defined locally:

1. **`--lock` (violet, lock-only).** "Violet is lock-only estate-wide"
   (theme.css:2236) has no token carrier — the estate violet exists only as aurora /
   dropdown literals (`#8b5cf6` theme.css:608/614, `#9b8cff` theme.css:1013).
   `lock-chip` ships neutral until the token lands.
2. **`--teal-entry` (Recovery phase hue).** Engine taxonomy maps Recovery to
   `#2dd4bf` (engine/sector_cycles.py:129); theme.css has no teal. `phase-chip`
   Recovery renders neutral until a token lands.
3. **Theme-neutral dialog backdrop.** Only `--pv-dialog-backdrop` exists
   (Prophet-namespaced, theme.css:121). `mobile-sheet` reuses it; a shared
   `--sheet-backdrop` should eventually replace it.

---

## asof-stamp

- **Purpose:** state when a panel's data was computed and from which named source.
- **Anatomy:** clock icon (monoline) · as-of datetime (tabular) · source display name
  · optional state word (FRESH / STALE).
- **Content contract:** exact as-of datetime with timezone (e.g. `2026-10-21 02:00
  UTC`); source display name (never a raw slug); state from {fresh, stale}. A missing
  as-of suppresses the panel value, never prints a blank or zero timestamp.
- **Tokens:** `--font-mono`, `--fs-label`, `--muted`, `--text`, `--fresh-ok`,
  `--ink-warn`.
- **States:** fresh (state word in `--fresh-ok`), stale (state word in `--ink-warn`).
- **ZH notes:** 截至 / 数据源 labels; freshness is status ink — never flips under
  红涨绿跌.
- **Keyboard/touch:** non-interactive; if wrapped in a detail link, that link carries
  the focus ring and a 44px target.
- **Do not:** never duplicate the stamp inside the same panel — one per panel.

## panel-footnote

- **Purpose:** the single merged methodology/honesty line at a panel's foot.
- **Anatomy:** top hairline · one-sentence footnote (≤ 1 sentence) · optional `?`
  receipt affordance (Tier 2 home for mechanics).
- **Content contract:** one sentence, plain words; constants (base rates, windows)
  stated once here, never repeated per row; optional correction sentence
  `Corrected <date>: <what changed>`.
- **Tokens:** `--fs-label`, `--muted`, `--text`, `--line`, `--ink-info`.
- **States:** corrected (correction sentence, "Corrected" marker in `--ink-info`).
- **ZH notes:** full-width punctuation; translate the sentence, keep one line.
- **Keyboard/touch:** the `?` affordance is a focusable 44px target when present.
- **Do not:** never stack a second footnote line — merge.

## state-banner

- **Purpose:** one panel-level banner stating a state that changes how the board is
  read (stale, regenerated schema, partial coverage, corrected, failed, loading,
  locked, abstained).
- **Anatomy:** state icon (monoline) · state word (caps) · one message sentence ·
  optional action link.
- **Content contract:** state from {stale, incompatible_generation, partial,
  corrected, error, loading, locked, abstained}; one plain sentence naming what the
  reader should do differently; optional action label + target. Severity ink:
  stale/partial/incompatible_generation → `--ink-warn`; corrected → `--ink-info`;
  error → `--ink-act`; loading/abstained → `--muted`; locked → neutral (lock glyph).
- **Tokens:** `--panel2`, `--line`, `--surface-warn-subtle`, `--ink-warn`,
  `--ink-act`, `--ink-info`, `--ink-link`, `--muted`, `--text`, `--fs-label`,
  `--fs-sm`, `--font-ui`.
- **States:** stale, incompatible_generation, partial, corrected, error, loading,
  locked, abstained (the banner is the panel-level home for all of them).
- **ZH notes:** state words translate; severity ink never flips (status plane).
- **Keyboard/touch:** action link focusable with 44px target; banner itself inert.
- **Do not:** never carry state on a colored edge — even 1px border, neutral or
  semantic-tinted, full stop on all four edges.

## stance-chip

- **Purpose:** the one action-toned call of a panel, in the house stance vocabulary.
- **Anatomy:** pill chip · stance text (the label IS the signal; never color alone).
- **Content contract:** value exactly one of **Act · Get ready · Watch — don't chase
  · Protect gains · Stand aside · Ignore** (doctrine Law 1). No seventh value; no
  truncation. Ink mapping (estate `.mx-stance` recipe, theme.css:2775): Act / Get
  ready → `--ink-ok`; Watch — don't chase / Protect gains → `--ink-warn`; Stand
  aside / Ignore → `--muted`.
- **Tokens:** `--fs-label`, `--font-ui`, `--panel`, `--line`, `--text`, `--ink-ok`,
  `--ink-warn`, `--muted`.
- **States:** fresh, stale (stale tag rides the row, not a recolor of the stance).
- **ZH notes:** 行动 / 准备就绪 / 观望——勿追高 / 保护收益 / 暂时回避 / 忽略;
  stance is not direction — never flips under 红涨绿跌, never painted `--up/--down`.
- **Keyboard/touch:** when the chip links to a detail view it is focusable, 44px.
- **Do not:** never invent a stance outside the six, and never print a stance for an
  abstained call — abstained renders its own tag (see timing-ladder-row).

## direction-delta

- **Purpose:** a signed change over a stated horizon — the ONLY component whose ink
  flips under zh.
- **Anatomy:** arrow icon (up / down rotated 180° / none for flat) · signed value
  (tabular, explicit `+`/`−`) · basis label (horizon or series).
- **Content contract:** value with sign and unit; direction enum {up, down, flat};
  basis (e.g. `3m`); as-of via the panel stamp. Unknown value renders `—` +
  "unavailable" in `--muted` — never `0.0%`.
- **Tokens:** `--fs-sm`, `--fs-micro`, `--ink-up`, `--ink-down`, `--muted`,
  `--font-ui`.
- **States:** fresh, stale (value dims, `--muted`, with stale tag), error (renders
  the unavailable form).
- **ZH notes:** 红涨绿跌 — up renders red, down green under
  `html[data-lang="zh"]`, automatically: the chip inks are `--ink-up/--ink-down`,
  which re-resolve from the swapped `--up/--down` (theme.css:277–293). No local
  zh rule exists or may be added.
- **Keyboard/touch:** inert; a wrapping detail link carries focus/44px.
- **Do not:** never print an unsigned delta or a direction color on any other
  component — direction ink is centralized here.

## health-badge

- **Purpose:** pipeline/data health of a board (is the feed itself well?).
- **Anatomy:** status dot (fill + halo ring) · level word · checked-basis line.
- **Content contract:** level from {good, degraded, down}; basis naming what was
  checked and when (e.g. `engine run 2026-10-21`); as-of via panel stamp.
- **Tokens:** `--ink-ok`, `--ink-warn`, `--ink-act`, `--fresh-ok`, `--warn`,
  `--act`, `--ring-ok`, `--fs-label`, `--fs-micro`, `--muted`, `--font-ui`.
- **States:** fresh, stale, error (error renders level `down` + error-state, not a
  recolor).
- **ZH notes:** 良好 / 降级 / 中断 — health/danger ink is invariant in every locale
  (theme.css:259): NEVER flips, never derived from `--up/--down`.
- **Keyboard/touch:** inert; basis line may host a Tier-2 tip target (44px if
  focusable).
- **Do not:** never encode direction in the health dot or reuse it for market calls.

## lock-chip

- **Purpose:** mark content that exists but is not available at the reader's tier.
- **Anatomy:** padlock glyph (monoline) · "Locked" label · scope/reason subline.
- **Content contract:** what is locked (scope display name); reason class in plain
  words (e.g. `depth tier`); the locked content keeps its footprint (no layout
  shift) and is ghosted, never silently removed.
- **Tokens:** `--panel2`, `--line`, `--muted`, `--text`, `--fs-label`, `--fs-micro`,
  `--font-ui`. (Violet ink pending the `--lock` token — gap 1.)
- **States:** locked.
- **ZH notes:** 已锁定; violet is lock-only estate-wide — when the token lands it
  applies here and nowhere else; no direction flip.
- **Keyboard/touch:** inert by default; an upgrade/dismiss affordance, when present,
  is focusable with a 44px target.
- **Do not:** never paint any other component violet, and never blur content without
  this label present.

## model-prior-badge

- **Purpose:** provenance tag separating model output from prior (base-rate) context.
- **Anatomy:** caps tag · neutral fill · text label MODEL or PRIOR (label carries the
  meaning; fill never does).
- **Content contract:** source exactly `MODEL` or `PRIOR`; binds 1:1 to
  `engine/hazard_score.py` `source` field (`MODEL` = fitted model, `PRIOR` = KM
  family baseline — context, not a model output). **Law: in the hazard ladder the
  up/3m and up/6m cells are PRIOR** until re-qualified; four of six cells are
  qualified.
- **Tokens:** `--panel2`, `--line`, `--text`, `--muted`, `--fs-micro`.
- **Minimum size (VTC-009):** the tag label is never below 11px (`--fs-label`) on
  any viewport; the tag reduces by dropping padding, never by shrinking the type.
- **Producer-bound:** the PRIOR tag appears only when the producer emits
  `source: PRIOR`; the current `data/sector_cycles` producer emits MODEL×12 and no
  PRIOR value, so no PRIOR tag is rendered until it does.
- **States:** fresh, stale (rides the parent).
- **ZH notes:** 模型 / 历史基准 (plain words, not 先验); no hue flip — provenance is
  not direction or health.
- **Keyboard/touch:** inert.
- **Do not:** never colour MODEL green / PRIOR red, and never ship a PRIOR value
  without this tag beside it.

## grader-caption

- **Purpose:** the fixed epistemics line under any hit-rate figure.
- **Anatomy:** caption line (fixed sentence) · optional measured value + basis
  (data-bound).
- **Content contract:** the sentence is exactly **"Conditional hit rate, not a win
  rate"**; the recorded grader figure (~0.274) may appear beside it only with this
  caption, with its basis (n, window) bound from data; a partial basis omits fields
  rather than estimating them.
- **Tokens:** `--fs-label`, `--fs-micro`, `--muted`, `--text`.
- **States:** fresh, stale, partial (basis incomplete → fields omitted).
- **ZH notes:** 条件命中率，非胜率; muted epistemics ink in every locale.
- **Keyboard/touch:** inert.
- **Do not:** never relabel as "win rate", "accuracy", or "edge", and never show the
  number without the caption.

## source-rank-row

- **Purpose:** one row of a ranked source/list panel (rank, name, measured value).
- **Anatomy:** rank numeral · display name · measured value + unit · provenance slot
  (model-prior-badge) · as-of/state slot.
- **Content contract:** 1-based rank; display name (never a slug); value with unit
  and its plain-word meaning (doctrine Law 3); provenance when the value is
  model/prior; hairline between rows. Partial coverage renders `—` + "unavailable",
  never `0`.
- **Tokens:** `--fs-label`, `--fs-sm`, `--fs-micro`, `--font-mono`, `--muted`,
  `--text`, `--line`, `--ink-warn`, `--ink-info`.
- **States:** fresh, stale (stale tag `--ink-warn`), partial (unavailable form),
  corrected (corrected tag `--ink-info`).
- **ZH notes:** names/ranks translate; any change value renders through
  direction-delta (the only flip point).
- **Keyboard/touch:** row focusable when it opens a detail view; 44px target.
- **Do not:** never print a bare score without unit or meaning word.

## section-header

- **Purpose:** title block of one board section.
- **Anatomy:** eyebrow (optional, caps) · title (≤ 4 words) · count tag · optional
  `?` help slot · optional see-all slot (right-aligned).
- **Content contract:** plain title; count of underlying rows when shown; `?` hosts
  the Tier-2 mechanics; see-all only when more rows exist.
- **Tokens:** `--fs-label`, `--fs-h3`, `--fs-micro`, `--muted`, `--text`, `--line`,
  `--font-ui`.
- **States:** fresh, loading (title + skeleton count tag).
- **ZH notes:** drop letter-spacing/tracking on Hanzi (theme.css:566 idiom); no
  colored slab or edge behind the title.
- **Keyboard/touch:** `?` and see-all slots focusable, 44px.
- **Do not:** never put internal vocabulary in the title (doctrine Law 2).

## see-all-link

- **Purpose:** expand a capped list to its full membership.
- **Anatomy:** text link reading exactly **"See all N"** · chevron glyph.
- **Content contract:** N = real total count (> shown count), bound from data;
  appears after **at most 8** visible rows; href opens the full list. Renders only
  with a bound N — never a placeholder count, never when N ≤ shown rows.
- **Tokens:** `--fs-sm`, `--ink-link`, `--link`, `--line`.
- **States:** none of its own (hidden while the count is loading/error).
- **ZH notes:** 查看全部 N.
- **Keyboard/touch:** focusable link, visible focus ring, ≥ 44px tall on touch.
- **Do not:** never emit "See all" without the count.

## skeleton-block

- **Purpose:** loading placeholder that preserves the true geometry of the content it
  replaces.
- **Anatomy:** one neutral shimmer block per replaced element; variants match the
  target: `stamp`, `chip`, `line`, `row`, `cell`.
- **Content contract:** the block's height, width class, line count and radius equal
  the real component's — zero layout shift on swap; reduced-motion renders the flat
  surface, no shimmer.
- **Tokens:** `--surface-skeleton-deep`, `--text`, `--line`.
- **States:** loading (only).
- **ZH notes:** language-neutral; ZH text lines keep the same geometry contract.
- **Keyboard/touch:** inert; never focusable.
- **Do not:** never shrink-wrap to a smaller default bar — that is layout shift, not
  loading.

## empty-state

- **Purpose:** state that a dataset is honestly empty (distinct from failure).
- **Anatomy:** quiet monoline icon · one-line label · guidance sentence · optional
  action link.
- **Content contract:** what is empty (dataset display name); the honest reason in
  plain words when known (e.g. "nothing qualified today"); guidance says what to do
  (usually: nothing yet, board updates tonight); never fabricated rows.
- **Tokens:** `--fs-sm`, `--text`, `--muted`, `--line`, `--panel`, `--ink-link`.
- **States:** empty.
- **ZH notes:** 暂无数据 phrasing; keep the reason sentence.
- **Keyboard/touch:** action link focusable, 44px.
- **Do not:** never render zeros/dashes as content — empty is a stated condition.

## error-state

- **Purpose:** state that a load or computation failed.
- **Anatomy:** alert icon · label (e.g. "Couldn't load") · one message sentence ·
  retry action · error class (Tier 2, in a tip — never Tier-1 slugs).
- **Content contract:** human message ≤ 1 sentence; error class slug for the
  tooltip only; retry target id; as-of of the last good render when one exists.
- **Tokens:** `--ink-act`, `--fs-sm`, `--fs-micro`, `--text`, `--muted`, `--line`,
  `--panel`, `--panel2`.
- **States:** error.
- **ZH notes:** 加载失败 phrasing; danger ink never flips.
- **Keyboard/touch:** retry is a focusable 44px button; focus moves to it when the
  state replaces focused content.
- **Do not:** never show a stack trace or raw slug on Tier 1.

## series-picker

- **Purpose:** choose one series/horizon/universe for a panel.
- **Anatomy:** group label (visually hidden or eyebrow) · pill track · options
  (radiogroup semantics, `aria-checked`) · optional basis note.
- **Content contract:** option display names; exactly one selected; selection
  changes the panel's data basis (basis note states it).
- **Tokens:** `--panel2`, `--line`, `--panel`, `--text`, `--muted`, `--fs-label`,
  `--font-ui`.
- **States:** fresh, loading (skeleton options, same geometry).
- **ZH notes:** option labels translate; selected option = quiet fill + stronger
  text (never a colored edge or ring).
- **Keyboard/touch:** arrow keys move within the group; roving focus ring; ≥ 44px
  options on touch.
- **Do not:** never indicate selection with color alone — fill + weight + aria.

## phase-chip

- **Purpose:** where a name sits in the five-phase cycle taxonomy.
- **Anatomy:** pill chip · phase label (short form on Tier 1) · optional phase dot.
- **Content contract:** value exactly one of Trough / Recovery / Expansion / Peak /
  Downturn (short labels Bottoming / Prime entry / Trending / Topping / Rolling
  over; engine taxonomy engine/sector_cycles.py:126). Ink: Trough → `--ink-info`,
  Expansion → `--ink-ok`, Peak → `--ink-warn`, Downturn → `--ink-act`; Recovery →
  neutral `--muted` until the teal token lands (gap 2).
- **Tokens:** `--ink-info`, `--ink-ok`, `--ink-warn`, `--ink-act`, `--muted`,
  `--panel`, `--line`, `--text`, `--fs-label`.
- **States:** fresh, stale.
- **ZH notes:** labels from the engine's PHASE_ZH (筑底阶段 / 复苏阶段 / 扩张阶段 /
  顶部阶段 / 下行阶段); phase is not price direction — never flips, never
  `--up/--down`.
- **Keyboard/touch:** inert; filterable variants are focusable chips with 44px
  targets.
- **Do not:** never invent a sixth phase or recolor phases per-universe.

## leg-timeline-item

- **Purpose:** one leg of the cycle turns/legs timeline (clicking reveals its
  narrative).
- **Anatomy:** verb chip (Rally/Selloff, arrow glyph, neutral ink) · date range ·
  inline direction-delta (the magnitude — the colored, zh-flippable part) · status
  tag (Open / Major) · collapsed narrative (Tier 2).
- **Content contract:** leg direction {up, down}; start/end dates (ISO); magnitude
  through a direction-delta instance; open-leg flag (running extreme — magnitude is
  provisional); major flag (≥ 20% swing, engine/sector_cycles.py:139); one-line
  narrative on expand.
- **Tokens:** `--panel2`, `--panel`, `--line`, `--text`, `--muted`, `--fs-label`,
  `--fs-sm`, `--fs-micro`, `--ink-info`.
- **States:** fresh, stale, partial (open leg — flagged), corrected (tag
  `--ink-info`).
- **ZH notes:** 上行 / 下行 verb labels; the verb chip stays neutral ink in every
  locale — the colored direction read lives in the inline direction-delta ONLY
  (packet law: 红涨绿跌 flips direction-delta alone). No left-edge accent (the
  legacy `.sc-leg` border-left idiom is repealed here).
- **Keyboard/touch:** whole item is a focusable disclosure (button semantics);
  44px tall minimum; expanded state announced.
- **Do not:** never color the verb chip with `--up/--down` — that moves the flip
  outside direction-delta.

## hazard-ladder

- **Purpose:** the six-cell calibrated turn-hazard grid P(turn within h months).
- **Anatomy:** column headers (1m / 3m / 6m) · two row labels (Down legs / Up legs) ·
  six cells: value (%, tabular) + model-prior-badge · active-row quiet fill ·
  epoch/PRIOR note line.
- **Content contract:** per cell — probability from
  `engine/hazard_score.py::score` (`1m/3m/6m`), `source` MODEL|PRIOR bound to the
  badge, `cell_verdict`; ladder-level — model epoch (e.g. `price_c4414dcb`),
  direction of the open leg (which row is active), and the qualification note:
  **four of six cells qualified; up/3m and up/6m remain PRIOR** (KM family base
  rate). PRIOR cell values render muted + tagged; never an untagged PRIOR value.
- **Tokens:** `--panel2`, `--panel`, `--line`, `--text`, `--muted`, `--fs-md`,
  `--fs-micro`, `--fs-label`, `--font-ui`.
- **States:** fresh, stale, incompatible_generation (schema/epoch guard trips →
  ladder suppressed, error-state + state-banner shown instead), loading (skeleton
  cells, same geometry).
- **ZH notes:** 下行 / 上行 row labels, 1个月/3个月/6个月 headers; probabilities are
  not direction ink — no flip; the revision-optimistic caveat stays in the Tier-2
  tip.
- **Keyboard/touch:** cells may host focusable tips (44px); the grid itself is
  static.
- **Do not:** never relabel PRIOR cells as qualified, and never summarize the ladder
  as a win rate — it is a conditional probability.

## timing-ladder-row

- **Purpose:** one name's rung on the timing ladder (call + basis + change).
- **Anatomy:** display name · stance-chip · window basis ("since <date>") · inline
  direction-delta · optional abstained tag or lock-chip.
- **Content contract:** display name; stance from the six values (via stance-chip);
  window start date; change via direction-delta; an abstained call renders the
  dashed "Abstained this cycle" tag in `--muted` — it is a recorded non-call, never
  silently mapped to a cautious stance; locked rows keep their footprint.
- **Tokens:** `--fs-sm`, `--fs-micro`, `--text`, `--muted`, `--line`.
- **States:** fresh, stale, abstained, locked.
- **ZH notes:** 自 <date> 起 basis; only the inline direction-delta flips.
- **Keyboard/touch:** row focusable when it opens a detail sheet; 44px target.
- **Do not:** never fill an abstained rung with a default stance.

## mobile-sheet

- **Purpose:** bottom-sheet container for board detail on ≤ 640px viewports.
- **Anatomy:** backdrop (dialog token) · sheet surface (even border, top radii,
  popover shadow) · drag handle · title row + close button · content slot (any spc
  components) · optional footer action.
- **Content contract:** title ≤ 4 words; close affordance always present; content
  slot hosts any component above; the sheet never introduces its own header family.
- **Tokens:** `--panel`, `--line`, `--popover-shadow`, `--text`, `--muted`,
  `--fs-h3`, `--fs-sm`, `--pv-dialog-backdrop` (gap 3: theme-neutral token pending).
- **States:** none of its own — hosts any child component state.
- **ZH notes:** 关闭 close label; no flip concerns beyond children.
- **Keyboard/touch:** open moves focus into the sheet; Esc/backdrop closes; focus
  returns to the opener; every control ≥ 44px; drag handle hit area ≥ 44px tall;
  page scroll locked while open.
- **Do not:** never a colored top edge or drop-shadow-only boundary — the even 1px
  border is the affordance.

## table-alternative-toggle

- **Purpose:** switch a dense table between the table and its alternative view
  (ladder/cards) — the narrow-width reading aid.
- **Anatomy:** two-option segmented control (radiogroup) · current/alt labels ·
  row-count note (aria-describedby).
- **Content contract:** both view labels in plain display words (e.g. Table /
  Ladder); the count of rows is preserved across the switch (stated for screen
  readers); disabled state carries a reason via lock-chip, not a bare grey-out.
- **Tokens:** `--panel2`, `--line`, `--panel`, `--text`, `--muted`, `--fs-label`,
  `--font-ui`.
- **States:** fresh, locked (alt view unavailable — opacity dim + lock glyph +
  `aria-disabled`).
- **ZH notes:** 表格 / 阶梯图 labels; selection = quiet fill + stronger text.
- **Keyboard/touch:** arrow keys toggle; visible focus ring; ≥ 44px options on
  touch; stays visible at narrow widths (that is where it matters).
- **Do not:** never swap views without preserving sort/filter state.
