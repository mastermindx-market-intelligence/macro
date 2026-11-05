# MarketOntology MO-J1 — Joined Research Journey Freeze

Date: 2026-09-25  
Parent: `marketontology-complete-parity-fanout-20260826-sol-001` / macro#6819  
Ruling: `marketontology-mo-j1-integration-first-20260924-sol-001`  
Meta-CEO: Sol under current Chairman direction  
Status: **FROZEN; A-SIDE IMPLEMENTATION MAY START AFTER THIS CORRECTION MERGES + FRESH SOURCE/COLLISION RECONCILIATION; B-SIDE WAITS FOR #746 CLOSE**  
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
- TXI chain library + per-name exposure screens in `engine.transmission_chains.resolve_blast`;
- TXI `chain_state.json` blast outputs for genuinely active chains;
- `engine.market_ontology.exposure_map` + `market_ontology.exposure_map/v1` as the separate Theme Map owner once an explicit reviewed shock→theme declaration and rights-admitted theme relation exist;
- Theme Graph identity-resolution + Data OS security-master identity for any automatic company deep link;
- Theme Graph identity-resolution sidecar;
- Data OS security-master identity;
- `lib.dataos.identity.parse_listing_key` for immutable listing-key validation only;
- `engine.theme_graph.store.read_identity_resolution(latest=True)` as the existing collapsed Theme Graph→Data OS identity sidecar reader;
- `engine.intelligence_workspace.entity.load_current_symbol_map` / `VendorAliasTable` as the existing current-symbol owner for Terminal navigation;
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

The live WTI path currently preserves context into Macro’s transmission page, but does **not** yet produce the complete company→Terminal continuation.

There are TWO distinct owner paths and they must not be collapsed:

1. **TXI native per-name exposure path — lawful now when the selected chain is active.** The chain YAML already declares structured per-company exposure screens. `engine.transmission_chains.resolve_blast` resolves them over the per-ticker substrate only for `arming|propagating|expressed` episodes and emits named channels with counts, cuts, unevaluable counts and sorted ticker arrays. This is display-only context and originates no score/rank/trade authority.
2. **Theme Map path — separate capability closure.** `engine.market_ontology.exposure_map` composes shock→theme→company, but its `ShockSpec.theme_node_ids` are deliberately CALLER-SUPPLIED. It must never infer which themes a shock hits. The obvious Finviz local oil themes are presently rights-unresolved for new GMI emissions. MO-J1 MUST NOT silently supply a guessed shock→theme mapping or bypass the rights gate merely to obtain company rows.

Therefore MO-J1's first automatic company continuation uses **existing TXI blast output when owner-backed output exists**. Full MO-DELTA-004 Theme Map closure remains separately honest until an explicit reviewed shock/path→theme declaration plus rights-admitted owner edges exist.

If the selected path is dormant and no owner-backed per-name output exists, the product shows the declared exposure-screen context and an honest unavailable/dormant state. It MUST NOT fabricate an affected-company list.

## 4. MO-J1A — Macro affected-company continuation

Owner: CEO A / F04 delivery side. #7970 is merged, so this side is no longer blocked by the former A carrier.  
No implementation START is claimed by this records freeze; source work may start after the current-symbol correction carrier merges and the builder re-reads current source/collisions.

### 4.1 Projection law — owner order

For the selected supported path, the consumer follows this precedence:

**A. TXI current owner output (preferred first slice).**

- Read the exact selected chain from the existing TXI state owner.
- Only `arming|propagating|expressed` chain states may supply automatic per-name exposure rows.
- Consume the existing `blast` channel output; do not re-evaluate screen clauses in page code.
- Preserve each channel’s bilingual label, `cuts`, `unevaluable`, `resolved` and note.
- Names remain deterministic/alphabetical owner output; no magnitude/rank is introduced.
- A dormant chain with `blast={}` produces **no automatic affected-company rows**.

**B. Future accepted Theme Map output.**

Once an explicit reviewed shock/path→theme declaration exists and the relevant GMI source family is rights-admitted, an accepted `market_ontology.exposure_map/v1` result may supply theme→company rows. Until then, MO-J1 cannot use this route as a substitute for TXI output.

**C. No owner-backed output.**

Show the path’s declared exposure-screen definitions and typed absence. A user may still navigate to ordinary company research through existing search/navigation, but that company MUST NOT be labelled “affected,” “beneficiary,” “at risk,” or equivalent merely because the user chose it.

