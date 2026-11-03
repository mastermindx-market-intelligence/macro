# F01 — Existing consumer requirements and resolved source differences

**Scope:** F01 shell composition and preservation requirements, supplementing candidate.3. This is not a new D02/D08 assignment, a released joint contract, a change to their source or a production implementation. The F01/F02 geometry is unchanged. The supplemental checks below were added after the earlier 79-case source review and remain unexecuted.

## 1. Exact consumer inputs and the geometry resolution

The existing D02 author delivered [comment 6597893509](https://github.com/mastermindx-market-intelligence/macro/pull/10645#issuecomment-6597893509), based on its [packet at a5e4e86092a447a8f4c2e1ecc930b076e106bdac](https://github.com/mastermindx-market-intelligence/macro/tree/a5e4e86092a447a8f4c2e1ecc930b076e106bdac/research/design_candidates/production_design_20261102/d02). D08 delivered [comment 6597852782](https://github.com/mastermindx-market-intelligence/macro/pull/10645#issuecomment-6597852782) and its [source conformance return at e89f527e3267b1d1dd27ac7507e9a25983c0c903](https://github.com/mastermindx-market-intelligence/macro/blob/e89f527e3267b1d1dd27ac7507e9a25983c0c903/research/design_candidates/production_design_20261102/d08/CONFORMANCE_REVIEW_20261103.md). Both compared F01's older candidate.1 at `b2d00ddc7e2dfbffdc3c5855e1a4dffe8c4226a5` with F02's handshake at `f7c25c4b9870cff260c2a4b998be18d6c04d36d0`.

Those findings were correct for those inputs. F01 subsequently accepted the F02 clarifications in **candidate.2 at `245a7d2cd62d88fb6d2ee3863f9d26c63052d8e7`**. Candidate.3 preserves them. This supersedes only the listed candidate.1 dimensions and ambiguity; it does not supersede either author's native-effect hold, independent findings or consumer qualification.

| Consumer concern | Source resolution | Discriminating value |
| --- | --- | --- |
| 600 versus 768 gutter cutoff | 16px each at <=600; 20px each above 600 and below 1200; 24px each at >=1200 | At 640, useful content600; at 700,660; at 600.5,560.5 |
| 400 versus440 modal pane | 440px at represented768/1024, constrained to viewport; full width with internal padding at <=600 | D's actual native pane remains400; it is an open repair, not agreement evidence |
| Fractional rail gaps | No rail at <=860;196px expanded above 860 and below 1200;224px at >=1200 | At 860.5 useful content624.5; at 1199.5,963.5; at 1200,928 |
| Dock threshold | Measure actual usable content after shell and reserved local chrome; require320+24+at least640 | Expanded first eligible1256; explicit compact1096 under these gutters; larger domain minimum still controls |
| Focus during resize | Preserve one evidence identity; reconcile modal/inert/scroll ownership on mode change | N10/N11 and G07 remain NOT_RUN; source concurrence is not behavior proof |

Current exact joint source: [candidate.3 at 3ec131bb4b515c5ede76f51e9d8e65f128bc19ae](https://github.com/mastermindx-market-intelligence/macro/blob/3ec131bb4b515c5ede76f51e9d8e65f128bc19ae/research/design_candidates/production_design_20261102/f01/JOINT_SHELL_SYSTEM_CONTRACT.md). F02's unchanged token blob and candidate.2 concurrence remain in that record. Later candidate.3 compact/chart/layer additions are pending F02/D06 review. Consumers must not retain the old400px/768px values as the current F01 proposal, nor describe the new candidate as released.

## 2. D02 local navigation inside the existing shell slot

The D02 [product specification](https://github.com/mastermindx-market-intelligence/macro/blob/a5e4e86092a447a8f4c2e1ecc930b076e106bdac/research/design_candidates/production_design_20261102/d02/PRODUCT_UX_SPEC.md) retains Macro Command's exact order: **Overview, Money, Policy, Rates, Inflation, Growth, Jobs, Housing, Consumers, Borrowing costs, Government debt, Trade**. Money retains liquidity/central-bank views; Growth retains economy/business; Borrowing costs retains borrowing/funding. This is distinct from the five illustrative Macro overview labels in F01 A/H. Neither set substitutes for the other.

F01 supplies the product identity and content-driven local-navigation slot. D02 keeps its fixed section map and existing selector semantics. At wide widths, allow the complete local row to wrap or scroll within its own region, with a visible selected label and reachable end controls. At narrow widths, the existing F01 view-menu option must expose every D02 section, then that section's actual subtabs. The global drawer cannot be the only route to a local view. Do not solve a twelve-section fit problem by removing sections, shrinking important targets below the house rule, changing section order, or adding a second domain bottom bar. The exact EN/ZH content remains with D02.

The [interaction contract](https://github.com/mastermindx-market-intelligence/macro/blob/a5e4e86092a447a8f4c2e1ecc930b076e106bdac/research/design_candidates/production_design_20261102/d02/INTERACTION_STATES.md) identifies `#<section>/<subtab>`, including `#money/central_banks`, `#growth/business` and `#credit/funding`, with existing `replaceState` behavior. Delayed fragment insertion must reapply selected state without stealing keyboard focus. Current/Drivers/History keep `#current`, `#drivers`, `#history`; the existing `mmx:shell-location` path reveals a hidden panel before resolving its anchor. F01 preserves these messages and canonical hashes; it does not invent a new parser or URL field.

Exactly one actual scroller owns each scroll action. Preserve whether that is the host, embedded document or local analytical object; account for sticky header offset when focusing a target. The current local drawer's inert handling does not prove the outer host is inert. The later integration must demonstrate the host/embedded boundary rather than infer it from a local focus-trap helper. Evidence dock/overlay changes preserve the same domain selection and return anchor; they do not remount a second analytical workspace.

The D02 contextual **Ask the analyst** uses its existing `MMBrain.explain(sectionId, localizedLabel)`, open/boot fallback and real `chat.html` fallback. Preserve that contextual action; a generic global Ask label is not a replacement. This source report does not resolve the separate D06 typed lifecycle gap identified by F01, and does not authorize a second Brain singleton.

## 3. Domain meaning that the shell must carry unchanged

The D02 [backend/data contract](https://github.com/mastermindx-market-intelligence/macro/blob/a5e4e86092a447a8f4c2e1ecc930b076e106bdac/research/design_candidates/production_design_20261102/d02/DATA_BACKEND_BUILD_CONTRACT.md) is the consumer authority for these distinctions. F01 does not recompute or promote them:

| Domain evidence | Shell/presentation preservation |
| --- | --- |
| Heuristic regime strength/agreement, fitted HMM membership, historical event frequency and qualified forecast | Keep their separate labels, bases and evidence classes. A generic confidence badge cannot turn them into one probability |
| `reading_state`, `display_score`, coverage and typed refusal | Unavailable display values stay unavailable even if an internal raw score is100; no zero/default substitution |
| Observation, release/publication, availability, retrieval/build and revision clocks | Keep supplied precision and missing vintage; a fresh shell build cannot refresh an old economic observation |
| Rights blocked, unsupported region, stale source and disagreement | Preserve different reasons and next actions; do not flatten them to an empty table or an account-upgrade prompt |
| Fourteen currently US-only economic workspaces | Region navigation never relabels their cached snapshots as another market |
| `execution_available=false`, `service_available=false` | Do not present runnable scenarios or working Save/alert success. D23 must qualify its actual mutation/readback path |

D02 owns `body.page-macro`; D03 retains `body.page-stocks` and its complete S&P1500 board. F01's five-row illustrative breadth example does not certify either universe or full coverage. Native A/B/H must either show the complete owner-provided set or disclose the subset, selection rule and route to the complete set. Session missingness, sector coverage and advancing-sector denominator are separate facts. No invented observations or dates may fill the missing specimen rows.

The historical `/macro/<id>.html` family resolves in D02 source to eleven **fetch-only inner fragments** under `/macro/fragments/`. F03 owns the registry/export correction. Preserve this distinction; neither the F01 directory proposal nor a display label admits those assets as standalone public documents. Existing internal404/access boundaries remain intact.

## 4. D08 consumer boundary

D08's conformance return uses the same Terminal source pin as F01 for the fifteen native panes and aliases. Its passing function/source and arithmetic checks are attributed to D08's detached specimen; F01 did not execute them and they are not browser/RIG acceptance. D08's source intentionally uses the earlier F01400px/768px proposal provisionally and needs to consume the resolution above through its existing author. No other D08 semantic contract, slice launch or ownership changes.

Retain D08's exact observation/return identity, inferred-side labeling, separate native panes and Futures/replay destinations, full source-owned table/export scope, and source/date/access limits. A selected strike/aggregate coordinate is not automatically a uniquely identified contract or a Plan leg. Save remains with the native Investigation/D23 owner. The earlier D08 safety-refused Paper operation remains held and is not retried, delegated or cured by this F01 source return.

## 5. Supplemental consumer acceptance cases — NOT_RUN

These six cases supplement the 79 earlier specifications, for **85 total unique cases**. They bind the new attributed consumer inputs without altering the agreed shell dimensions or claiming source/visual acceptance.

| ID | Setup/action | Required evidence / owner |
| --- | --- | --- |
| M01 | All twelve Command sections and actual subtabs at 320/390/700/1024, EN/ZH; switch from a late section after resize | Same fixed order, selected label and complete reachability in the local slot;44px important controls; no global-drawer substitution. F01 slot/D02 content/F02 anatomy |
| M02 | Enter `#money/central_banks`, switch to `#credit/funding`, traverse history, then open a hidden suite `#history` anchor during delayed loading | Existing hash/replace semantics; correct fragment/panel before anchor resolution; one scroller; preserved focus and no jump to the wrong section. D02 parser/host integration |
| M03 | From Command evidence, invoke contextual Analyst, close through its real owner, then reopen evidence at the same section and subtab | Same singleton and qualified contextual payload; no doubled dock/modal or guessed lifecycle event; D06 binding prerequisite remains explicit |
| M04 | Display an unavailable raw100 record, a rights-blocked source, a US-only workspace under attempted regional navigation, and false save-service flags | Typed refusal/coverage and actual market remain truthful; no fabricated score, new region, entitlement or save success. D02/D23 retain decisions |
| M05 | Compare consumer geometry at 640/700/600.5/860.5/1199.5 and 1024 overlay | Current candidate uses600/660/560.5/624.5/963.5 useful widths respectively,440px overlay at 1024; actual host insets measured separately. Historical400px/768px specimen does not count as current conformance |
| M06 | Review complete breadth subset and source-clock disclosure; inspect served viewport metadata and actual400%/mobile zoom behavior | Explain shown/total sector scope and comparison dates without invented values; retain magnification and all actions. D02's `maximum-scale=1`/`user-scalable=no` observation is an attributed source concern, not an executed F01 conformance failure |

Exact input blobs are in [CONSUMER_INPUT_RECEIPTS.json](evidence/source/CONSUMER_INPUT_RECEIPTS.json). The existing owners' reports are preserved at their pins; this note corrects only the consumer view of F01's current source and carries concrete retained obligations into its build/re-audit package.
