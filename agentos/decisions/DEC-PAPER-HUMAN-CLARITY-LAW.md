---
key: PAPER-HUMAN-CLARITY-LAW
question: >
  Where should product content and builder implementation detail live in Paper designs?
answer: >
  Product frames must make the user's current task immediately understandable.
  Necessary user explanations belong in named accessible disclosures.
  Architecture, implementation plans and detailed system contracts belong in
  linked builder documentation outside customer frames. Current variants must
  agree on shared values and states, and concise assurances must stay within
  the governing behavior contract.
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
  - "docs/DESIGN_DOCTRINE.md and WORKFLOW_ENHANCEMENTS.md at 6ac8c20013dbea575f7007d51ba37d952056f927"
  - "WORKFLOW_ENHANCEMENT_REGISTER.json at 6ac8c20013dbea575f7007d51ba37d952056f927: 104 current workflow frames and exact native bindings"
  - "Final residual copy and relocation proof: research/paper_human_clarity/WORKFLOW_ENHANCEMENT_REGISTER.json / finalResidualPass in PR #10874; final source acceptance follows its exact merge receipt"
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

## Initial evidence at authoring — historical

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

## Continued design application — 9 November 2026

The first source package was accepted in PR #10867, merge
`6b25578ad1b7c10e724b25170e2d0ab46acbead1`. That result and the synchronized
personal skill remain accepted; this continuation does not repeat their work.

The Chairman’s continuation extended the design work through complete News and
International help/result journeys and further evidenced portfolio repairs.
The current directory is `research/paper_human_clarity/PORTFOLIO_DISPOSITIONS.md`.
News’s current contextual journey is now p-5-0 / 3HH-0; its independent rail
remains p-2-0 / 27L-0. Older count/help layouts are labelled references.

The unique edited-file count is now 16 across the 18 audited product/system
files. Native tree readback verifies 104 current workflow frames: 20 News,
32 International calculation-help, 36 International result/qualification/return,
and 16 tool-method frames. The final bounded pass separately repairs 17 text
placements in Options, Expectation, Hub and Sector; original types, storage,
navigation and source qualifications remain in linked Build sections and the
existing preservation register.

The same canonical law 9X3-0 now sits in content-fit carrier ANF-0.
Its AND-0 acceptance clause and DESIGN_DOCTRINE §8 require one identified
current design per case, consistent shared fixture values/units/dates/states,
and assurances bounded by the actual behavior contract. Proposed persistence,
background continuation and once-only behavior cannot become product promises
merely through shorter copy.

PR #10874 on `sol/paper-workflow-depth-20261108-c3-2335` owns this continued
source package. It was open and unarmed when this amendment was prepared.
The final exact-head checks and merge receipt govern source acceptance.
WORKFLOW_ENHANCEMENTS.md and WORKFLOW_ENHANCEMENT_REGISTER.json retain the
implementation contracts, native effects, preserved originals and negative
qualifications. No new workstream, lifecycle, runtime state or release authority
is created by this continuation.

## Authority and acceptance limits

This standalone decision uses path-scoped `affects`. Workstream association
remains `NOT_ORG_LINKED`; no new workstream, program, accepted Direction,
plan-adoption record or Executive root is asserted. The completed XPV2 reference
workstream is not reopened.

This is a Paper design and workflow result. It does not assert implemented
navigation, source qualification, application deployment or production
acceptance. Runtime result-route bindings, provider URL bindings, fixture
mismatches and News source/spec gaps remain explicit in the implementation
guides. Existing protected and draft assets remain protected and draft.

No external dialogue, watcher, release or runtime action is authorized by this
record. Future builders must use the named source/state owners and satisfy the
real-path acceptance appropriate to the feature they implement.
