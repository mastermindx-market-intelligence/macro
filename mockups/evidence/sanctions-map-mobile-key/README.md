# O28 R2 — mobile-key calibration record

## Purpose

Calibration of the O28 mobile UK-news mark (solid hairline below 600 px).
The CSS sweep + baseline receipts pin the chosen (W, OD, OL) against the mark
it replaces — a mark nobody can see while the legend promises one is
dishonest. D54 rules govern the choice; this directory holds the
measurements that the choice rests on.

## D54 rulings (binding, from the seat)

(i) the light-theme chroma criterion `mark_mean_chroma < rung3_mean_chroma`
is **WITHDRAWN** as mis-specified. R1 measured the light rung-3 fill at
chroma 0.53 — near-achromatic — so no coloured mark could ever satisfy
it. Replaced by **`light mark_mean_chroma <= dark mark_mean_chroma`**
(light is never louder than dark).

(ii) The legibility floor is **CALIBRATED against the mark this change
replaces**, not assumed: origin/main's mobile mark first (dashed `13 8`,
width 1.5, full opacity); FLOOR = 20 if `min(baseline_dark, baseline_light)
>= 25`, else FLOOR = `min(baseline_dark, baseline_light)` — the new solid
mark must be at least as present as the dashed one it replaces, and never
invisible.

(iii) Choose the **QUIETEST** setting that clears FLOOR on both themes
from a fixed sweep grid — never a guess, never a widened grid.

(iv) Everything else from R1 stands: solid hairline below 600 px; legend
key mirrors the mark per theme (width, style, opacity); desktop rules
untouched; no colour literals; `vector-effect:non-scaling-stroke` inherited
from :49.

## Metric definition (capture.py)

- `uk_box_blue_px` — count of pixels in a 21×21 CSS-px PNG clip centred on
  the GBR bbox (`cx = bbox.x + bbox.w/2`; `cy = bbox.y + bbox.h/2`;
  clip = `cx-10.5, cy-10.5, 21×21`); full-page screenshot at DPR 1.
  Per-theme stroke colour: dark `(122, 167, 224)`, light `(41, 90, 234)`.
  Pixel counted when `Σ((rgb_i − stroke_i)²) < 60² = 3600`.
  Max value = 441 (entire 21×21 box).
- `mark_mean_chroma` — mean of `max(r,g,b) − min(r,g,b)` over all 441
  pixels of the UK box (every pixel — not just blue ones).
- `rung3_mean_chroma` — same metric on a 21×21 clip centred on the first
  `.wm-c[data-rung="3"]` node (RUS).

Capture tool: `capture.py` (this directory). All scratch CSS, threshold
classifiers, and DOM-evaluation paths are shared with R1 — only the O28
CSS patch parameters (W, OD, OL) and the parity-resolution path differ.

## Baseline (S1) — the mark being replaced

Captured via `capture.py --baseline --theme both --locale en` against
origin/main's CSS (the dashed `13 8` + width 1.5 rule, full opacity).

| theme | uk_box_blue_px | mark_mean_chroma | rung3_mean_chroma |
|-------|----------------|------------------|-------------------|
| dark  |             31 |            17.61 |              9.14 |
| light |             31 |            18.03 |              0.53 |

`FLOOR=20` per D54(ii): `min(31, 31) = 31 ≥ 25` → FLOOR = 20.

The light rung-3 chroma (0.53) confirms D54(i)'s reading — that cell's
land is near-achromatic, so the chroma-louder-than-rung3 test was a
trap no coloured mark could satisfy.

## Sweep (S2) — 21 captures, fixed grid

Grid: W ∈ {1, 1.25, 1.5}; dark OD ∈ {.7, .85, 1}; light OL ∈ {.55, .7, .85, 1}.
Per W: 3 dark × 4 light = 7 measurements, × 3 W = 21 total.

`dark@W=1.25, OD=.7`        uk_box_blue_px= 0  mark_chroma=15.399  rung3=9.141  parity=False
`dark@W=1.25, OD=.85`       uk_box_blue_px=20  mark_chroma=16.766  rung3=9.141  parity=False
`dark@W=1.25, OD=1`         uk_box_blue_px=33  mark_chroma=18.070  rung3=9.141  parity=False
`light@W=1.25, OL=.55`      uk_box_blue_px= 0  mark_chroma=10.676  rung3=0.533  parity=False
`light@W=1.25, OL=.7`       uk_box_blue_px= 0  mark_chroma=13.431  rung3=0.533  parity=False
`light@W=1.25, OL=.85`      uk_box_blue_px=22  mark_chroma=16.156  rung3=0.533  parity=False
`light@W=1.25, OL=1`        uk_box_blue_px=27  mark_chroma=18.807  rung3=0.533  parity=False

