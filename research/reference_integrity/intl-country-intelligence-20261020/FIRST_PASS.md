# International reference review — neutral first-pass inputs

Reference: intl-country-intelligence-20261020. Route: intl.html.
This file provides artifact locations and user tasks; it is not a verdict or designer rationale.

## User job

Understand countries' current economic, policy and market conditions, their published economic paths and the mechanisms or conditions that could change those paths, using traceable research; use comparison and other research tools as supporting tasks.

## Before

- Actual anonymous production: production/intl.html, SHA-256 9e73a81c020459c0d1d440987670d10cd137480f7660817a83ed176a2aa1862b.
- Production source snapshot: production/source/, from a815e54f50e012fd693c9a1ec311f5e814f330bd.
- baseline.yml: capability ledger, capture provenance, access gaps and design lineage.
- first_pass_capability_tasks.yml: all 71 source capabilities and destinations; primary and cross-cutting tasks; catalogue entries.
- Before screenshot directory: mockups/refs/reference_integrity/intl-country-intelligence-20261020/before/.
- Eight viewport files: viewport-{desktop|mobile}-{en|zh}-{light|dark}.png.
- Full captures and exact hashes: production_capture_manifest.json; direct images: production_viewports.json.
- Capture occurred after implementation and before deployment. Five workspace scripts returned HTTP 401; four workspace styles were MIME-denied in actual production. Source inventory is not proof that those client controls worked in that captured state.

## After

- proposed/intl.html: complete unchanged scripts.build_intl output from product source 6ad0c377ed80a8ccf07ecbfb6c7b44530b753cf7.
- HTML SHA-256: f8457cca66eb6f7177b87a6aa52787d501dba3e1c221bee1a74ef5981f7f5c83.
- Adjacent CSS/JS files under proposed/ are the assets served for the capture.
- Source at the review artifact commit: templates/intl.html.j2, templates/intl_country_cockpit.html.j2, templates/intl_country_cockpit.css, templates/intl_country_cockpit.js, retained templates/intl_workspace/ and workspace JS/CSS, scripts/build_intl.py, engine/intl_country_analysis.py and country input readers.
- complete_build_receipt.json binds output and source. production_input_snapshot.json binds a read-only copy of existing production inputs (source observation/acquisition dates are not rewritten).
- After screenshot directory: mockups/refs/reference_integrity/intl-country-intelligence-20261020/after_full/.
- Eight canonical full captures: complete_capture_manifest.json.
- Twelve direct viewports: viewport-{desktop|mobile|narrow}-{en|zh}-{light|dark}.png. Widths 1440, 390 and 320.
- Supporting tool views: tools-{overview|compare|macro|risk|history|library}-desktop-en-light.png and tools-<view>-mobile-zh-dark.png.
- complete_browser_receipt.json records captured states and actual navigation observations. Mounted panels can contain unavailable observations; do not infer population from panel existence.
- This after render contains the whole page. The separate after/ directory and proposed_visual_manifest.json are the earlier reduced country fixture, retained as provenance; do not use them as evidence that the complete page lacks supporting panels.

## Reproducible artifact inspection

The PNGs are direct browser evidence. Read them as images, not only file metadata. Use the before/after full captures alongside legible viewport shots; inspect all language/theme/viewport axes.

The read-only capture adapter capture_complete_reference.py serves proposed/ in a fresh real Chrome context at http://intl.test/intl.html. Its route_assets/context_for helpers can be imported for independent local browser inspection. External network calls are aborted in this isolated artifact. It is not the production URL. Do not overwrite committed capture outputs during a review; use /tmp for independent screenshots if needed.

## Rationale quarantine

Pass 1 may read this file, baseline.yml, first_pass_capability_tasks.yml, the named production/proposal source, artifact HTML/assets, capture images and factual input/capture receipts.

Do not open proposal.yml, DESIGNER_RATIONALE.md, any review/verdict/approval file, earlier review conclusions, review_repair_20261020/REVIEW_REPAIR.md, PR discussion, or author narrative. Product-specific prior conclusions are not first-pass evidence.

Freeze the first findings before receiving rationale. Review responsibilities cover capability preservation, actual user tasks, information loss, authority and visual quality. A later follow-up supplies rationale and data constraints for per-finding amendments; preserve both passes and any dissent.
