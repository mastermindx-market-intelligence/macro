# MarketOntology MO-J1 — Joined Research Journey Freeze

Date: 2026-09-25  
Parent: `marketontology-complete-parity-fanout-20260826-sol-001` / macro#6819  
Ruling: `marketontology-mo-j1-integration-first-20260924-sol-001`  
Meta-CEO: Sol under current Chairman direction  
Status: **FROZEN FOR IMPLEMENTATION AFTER CURRENT A/B ACTIVE CARRIERS CLOSE**  
Capability state: **NOT_BUILT AS ONE JOINED JOURNEY**; constituent owners are already substantially built.

## Procedure / source pins used for this freeze

- Mastermind protected procedure: `622d128d64a79c3e4dd45f748b8a8db7ec2e2741`
- Macro source inspected for this freeze: `ad38f308945cdcd36a01111e88009ab895f9367c`
- Terminal source inspected for this freeze: `94403c1dd6693c41ae2100a9deafa2ce968ffa1b`

This file freezes one product seam. It does not create a new lifecycle, queue, graph, identity plane, research store, evidence store, thesis store, router or monitoring engine.

## 1. User outcome

A researcher begins with a real market development, follows the currently supported transmission/evidence path, chooses a canonically mapped affected company, opens that company in Terminal without losing why they came, creates or updates the canonical thesis, later reopens it and sees what changed, and uses the already-supported monitoring path.

The first accepted joined journey is:

```
ordinary Macro entry
→ WTI Live Path / current transmission reading
→ theme exposure
→ canonically mapped company
→ Terminal Company Intelligence
→ Your theses
→ create/revise canonical thesis
→ reopen / see what changed
→ existing supported monitor or condition
```

The first release is **research continuity**, not ranking, recommendation, trade construction, calibrated confidence, position sizing or portfolio authority.

## 2. Existing owners that MUST be reused

### Macro / F04

Already exists:

- live WTI explorer and private owner-data path from F04 #6872;
- `engine.market_ontology.exposure_map`;
- contract `market_ontology.exposure_map/v1`;
- Theme Graph membership/exposure edges;
- Theme Graph identity-resolution sidecar;
- Data OS security-master identity;
- `lib.dataos.identity.parse_listing_key`;
- house precedent for Macro → Terminal Company Intelligence links in Stage Analysis and Company Intelligence dossier surfaces.

The exposure-map contract already provides:

- shock;
- themes;
- companies;
- company node id;
- market scope;
- rights family;
- resolved identity state;
- `security_id`;
- `listing_key`;
- `issuer_id`;
- collision information;
- path evidence;
- typed unavailable/abstention reasons.

Its authority ceiling is already correctly fixed at:

```
research_display_only
```

It MUST NOT gain score, rank, confidence, weight, magnitude ordering, gate, size or trade semantics for MO-J1.

### Terminal / F11 + Company Intelligence

Already exists:

- canonical company route: `/analysis?symbol=<SYM>&page=intelligence`;
- Company Intelligence surface;
- Analysis workspace;
- ordinary `Your theses` continuation added by #742;
- canonical Thesis object/version store;
- thesis subject-ref contract;
- save/revise/version-conflict behavior;
- live thesis journey prover merged by #744;
- thesis “What changed” implementation on #746 once accepted;
- existing thesis-condition / alert owners.

No new research store or thesis store is permitted.

## 3. Current missing seam

The live WTI path currently preserves context into Macro’s transmission page, but does **not** yet produce the complete:

```
transmission/theme
→ resolved affected company
→ Terminal Company Intelligence
```

product continuation.

The exposure-map producer already composes shock → theme → company. The missing work is a consumer projection plus a bounded cross-app context carrier.

Therefore the first MO-J1 implementation must consume the existing exposure map; it must not derive a new company mapping in page code.

## 4. MO-J1A — Macro affected-company continuation

Owner: CEO A / F04 delivery side after current #7970 closes.  
No implementation START is claimed by this records freeze.

### 4.1 Projection law

For the selected supported shock/path, the consumer calls the existing exposure-map owner with caller-supplied theme ids and the relevant `asof` / `knowledge_cutoff`.

Render each theme in the producer’s deterministic order.

For each company:

- display only data already admitted by `market_ontology.exposure_map/v1`;
- preserve the path kind and source/evidence provenance already present;
- never derive magnitude, score, rank or “top beneficiary” semantics;
- never silently drop typed abstentions.

### 4.2 Security-link gate

A company can receive an **Open company research** CTA only when all are true:

