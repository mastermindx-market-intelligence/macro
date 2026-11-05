# Sector Central working design reference · 2026-10-18

**DESIGN REFERENCE · NOT LIVE · NOT_APPLIED_TO_PAPER · BROWSER/PRODUCTION ACCEPTANCE PENDING**

Parent: macro#7646 / sector-central-redesign-20260921-sol-001.
Source baseline: edc7c8976a50482cd52e13910b1b1ad188d113dd.

## Review

Open **preview.html** as a standalone document. It contains the styles, code and dated examples; it makes no external data or font request. The multi-file index.html version is for an ordinary HTTP server rooted at this repository.

The reference provides Brief → Explore → selected dossier → retained Research context. Explore exposes Rotation, Turns, Leadership, Money, Confluence and Cycles. The review toolbar changes light/dark, EN/ZH, and source/loading/empty/stale/error/signed-out examples. It sits outside the product frame.

The reference is an implementation of the proposed presentation, not the completed production migration. Source parsing and consistency checks are separate from browser evidence. The selected Browser could not reach Studio loopback, then explicitly refused a data URL under its http/https-only policy. No alternate browser or execution workaround was used. **No visual or interaction PASS is claimed.**

## Exact data boundaries

- **Brief / measured leadership / event observations:** existing tests/fixtures/leadership_rotation/measured_read_v1.json. Synthetic values dated October 9, 2026. Nine of eleven sectors are measured; XLRE and XLU remain explicitly unmeasured. Native rank and percentage values are preserved.
- **Rotation:** a field-only projection of the preserved R3 marketdata/subsector_rotation.json: 11 sector ETFs, 269 industries, 41 themes, dated August 19, 2026. Native rs_ratio / rs_mom coordinates and quadrant labels are used. The later v2 fields and tail do not share that coordinate contract and are not combined with it.
- **Money:** the R3 si_handoff flow classification and baskets market_concentration readings. No cash amount, ETF fund flow, or live treemap is invented.
- **Confluence:** separate S&P / Nasdaq / Russell / Baskets artifacts, with 65 / 12 / 93 / 49 retained rows. Original order, class, entry and regime fields remain distinct. Search changes display rows, not source coverage or eligibility.
- The archive was captured at 4c55fe433490adfd75fd901ef25f5793db2202db on August 20, 2026. All seven source hashes and byte counts are verified against the retained capture receipts before projection; their exact paths and the receipt-manifest hash are included in archive_sources.json. The independent October test fixture and August archive are never presented as one synchronized snapshot.

Cycle history, Time Machine chunks, live ETF flows/treemap, gated action hydration, verified dated company membership and a live Prophet receiver remain outside this reference. Their original capabilities have explicit migration destinations in the 92-row crosswalk. Unavailable examples do not complete those capabilities.

## Rebuild

From this directory, or with repository-relative paths:

```sh
python3 build_archive_reference.py
python3 build_reference.py
node --check reference.js
```

The archive builder selects fields from existing immutable fixtures; it does not calculate market values, mutate source fixtures or execute any production builder. The standalone builder selects the canonical shared-theme custom properties actually consumed by the reference and includes native Chinese directional overrides. Both builders are review-only utilities.

## Design and integration ownership

Current Paper R2 p-Y-0 remains the canvas baseline. The canonical specimen supplies typography/spacing/radius scales; templates/theme.css owns the palette. No production token family or root router is introduced.

Global navigation is outside this frame. The shared shell must host Sector through one route/access authority. A whole Terminal application with its own hidden header/router is not an acceptable embedding seam.

The Chairman's permanent no-colored-container-edge rule is recorded in the doctrine, design system, AGENTS/CLAUDE guidance, and callout specimen. Semantic chart ink, neutral dividers and complete focus outlines remain valid.

## Governing files

- ../../research/redesign/SECTOR_CENTRAL_20261018_DESIGN_DRAFT.md
- ../../research/redesign/SECTOR_CENTRAL_20261018_CAPABILITY_CROSSWALK_DRAFT.md
- ../../research/redesign/SECTOR_CENTRAL_20261018_PAPER_ACCEPTANCE_DRAFT.md

Production-source custody, Paper catalog qualification, the original held candidate-browser matrix, independent review and normal release remain separate acceptance gates.