(W=1 — all dark rows under FLOOR=20; W=1.5 — clears but is not smallest;
full 21-row table in `sweep.json`.)

## Choice (S3) and the deterministic rule

- **W=1** — no dark OD clears FLOOR=20 (max blue_px = 13 at OD=1). Skip.
- **W=1.25** — dark OD=.85 → blue_px = 20 ✓; light OL=.85 → blue_px = 22 ✓.
  Both themes clear at the smallest grid value. OL ≤ OD (.85 ≤ .85) ✓.
  light chroma (16.156) ≤ dark chroma (16.766) ✓.
- **W=1.5** — also clears (dark@.85 = 33, light@.85 = 30) but is not the
  smallest W. Skip per D54(iii).

**Chosen: W=1.25, OD=.85, OL=.85.**

WHY this is the unique answer under D54: smallest W clearing FLOOR on
both themes is W=1.25; the smallest OD at W=1.25 that clears is .85;
the smallest OL at W=1.25 that clears is .85; OL ≤ OD and light chroma
≤ dark chroma both hold — no re-step required.

The previous R1 pick (.7 / .55) measured `uk_box_blue_px` 1/0/1/0 of 441
at W=1 — invisible. R2's mark at (W=1.25, OD=.85, OL=.85) measures 20/22
on dark/light — at least as present as the dashed mark it replaces (31/31)
isn't the bar; clearing FLOOR=20 is.

## DARK TREATMENT (theme art direction)

- The GBR mark stroke is a **solid hairline**, stroke-width `1.25` with
  `vector-effect: non-scaling-stroke` (inherited from the desktop rule
  at :49).
- Opacity `.85` — calm command-center restraint, no glow.
- Legend key mirrors: `border: 1.25px solid var(--ink-link)`, opacity `.85`.
  Width parity is verified against the **CSS source** (`stroke-width:1.25`
  vs `border:1.25px solid`), not against `getComputedStyle()` —
  Chromium rounds HTML border-width to integer pixels in computed style
  (1.25 → 1) but preserves SVG stroke-width as written; the source-CSS
  parity check is the only honest comparator across the sub-pixel gap.

## LIGHT TREATMENT (theme art direction)

- Same solid hairline at `stroke-width: 1.25` / `border: 1.25px solid`.
- The light override sets `stroke-opacity: .85` on the GBR mark and
  `opacity: .85` on the legend key — these match dark **by construction**
  (D54(i) withdrew the chroma-louder-than-rung3 test; light vs dark
  is now constrained by `light chroma ≤ dark chroma`, which holds at
  this choice).
- Visual treatment: research workspace, hairline discipline, shadow
  instead of glow — the SAME solid hairline as dark, calibrated to the
  same legibility floor.

## Mechanisms that intentionally differ (dark vs light)

- The CSS carries TWO light overrides (one on the GBR mark, one on the
  legend key) that pin `opacity .85` explicitly. These are kept even
  when OL = OD (`.85`) — they pin the **parity contract** (theme
  attribute is named in the source so future OD/OL changes can
  re-diverge without re-deciding the parity semantics). The marks
  themselves are otherwise identical in dark and light.

## D9 disclosure (page chrome)

The cross-origin "Ask Mastermind" floating button is **NOT** present in
the local-served fixture — it loads cross-origin and the local fixture
does not include it (R1's event-layer-fix README §"Fixed page chrome —
Ask Mastermind button" established this). No FAB hiding was needed; the
mark is measured without the FAB in the frame.

## What was NOT captured

- **Desktop** — unchanged by this PR (rules at :47–62, :79 stay exactly
  as origin/main). The capture includes desktop screenshots for the
  OWNER receipt (`mockups/evidence/sanctions_map/`) but the mobile-key
  calibration is 390-px only.
- **Hover / focus on the SVG path** — none. The path is decorative and
  has no hover handler; focus would be meaningless.

## Files

- `capture.py` — measurement primitive (4-cell capture, refactored R2).
- `sweep.py` — 21-row grid driver that re-uses `capture._capture_one`.
- `dom.json` — 4 cells at the FINAL block (W=1.25, OD=.85, OL=.85).
- `baseline.json` — 2 cells at origin/main's dashed `13 8` + 1.5.
- `sweep.json` — 21 rows × (theme, W, opacity) at the fixed grid.
- `cells/baseline-{dark,light}-390.png` — UK-zoom crops at the baseline.
- `cells/{dark,light}-{en,zh}-390-{ukzoom,legend}.png` — 4 final cells ×
  ukzoom + legend (8 crops).
- `EVIDENCE.yml` — receipt pointer to the OWNER manifest.