# Sector Intelligence — Sector Central Paper pivot (SIC design reference `design_refs/sector-paper-20261021`)

Visual evidence for `templates/_sector_central_paper.css.j2` (new, included by `templates/sector_central.html.j2`)
and the Sector Central template changes of macro #9917 (Sector Intelligence + Cycles completion, programme #7646):
the Paper-reference page shell, workflow strip (Explore / Research / Watches), view buttons, brief and action
controls, on the page as an anonymous reader sees it.

* Capture: `scripts/capture_page_evidence.py` 1.4.0 against a local build of the #9917 integration head
  (`c8b048dd5bf3`, render worktree: `python -m scripts.build_site` then `scripts/build_sector_central.py`
  on the data as built, session 2026-10-30 — not production). Route `/sector_central.html` (registry row
  `macro:sector_central`), eight rest cells (desktop 1440×900 / mobile 390×844 × en/zh × dark/light) plus
  the hover and focus states the new CSS adds (`.si-workflow-link:hover`, `:focus-visible`), forced with
  the browser's real hover/focus primitives on the first workflow link: 24 states attempted, 24 captured,
  hover and focus confirmed applied on desktop/en in dark and light (`--si_workflow_hover` /
  `--si_workflow_focus` files). No failed requests, no console errors.
* Not proven here: signed-in tiers (anonymous only — the member boards render their gated preview),
  loading/empty/stale/error page states, the `.si-paper-action` / `.si-brief-list a` hover rules on
  elements only members see, and production. Production proof is owed at P22 on the released site.
