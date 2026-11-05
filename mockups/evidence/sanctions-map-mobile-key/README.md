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

(ii) D58 (amends D54(ii)) — D54(ii) is amended: the sentence "the new
solid mark must be at least as present as the dashed one it replaces"
is STRUCK. FLOOR is a VISIBILITY floor, not a loudness-parity bar:
FLOOR = 20 when `min(baseline_dark, baseline_light) >= 25`, else
FLOOR = `min(baseline_dark, baseline_light)`. Rationale, measured in
sweep.json: `uk_box_blue_px` counts pixels within colour-distance 60 of
the full-opacity stroke colour, so it is an opacity cliff
(W=1.25: .7 -> 0, .85 -> 20/22, 1 -> 33/27), not a legibility measure;
matching the dashed 1.5-wide baseline's 31/31 would need W=1.5 with OL=1
(41), which inverts the D54(i) chroma order (light 21.88 > dark
17.98/19.51), or would break width continuity with the desktop 1.25
mark. The chosen rung (1.25/.85/.85) is legible in both themes (seat's
Opus review at 10x zoom); dark sits exactly at FLOOR with zero margin —
recorded, not hidden: the receipt is static and the test reads
committed receipts, so the gate cannot flake.

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

`FLOOR=20` per D58 (amending D54(ii) — a visibility floor, not a
loudness-parity bar): `min(31, 31) = 31 ≥ 25` → FLOOR = 20.

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

`parity=False` in the sweep rows is RENDERED-width parity: Chromium rounds
the legend key's `border:1.25px` to `1px` in `getComputedStyle()` while the
SVG stroke keeps `1.25px`, so a rendered comparison can never read True at
W=1.25 (nor at 1.5). `dom.json`'s `key_mark_parity` (True) is computed from
the SOURCE CSS — the two columns disagree by construction, and the
legibility test asserts the source form (see "DOM record").

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
on dark/light — clearing FLOOR=20 (D58) is the bar.

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
- Visual treatment: research workspace, hairline discipline — the
  SAME solid hairline as dark, calibrated to the same legibility floor.

## Mechanisms that intentionally differ (dark vs light)

None — the mark is a shared 1.25 hairline at .85 in both themes by
design (token-only difference: `--ink-link` resolves to each theme's
link ink). Judged as a design in each theme: dark reads as a calm
outline on the `--panel2` map; light as a crisp saturated hairline on
the near-white map — the most saturated element in the frame, accepted
for a single small annotation.

## DOM record

`key_mark_parity` is derived from the SOURCE CSS (legend border 1.25px
vs stroke 1.25), not from the rendered border — Chromium rounds a
1.25px border to 1px at DPR 1 (`legend_news_i_border_width: "1px"`).

dark `uk_box_blue_px` = 20 = FLOOR — zero margin, recorded; static
receipt, deterministic test.

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
- `cells/baseline-{dark,light}-390-legend.png` — legend crops at the
  baseline (R4: `--baseline` writes `baseline-`-prefixed names so a
  final-rung run can no longer overwrite them).
- `cells/{dark,light}-{en,zh}-390-{ukzoom,legend}.png` — 4 final cells ×
  ukzoom + legend (8 crops).
- `EVIDENCE.yml` — receipt pointer to the OWNER manifest.

## R4 (2026-10-03) — review repairs, re-generated by the R4 module

- `dom.json` and `baseline.json` were re-generated by the R4 `capture.py`
  (sha256 `d48820a7…`) so `capture_tool_module_sha256` pins the module that
  produced them. Every metric is unchanged: final rung dark 20 / light 22
  `uk_box_blue_px` (parity True, `1.25px` @ `.85`), baseline 31 / 31.
- Determinism, measured: the re-generated baseline UK-zoom crops
  `cells/baseline-{dark,light}-390.png` are byte-identical to the R2
  capture (sha256 `853a27b2…` / `17f0e781…`, the values `baseline.json`
  has recorded since R2), and the four final-rung `ukzoom`/`legend` crops
  are byte-identical to the R3 commit (no `cells/*` modification in the R4
  diff).
- Baseline legend crops `cells/baseline-{dark,light}-390-legend.png` are
  committed for the first time. Root cause of the R3 loss: `--baseline`
  wrote the SAME `{theme}-{locale}-390-*` names as the final-rung run, so
  the later run overwrote the earlier crops and R3's orphan pass deleted
  the collided files; `_crop_names()` now prefixes baseline crops.
