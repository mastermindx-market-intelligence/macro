# Government Revenue: mobile inputs and source-details repair

Continuation of PR #7450 on its existing source branch, not a replacement UI or a new release path.

## User outcome and boundaries

A reader can filter procurement records, inspect one, open its sources, and return to the same
place using touch or a keyboard. Search text and selected values survive closing a mobile panel.
The underlying procurement records, publisher links, amounts, issuer mappings, gates, and research
meaning stay unchanged. The already-accepted D0R–D3 capabilities are not reopened.

The motivating production page was opened anonymously at 390 × 844. Shift+Tab from mobile Filters
escaped to `workspaceUnlock`; Escape left focus outside the opener; `/` tried to focus a hidden
search field. The patch also revealed and fixes a source drawer visually covered by its parent
mobile inspector (992 had been above 991), plus bilingual native option text and untranslated
Chinese placeholders. Native `<option>` labels are now plain text, translated by the existing
page-language boot without altering their values.

## Design treatment

**Dark treatment:** preserve the existing charcoal research panels, subtle borders, muted records,
and cyan keyboard focus. **Light treatment:** preserve white panels on the cool canvas, hairlines,
and shadow/blur separation rather than adding a dark-theme glow. Layout, typography, density,
semantic colors, and content hierarchy are unchanged in both themes. The only visual CSS change
is overlay ordering: parent sheet 992, nested backdrop 993, source drawer 994. Closing a source
restores its parent; no second modal framework or global navigation layer is introduced.

## Evidence

`manifest.json` is emitted by the existing `scripts/capture_page_evidence.py`, using the
`mastermind.p0_evidence.v2` schema. `EVIDENCE.yml` uses the existing page-evidence receipt schema.
It includes dark/light × EN/ZH × desktop 1440 × 900 / mobile 390 × 844, with honest access gaps.
The full-height mobile captures are intentionally large because the existing feed contains 500 rows.

`verify_interactions.py` serves the generated site on an ephemeral loopback port and uses actual
clicks, typing, Tab/Shift+Tab, Escape, slash, and resizing. It invokes no internal application test
helpers. It checks actual hit-testing inside the source drawer, not only DOM visibility. The server
and browser close in `finally`; it is not a watcher. Run from any checkout:

```sh
python3 mockups/evidence/uiux-government-revenue-mobile-20260920/verify_interactions.py
```

`interaction-results.json` records all eight browser cells. The source-detail and filter PNGs show
the real open states. The bilingual form labels and visible focus were visually inspected; the
source drawer is now in front of its parent in both material treatments. The source-detail payload
remains intentionally detailed. Local HTTP API routes absent from this static fixture return 404;
the capture manifest retains these errors and membership gaps. This does not claim authenticated
production proof or a healthy live acquisition service. Browser JavaScript exceptions are zero.

`regressions.txt`: 242 passed, 2 skipped, 1 deselected. The deselected temporal exemplar test already
requires an event absent from the committed workspace (`govws-aa6f1867ab7cae18de92e16c`); it is not
silently repaired with invented data. Thirteen newly added behavior/wiring/form/stacking checks live
in the existing CI-owned `tests/test_government_revenue_ui.py`. No new CI job was added.

## Source and release identity

Pre-repair semantic head: `d1172fc522837e7e9571e181c5214315aeea5506`.
Protected Skillpack: `Mastermind@9e796168b467c17d9853f139c4e4a6ccdf3a3a87`, v1.0.1.
Generated CSS: `2823b7e8.css`, byte-identical to the template style block and SHA-256 named.
Embedded `gov-data` bytes remain SHA-256
`d47452ab8287d72e0a84a748ecabe10aa9de89797f944d0ea2f6b4a56f4a6fda`.

Built and browser-tested is not shipped. The last observed #7450 head had all twelve packs and
`ci-gate` green but a binding Vercel deployment quota failure. The complementary pilot context is
non-binding only for a `main` target under the existing release classifier. Do not weaken that
classifier, bypass preview failure, deploy unmerged bytes, or create a replacement PR. A fresh
semantic head requires its own concluded checks and current integration proof before release.
