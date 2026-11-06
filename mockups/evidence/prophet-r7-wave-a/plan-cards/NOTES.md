# Prophet R7 Wave A1: plan-card record-state marks specimen

What this receipt covers: the two record-state marks that #9954 adds to
`templates/_us_prophet_plan_cards.html.j2`. "Reconstructed from the <date> plan"
appears on outage-backfill rows, and "Older signal only" appears on
legacy-formation-alias rows that are not current candidates.

## How the specimen was made

- `source/component.html` is rendered from the real template, not hand-copied. It
  uses the build_site Jinja environment (FileSystemLoader on `templates/`,
  autoescape on, the `tr` global). It makes the same
  `{% import "_prophet_card.html.j2" as pv %}` / `{{ pv.pv_css(setup_detail=true) }}`
  calls and the same `{% include "_us_prophet_plan_cards.html.j2" %}` inside an
  `.nbgrid` that `templates/dashboard.html.j2` makes for the US plan grid.
- The page links the real `site/theme.css` and `site/theme.js`, so theme and
  language switching come from the production chrome. The specimen frame uses tokens
  only (`--bg`, `--panel`, `--line`, `--r-card`, `--font-ui`, `--fs-*`, `--muted`)
  and has no accent stripe on any edge.
- The data is a fixture, and the page says so in its lede. Each specimen cell
  renders one plan row through the include with its own `cand_map`.

## States shown (one card each)

1. Plain: live origination on a tier-event date basis. No new mark (control).
2. Reconstructed, dated: `origination_mode` is `outage_backfill_2026_08_09` and
   `recorded_at` is `2026-08-09`. Shows "Reconstructed from the Aug 9 plan" /
   "依据 8月9日计划重建".
3. Reconstructed, no valid date: `recorded_at` is `2026-13-40`, which fails the
   strict date check. Shows the fallback "Reconstructed plan, original date not
   supplied"; no date is guessed.
4. Older signal only: `signal_date_basis` is `legacy_formation_alias` and the
   ticker is not in `cand_map`. Shows the dashed absence mark.
5. Legacy basis, still a candidate: the same basis, but the ticker is in
   `cand_map`. No mark.
6. Both marks: a reconstructed legacy row that is not a candidate. Both marks
   appear, in record order.

## Cells

- 8 rest cells: desktop 1440x900 and mobile 390x844 × en/zh × light/dark.
- #9954 adds no `:hover` or `:focus` rule, so no force-state cells are needed.
- Capture tool: `scripts/capture_page_evidence.py` v1.3.0 as committed on the PR
  head. Run with site-dir set to the repository root,
  `--settle-ms 1500 --timeout-s 30`.

## Gaps

- The specimen shows the cards, not their placement inside `dashboard.html`.
  #9954 does not change placement, and the dashboard grid is data-dependent.
- The "Ask Mastermind" launcher in the cells is injected by the production
  `theme.js`. It is not part of this component.
