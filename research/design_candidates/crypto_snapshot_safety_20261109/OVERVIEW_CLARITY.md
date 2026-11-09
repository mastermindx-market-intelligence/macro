# Overview: readable comparison and risk fields

## Outcome

The existing Beyond Bitcoin summary now identifies both readings: **Vs BTC** and **Risk** in English, **相对 BTC** and **风险** in Chinese. An unavailable comparison is explicitly attached to its field; it does not imply that the asset's risk reading or all asset evidence is unavailable.

Each field remains in the existing compact paragraph. The two groups share a line when there is room and wrap independently on narrow screens. Their supplied values, the asset order and the Inspect asset action remain unchanged.

The same phase resets H3 margins within existing section headers. Beyond Bitcoin and its Explore markets link now start together. What matters no longer inherits the browser's extra heading margins; panel-contained headings already had zero margins.

## Build ownership and exact change

| Owner | Change | Invariant |
|---|---|---|
| HTML template | Add the two bilingual field prefixes in the two Overview summaries | Same projected values, identity, action, order and routes |
| R4 CSS | Wrap the two groups, allow the relevant information column to shrink, reset section H3 margins | Existing 12.5px summary type and 40px Inspect action height |
| Existing renderer | Regenerate the two candidate HTML routes and served CSS from the retained view JSON | No producer run, history refresh or data collection |
| Existing JavaScript | No change | Same dialog, return navigation, focus, settings and storage owners |
| Projection and producer | No change | Prior null/directional-state qualification stays intact |

The information-column rule is scoped to a watch row containing `.cri-watch-meta`. Other watch rows, including demand, macro and historical-review content, are outside that rule. No new description, tooltip, disclosure, icon or controller is introduced.

The exact three source transformations are in [SOURCE_TRANSFORMS.json](overview/SOURCE_TRANSFORMS.json). Reversing one template transformation and two CSS transformations recovers parent `a027c389a6c5e6c207c35d5bdbecf1e24defe0fb` exactly. Asset version is `602406872d1d`.

The two saved HTML pages differ only in their two Overview summary blocks and generated asset-version references. The saved view JSON, JavaScript, builder, projection, tests and shared assets are among **16 unchanged inputs**. Five published paths change: the template, template/served CSS and the two candidate HTML pages.

## Native visual and workflow proof

Final proof used Chrome `157.0.8103.39`, five fresh contexts/pages, actual native layout/input/timers, loopback-only asset delivery and no personal browser profile. Only Date was fixed to the historical fixture context. This is bounded readback for a presentation change, not an additional mirrored pytest suite.

| Case | Data | Theme and input | Verified |
|---|---|---|---|
| English 320px | Retained historical view | Dark, fine pointer | Both labels fit; both Inspect→Close returns |
| Chinese 320px | Retained historical view | Light, touch | Both labels fit; both Inspect→Close returns |
| English 390px | Synthetic unavailable comparison plus valid zero | Dark, fine pointer | Unavailable belongs to Vs BTC; Risk remains; both returns |
| Chinese 390px | Synthetic Building history plus valid zero | Light, touch | Canonical history and risk labels; both returns |
| English 1440px | Retained historical view | Dark, fine pointer | Single-line groups and shared header alignment; both returns |

All **ten Inspect→Close journeys** opened the expected asset, restored Overview and returned focus to the original opener. All cases preserve the exact projected asset data. Summary text remains 12.5px with the same locale font family. There is no page/row overflow or text/action overlap. Section H3 margins are zero in all five heading instances; Beyond Bitcoin and its link have equal top coordinates in every case.

Final script duration: **6.098s**; subprocess: **6.349s**; wrapper: **6.56s**. There were **zero page errors, external requests or WebSocket requests**. No saved-snapshot entry was created.

Eight final images were inspected: five section crops, two complete Overview elements and the Bitcoin Test the outlook section. A separate two-context native viewport diagnostic resolved the apparent launcher overlap in tall-element images: the Solana Inspect action is fully clear at actual maximum scroll at 320px and 1440px. However, at 1440px the existing Ask Mastermind launcher covers the lower-right part of the footer's Bitcoin model & methods control. The footer button occupies y740.109–780.109; the launcher begins at y766, and the footer's bottom-right hit point is owned by the launcher. The 320px footer is clear. Both viewport screenshots were inspected. This is a demonstrated pre-existing bottom-clearance defect, not an Overview-row defect; the next safe phase will correct the existing content clearance. No shared-launcher behavior was changed here.

The viewport diagnostic recorded two contexts/pages, zero page errors or external/WebSocket traffic and 4.972s. It completed the two 320px action/focus paths. It intentionally did not attempt the 1440px actions after recording failed clearance. An earlier strict observer exited at a clearance assertion before saving per-target measurements; its exact failed point is not established. The diagnostic preserved measurements and screenshots before deciding whether to attempt actions. See [viewport evidence](overview/VIEWPORT_DIAGNOSTIC.json).

## Proof history and qualifications

1. The parent renderer reproduced both saved pages, view JSON, JavaScript and CSS exactly from retained data.
2. An initial readback harness used a two-argument route lambda; Playwright supplied its Request as that second argument, replacing the captured HTML. It failed before accepting a rendered page. A one-argument closure corrected the harness. This was not a product failure.
3. Corrected parent readback passed two contexts/pages and four Inspect→Close journeys in 4.017s. The parent image exposed the unlabeled fields and default H3 offset.
4. An initial candidate source preflight counted watch rows across the whole page rather than Overview. It failed before copying any served artifact or launching candidate browser proof. The preflight was restricted to the Overview section, and the shrink rule was narrowed to the new summary class before the first served candidate.
5. First served candidate `c41504ba8019` passed all five cases and ten journeys in 6.164s. Its images confirmed the existing H3 offset still needed correction.
6. Final `602406872d1d` adds only the heading-margin reset and passes the five cases above. It records zero margins, heading/link alignment and the additional full-element/Bitcoin captures.

These are separate bounded runs. The earlier 67-contract/four-browser integrity proof and prior complete comparison proof remain scoped to their recorded source revisions. This phase does not claim a new complete test-suite run.

## Builder acceptance and next work

Preserve explicit field ownership, readable full values and the existing action target at 320px in both languages. Keep the comparison and risk groups able to wrap; do not restore a separator that can dangle at a line boundary. Do not reduce type size to force a line fit.

Paper's Overview references should show the same compact labels. Its comparison Build note should reference the current implementation/proof. The applied text and conservation receipt are recorded separately in the estate audit so Paper provenance does not depend on a self-referential commit hash.

Next bounded consumer findings are invalid asset quote prices, small positive prices rounding to zero, and duplicated fallback asset name/symbol labels. These are source-supported consumer gaps, not claims of bad production histories. Native viewport proof now identifies the footer's desktop bottom-clearance defect; it is the immediate next safe correction. Producer history validity, missing trend inputs and paired-window receipts remain separate authority/data work.

This dependent PR remains Draft, unarmed and unmerged. H5/model, alerts, hosted/independent visual acceptance, public-route cutover and release/admission holds remain. Historical/synthetic verification does not establish current-market freshness or production acceptance.
