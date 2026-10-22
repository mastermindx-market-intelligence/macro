# Cycles corrections HTML specimen (boards 28–31, 34–36) — PAPER_CAPACITY_LIMITED

Seat-authored HTML specimen of the R4 Sector Cycles corrections for the
`sector-intelligence-cycles-20261021` reference set. It exists for the same reason as
the Brief specimen (boards 23–27, 32, 33, 37): the Paper file `01M2WGNCX9475G79JRKJTCM08P` carries a
file-wide size-limit warning and the seat makes no Paper writes, so the corrections the
revision mandate requires on the Cycles boards (1–8) are drawn from the committed copy
deck, the shared component CSS and three production rows instead. It is a **design
specimen, not production**: the production template remains `templates/sector_cycles.js`
+ `templates/sector_cycles.html`, and nothing here is a build input.

## What it is bound to

- `../copy_deck.json` — every visible string: `cycles.*` (title, tagline, intro, section
  headers, phase chips, hazard/rhythm/overdue/parity chips, `hazard_unavailable`,
  `sizing_inert`, `leadlag_stop`, `stance_label`, `phase_age_*`, `read_provenance`,
  `forecast_footnote`, `hazard_footnote`), `components.*` (as-of stamp, MODEL/PRIOR badge,
  grader label/caption, footnote), `states.*` (fresh, incompatible_generation) and
  `authority.*` (basis, built stamp, grader body). The four `cycles.*` keys added for this
  specimen each carry a `source` citation (producer field, engine line or masterplan line).
- `example_dataset.json` — three production rows (XLF, XLK, XLC) captured verbatim from
  `site/sector_cycles_data.js` at the local render `d86344b93a0bd` (payload `meta.asOf`
  2026-10-20), plus `meta`, `phases`, `rotation_context` and one labeled fixture
  (`_fixtures.incompatible_generation`, used only by board 31 via `?state=`).
- `enum_zh.json` — ZH forms of the producer enums that deck placeholders consume
  (`next_turn` peak/trough, `kind` sector/basket). The EN forms are the producer values.
- `../components/components.css` — `spc-asof-stamp`, `spc-chip`/`spc-phase-chip`,
  `spc-model-prior-badge`, `spc-hazard-ladder` family, `spc-grader-caption`,
  `spc-state-banner`, `spc-icon`. `cycles.css` adds only page layout and the card recipe.
- `../../../templates/theme.css` + `navigation-refresh.css` — production tokens and the
  real header chrome (`../brief_repair/nav_static.html`, a static capture copy; not a
  source — see `chrome.specimen_copy` in proposal.yml).

## Corrections drawn (mandate items this specimen answers)

