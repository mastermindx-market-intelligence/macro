# PR #9271 — measured-read panel evidence (LR-T18-EV1R)

**VERDICT: FAILED — the `#si-measured` panel never renders at the pinned head `8558d17e`.**

Everything in this directory is **SYNTHETIC LOCAL — not production**: the template was
rendered locally (same Jinja env as `scripts/build_sector_central.py`), state came from
locally injected data (`tests/fixtures/leadership_rotation/measured_read_v1.json` +
mutations of the committed `SECTOR_CYCLES` object), and the site was served from
`127.0.0.1` only. The browser context aborted every non-127.0.0.1 request (none occurred).

## What the crops show

| file | what it shows |
|---|---|
| `broken-overview-1440-dark.png` | The page a visitor gets at `?g=XLE#map` (dark/command-center): the Overview view only. The measured-read panel section exists in the DOM but lives in the hidden Map view and never becomes visible. Console: `Unexpected token '<'`. |
| `broken-overview-1440-light.png` | Same at the light/research-workspace art direction. |
| `DIAGNOSTIC-forced-mapview-skeleton-1440-dark.png` | **Diagnostic only — not a render.** `.si-view[data-view="map"]` was force-set to `display:block` in devtools style to show the server-rendered shell that ships: skeleton `#mr-cov`, empty `#mr-list`, empty `#mr-status`, empty `#mr-detail`. No state chip, no rows, no history ever populates. |

## The defect (one line)

`templates/sector_central.html.j2` opens the mr-panel `<script>` at **line 3610** and
never closes it: after `/* mr-panel:end */` (**line 4118**) the next markup is
`<script src="si_workspace.js"></script>` (**line 4124**) with **no `</script>` between**.
The parser therefore ends the script at the `</script>` on line 4124, swallowing
`<script src="si_workspace.js">` as JavaScript text → `SyntaxError: Unexpected token '<'`:

- the whole mr-panel script (all 14 interface states, deep link, keyboard, history,
  popstate) never executes;
- `si_workspace.js` is never even fetched (it exists only as text inside the dead
  script) → no view router → `.si-view[data-view="map"]` stays `display:none` →
  `#si-measured` is never visible.

Proven data-independent: identical failure on all 12 injected-data variants
(ok / full / stale / absent / outage / invalid / nodata / hloading / hfailed /
genmis / hrecon / obsincompat). See `RECEIPT.json` for the full in-browser proof,
the builder checks (render env matches `build_sector_central.py:453`; `write_page`
does not repair markup), and per-file sha256.

The committed `site/sector_central.html` at this head contains no mr-panel at all
(stale build predating the template change), so CI never exercised this path.

## `-synth` meaning

The planned `CYR` cycles object is synthetic layout data (11 sectors × 120 weekday
points, formula-generated). Every crop that would have used it carries `-synth`.
No `-synth` crops exist here because no history crop could be taken.

## How to reproduce

```
git fetch origin +refs/heads/claude/lr-t18-sector-central-journey-2026-10-14
git worktree add --no-checkout wt 8558d17ea7cf468c1a7dc568949fed56dda67f83
# render templates/sector_central.html.j2 with the build script's env
# (basket_member_syms=['SPY'] suffices), serve the site, open ?g=XLE#map
# → console: "Unexpected token '<'"; #si-measured never visible
```

**Fix for the PR author:** add `</script>` after `/* mr-panel:end */` (between
template lines 4118 and 4124), then re-run this evidence lane against the fixed head.
