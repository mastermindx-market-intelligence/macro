---
key: PAPER-HUMAN-CLARITY-LAW
question: >
  Where should product content and builder implementation detail live in Paper designs?
answer: >
  Product frames must make the user's current task immediately understandable.
  Necessary user explanations belong in named accessible disclosures.
  Architecture, implementation plans and detailed system contracts belong in
  linked builder documentation outside customer frames.
rationale: >
  The Chairman identified excessive context and implementation narration inside
  product designs as a recurring usability defect. Separating these audiences
  reduces confusion while retaining system features, meaningful limitations
  and the detail future builders need.
alternatives:
  - option: Keep implementation and architecture narration inside product frames.
    why_not: It competes with the user's task and makes the product harder to understand.
  - option: Delete dense detail without preserving its meaning and destination.
    why_not: It loses requirements, method qualifications and implementation context.
evidence:
  - "docs/DESIGN_DOCTRINE.md at c34658679387763ec20261455df8e01d4f83282d"
  - "research/paper_human_clarity/PORTFOLIO_DISPOSITIONS.md at c34658679387763ec20261455df8e01d4f83282d"
  - "research/paper_human_clarity/APPLIED_EFFECTS.json at c34658679387763ec20261455df8e01d4f83282d"
  - "research/paper_human_clarity/FINAL_QA.json at c34658679387763ec20261455df8e01d4f83282d"
affects:
  - docs/DESIGN_DOCTRINE.md
  - research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md
  - research/paper_human_clarity/**
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-11-08
---

# Paper designs must be immediately understandable

## Ruling and scope

This records the Chairman's current instruction of 8 November 2026, beginning
with News Intelligence and extending the clarity pass across eligible Mastermind
Paper product assets. Product text carries the task, result, meaningful state,
essential limitation and next action. Named user help carries deeper explanations.
Build references and source guides carry full engineering contracts.

This clarifies the existing disclosure doctrine; it does not replace source,
financial, lifecycle, access, data-quality or release owners. Long research that is
the user's actual task remains substantive content. Missing, stale, partial,
unconfirmed and unavailable states must not disappear merely to shorten copy.

## Evidence at authoring

At source head `c34658679387763ec20261455df8e01d4f83282d`, the complete package was
saved and read back: 39 resources inventoried, 18 product/system files audited,
15 files edited in Paper. Original text, identities, relocation destinations,
calculation/source contracts and remaining implementation gaps are recorded in
the applied-effect and preservation registers.

The canonical Paper law is node `9X3-0` in Design System file
`01M312VSDSZFVT45674GDVJVZN`, page `p-9-0`. News Product is file
`01M5EXPMQTSBFBAM8KKG83FTZH`, page `p-2-0`; its full build guide is
`research/paper_human_clarity/NEWS_INTELLIGENCE_BUILD_GUIDE.md`.

The personal Paper skill is committed and synchronized at
`df88ac0266c0eeeeb5e31bc06229d74b37dd84a2`. Its content-placement rule and
preservation workflow changed; connection/security instructions did not.

Paper effects, parent readbacks, representative native renders and skill
persistence are verified. The source package is on
`sol/paper-human-clarity-20261108-c3` pending normal repository publication at this
record's authoring point. Actual source acceptance is determined by the owning
PR's exact head, required checks and merge receipt.

## Authority and acceptance limits

This standalone decision uses path-scoped `affects`. Workstream association
remains `NOT_ORG_LINKED`; no new workstream, program, accepted Direction,
plan-adoption record or Executive root is asserted. The completed XPV2 reference
workstream is not reopened.

This is a Paper design and workflow result. It does not assert implemented
navigation, source qualification, application deployment or production
acceptance. Existing unrepresented tool routes, provider URL bindings, fixture
mismatches and News source/spec gaps remain explicit in the implementation
guides. Existing protected and draft assets remain protected and draft.

No external dialogue, watcher, release or runtime action is authorized by this
record. Future builders must use the named source/state owners and satisfy the
real-path acceptance appropriate to the feature they implement.
