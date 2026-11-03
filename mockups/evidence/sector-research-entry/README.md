# Sector Intelligence — research entry island on the Research Vault (SIC-I05R)

Visual evidence for the `#si-research-entry` island that `templates/research_vault.html.j2` gains in
macro #9917 (Sector Intelligence + Cycles completion, programme #7646). The island only renders when the
page is reached with a valid `si_subject` query (`(sector|subsector|theme|stock):<id>`), so the capture
route carries one: `/research_vault.html?si_subject=sector:XLK&si_origin=sector_central.html`.

* Capture: `scripts/capture_page_evidence.py` 1.4.0 against a local build of the #9917 integration head
  (`c8b048dd5bf3`, render worktree, data as built — not production). Eight rest cells
  (desktop 1440×900 / mobile 390×844 × en/zh × dark/light) plus the two interaction states the new CSS
  adds (`textarea:hover`, `textarea:focus`), forced with the browser's real hover/focus primitives on
  every cell: 24 states attempted, 24 captured, hover and focus confirmed applied on desktop/en in both
  dark and light (`--si_entry_hover` / `--si_entry_focus` files).
* Not proven here: signed-in tiers (anonymous only), loading/empty/stale page states, and the live
  catalogue — the static render tree has no API, so `/api/research/catalog` and
  `/api/billing/offers/founding_pro` fail (recorded in `manifest.json` under `failed_responses`); the
  vault body therefore shows its baked report cards and the API-less state, which is honest for the
  island but not a production readback. Production proof is owed at P22 on the released site.
