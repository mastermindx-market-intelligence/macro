---
key: DESIGN-COLOR-ROLE-PROJECTION
claim: >
  The Paper projection now has source-derived light warning/up/down/link text inks,
  but its 10px STALE label still uses raw amber at 3.612765:1 on white and general
  solid-label fill roles remain absent; source inks still need actual consumer-pair
  checks because specific dark and hue-tinted combinations fail.
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
  41f0c3bdea3979faf4a57f2a98e31a4df54a5973; R3 native token/binding readback and
  tests/test_prophet_verb_ink_contrast.py at fe7b900e4c28ba2d4a4d327bb996526f09019753.
scope:
  - macro
  - templates/theme.css
  - tests/test_prophet_verb_ink_contrast.py
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

At the R2 baseline, the unchanged Prophet test file passed 87 targeted tests against
its exact extracted source. The later R3 test-only repair below supersedes the
unchanged-helper claim; neither phase proves a native Paper fix or a full-repo pass.

## Reproduction caveat

The pre-R3 Prophet color helper's selector matcher was not a general global-token
CSS cascade: it included descendant html-language remaps. The diagnostic
excluded those descendants and nested conditional rules, expanded source percentage
variables, and used a negative control to distinguish root from scoped values.

Corrected diagnostic SHA256:
`c655cf379429eed4b2f8de26967be3cacbeb3cc1a729f8eb7da0bb6daa5a0d8c`.
The earlier scoped-selector-contaminated report
`8ae96f8f7abaf273316e14d996e957c5932f6c62f93387b36b11f22048b69863`
is superseded. R2 changed no shared parser or palette. R3 deliberately corrects the
existing helper below; it still does not implement arbitrary CSS or conditional rules.

## Owner and next action

Continue through the incumbent design-system PR #7394 and its existing source branch.
Keep #8041's doctrine/decision ownership and current per-page specialization intact.
Native application remains held for file-wide writer reconciliation; after that gate,
re-read current source/token/node identities, reuse the already-present warning ink
without creating or overwriting it, bind the one small label and verify its after-state. Do not
infer custody, worker liveness or permission from this Agent OS record.

## R3 — actual projection movement and evidence-consumer repair

Native M1 readback now finds `--mx-light-ink-warn=#7D5922`, alongside light
up/down/link ink aliases added by another session. This is the source warning
mixture rounded to 8-bit RGB: the actual alias calculates to 6.317604:1 on white,
not the unrounded mixture's 6.326019:1. Node `13N-0` still binds the old raw role.
This session performed no native token or node mutation. Do not replay token creation.

Commit `fe7b900e4c28ba2d4a4d327bb996526f09019753` changes only the existing
contrast test file: exact whole-selector admission prevents widget, combinator and
pseudo-state rules from becoming global theme values. Thirteen added controls
produced 10 failures / 3 passes before repair, then the complete file passed 100
tests with current-main theme bytes and independently with the older branch theme.
Reverting just admission reproduced the 10 failures. All 87 prior tests remain.
The existing CI command already includes this file; no new runner/checker was added.
This is test-source qualification, not general CSS-parser, browser or product acceptance.