| Correction | Binding | Where |
|---|---|---|
| Position is the v2 family only | `now.pos_v2` rendered as the headline `/100` under `cycles.pos_label`; legacy `pos`, `phase`, `action`, `timing_state`, `signal` are **not rendered** on the face. Wave 2 (SIC-V2-C07/PRC-025): the legacy cycle-position numerals and projected-turn dates inside `now.read`/`read_zh` are stripped from 'The read' (`STRIP_EN`/`STRIP_ZH` in `build_cycles.py`) and the verbatim read is kept under `cycles.read_provenance` in the card's provenance drawer | card head / drawer |
| Phase is `phase_v2` | `spc-phase-chip[data-phase]` from `now.phase_v2`; XLC shows the legacy/v2 disagreement the mandate names (legacy `Trough`, v2 `Downturn`) by drawing v2 only | card head |
| One stance vocabulary (SIC-V2-C01/VTC-013) | `now.stance` (engine vocabulary `engine/cycle_ontology.py:113-123`: AVOID · WAIT · GET READY · BUY · HOLD · TRIM · SELL · COUNTERTREND ONLY · HIGH-RISK BOUNCE) is bound by `STANCE_MAP` in `build_cycles.py` to the six doctrine stances (`components.stance_*`): BUY→Act · GET READY→Get ready · HOLD, HIGH-RISK BOUNCE→Watch — don't chase · TRIM, SELL→Protect gains · WAIT, AVOID, COUNTERTREND ONLY→Stand aside · null→Ignore. Stance ink by `data-stance` (`--ink-ok` / `--ink-warn` / `--muted`), never `--up`/`--down`. The engine stance + tone (`cycles.stance_engine_pattern`) and `now.divergence_note` stay in the provenance drawer; `cycles.clocks_chip` only when `now.divergence`. Captured rows: XLF HOLD→Watch, XLK HIGH-RISK BOUNCE→Watch, XLC SELL→Protect gains | card head / drawer |
| Measured phase age, not zero | `now.phase_v2_age` by `status`: `lower_bound` → `cycles.phase_age_lower_bound` (n = sessions, date = observed_from); `measured` → `phase_age_measured`; else `phase_age_unknown`. All three captured rows are `lower_bound` (history_rows 56) | card head |
| Hazard: MODEL vs PRIOR vs unavailable | `now.hazard.{1m,3m,6m}` → `spc-hz-val` + `spc-model-prior-badge[data-source]` + `cell_verdict`; `unavailable: true` → three gap cells (CSS dashed mark, no typed glyph, never 0 %) + `cycles.hazard_unavailable` + `unavailable_reason`; `estimate_kinds.model_cell_current_claim = parity_failed` → ladder muted + `cycles.hazard_parity_chip` + the claim code | hazard section |
| Live parity recorded, not repaired | `meta.live_hazard_parity` (PARITY_FAILS · 15 failing features · measured_on a038b3f3) in the basis panel, the methods panel and metadata | header, methods, metadata |
| Rhythm is descriptive and may be overdue | `rhythm.window{low,central,high}` with `rhythm.next_turn`, `cycles.rhythm_kind`, `cycles.overdue_chip` when `rhythm.overdue`; footnote `cycles.forecast_footnote` with the producer month strings (no ▲/▼) | rhythm section |
| Sizing inert | `cycles.sizing_inert` with its source citation (`engine/sector_central.py:453 size_mult = 1.0`, W4.6) | methods |
| Lead-lag STOP | `cycles.leadlag_stop` with its source citation (masterplan line 169, W5.1 STOP/NO-GO) | methods |
| Grader denominator | `components.grader_caption` ("Neutral included. Not a win rate.") + `authority.grader_body`; **no number is drawn** — the captured `premiumdata/sector_central.json` has no grader key at this render | grader panel |
| Generation guard on the raw clocks | `rotation_context.events/fragmentation` status chips (`aligned · 2026-10-20`); board 31 shows the `incompatible_generation` banner from the labeled fixture and prints the fixture label under it | events panel |
| Correction contract | `meta.correction_contract.status = none_native` + its basis string, verbatim | metadata |

## Boards

| # | File | Viewport | Theme | Locale | Query | Height px |
|---|---|---|---|---|---|---|
| 28 | `28-cycles-desktop-light-en.png` | 1440 | light | EN | `?theme=light&lang=en` | 2368 |
| 29 | `29-cycles-desktop-dark-en.png` | 1440 | dark | EN | `?theme=dark&lang=en` | 2368 |
| 30 | `30-cycles-mobile-dark-zh.png` | 390 (iframe host) | dark | ZH | `mobile_frame.html?src=cycles.html&theme=dark&lang=zh` | 5436 |
| 31 | `31-cycles-mobile-light-en.png` | 390 (iframe host) | light | EN | `…&theme=light&lang=en&state=incompatible_generation` (fixture) | 6116 |

Boards 30/31 are rendered inside `mobile_frame.html` because headless Chrome clamps its
window width to ≥500 px; the host page copies `data-h`/`data-w`/`data-ovf` from the 390 px
iframe document so the measurement is the mobile document's own.

## How to render

```
python3 build_cycles.py      # writes cycles.html from the deck + dataset
./render.sh                  # measures each board's document height, screenshots at 1x
```

## Gates (all passed at the committed render)

- `data-ovf=""` on all four boards (no element wider than the viewport); `data-w` = 1440 / 390.
- Glyph gate (python3, prose outside `<code>`/`.mono`/the nav): 0 typed `— → ← ↑ ↓ ▲ ▼`
  in deck-bound text. The three remaining em dashes are **producer values** rendered
  verbatim (`now.divergence_note` / `divergence_note_zh` for XLF) — a producer finding,
  recorded below, not a specimen edit.
- 0 `border-left` / `border-right` in `cycles.css` (no container edge stripes).
- `python3 scripts/check_reference_integrity.py` clean for the set; `boards_manifest.yml`
  rows 28–31 and 34–36 carry `png_px` equal to the PNG headers, `node_id: null`, `page_id: null`,
  `paper_state: PAPER_CAPACITY_LIMITED`, `capture: html-specimen-chrome-headless-1x`.

## Producer findings surfaced by the specimen (not cured here)

