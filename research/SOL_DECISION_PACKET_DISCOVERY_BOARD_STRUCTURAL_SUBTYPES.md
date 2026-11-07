# Sol decision packet — Discovery Board structural subtypes

**Status:** PROPOSED BINDING RULING — independent review required before merge  
**Decision owner:** Sol / design-system architecture  
**Observed Macro source:** `6db3af31f12259acd0ea8d6286c0bbbcff6c99ef`  
**Protected Sol procedure:** Mastermind@`a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`  
**Primary live consumer:** `macro:confluence_screener`  
**Related RIG carrier:** PR #7727 / `confluence-screener-paper-r1`

## 1. Decision

`discovery_board` remains the product/job archetype for ranked and filterable opportunity surfaces.
It MUST NOT, by itself, authorize a count ladder or imply a lifecycle data contract.

For design migration and reference-integrity work, Discovery Board has two adjudicated structural
subtypes:

1. **`lifecycle_board`** — a board whose producer exposes one canonical population partitioned by
   an exhaustive, disjoint lifecycle enum. Its identity device is `.mx-ladder`, and the
   canonical-count invariant applies. This subtype is restricted to Prophet/lifecycle-derived
   surfaces under the binding 2026-08-12 §J.9 Sol ruling.
2. **`ranked_screener`** — a board whose producer exposes ranked/filterable candidates and evidence
   but no lawful exhaustive/disjoint lifecycle enum. Its identity is the **ranked evidence stack**:
   rank + evidence/leg stack + validation/freshness truth + filter state + entitlement transition,
   composed from existing canonical primitives. `.mx-ladder` is prohibited.

This is a structural-selection ruling, not a new component system and not a new product-archetype
vocabulary.

## 2. Why this ruling is required

Current source contains a real contradiction:

- `MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` §10 says every `discovery_board` has the count ladder as
  its exclusive identity device and the canonical B composition begins header + ladder.
- The same constitution's component inventory, carrying the binding Sol rider, restricts
  `.mx-ladder` to Prophet/lifecycle-derived surfaces.
- `SOL_DECISION_PACKET_J9_COUNT_LADDER.md` ratifies that restriction explicitly and requires the
  ladder cells to derive from a canonical exhaustive/disjoint lifecycle model.
- `macro:confluence_screener` is registered as `discovery_board`, but its actual contract is
  ranked signal-stack combinations with D/W evidence legs. It does not expose a lawful lifecycle
  enum from which ladder cells can be derived.
- The later estate census records that the current `archetype` field is not, in practice, a
  reliable structural key: `discovery_board` is a catch-all with multiple coherent cohorts.

A migration that obeys the old B layout literally would therefore have to invent stage/lifecycle
truth or violate the Prophet-only ladder rider. Both are forbidden.

## 3. Deterministic subtype selection

A migration/reference packet may classify a `discovery_board` as `lifecycle_board` only when all
of these are proven from the producer contract:

- one canonical population exists;
- its lifecycle/state cells are exhaustive and disjoint;
- every displayed population count is a ladder cell, ladder total, or deterministic derivation;
- the semantic axis is genuinely lifecycle, not a visual grouping, timeframe label, rank, topic,
  or model output;
- the route is Prophet/lifecycle-derived under the J9 rider.

If any condition is absent, the route MUST NOT render `.mx-ladder`.

A ranked/filterable board with no lawful lifecycle model may use `ranked_screener` when its primary
job is to discover and compare candidates. The migration packet must cite the actual ranking/evidence
contract and preserve null, stale, access, locale, theme, responsive, and interaction truth.

The remaining Discovery Board cohorts (heatmaps, radars, allocation/basket boards, and other
structurally distinct families) are **UNADJUDICATED by this packet**. They must not inherit either
subtype by analogy. Their migration packets must prove their own structural grammar or wait for the
future registry-structure owner.

## 4. Ranked-screener composition

The ranked-screener identity is a composition of existing primitives, not a new global widget:

1. question/answer header;
2. filter controls that change the candidate view without changing evidence truth;
3. ranked evidence rows/cards;
4. for each surfaced rank: explicit evidence/leg stack and validation/freshness context;
5. honest entitlement transformation where protected identities exist;
6. loading / empty / stale / error / disabled states;
7. methodology/honesty disclosure.