### 4.2 Security-link gate

A company can receive an **Open company research** CTA only when the exposure relationship is owner-backed **and** current identity resolves safely.

For a TXI blast name:

1. the selected chain is `arming|propagating|expressed`;
2. the name appears in an existing resolved TXI `blast.<channel>.names` list;
3. the candidate maps to a real existing Theme Graph company node for the same market/listing scope — never mint a graph node from the ticker;
4. the existing Theme Graph/Data OS identity resolver returns `resolution_state == "RESOLVED"`;
5. `security_id` and `listing_key` are non-null;
6. no entity-type/cross-market/alias ambiguity or refusal exists;
7. the canonical listing parser can parse the exact owner-supplied `listing_key`.

For a future Theme Map row, use the identity block already emitted by `market_ontology.exposure_map/v1` and apply the same non-ambiguous RESOLVED gate.

The immutable `listing_key` is an identity receipt, **not necessarily the ticker a user should navigate with today**. `lib.dataos.identity.parse_listing_key(listing_key)` may validate the exact owner-supplied listing grammar, but its `.code` is the **inception code** and MUST NOT be promoted to the current Terminal symbol.

The Terminal navigation symbol MUST instead come from the existing Data OS current-symbol owner for the resolved `security_id`: `engine.intelligence_workspace.entity.load_current_symbol_map` / `VendorAliasTable.vendor_symbol_for` (or its accepted current-owner equivalent), at the current effective date. The current symbol must resolve back to the same `security_id`. TXI's bare ticker array and display labels remain non-authoritative for this join.

If current-symbol resolution is missing, ambiguous or refused — including a rename where only the immutable inception code is available — render the honest exposure state but **no security deep link**. The current-repository rename regression `US-XNYS-EQR` → current store symbol `VMRK` must prove that the URL uses `VMRK`, never stale inception code `EQR`. A historical rename fixture may be used only if its alias rows are present in the candidate's exact source.

If any gate fails, render the honest exposure state but **no security deep link**.

### 4.3 Deterministic display

TXI and exposure-map owners both forbid MO-J1 from inventing magnitude ordering. The consumer therefore may:

- preserve the TXI owner’s sorted ticker order or exposure-map deterministic company-node order;
- group TXI rows by named exposure channel, or future Theme Map rows by theme;
- expose bounded “show more” / search interactions for dense channels;

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
mo_channel=<TXI exposure-screen id, when the company came from TXI blast>
mo_theme=<theme node id, only when a future accepted Theme Map result supplied it>
mo_company=<existing Theme Graph company node id>
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
- `mo_channel` is a bounded owner-emitted TXI screen id; it is descriptive context only;
- `mo_company` uses the existing Theme Graph company-id grammar and must name an existing graph node;
- `mo_theme` is optional and is accepted only from a future rights-admitted Theme Map result;
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

Owner: CEO B / F11 side after #746 closes. #747 shared heal is already merged and is DO_NOT_REDO.

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

### Gate 0 — edge-local predecessor gates

A:
- #7970 is merged; A-side MO-J1 source work may proceed independently after this packet's current-symbol correction merges and a fresh current-source/collision read is clean.

B:
- #747 shared CI heal is merged and must not be replayed;
- finish #746 under the evidence-recapture ruling;
- prepare #744 signed-in proof.

B's active carrier blocks only the B-side Thesis/Analysis paths. It does **not** serialize the disjoint Macro/F04 half.

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
2. opens a supported current transmission path;
3. reaches a real owner-backed per-name exposure from an active TXI chain (or, later, an accepted rights-admitted Theme Map result);
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

1. **A-side now:** after the current-symbol correction carrier merges, run a fresh Macro consumer collision census and commission MO-J1A under CEO A. The Paper connective design is already accepted as the implementation reference.
2. **B-side independently:** keep #746 on its incumbent carrier through evidence recapture/release; only after #746 closes commission MO-J1B on the Terminal Analysis/Thesis paths.
3. Keep the exposed cross-app contract frozen unless a builder proves a concrete incompatibility.
4. Do not wait for B to start A, and do not widen B's active #746 with MO-J1 code.
5. Batch F04 entitled proof + #744 thesis proof + final joined MO-J1 proof into the smallest possible Chairman acceptance windows.

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

## 18. Semantic correction — immutable listing identity is not the current navigation symbol