1. the exposure-map company is present after the owner’s rights gate;
2. `identity.state == "RESOLVED"`;
3. `security_id` is non-null;
4. `listing_key` is non-null;
5. the identity row has no unresolved/refusal state;
6. there is no ambiguous identity collision that makes the company→security continuation unsafe;
7. the canonical listing parser can parse the exact owner-supplied `listing_key`.

The symbol used for the Terminal navigation link MUST come from canonical `lib.dataos.identity.parse_listing_key(listing_key)`, not by reparsing the Theme Graph company node id and not by matching a display ticker string.

If any gate fails, render the honest company/exposure state but **no security deep link**.

### 4.3 Deterministic display

Exposure-map v1 forbids ordering by magnitude. The consumer therefore may:

- use the existing deterministic company-node ordering;
- group by theme;
- expose a bounded “show more”/search interaction if needed for density;

but it MUST NOT call the first displayed name “top,” “best,” “most affected,” “leader,” “beneficiary,” or equivalent unless a separately accepted owner actually supplies that semantic.

### 4.4 Existing Terminal URL owner

Use the existing Company Intelligence route:

```
https://app.mastermind-x.com/analysis?symbol=<CANONICAL_SYMBOL>&page=intelligence
```

MO-J1 adds only a bounded, non-secret continuation context described in §5.

No token, source body, entitlement, user id, thesis body or credential enters the URL.

## 5. Cross-app continuation contract — `mastermind.market-ontology-context/v1`

This is a **transient navigation context**, not a durable research object.

It carries immutable/public identifiers needed to explain why the user arrived and to construct a safe return link.

Recommended closed URL vocabulary:

```
mo_from=ontology
mo_chain=<TXI chain id>
mo_focus=<path node id, if present>
mo_path_rev=<WTI path revision, if present>
mo_theme=<theme node id>
mo_company=<company node id>
mo_security=<Data OS security_id>
mo_asof=YYYY-MM-DD
mo_kc=YYYY-MM-DD
```

### 5.1 Validation

Terminal must parse these through one small typed helper.

Rules:

- duplicate values for an identity-bearing `mo_*` field invalidate the **context**, not the company route;
- every value is bounded in length;
- dates use the existing strict date vocabulary;
- `mo_company` uses the existing Theme Graph company-id grammar;
- `mo_security` is a bounded opaque identifier, never reparsed to mint identity;
- `mo_from` is a closed enum whose first value is `ontology`;
- malformed context fails closed to **company research with no MarketOntology context**;
- malformed context MUST NOT block an otherwise valid company page;
- no query field is trusted as prose.

This helper owns navigation parsing only. It does not become an identity owner.

### 5.2 Context banner

When valid, Terminal Company Intelligence shows a compact, bilingual context strip:

- fixed product label: **Opened from WTI Live Path**;
- fixed explanatory copy: this company was opened from a MarketOntology research path;
- **Back to WTI Live Path** action reconstructed only from validated identifiers;
- visible `asof` / knowledge-cutoff when present;
- no claim that membership equals causality, upside, downside or recommendation.

The banner does not need to print raw chain/theme/company ids.

### 5.3 Persistence law

The context is transient.

Allowed:

- remain in the current URL while switching Company Intelligence subpages;
- be explicitly forwarded into `view=theses`;
- remain in the browser history for the current navigation;
- construct the exact back-link.

Forbidden:

- new localStorage/sessionStorage persistence;
- a new database/table;
- thread-global state;
- silent insertion into future unrelated research;
- copying source bodies into the URL;
- auto-mutating an existing thesis.

### 5.4 Theses handoff

The existing Analysis → Your theses link currently constructs a fresh URL from symbol/view. MO-J1 should preserve only the **validated** `mo_*` context fields in that link.

Thesis route behavior remains owned by the existing F11 system.

On the thesis workspace, valid context may render the same compact “Opened from WTI Live Path” context strip while the user creates/revises research.

Opening a specific thesis may keep the validated `mo_*` fields in browser history, but the context is still transient and is not automatically persisted into the thesis.

If/when a later accepted evidence-to-thesis owner creates a canonical evidence pointer, that owner may add an explicit **Attach evidence** action. MO-J1 MUST NOT pre-empt that architecture by stuffing URLs or blobs into thesis content.

## 6. Thesis identity boundary

Current Thesis subjects already support:

- `data_os.security_master` resolved issuer subjects;
- `terminal.analysis_symbol` listing-scoped subjects;
- `macro.theme_registry` theme subjects.

