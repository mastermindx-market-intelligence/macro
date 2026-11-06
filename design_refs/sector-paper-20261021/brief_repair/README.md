# Brief HTML specimen (boards 23–27, 32, 33, 37) — PAPER_CAPACITY_LIMITED

Seat-authored HTML specimen of the R3 Sector Brief (board 12/13/22 family) for the
`sector-intelligence-cycles-20261021` reference set. It exists because the Paper file
`01M2WGNCX9475G79JRKJTCM08P` carries a file-wide size-limit warning and the seat makes
no Paper writes; the specimen is rendered from the committed copy deck and the shared
component CSS instead. It is a **design specimen, not production**: the production
template remains `templates/_sector_central_brief.html.j2`, and nothing here is a
build input.

## What it is bound to

| Input | Source |
|---|---|
| Copy | `../copy_deck.json` → `brief.*`, `components.*`, `states.locked_body` (23 brief keys added with this specimen; every key records its production `source` line) |
| Tokens | `templates/theme.css` (dark/light), `templates/navigation-refresh.css` |
| Components | `../components/components.css` (`.spc-asof-stamp`, `.spc-panel-footnote`, `.spc-lock-chip`/`.spc-lock-why`, `.spc-grader-caption`, `.spc-sr`) |
| Data | `example_dataset.json` — rows copied from the rendered `site/sector_central.html` + `site/premiumdata/sector_central.json` of the render tree at as-of 2026-10-19 |
| Chrome | `nav_static.html` — a static copy of the rendered header. **Non-normative**: `templates/_site_nav.html.j2` is the only header source; the copy exists because `file://` fetch is CORS-blocked. |

## Lane → stance binding (doctrine stance titles, production lane label as qualifier)

Wave 2 (SIC-V2-C13, VTC-013): each lane is titled with its doctrine stance
(`components.stance_*`) and carries the production lane label beneath as a qualifier
(`.brf-lane-qual`), so the Brief and the Cycles cards share one stance vocabulary.

| Production lane id | Legacy label (EN / ZH) | Specimen stance | Stance copy key |
|---|---|---|---|
| `ab-buy-fold` | Buy now / 立即买入 | `act` | `components.stance_act` |
| `ab-soon-fold` | Almost ready / 即将就绪 | `get_ready` | `components.stance_get_ready` |
| `ab-run-fold` | In favour — don't chase / 顺势但勿追高 | `watch` | `components.stance_watch` |
| `ab-trim-fold` | Take profits / 获利了结 | `protect` | `components.stance_protect` |
| `dash-hold-fold` | Stand aside / 观望 | `aside` | `components.stance_aside` |
| bottoming strip | may be bottoming / 或正筑底 | `watch` | `brief.bottoming_title` + `components.stance_watch` chip |

Stance ink never flips by locale; direction ink (`.brf-delta[data-dir]`) follows
`html[data-lang="zh"]` through `--ink-up/--ink-down`. Stance ≠ direction (COMPONENTS.md).

## Boards

| Board | Cell | URL | PNG |
|---|---|---|---|
| 23 | desktop 1440 · light · EN | `brief.html?theme=light&lang=en` | 1440×2730 |
| 24 | desktop 1440 · dark · EN | `brief.html?theme=dark&lang=en` | 1440×2730 |
| 25 | mobile 390 · dark · ZH | `mobile_frame.html?src=brief.html&theme=dark&lang=zh` | 390×4511 |
| 26 | mobile 390 · light · EN · **locked** | `mobile_frame.html?src=brief.html&theme=light&lang=en&state=locked` | 390×4686 |
| 27 | coverage matrix (Brief + Cycles: surface × viewport × theme × locale, drawn vs renderable) | `coverage_matrix.html?theme=light&lang=en` | 1440×1026 |
| 32 | desktop 1440 · light · ZH | `brief.html?theme=light&lang=zh` | 1440×2752 |
| 33 | desktop 1440 · dark · ZH | `brief.html?theme=dark&lang=zh` | 1440×2752 |
| 37 | mobile 390 · dark · EN | `mobile_frame.html?src=brief.html&theme=dark&lang=en` | 390×4903 |

Manifest rows 23–27, 32, 33, 37: `node_id: null`, `page_id: null`,
`capture: html-specimen-chrome-headless-1x`, `paper_state: PAPER_CAPACITY_LIMITED`.
They are not Paper exports and must never be relabelled as such.

## How to render

```bash
python3 build_brief.py      # copy deck + dataset → brief.html (asserts 26 stand-aside rows)
./render.sh                 # headless Chrome → ../../../mockups/refs/.../proposal/{23,24,25,26,27,32,33,37}-*.png
```

- Headless Chrome clamps its window width to ≥500px, so a `--window-size=390,…` render
  lays out at 500px and crops. Mobile boards therefore render inside `mobile_frame.html`
  (a 390px iframe host); `--allow-file-access-from-files` is required for the
  same-origin readback.
- `render.sh` measures each page's `data-h` probe (scrollHeight) and renders at that
  height + 40px, so no board is cut.
- Each page sets `data-w` (scrollWidth) and `data-ovf` (first elements past the
  viewport). Accepted state: `data-w="390"`, `data-ovf=""` for every mobile cell.

## Gates (all passed at the committed render)

```bash
/usr/bin/grep -n -E "border-left|border-inline-start|border-top:[^;]*(var\(--(up|down|ok|warn|accent)|#)" brief.css   # empty: no colored edge
/usr/bin/grep -c "Check entry signals" brief.html                                                                       # 0: legacy action language gone
```

## Known specimen limits (not production claims)

- Basket links point at `../../../site/baskets/…`, which is absent on the sparse
  session tree; the nav's scripts 404 under `file://`. Both are inert in a PNG.
- `brief.stance_day_one` renders the singular "1 day in / 已持续1天" (SIC-V2-C14, VTC-020);
  production still prints "1 days in" (PRC-002 family) — the cure belongs in the template.
- **Declared gap (PRC-028):** production draws per-row gate chips on the Bottoming Watch
  strip; the captured dataset carries `chips: []` for every row, so the specimen draws
  none. This is a data gap at capture, not a design decision; the strip renders chips
  once the dataset carries them.
- Typed em dashes inside producer prose (`now.divergence_note`, lane qualifiers copied
  verbatim from production) are kept as shipped; the deck glyph rule governs deck copy.
- Shared shell: `../components/si_shell.{py,css}` draws the canonical nav, page header and
  a six-link workflow switcher (production draws four). `si_shell.css` blocks 4 and 5
  (switcher wrap and side-foot as-of wrap at ≤767px) are **proposals, not production
  CSS** (SIC-V2-C02/C03).
- Coverage matrix (board 27): 14 of 16 Brief + Cycles cells drawn; the Brief gap is
  mobile · light · ZH (renderable by query string, not frozen).
- `stat_zh.json` holds zh glosses for `stat_en` values the producer ships
  English-only in `site/premiumdata/sector_central.json` ("uptrend intact",
  "downtrend"). They are specimen-only; the PRC-001 cure is localisation at the
  template/producer, not here.
- Coverage counts (11 sectors / 49 baskets) come from the render-tree build log;
  bottoming positions are read from the rendered strip; no grader number is invented
  (the track-record panel carries only the deck caption and link).
- The render tree reported `rotation artifact generation incompatible_generation
  (as_of_mismatch) — conviction sort retained`; the specimen shows the retained sort.
