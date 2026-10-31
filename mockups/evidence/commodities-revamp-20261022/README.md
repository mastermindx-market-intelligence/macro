# Commodities visual revamp — review evidence

This candidate replaces the sparse R3 composition with an editorial brief, a signed 17-asset market map, a price/explanation workspace, a shared-scale comparison and a research worksheet. It preserves R3's data, navigation, source clocks, company continuation and export/import contracts.

## Design source

Recovered from Paper file `01M2WGNCX9475G79JRKJTCM08P`, page `p-L-0`. Original Overview `1HCJ-0` supplies the narrative structure; R3 `6JKF-0` supplies the functional boundary; North Star `21WR-0` informs analytical density. Reference screenshots and original JSX are retained in `references/`.

**Paper canvas remains unchanged.** The vendor reports: “Your file is too large. Further changes will result in data loss. Please start a new file.” Applying the polished design requires a safe successor Paper file. This does not qualify as Paper completion.

## Capture and behavior evidence

- `overview/manifest.json`: canonical capture owner, 8 rest cells plus 16 actual hover/focus cells.
- `views-final/manifest.json`: canonical capture owner, 32 rest cells across Explore, Relationships, Compare and Research note.
- Every view: 1440×900 and 390×844, dark/light, EN/ZH. Full-page PNGs are content-addressed.
- `browser-journey.json`: actual anonymous local Chromium checks; real file export and fresh-context import; signed comparison geometry; mobile active-tab visibility and uncut choices; keyboard/assistant/advanced behavior. Company transport is an intercepted first-party-origin fixture, not authenticated Terminal proof.
- `dom-journeys.json`: 27 rendered-DOM journeys; no visual-layout or production claim.
- `final-source-checks.json`: 67 Python tests plus 35 subtests; 6 JavaScript contracts; null/zero/scale/draft presentation regression; publication guard.
- `render-receipt.json`: presentation-only reconstruction from exact published payload. No collector, score or forecast executed. Payload bytes unchanged.
- `design-ratchet.txt` and `visual-evidence-guard.txt`: mechanical guards, not design taste or production proof.

The old DOM check's fixed “Inflation link unconfirmed” headline fails against unchanged base `2148a983…` as well. Snapshot-specific headline, Gold clock and company availability assertions now check the actual published payload; synthetic domain tests retain the economic invariants.

## Reproduction

```sh
python3 scripts/render_commodity_workspace_review.py --base 2148a98367be4239baac6af5bad103b2fb6f78e9 --reuse-published-workspace --output site/commodities.html --receipt mockups/evidence/commodities-revamp-20261022/render-receipt.json
python3 scripts/verify_commodity_workspace_browser.py --receipt mockups/evidence/commodities-revamp-20261022/browser-journey.json
```

Local review bytes, source/visual review, GitHub CI, covering normal render, exact served cohort and authenticated live journey are separate acceptance facts. Production acceptance remains pending until independently observed after publication.

## Integrated release candidate

Main advanced to `64ef5131a5f50fb65f0ad25a049a457e18258495` with a newer accepted payload and shared assets. The conflict was resolved by preserving that exact payload and reconstructing only the presentation. Current captures are `integration-overview/` and `integration-views/`; current checks are `integration-checks.json`, `integration-browser-journey.json` and `integration-dom-journeys.json`. The earlier directories remain dated pre-integration evidence. See `reviews.md` for the actual independent review scopes and `integration-render-receipt.json` for the payload-preservation proof. Production and Paper acceptance remain separate.
