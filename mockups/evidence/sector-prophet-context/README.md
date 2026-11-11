# Sector Intelligence — Prophet context island on us_stocks.html (SIC Paper pivot)

Visual evidence for `templates/_sector_prophet_context.html.j2` (markup + inline `<style>` from
`_sector_prophet_context.css.j2`), the island that `templates/dashboard.html.j2` includes on
`us_stocks.html` in macro #9917 (Sector Intelligence + Cycles completion, programme #7646). The island is
`hidden` unless the page is reached with a valid `si_sector` query, so the capture route selects
Information Technology: `/us_stocks.html?si_sector=XLK&si_asof=2026-10-30&si_gen=sc-2026-10-30&si_origin=sector_central.html`
(as-of and generation are the island's documented query contract; the render tree's data session is 2026-10-30).

* Capture: `scripts/capture_page_evidence.py` 1.4.0 against a local build of the #9917 integration head
  (`c8b048dd5bf3`, render worktree, `python -m scripts.build_site` on the data as built — not production).
  Eight rest cells (desktop 1440×900 / mobile 390×844 × en/zh × dark/light): 8 attempted, 8 captured.
  The partial adds no hover/focus rules, so no forced interaction state is claimed.
* Not proven here: signed-in tiers (anonymous only), loading/empty/stale/error page states, and the live
  feeds — the static render tree serves no `live/` directory, so `live/prophet_live.json` and
  `live/release_publications.json` 404 (recorded under `failed_responses` / `console_errors` in
  `manifest.json`); the page shows its built-in state for those. Production proof is owed at P22 on the
  released site.