- Legibility test: light rows compare their rendered stroke opacity to the
  LIGHT CSS value (`.85` both, so no value changed — the comparator did).
- Owner receipt `mockups/evidence/sanctions_map/`: fully recaptured in R3
  by one run of `scripts/capture_page_evidence.py` 1.3.0, so its
  `tool.module_sha256` is honestly the single sha `8d753e28…`; the
  attribution test accepts that form and still checks every per-cell stamp
  names the same module (the historical list-form contract is kept).

## R5 (2026-10-03) — sweep provenance, collision closure, superseded force-state rows

Opus R4 delta review (PASS-WITH-NITS) left one MINOR and three nits; all closed
here, plus the explicit ruling Sol's support audit (#8307 comment 5966226953)
asked for on the owner manifest's history.

**sweep.json provenance.** The committed `sweep.json` was written by module
`75d6e65d…`, the R2 lane's uncommitted intermediate of `capture.py` (b23efdfe
and 245335a7 both carry `f885069…`). Its parity column is RENDERED-width parity
— verified from the data, not the code: `legend_news_i_border_width` is `1px`
on all 21 rows and `key_mark_parity` is True exactly when W=1. `sweep.json` is
NOT regenerated: it is the S2 receipt D54/D58 were ruled on. `sweep.py` is
repaired so the committed code reproduces that column's semantics: a sweep row
now records `key_mark_parity` explicitly as `gbr_stroke_width ==
legend_news_i_border_width` (rendered) and `key_mark_parity_source` as the
source form, passes each grid point's block to `_capture_one`, and writes its
crops into its own scratch directory (`cells_dir=`), so a grid point can never
overwrite `cells/{theme}-en-390-*.png` (the collision class R4 closed for
`--baseline`, now closed for every caller).

**baseline.json `o28_block`.** A `--baseline` run renders `_OLD_MOBILE`, so its
block now records what was rendered — `width 1.5`, `stroke_dasharray 13 8`,
opacities null, `block: _OLD_MOBILE` — parsed from the constant, not the
ignored argument defaults the R2–R4 file carried.

**Attribution pin.** The string branch of the attribution test now pins the
1.3.0 module literal `8d753e28…` exactly as the list branch pins `97b44358…`;
a made-up hex digest no longer passes.

**Ruling — the three 2026-09-08 force-state rows are SUPERSEDED, not silently
dropped (CEO A seat, owner of #8307).** The base owner manifest
(`85932a1b:mockups/evidence/sanctions_map/manifest.json`) carried eight rest
cells plus three OPTIONAL force-state cells — `unknown_rung` dark/light and
`theme_toggle_dark_to_light` — captured 2026-09-08 against the pre-D54 template
under a pre-commit disclosure target (HEAD `8e6b1339` + an uncommitted rebuild)
with `axes.force_states: []`, i.e. hand-driven rows, not CLI force states. The
contract never required them: `EVIDENCE.yml` names only the manifest, and
`scripts/check_ui_visual_evidence.py` (MINOR-3 docstring) classes a
`force_state` cell as an additional state OUTSIDE the required
viewport × locale × theme matrix. The 2026-10-03 full recapture by 1.3.0
depicts CURRENT bytes (8 rest + 8 `row_hi` focus cells, gate rc=0). Mixing
09-08 cells into a receipt of current bytes would assert states of a page that
no longer exists, and the 1.3.0 force-state kinds (body class/attribute, hover,
focus) cannot drive a DATA state (an unknown rung) or a theme toggle, so they
cannot be recaptured as current evidence by this tool. The light-theme
unknown-rung hatch stays pinned at template level by
`tests/test_sanctions_map_page.py::test_light_theme_unknown_rung_keeps_hatch`.
The three cells remain in git history (PNGs `662dcf3f…`, `b17aa17f…`,
`b7b66af7…` at 85932a1b). Attribution follows from the same fact: every current
cell was made by one run of `8d753e28…`, so the single string is the true
attribution; a list with `97b44358…` first would attribute sixteen cells to a
module that made none of them (the checker's own rule: an unstamped cell
attributes to element 0).

**Re-generation.** `capture.py` changed (cells_dir, baseline o28_block), so both
JSON receipts were re-generated by the R5 module on the same mini2 host; all
twelve referenced crops are byte-identical to R4 (shas unchanged), and the
metrics are unchanged (dark 20 / light 22 final; 31 / 31 baseline).