MO-J1 does not silently upgrade the current F11 create flow from `terminal.analysis_symbol` to a new identity authority.

The Macro deep link may carry the resolved Data OS `security_id` as context, but the existing Thesis object continues to use whichever accepted subject owner the current F11 implementation lawfully uses.

A separate identity-upgrade decision is required if product owners later want the thesis itself to migrate from listing-scoped to security-master-resolved identity.

## 7. MO-J1B — Terminal continuation and thesis continuity

Owner: CEO B / F11 side after #747 shared heal and #746 close.

Smallest expected product surface:

1. typed MarketOntology query parser/helper;
2. context banner on Company Intelligence / Analysis workspace;
3. bounded context preservation into `Your theses`;
4. same banner on the thesis workspace when valid;
5. back-link to the exact WTI path/revision/step when reconstructable;
6. no change to Thesis persistence schema.

Do not widen #746 or #747 with MO-J1 code. They close first.

## 8. Monitoring continuation

MO-J1 reuses the existing Thesis-condition/Alerts path.

First-release acceptance requires that the researcher can reach and understand the already-supported monitor/condition state from the thesis flow.

It does **not** require external email/push delivery if the drain is intentionally disabled.

Keep these claims separate:

- condition exists;
- condition evaluated;
- in-product FIRED/closed-window state exists;
- outbox row exists;
- external delivery occurred.

No layer may promote one of those facts into another.

## 9. Negative states

The joined journey must visibly survive:

- F04 owner store unavailable;
- no themes declared;
- no theme edges;
- no membership yet;
- rights suppressed;
- unresolved identity;
- identity collision;
- malformed cross-app context;
- anonymous Terminal access;
- wrong/unavailable thesis;
- stale-version thesis conflict;
- unsupported/missing monitor state.

A missing affected-company mapping must never become a guessed security link.

## 10. Paper design brief — connective design only

Design owner: existing `MASTERMIND PAGES` Paper document / incumbent design-convergence owner.

Do not redesign Macro Command, Company Intelligence, Research Workspace or Thesis Workspace from zero.

Create a bounded MarketOntology joined-journey page containing:

### Frame A — WTI Live Path → affected companies

Show:

- current path state;
- theme exposure group;
- company rows from the accepted exposure-map contract;
- provenance/availability state;
- **Open company research** CTA only on canonically linkable rows.

Include dark/light and desktop/mobile state decisions by reusing current tokens.

### Frame B — Terminal Company Intelligence arrival

Show:

- current Company Intelligence surface;
- the compact **Opened from WTI Live Path** context strip;
- as-of / knowledge-cutoff;
- Back to WTI Live Path;
- existing Your theses continuation.

### Frame C — Thesis continuation

Show:

- existing Thesis workspace;
- the same transient context strip;
- create/revise path;
- accepted “What changed” presentation from #746 when merged;
- monitor/condition continuation.

### Frame D — negative/degraded examples

At minimum:

- exposure known but identity unresolved → no security CTA;
- context malformed/expired/unsupported → Terminal still opens company research without context;
- source revised after leaving → return path makes the revised state explicit;
- monitor unavailable → no false delivery claim.

No new design tokens unless an incumbent token gap is proven.

## 11. Implementation phasing

Do not exceed current product WIP merely to start MO-J1 early.

### Gate 0 — current work closes

A:
- finish/release/prove #7970 under its current owner.

B:
- preserve/finish #747 shared CI heal;
- finish #746 under the evidence-recapture ruling;
- prepare #744 signed-in proof.

### Gate 1 — design / contract

May proceed without source custody:

- Paper connective frames;
- exact URL/parser contract tests;
- collision census for expected implementation paths.

### Gate 2 — Macro half

Expected bounded paths are in the existing F04 consumer plane plus tests/evidence. The builder should discover the exact current consumer seam before declaring path scope.

No change to `engine/market_ontology/exposure_map.py` unless a genuine owner-contract defect is proven. The desired state is to **consume** v1, not widen it.

### Gate 3 — Terminal half

Expected bounded paths:

- a new small `lib/` parser/helper for MarketOntology context;
- Analysis workspace context UI / link preservation;
- Thesis workspace context UI only where required;
- i18n/CSS/tests/evidence as needed.

Do not create a new context database or service.

### Gate 4 — real joined proof

A permitted signed-in user:

