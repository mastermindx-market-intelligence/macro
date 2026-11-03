# F02 coverage supplement

**Prepared, not applied.** This supplement adds four focused compositions and five append steps. It leaves the original six-board, 171-step packet unchanged at SHA256 `a52e7566fa7ff5ae8e55874fb2b28e0d5cfc1fbc415530532294d9c590c35d4d`.

The root agent remains the only Paper writer. All identities in `parent`, `target_board_key`, `source_step_key` and clone plans are local construction keys, not claimed Paper node IDs. Bind them to actual observed IDs before any effect.

## Inventory

| Board | Initial size | Steps | Coverage added |
| --- | --- | ---: | --- |
| `macro-zh-evidence-return-390` | 390 × 1460 | 20 | Chinese selected-row evidence, full source/clock/unit identity, 44px close/return controls and a matching post-close selected/focused row |
| `width-768-overlay` | 768 × 1130 | 31 | 728px primary with no rail; full ten-row comparison; 440px modal overlay instead of an inadequate dock |
| `width-1024-overlay` | 1024 × 1130 | 32 | 196px rail and 788px primary; full comparison; 440px modal overlay without compressing the underlying table |
| `width-1600-docked` | 1600 × 1300 | 43 | 1328px usable content, 984px primary comparison and 320px complementary dock separated by 24px |

All four go on existing canonical page `p-5-0`. Heights are initial construction bounds; inspect actual fit and adjust through the normal guarded native workflow. These are width evaluations and component journeys, not replacement domain workspaces.

`append_to_existing` adds:

| Existing board key | Parent key | Steps | Added treatment |
| --- | --- | ---: | --- |
| `controls` | `board` | 2 | Explicit default / hover / selected / keyboard-focus comparison, using the existing 1344px content width |
| `states-matrix` | `matrix` | 2 | Source unavailable and access-service unavailable, each as one aligned dark/light comparison row |
| `states-matrix` | `board` | 1 | Adjacent source-owner, access-owner, server-payload, retry and bilingual-copy contract |

The controls board’s current 48px padding is respected. Existing state rows and controls are retained. Re-read the current native board before appending and verify its final height afterward.

## Provisional width rules used

These values come from `SYSTEM_CONTRACT.md` §6 and the existing `pattern-lab.html` CSS; they do not establish a released F01 contract.

| Viewport | Header | Rail | Side padding | Usable primary before evidence | Evidence treatment | Primary with dock |
| ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 768 | 56 | 0 | 20 × 2 | 728 | 440px right-side modal overlay | Hypothetical 384: below 640px minimum |
| 1024 | 64 | 196 | 20 × 2 | 788 | 440px right-side modal overlay | Hypothetical 444: below 640px minimum |
| 1600 | 64 | 224 | 24 × 2 | 1328 | 320px dock + 24px gap | 984 |

The actual specimen switches the header to 56px only at `max-width: 860px`; the 1024px study therefore retains 64px. Its modal CSS is `width: min(440px, 100%)`, with full width at `max-width: 600px`. The 390px Chinese evidence uses the full available width with a 350px inner body.

The two overlay studies construct the complete native ten-row, five-field table first. A checkpoint on the tenth row requests the **closed-state capture before the backdrop is added**. The final overlay is a separate absolute layer inside the exact-width viewport, with an intentional dark backdrop; the original table is retained at its full width underneath. Final capture verifies the open state. Modal occlusion does not remove fields or shrink the underlying primary area.

The five comparison fields remain Sector, Above 50D, percentage-point change, covered/eligible and source/evidence action. Unknown Energy values and the actual-zero Health care change remain distinct. Dense comparison rows are 40px. Overlay close/return controls are 44px. The right-side inspector shows the complete selected observation with the same source identity.

## Chinese evidence and return

The selected record is exactly:

`f02.fixture.v2/macro/sector/communication_services/share_above_50d/2026-10-30`

It retains **66.7%**, **+1.13 pp** and **21 / 21**. The comparison explains `65.57% → 66.70% = +1.13 percentage points`, not a 1.13% relative increase. Observation is settled 20:00 UTC, publication 20:02 UTC and retrieval 20:03 UTC on 30 October 2026. Row coverage is explicitly distinct from the universe history’s 7/8 observations.

The close label is **关闭** and return label is **返回“通信服务”行**. The adjacent contract specifies one named modal, initial focus, contained Tab/Shift+Tab, Escape, inert background, stable-identity return, retained sort/filter/scroll, and the named table-heading fallback when a row disappears. Navigation and language changes do not save or create a new URL. The return specimen uses the exact existing Chinese comparison row input, including its independent selected fill and focused 44px source control.

## Unavailable-source and unavailable-access distinction

Source unavailable is an availability failure owned by the source/coverage path. Other valid evidence retains its own clocks. “View coverage” opens the existing coverage receipt; a source retry appears only when its owner supplies the real read callback.

Access-service unavailable is an entitlement-provider failure. It does not assert plan denial, session expiry or a need to buy another plan. Public evidence stays available; the server withholds protected payload until access is established. “Retry access check” binds to the existing access owner and remains a read operation. No source refresh, sign-in, plan change or save is silently substituted.

## Clone opportunities

1. **Chinese return row:** `macro-light-zh-390 / sector-3` and the new `returned-selected-row` have byte-identical HTML. Reuse the observed native row if convenient.
2. **768 → 1024 modal:** the entire 440px `overlay` subtree and all descendant inputs are identical. The target scene and backdrop dimensions differ. The existing observed sheet can be cloned/reparented into the new scene without reconstructing its ten source groups.
3. **1280 → 1600 docked board:** the existing `macro-docked-1280` and new wide evaluation have identical step keys, parents and tag topology. `supplemental-wide-clone.json` supplies four text changes, 71 style targets, the explicit artboard-width change and 20 SVG geometry-attribute changes across one chart subtree. The dock stays 320px; primary/table column widths and chart coordinates intentionally change. Do not treat this as a theme-only clone or reuse the old chart geometry unchanged.

All clone plans require the actual descendant map and current source JSX/tree. Native repairs applied after the inputs must be reconciled before applying a delta. SVG attributes require observed editable vector mappings or a bounded replacement of the actual mapped chart subtree. No Paper IDs, successful clone effects or final-fit results are asserted by this supplement.

## Evidence and reproduction

- `supplemental-boards.json` SHA256: `aa5bb0dc6880bcc8fe50ce1b7c16fe6ad6945b6d962bf7bb921376456616bf50`
- `supplemental-wide-clone.json` SHA256: `d1ba2b6a2147d82fc3ad84f325496a7803662535fb3a515688be8b7538d144e1`
- `supplemental-validation.json`: single-root/parent checks, markup/style constraints, original-packet preservation, exact record/clocks/arithmetic, ten rows/source fields, source-bound width calculations and clone equivalence.

Run `python3 build_supplemental_inputs.py`, then `python3 validate_supplemental_inputs.py`. The scripts operate only on local preparation files. They do not connect to Paper or a browser. Actual native rendering/editability, CJK quality, focus/touch/zoom behavior, source services and final independent review remain separate evidence.
