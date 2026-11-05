---
lane: F08
status: RECORDS_ONLY / ACCOMPANIES_B-F08-B5-3
product_effect: NONE
runtime_effect: NONE
data_effect: NONE
amends: MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md §1 owner table and §13 row C7
authority: Meta-CEO B seat ruling SB-5 on spec B-F08-B5-3 (2026-09-09), successor seat session d640f3ef — PROPOSED — seat ratifies
date: 2026-09-09
freeze_file_edited: false
---

# F08 C7 — sole-assembler claim, scoped (amendment)

This record amends `research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md`
§1 owner table (`engine/alert_triage.py` sole board assembler) and §13 row C7
(`templates/_us_act_now_board.html.j2` is an untraced second board-like surface
→ V1 disposition task). The freeze file itself is **not** edited.

## Trace (what renders the act-now board)

Two hosts, one shared include, both server-side:

- `templates/dashboard.html.j2:15805` — `{% include "_us_act_now_board.html.j2" %}`
  (the us_stocks page);
- `templates/sector_central.html.j2:2202` — the same include, guarded on
  `action_board` being truthy.

Two tier-gate payload renders of the same template:

- `scripts/build_site.py:5621-5623`;
- `scripts/build_sector_central.py:156-159`.

One assembler, `scripts/build_site.py::action_board` (`:1991-1993`), with four
inputs: sector timing, notable stock cycle rows, basket action items, and a
sector-setup lookup. Called once at `:6186-6187`, persisted to
`site/basketdata/action_board.json` at `:6202-6205`, and read back by
`build_sector_central` at `scripts/build_sector_central.py:391` (the reader
pattern documented at `:47` and `:386`). The template's own header states the
same thing (`templates/_us_act_now_board.html.j2:3-19`).

`engine/alert_triage.py` is a pure assembler over six alert engines (`engine/alert_triage.py:1-9`) and owns exactly three artifacts, named in its own docstring at `engine/alert_triage.py:35-48`, via the single page owner `scripts/build_site.py::build_alerts_page`: `site/alerts.html`, `site/factordata/alerts_triage.json`, `site/alertsdata/feed.json`. A token scan of `engine/alert_triage.py` for
`action_board`, `act_now`, `basketdata`, `us_act_now`, `sector_timing` returns
zero hits. `action_board()`'s inputs are none of those engines; it writes none
of those three artifacts. The one occurrence of the string "alert" in the board
template is an icon name (`templates/_us_act_now_board.html.j2:303`).

## Amended claim (scoped)

`engine/alert_triage.py` is the sole assembler of the **alert-triage board**
and of its three published artifacts — `site/alerts.html`,
`site/factordata/alerts_triage.json`, `site/alertsdata/feed.json` — over the
six alert engines named at `engine/alert_triage.py:1-9`.
`scripts/build_site.py::action_board` is the sole assembler of the
**sector/theme act-now board** and of its artifact
`site/basketdata/action_board.json`, over sector timing, notable cycle rows,
basket action items and the sector-setup lookup. The two share no input, no
artifact and no read in either direction. Neither may acquire the other's
inputs or write the other's artifacts without a new ruling.

## Disposition

**C7 — RESOLVED BY AMENDMENT (2026-09-09). Not a second alert-board assembler; a name collision.**

Mechanical guard: `tests/test_act_now_board_assembler.py`.

## Honest residual (out of scope)

`action_board()` lives in `scripts/build_site.py`, a 6000-line build script,
rather than in an `engine/` module. That is a placement observation, not a
collision, and it is explicitly **out of scope** here — recorded so a later
reader does not mistake this amendment for a claim that the placement is ideal.
