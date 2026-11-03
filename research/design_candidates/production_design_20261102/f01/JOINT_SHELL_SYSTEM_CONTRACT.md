# F01/F02 — Shell-system interface candidate

**Contract: F01-F02-SHELL/1.0.0-candidate.2**  
**Acceptance: PARTIAL / RIG draft; candidate interface concurrence recorded.** F01 accepts the F02 author's source-bound geometry, cutoff and transition clarifications below. This is a joint interface candidate, not a released foundation, independent design acceptance or permission to implement.

| Binding | Exact reference |
| --- | --- |
| Programme/assignment | Macro [6e1862867193ec6486a22001a0e4fb515da20448](https://github.com/mastermindx-market-intelligence/macro/tree/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102) |
| F01 source | [#10645](https://github.com/mastermindx-market-intelligence/macro/pull/10645), f01/ only |
| F02 author/source | mastermindx-2, [#10630](https://github.com/mastermindx-market-intelligence/macro/pull/10630), [c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82](https://github.com/mastermindx-market-intelligence/macro/tree/c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82/research/design_candidates/production_design_20261102/f02) |
| F02 system input | F02-SYSTEM/1.0.0-candidate.2; native authoring/review in progress at inspected source |
| F02 concurrence | [F01_HANDSHAKE_CANDIDATE.md at f7c25c4b9870cff260c2a4b998be18d6c04d36d0](https://github.com/mastermindx-market-intelligence/macro/blob/f7c25c4b9870cff260c2a4b998be18d6c04d36d0/research/design_candidates/production_design_20261102/f02/F01_HANDSHAKE_CANDIDATE.md), blob 58b18e3ef094f1c24dfe4f583d73cb2ae9aa7306 |
| Unchanged token input | token-map.json blob a7ec801d3b559cc64f4fd57141c32f63098c6461 at both c6eb32e and f7c25c4; source-scope collisions and proposed light roles remain explicit |
| Coordination | [F01 request to existing F02 author, comment 6596927050](https://github.com/mastermindx-market-intelligence/macro/pull/10630#issuecomment-6596927050) |
| F01 editable Paper | [MASTERMIND PAGES / p-27-0](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-27-0); exact board IDs and frozen supporting evidence in the manifest |
| Retained predecessor | [p-23-0](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-23-0), all 17 boards retained |
| F02 editable source | [Canonical Design System / p-9-0](https://app.paper.design/file/01M312VSDSZFVT45674GDVJVZN/p-9-0); F02 owns its current review/effect truth |
| Procedure used | Mastermind b2326bbe30e9988d26199f5e774a482b9c09068a; compatible skillpack 1.0.1 |

## 1. Ownership and change rule

Candidate.2 changes from the F01 candidate.1 checkpoint at b2d00ddc7e2dfbffdc3c5855e1a4dffe8c4226a5: accepts the F02 content-gutter boundary at 600px rather than 768px; accepts a 440px tablet evidence overlay rather than 400px; makes the 600/860/1200 inequalities continuous for fractional CSS widths; and records reciprocal interface concurrence. It preserves the measured-content dock rule, 1256/1096 calculated thresholds, owners and release hold. F02's concurrence originally referenced the initial F01 carrier and actual Terminal CSS; this F01 response binds the resulting clauses to candidate.2, rather than claiming F02 reviewed all later F01 pixels or source changes.

F01 owns global composition, navigation hierarchy, search/directory entry, market destination treatment and shell return affordances. F02 owns tokens, shared component anatomy, data formatting, density and accessibility/motion primitives. Domain owners preserve their views, data semantics, producer identities and histories. F03 tracks organization, lineage and exact route/export admission; this candidate does not replace its registry or census. D07's analysisRoute remains authoritative and D23 owns saved objects/alerts. D06 retains focused Terminal and the single Brain owner.

Either author can propose a shared change; neither silently rewrites the other's branch or boards. Any change to usable widths, mode boundaries, slot semantics, return invariants, shared token roles or overlay/focus behavior creates a new candidate version with a change list. Domain owners then recompose and re-review affected screens. A source commit or native edit does not itself release the foundation.

## 2. Geometry and available width

All dimensions are CSS pixels and proposed interface values. Header height excludes OS/browser safe areas. The content inset is applied once; legacy/native children must not add the same gutter twice.

| Property | Candidate rule |
| --- | --- |
| Expanded navigation | 224 at viewport >=1200; 196 at widths >860 and <1200 |
| Compact navigation | 72, explicit user choice on desktop; no auto-collapse for evidence |
| Narrow navigation | One modal drawer at <=860; consumes zero width when closed |
| Header | 64 above 860; 56 at <=860 |
| Content gutters | 16 each at <=600; 20 each at >600 and <1200; 24 each at >=1200 |
| Local navigation | Content-driven, ordinarily at least 44 high; wrap/contained overflow or explicit view menu when needed; never clip a view |
| Docked inspector | 320 wide +24 gap; primary content must remain >=640 or the domain's larger qualified minimum |
| Modal inspector | 440 wide at represented 768/1024 widths, constrained to available viewport; at <=600, full viewport width with internal content padding |
| Reading measure | Domain/public composition chooses comfortable measure; no forced analytical full-width prose |
| Important touch control | House target44; phone rows>=48; wrapped content may require more |

Measure useful content width after actual navigation, both gutters and any additional reserved local chrome. Dock eligibility requires useful width >=984 before any larger domain minimum. The example table assumes no additional local reserved chrome. Header internal padding is a separate F01 composition choice, not automatically the content-gutter token. Historical source media rules use literal 861/1199 integer cutoffs; candidate.2 specifies continuous inequalities and does not assert the incumbent already behaves identically at fractional widths.

| Viewport | Default nav | Main slot before gutters | Useful content | Primary with dock | Mode |
| ---: | ---: | ---: | ---: | ---: | --- |
| 320 | 0 | 320 | 288 | — | Full-width/modal |
| 390 | 0 | 390 | 358 | — | Full-width/modal |
| 768 | 0 | 768 | 728 | — | Modal |
| 1024 | 196 | 828 | 788 | 444 would fail | Modal |
| 1280 | 224 | 1056 | 1008 | 664 | Dock eligible |
| 1440 | 224 | 1216 | 1168 | 824 | Dock eligible |
| 1600 | 224 | 1376 | 1328 | 984 | Dock eligible |

Expanded default first docks at1256:1255 leaves639,1256 leaves640. Explicit compact first docks at1096 with the actual 20px gutters:1095 leaves639,1096 leaves640. A1103/1104 test using a forced48px total inset is a distinct arithmetic fixture, not the responsive threshold. At1199/1200, navigation and gutters change, so eligibility must use the resulting container; it is not a single viewport-only “desktop” flag.

## 3. Slots and responsibilities

| Slot | F01 supplies | F02 supplies | Domain retains |
| --- | --- | --- | --- |
| Global nav/header | Placement, mode, exact destination/context behavior | Controls, icons, neutral selected/hover/focus treatment | No domain mutation from nav |
| Product identity/local nav | Space and coherent hierarchy | Section/tabs/link anatomy | Exact view vocabulary, parser, entity identity |
| Primary analytical object | Measured usable container | Table/chart/metric/empty-state contracts | Full columns/history, filters, clocks, units, definitions |
| Evidence | Dock/modal coordination, close/return rules | EvidenceTrigger/Inspector anatomy | Field/row/source identity, citation precision and access |
| Access/recovery | Consistent scope and location | StatePanel/TierGate/SaveFeedback patterns | Real guest/denied/expired/error/uncertain inputs and actions |
| Theme/locale | Existing owner integration and focused-shell exception | Semantic roles and readable EN/ZH variants | Content language, sign convention, currency and source truth |

The component names are specification vocabulary, not invented TypeScript exports or a new package. Existing source entry points remain in SOURCE_AND_DATA_CONTRACT.md. F02's token-map.json binds roles to current source aliases and proposed specimen colors. Dark NOIR roles observed in Paper are reused. Light specimen roles remain explicitly proposed. Do not alias tokens by identical spelling across repositories.

## 4. Invariants

1. Native/legacy admission, exact query/hash contracts, access and the Analysis parser stay with existing owners.
2. Market links are destinations. A true cross-market entity transition requires a qualified domain mapping; language cannot relabel data.
3. One top-level modal owns focus/scroll. A docked inspector is nonmodal. Closing restores logical context and never resolves an uncertain save.
4. Only a confirmed owner outcome says Saved. Fresh transport/build/context does not imply fresh market data.
5. /terminal keeps its focused chrome and Brain singleton. Public acquisition/reading and internal OS/admin keep distinct audience and authorization boundaries.
6. No colored container borders/accent stripes; neutral grouping, quiet fills and text hierarchy. Accessible focus outlines and data marks remain allowed.
7. Feature/history retention is evaluated against real source and predecessors, not only the amount visible in a specimen.

## 5. Concrete compositions and review entry

A and B compare the same Macro task at1440. C composes a Company table/history and evidence at1280 using the664px main object. D shows Options at1024 with788px content and modal evidence. E is390 ZH light; F is320 EN dark; G is768 ZH drawer; H is1280 compact. I is the owner-bound state atlas. Read me identifies scope and acceptance. Existing focused-Terminal and access/save references on p-23-0 remain part of the retained evidence set.

The source/pixel/JSX manifests record actual artifacts, hashes and any unresolved Paper operation. Readable native boards do not establish keyboard behavior, responsive implementation, screen-reader conformance or production serving. Static measurement and later browser proof are separate evidence classes.

## 6. Concurrence, review truth and release gate

The two authors' candidate interface agreement is now source-bound: F02's f7c25c4 handshake plus F01's candidate.2 acceptance of its specific clarifications. It does not establish reciprocal review of the complete visual sets, a final native freeze, consumer qualification or a released foundation. Opening, closing and switching evidence remain read-only; overlay/dock changes preserve identity and reconcile focus/inertness without mounting two inspectors. No token alias, endpoint, storage key or save authority is created by this agreement.

The candidate remains unreleased until both owners' Paper effects are reconciled and final captures are frozen; independent product/regression and visual/taste reviewers assess a closed packet; material findings are resolved on the reviewed artifacts; and QA01 qualifies representative cross-product journeys and retained coverage. Actual reviewer identity, input hashes, findings and disposition must be recorded. Self-review or a coordination comment cannot satisfy this gate.

At inspected F02 head f7c25c4, its source reports PARTIAL/RIG draft and NATIVE_WRITES_PAUSED_EFFECT_UNRESOLVED, with an unresolved Chinese-phone footer operation. Its prior BLOCK findings and repair work are not superseded by this agreement. The F01 state-8 effect remains separately unresolved. No author silence, source merge or tool write-schema receipt is design acceptance. The programme's implementation hold remains in force.
