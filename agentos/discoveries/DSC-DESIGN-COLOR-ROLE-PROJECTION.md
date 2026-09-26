---
key: DESIGN-COLOR-ROLE-PROJECTION
claim: >
  The inspected Paper system projection lacks the source theme's general text-ink and
  solid-label fill roles, and its 10px light STALE label uses raw amber at 3.612765:1
  on white; copying every source ink without consumer-pair checks would also preserve
  specific failing dark and hue-tinted combinations.
falsifier: >
  Re-read Paper file 01M2WGNCX9475G79JRKJTCM08P, page p-1-0, node 13N-0 and its
  ancestors with get_computed_styles, plus get_basic_info tokens; compare the current
  templates/theme.css blob and recalculate the actual foreground/background pairs.
  A corrected binding or changed source invalidates the affected current-defect claim;
  actual browser disagreement invalidates the affected arithmetic projection.
so_what: >
  Project existing source roles instead of inventing page-local colors; repair the
  single small label without repainting the large hero; measure actual flat, tinted
  and interaction-state pairs before adopting a primitive. Preserve explicit state
  text with an existing primary-text role where a semantic ink pair fails. Reconcile
  one-writer-per-file custody before touching shared Paper tokens.
kind: landmine
verified_at: 2026-09-26
verified_by: >
  Native M1 guarded Paper get_computed_styles for 13N-0/13M-0/13K-0/13H-0/12F-0;
  source-derived 288-pair diagnostic with exact top-level selector and locale controls;
  macro PR #7394, research/DESIGN_SYSTEM_READABILITY_REPAIR_2026-09-26.md at
  987d3d7c9ae3dc8450e080c25a5f9fb8b1d79030; source theme blob
  41f0c3bdea3979faf4a57f2a98e31a4df54a5973.
scope:
  - macro
  - templates/theme.css
  - research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md
  - research/DESIGN_MIGRATION_FACTORY_V1.md
confidence: verified
---

## Evidence boundary

This discovery records an observed editable-component binding and scoped source-derived
color calculations. It is not a deployed defect census, universal accessibility verdict,
Paper mutation receipt, reference approval, source lease or new execution gate.

The proposed light warning ink is the source role's existing 62% warn / 38% text sRGB
mixture: rgb(125.34, 88.70, 34.36). It calculates to 6.326019:1 on the observed white
panel, versus raw amber's 3.612765:1. The large 46px hero uses a different threshold
and must not be changed merely because it shares the raw hue.

The wider calculation found 94/96 text-ink/flat-surface pairs passing normal-text
contrast; both failures are dark act on panel2, at 4.250667:1. All 32 inspected
white-label/solid-fill pairs passed. Six of 64 constructed own-hue-tint stress pairs
failed. These stress compositions are not claims that those exact pairs occur on
production pages. The repair contract contains the exact cases and limited claims.

The existing Prophet test file passed 87 targeted tests against its exact extracted
source. It was not changed and does not prove a new native Paper fix or a full-repo pass.

## Reproduction caveat

The existing Prophet color helper's selector matcher must not be treated as a general
global-token CSS cascade: it can include descendant html-language remaps. The diagnostic
excluded those descendants and nested conditional rules, expanded source percentage
variables, and used a negative control to distinguish root from scoped values.

Corrected diagnostic SHA256:
`c655cf379429eed4b2f8de26967be3cacbeb3cc1a729f8eb7da0bb6daa5a0d8c`.
The earlier scoped-selector-contaminated report
`8ae96f8f7abaf273316e14d996e957c5932f6c62f93387b36b11f22048b69863`
is superseded. No shared parser or palette was silently modified to obtain a pass.

## Owner and next action

Continue through the incumbent design-system PR #7394 and its existing source branch.
Keep #8041's doctrine/decision ownership and current per-page specialization intact.
Native application remains held for file-wide writer reconciliation; after that gate,
re-read the current source/token/node identities, project the missing existing warning
ink once, bind the one small-label consumer and verify the actual after-state. Do not
infer custody, worker liveness or permission from this Agent OS record.