1. `now.read` / `read_zh` narrate the **legacy** position ("cycle position 47/100" for XLF
   while `pos_v2` is 72.64; XLC narrates "Bottoming" while `phase_v2` is `Downturn`). The
   narrative is generated from the legacy family (`engine/sector_cycles.py::_engine_read`).
   Wave 2 strips the legacy numerals and dates from the face copy and keeps the verbatim
   read under `cycles.read_provenance` in the provenance drawer (SIC-V2-C07); the cure is
   in the producer (C14), not in copy.
2. `proj{central,low,high}` (2026-06 / 2026-05 / 2026-09 for XLF) disagrees with
   `rhythm.window` (2026-07 / 2026-05 / 2027-02). The specimen binds the footnote to
   `rhythm` (the versioned, descriptive contract, `rhythm_version 1`) and does not draw
   `proj`; the production template still draws `proj` (`templates/sector_cycles.js:1420`).
3. `now.divergence_note` carries a typed em dash in both locales — the deck glyph rule
   does not reach producer prose. Cure belongs to `engine/cycle_ontology.py`.
4. `design_refs/sector-paper-20261021/cycles_ia.md:166` cites `engine/sector_central.py:404`
   for `size_mult = 1.0`; the line is `:453` (recorded in the deck `source` field).
5. No captured row carries a PRIOR hazard cell (XLK/XLC are `unavailable`,
   `non_monotone_cdf`); the PRIOR badge path is exercised by the component specimen
   (board 0) only. Board coverage of a real PRIOR cell stays with the P10–P13 journey.

## Wave 2 (SIC-V2 round-2 repairs) — what changed in this specimen

- **Shared shell (C02/C03/C09, VTC-014/015):** `../components/si_shell.py` emits the
  canonical site nav (`../brief_repair/nav_static.html`), the production page header
  (`.si-page-header` / `.si-page-identity` / `.si-side-foot`, with the as-of stamp in the
  side-foot) and a six-link workflow switcher with `aria-current="page"` on Cycles.
  `../components/si_shell.css` block 1 is a verbatim copy of
  `templates/_sector_central_paper.css.j2` (production draws four workflow links; the
  accepted shell draws six). **Blocks 4 and 5 are proposals, not production CSS**: the
  switcher wraps to a second row at ≤767px and the as-of stamp wraps inside the 40%
  side-foot (measured overflow of 493px / 248px before the fix; probe `data-w=390`
  `data-ovf=""` after).
- **Provenance drawers (C04, VTC-016/PRC-024):** every producer identifier, hash, path,
  field name and the full `cycles.hazard_footnote` moved off the card face into closed
  `<details class="cyc-prov">` drawers ("How this was measured / 测量方式"): one per card,
  plus methods, grader, events and metadata. The face carries `cycles.hazard_face_note`
  only. `/usr/bin/grep -c 'cyc-prov' cycles.html` → 7 drawers; 0 identifiers outside them.
- **ZH enums (C04/PRC-031):** `enum_zh.json` glosses the producer enums the engine ships
  English-only (`peak`/`trough`/`sector`/`basket`/`up`/`down`/`price`/`aligned`); the nav
  search placeholder and mono labels are ZH under `html[data-lang="zh"]`.
- **Banner and qualifier (C06, VTC-018):** the `incompatible_generation` banner body wraps;
  the `aligned` chips under it are muted (`.cyc-hz-muted`) and carry the dated qualifier
  `cycles.aligned_qualifier` as a wrapping note (`.cyc-ev-qual`), shown only under
  `html[data-state="incompatible_generation"]`.
- **Badge and projection (C10/C11):** the MODEL/PRIOR badge renders at 11px
  (`--fs-label`); `proj{central,low,high}` is drawn beside the rhythm method inside the
  drawer (`cycles.proj_label`), never on the face.
- **Boards 34–36:** ZH desktop light/dark and ZH mobile light added (PRC-027); boards
  28–31 re-rendered. Coverage matrix (board 27) now covers both surfaces: 14 of 16 cells
  drawn; the remaining Cycles gap is mobile · dark · EN.
- **Producer prose is verbatim:** typed em dashes inside `now.divergence_note` and other
  engine strings are kept as shipped (finding 3 below); the deck glyph rule governs deck
  copy only.

## Known specimen limits (not production claims)

- Three sectors, not eleven; no chart, series picker, zoom or touch sheet (C25/C26/C28
  remain on boards 3/5 and on the production page).
- Static HTML: no hydration, no live-region status, no keyboard activation to prove;
  the `<details>` drawers are closed in every capture (their open state is not frozen).
- The `incompatible_generation` state on board 31 is a **labeled fixture**; the captured
  Cycles clocks were `aligned` on 2026-10-20 (the render-log mismatch was Central's
  rotation artifact, not Cycles).