The rank itself is ordinal evidence organization, not lifecycle state. A visual convergence motif may
be decorative only when it makes no unsupported semantic claim. Labels such as `4H / 3D / 2W`
must not appear unless the route contract actually supplies those intervals.

## 5. Confluence Screener ruling

`macro:confluence_screener` is **`discovery_board / ranked_screener`** for the current migration.

Its governed reference MUST preserve:

- the primary user question: “Which names line up across the signal stack today?”;
- rank 1 public identity/evidence;
- rank 2–3 public count/evidence with protected identities omitted until entitled hydration;
- the builder-owned variable-length D/W leg stack, including three-leg cases, without minting a special third-leg semantic;
- recent-vs-older validation truth and runtime-owned values;
- Dark/Light, EN/ZH, desktop/390 mobile;
- loading, empty, stale, error, disabled, filter, hover/focus, and applicable interaction states;
- a representative entitled/unlocked transition using non-live placeholders in design evidence.

It MUST NOT invent lifecycle cells, a generic ladder, unsupported timeframe semantics, fake blurred
ticker identities, or a second ranking/trade authority.

The Paper reference on file `01M2WGNCX9475G79JRKJTCM08P`, page `p-A-0`, remains provisional.
PR #7727 remains the RIG/evidence carrier. This ruling does not approve that reference by itself.

## 6. Relationship to current design law and registry work

This packet narrowly supersedes the statements that **every** Discovery Board structurally begins
with a ladder or that the archetype field alone authorizes the ladder. It does not repeal the
Discovery Board product/job archetype.

Until the constitution can be reconciled without colliding with incumbent PR #7394:

- the J9 Prophet-only ladder rider remains fully binding;
- this packet is the controlling subtype decision for Confluence and any later route that proves
  the same ranked-screener contract;
- no edit is made here to `MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` because PR #7394 currently owns that
  path;
- no new registry key is minted here.

The broader Registry V2 question remains separate. A future accepted schema may add a derived
structural key (for example from template/builder/route contract) or document `archetype` as a
product-job grouping. This packet does not pre-empt that owner.

### Editable-projection follow-up

The current Paper file contains an existing artboard `1RY-0` named
`B · Discovery Board · Starter`. Its composition hardcodes the lifecycle count ladder
(`EARLY / BUILDING / READY / ACTIVE`). That artboard is therefore a **lifecycle-board starter**,
not a universal Discovery Board starter.

After this ruling is accepted, governed editable projections MUST stop presenting that artboard as
the generic B structural template. The lawful follow-up is to preserve the existing artboard but
relabel/qualify it as the lifecycle subtype, and to represent `ranked_screener` as a separate
composition variant built from existing primitives. Do not delete the lifecycle starter, do not
invent a second token/component authority, and do not treat this projection cleanup as source-law
acceptance by itself.

Until that projection cleanup is complete, designers working on ranked screeners MUST cite this
decision packet and MUST NOT copy the ladder from `1RY-0` merely because the route registry says
`discovery_board`.

## 7. Effect on the current RIG and migration chain

For PR #7727:

- remove unsupported `4H / 3D / 2W` semantic labels from the proposal;
- restore variable-leg-depth parity: the reference must visibly tolerate the builder's three-leg cases on mobile and ZH desktop without minting a special third-leg semantic;
- add representative paid/unlocked evidence without protected ticker values;
- re-freeze all proposal captures after the bounded Paper repair;
- run the normal independent RIG critiques against the ranked-screener contract.

Production `templates/confluence_screener.html.j2` and
`scripts/build_confluence_screener.py` remain untouched until a RIG approval receipt exists.

## 8. Non-goals

This ruling does not:

- re-archetype Confluence;
- change the Confluence producer, rank calculation, entitlement model, or payload;
- authorize Paper writes while the accepted Paper runtime/catalog gate is closed;
- create a new ladder, component authority, registry authority, RIG process, or migration lifecycle;
- classify heatmaps/radars/allocation boards;
- approve or merge PR #7394, #7630, #7727, or Mastermind #934.

## 9. Acceptance

Before this packet merges:

1. independent semantic review must confirm it preserves the J9 rider and does not invent data;
2. repository checks must pass at the exact head;
3. reviewers must confirm the packet is a narrow structural adjudication, not a second design-system
   authority or a covert Registry V2 implementation.

After merge, PR #7727 may cite this decision as the design-authority resolution for its
DESIGN-SYSTEM GAP, while all separate Paper-runtime and RIG gates remain binding.