1. starts on ordinary Macro navigation;
2. opens WTI Live Path;
3. reaches a populated owner-backed exposure;
4. chooses a canonically resolved company;
5. arrives in Terminal Company Intelligence with context visible;
6. opens Your theses with context retained;
7. creates/revises or reopens the canonical thesis;
8. sees the accepted “What changed” behavior;
9. reaches the existing supported monitor state;
10. returns to the correct WTI path context.

The receipt binds exact deployed revisions on both products.

## 12. Review falsifiers

A reviewer should fail the build if any are true:

- page code derives shock→theme or theme→company membership itself;
- a bare ticker is used as the durable identity join;
- unresolved/colliding identity still gets a Terminal CTA;
- company rows are ranked without an accepted ranking owner;
- Macro→Terminal context includes source bodies, credentials or user data;
- Terminal stores context in a new persistence plane;
- malformed context blocks ordinary company research;
- Thesis is auto-mutated from URL context;
- monitoring UI implies external delivery without delivery proof;
- one side recreates an owner that already exists.

## 13. Completion boundary

MO-J1 is complete only when the real served signed-in joined journey passes at accepted revisions.

Intermediate states remain truthful:

- packet/design only → `SPEC_ONLY`;
- code merged, no real joined proof → `BUILT_NOT_PROVEN`;
- anonymous-only proof → still not signed-in accepted;
- one half proven without the seam → parent MO-J1 remains incomplete.

## 14. Research parallelism

The existing R1 parity/workflow research packet may run independently while MO-J1 is built.

Its job is not to redesign MO-J1. Its downstream consumer is the **post-MO-J1 parity roadmap**:

```
already exists
exists but disconnected
built not proven
needs UX continuation
needs data/rights work
genuinely absent
not worth copying
candidate for beyond-parity improvement
```

R2 transmission-method research should not block the descriptive/read-only exposure path frozen here unless it proves this contract materially unsafe.

## 15. Exact next action

After current A/B active carriers close:

1. run a fresh collision census on the Macro consumer paths and Terminal Analysis/Thesis paths;
2. consume the Paper connective design;
3. commission MO-J1A and MO-J1B as two disjoint implementation units under their incumbent A/B delivery principals;
4. keep the exposed cross-app contract frozen unless a builder proves a concrete incompatibility;
5. batch F04 entitled proof + #744 thesis proof + final joined MO-J1 proof into the smallest possible Chairman acceptance windows.

Parent mission remains incomplete after MO-J1. MO-J1 is the first coherent integrated product milestone, followed by portfolio/capital-impact and continuous-decision-loop waves toward full parity and beyond-parity.

## 16. Paper connective-design receipt

Design system owner reused: existing Paper file **MASTERMIND PAGES**. No second design system or new token family was created.

Paper identity:

- file: `MASTERMIND PAGES`
- file id: `01M2WGNCX9475G79JRKJTCM08P`
- page: `MarketOntology · Joined Journey · 2026-09-25`
- page id: `p-G-0`
- page URL: `https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-G-0`
- primary artboard: `MO-J1 · Joined Journey · Desktop Storyboard · V1`
- artboard id: `VS0-0`

The storyboard is a connective product contract, not a replacement visual system. It uses the existing Mastermind dark tokens and Inter scale and shows:

1. **WTI Live Path → affected company**
   - theme exposure remains research-display-only;
   - canonically resolved company gets **Open company research**;
   - unresolved company remains visible as exposure context but has **No link**.
2. **Company Intelligence arrival**
   - compact **Opened from WTI Live Path** context strip;
   - path revision / as-of context;
   - explicit Back-to-path affordance;
   - existing **Your theses** continuation.
3. **Thesis continuity**
   - same transient context strip;
   - context is visibly not silently persisted;
   - accepted “What changed” concept from #746 is the reopen surface.
4. **Monitoring return**
   - in-product condition state reopens research;
   - external delivery remains a separate claim.
5. **Degraded-state strip**
   - unresolved identity → show exposure, no Terminal CTA;
   - revised path → return explains revision change;
   - malformed context → company research still opens, context drops;
   - unavailable monitor → no false external-delivery claim.

Paper edits were applied through the guarded adapter with observed responses. A wrapper error occurred only after the Stage-2 write response had returned; the artboard was read back before any further edit, confirming the Stage-2 frame existed. No ambiguous Paper effect remains. The final storyboard was screenshot-reviewed for spacing, hierarchy, contrast, alignment and failure-state clarity; the affected-company action lane was then aligned to a fixed trailing slot before the artboard was released with `finish_working_on_nodes`.

This design receipt does not prove implementation or production acceptance.