**This section supersedes any earlier wording in this packet that could be read as deriving a current Terminal ticker from `ListingKey.code`.**

Fresh source adjudication against Data OS established:

- a listing key is mint-once identity and intentionally preserves the inception code across symbol renames;
- `parse_listing_key` validates and parses that immutable identity; it is not the current-symbol resolver;
- Theme Graph identity rows are generation sidecars, so consumers use the existing collapsed `engine.theme_graph.store.read_identity_resolution(latest=True)` reader rather than treating raw parquet generations as independent current identities;
- the existing current-symbol owner is the time-aware alias layer, exposed to consumers through `engine.intelligence_workspace.entity.load_current_symbol_map` / `VendorAliasTable.vendor_symbol_for`;
- therefore MO-J1 must join TXI → Theme Graph/Data OS on `security_id`, then obtain the current navigation symbol from that owner;
- if the current symbol cannot be resolved uniquely to the same `security_id`, the product keeps the exposure row and withholds the Terminal CTA.

Required mutation/falsifier: use the current-repository EQR→VMRK seam (immutable `security_id=SEC:US-XNYS-EQR`, `listing_key=US-XNYS-EQR`; current `store` alias `VMRK`) or an equivalent exact-source rename fixture. The deep link must use the **current** symbol; deleting/bypassing the current-symbol lookup must make the test fail. A stale inception-code URL is a blocking identity defect.

This correction changes no identity authority, store, schema or persistence plane. It only prevents a consumer from confusing immutable identity with current display/navigation naming.

## 17. Semantic correction — TXI-first company continuation

**This section supersedes any earlier reading of this packet that makes `market_ontology.exposure_map` a prerequisite for the first MO-J1 automatic company list.**

Fresh source adjudication after the initial freeze established:

- `market_ontology.exposure_map` is merged and useful, but has no production caller today;
- its shock→theme input is deliberately caller-supplied because inferring that edge is a causal claim;
- the natural Finviz oil local themes are currently rights-unresolved for new GMI public emission;
- house-curated broad energy baskets are explicitly not canonical themes and cannot be laundered into `ShockSpec.theme_node_ids`;
- the WTI chain already has structured, reviewed per-name exposure screens over real stockdata fields;
- TXI already resolves those screens into `blast` names when a chain is active;
- current WTI chain state at the adjudication read (`data/transmission/chain_state.json`, as-of 2026-09-23) is `dormant`, so its `blast` is honestly empty;
- at that same read, `real_rate_peak_gold_rerate` is `arming` and has an owner-backed `real_rate_beneficiary` blast, proving the existing owner can supply live per-name exposure when the state permits.

Therefore:

1. MO-J1 is a **generic joined transmission→company research journey**, not a promise that dormant WTI always has affected-company rows.
2. WTI remains the shipped F04 live-path exemplar. When dormant, it shows path/exposure-screen context and no fabricated automatic company list.
3. The first real joined proof MAY use another currently active TXI chain whose owner emits a nonempty blast, provided the ordinary user can reach that chain and all identity/context gates in this packet pass.
4. The Paper storyboard’s company row is a **target state conditioned on owner-backed per-name output**, not evidence that the current WTI episode has such a row.
5. MO-DELTA-004 Theme Map remains separately incomplete until its explicit shock→theme declaration, GMI rights, PIT and product-surface acceptance are satisfied. MO-J1 must not falsely close it.
6. Historical/replayed per-name blast is NOT assumed available. No replayed company list may be claimed unless the existing TXI/substrate owners prove point-in-time per-name resolution at that exact replay date.

This correction narrows authority while improving the implementation path: reuse current TXI per-name output first; close Theme Map honestly on its own evidence.


## 19. Concurrency correction — block the edge, not the mission

The original freeze was authored while A and B both had active predecessor carriers and therefore used a whole-program "after current A/B carriers close" sentence. That sentence is superseded.

Current accepted state at this correction:
- A's #7970 predecessor is merged;
- B's #747 shared heal is merged;
- B #746 remains the incumbent Thesis carrier.

The A-side F04 consumer paths and B-side Terminal Thesis/Analysis paths are disjoint. Under the active-execution law, B's open carrier blocks only B's overlapping edge. It does not justify leaving A idle.

Therefore MO-J1A may start after this correction merges plus a fresh source/collision read. MO-J1B still waits for #746 to close. This changes scheduling only; it grants no new source authority, persistence plane, deployment privilege or acceptance shortcut.

