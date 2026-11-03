# F01 — Existing consumer requirements and resolved source differences

**Scope:** F01 shell composition and preservation requirements, supplementing candidate.4. This is not a new D02/D06/D08 assignment, a released joint contract, a change to their source or a production implementation. The F01/F02 geometry is unchanged. The supplemental checks below were added after the earlier 79-case source review and remain unexecuted.

## 1. Exact consumer inputs and the geometry resolution

The existing D02 author delivered [comment 6597893509](https://github.com/mastermindx-market-intelligence/macro/pull/10645#issuecomment-6597893509), based on its [packet at a5e4e86092a447a8f4c2e1ecc930b076e106bdac](https://github.com/mastermindx-market-intelligence/macro/tree/a5e4e86092a447a8f4c2e1ecc930b076e106bdac/research/design_candidates/production_design_20261102/d02). D08 delivered [comment 6597852782](https://github.com/mastermindx-market-intelligence/macro/pull/10645#issuecomment-6597852782) and its [source conformance return at e89f527e3267b1d1dd27ac7507e9a25983c0c903](https://github.com/mastermindx-market-intelligence/macro/blob/e89f527e3267b1d1dd27ac7507e9a25983c0c903/research/design_candidates/production_design_20261102/d08/CONFORMANCE_REVIEW_20261103.md). Both compared F01's older candidate.1 at `b2d00ddc7e2dfbffdc3c5855e1a4dffe8c4226a5` with F02's handshake at `f7c25c4b9870cff260c2a4b998be18d6c04d36d0`.

Those findings were correct for those inputs. F01 subsequently accepted the F02 clarifications in **candidate.2 at `245a7d2cd62d88fb6d2ee3863f9d26c63052d8e7`**. Candidates.3 and.4 preserve them. This supersedes only the listed candidate.1 dimensions and ambiguity; it does not supersede either author's native-effect hold, independent findings or consumer qualification.

| Consumer concern | Source resolution | Discriminating value |
| --- | --- | --- |
| 600 versus 768 gutter cutoff | 16px each at <=600; 20px each above 600 and below 1200; 24px each at >=1200 | At 640, useful content600; at 700,660; at 600.5,560.5 |
| 400 versus440 modal pane | 440px at represented768/1024, constrained to viewport; full width with internal padding at <=600 | Revised D now measures440 in the six-board be157007 freeze; static anatomy is not runtime modal qualification |
| Fractional rail gaps | No rail at <=860;196px expanded above 860 and below 1200;224px at >=1200 | At 860.5 useful content624.5; at 1199.5,963.5; at 1200,928 |
| Dock threshold | Measure actual usable content after shell and reserved local chrome; require320+24+at least640 | Expanded first eligible1256; explicit compact1096 under these gutters; larger domain minimum still controls |
| Focus during resize | Preserve one evidence identity; reconcile modal/inert/scroll ownership on mode change | N10/N11 and G07 remain NOT_RUN; source concurrence is not behavior proof |

Current joint source: [F01-F02-SHELL/1.0.0-candidate.4](JOINT_SHELL_SYSTEM_CONTRACT.md), bound by this document's enclosing immutable commit. F02's unchanged token blob and candidate.2 concurrence remain in that record. Later compact/chart/layer changes and candidate.4's focused-reader/Brain/focus/return clauses await scoped owner concurrence. Consumers may use unchanged geometry for source mapping, retention, candidate composition analysis, test specification and build planning while retaining their existing holds. Neither the old400px/768px input nor the new version is a released foundation.

## 2. D02 local navigation inside the existing shell slot

The D02 [product specification](https://github.com/mastermindx-market-intelligence/macro/blob/a5e4e86092a447a8f4c2e1ecc930b076e106bdac/research/design_candidates/production_design_20261102/d02/PRODUCT_UX_SPEC.md) retains Macro Command's exact order: **Overview, Money, Policy, Rates, Inflation, Growth, Jobs, Housing, Consumers, Borrowing costs, Government debt, Trade**. Money retains liquidity/central-bank views; Growth retains economy/business; Borrowing costs retains borrowing/funding. This is distinct from the suite Current / Drivers / History now drawn in revised F01 A/H/E. Neither set substitutes for the other.

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

D02 owns `body.page-macro`; D03 retains `body.page-stocks` and its complete S&P1500 board. F01's five-row illustrative breadth example does not certify either universe or full coverage. Selected-direction native A/H/E must either show the complete owner-provided set or disclose the subset, selection rule and route to the complete set. Session missingness, sector coverage and advancing-sector denominator are separate facts. No invented observations or dates may fill the missing specimen rows.

The historical `/macro/<id>.html` family resolves in D02 source to eleven **fetch-only inner fragments** under `/macro/fragments/`. F03 owns the registry/export correction. Preserve this distinction; neither the F01 directory proposal nor a display label admits those assets as standalone public documents. Existing internal404/access boundaries remain intact.

## 4. D08 consumer boundary

D08's conformance return uses the same Terminal source pin as F01 for the fifteen native panes and aliases. Its passing function/source and arithmetic checks are attributed to D08's detached specimen; F01 did not execute them and they are not browser/RIG acceptance. D08's source intentionally uses the earlier F01400px/768px proposal provisionally and needs to consume the resolution above through its existing author. No other D08 semantic contract, slice launch or ownership changes.

Retain D08's exact observation/return identity, inferred-side labeling, separate native panes and Futures/replay destinations, full source-owned table/export scope, and source/date/access limits. A selected strike/aggregate coordinate is not automatically a uniquely identified contract or a Plan leg. Save remains with the native Investigation/D23 owner. The earlier D08 safety-refused Paper operation remains held and is not retried, delegated or cured by this F01 source return.

## 5. Supplemental consumer acceptance cases — NOT_RUN

These six cases supplement the 79 earlier specifications, for **85 cases at that earlier checkpoint**; candidate.4 adds C10 for **86 current unique cases**. They bind the new attributed consumer inputs without altering the agreed shell dimensions or claiming source/visual acceptance.

| ID | Setup/action | Required evidence / owner |
| --- | --- | --- |
| M01 | All twelve Command sections and actual subtabs at 320/390/700/1024, EN/ZH; switch from a late section after resize | Same fixed order, selected label and complete reachability in the local slot;44px important controls; no global-drawer substitution. F01 slot/D02 content/F02 anatomy |
| M02 | Enter `#money/central_banks`, switch to `#credit/funding`, traverse history, then open a hidden suite `#history` anchor during delayed loading | Existing hash/replace semantics; correct fragment/panel before anchor resolution; one scroller; preserved focus and no jump to the wrong section. D02 parser/host integration |
| M03 | From Command evidence, invoke contextual Analyst, close through its real owner, then reopen evidence at the same section and subtab | Same singleton and qualified contextual payload; no doubled dock/modal or guessed lifecycle event; existing Brain/D14/host lifecycle prerequisite remains explicit; D06 retains its separate focused variant |
| M04 | Display an unavailable raw100 record, a rights-blocked source, a US-only workspace under attempted regional navigation, and false save-service flags | Typed refusal/coverage and actual market remain truthful; no fabricated score, new region, entitlement or save success. D02/D23 retain decisions |
| M05 | Compare consumer geometry at 640/700/600.5/860.5/1199.5 and 1024 overlay | Current candidate uses600/660/560.5/624.5/963.5 useful widths respectively,440px overlay at 1024; actual host insets measured separately. Historical400px/768px specimen does not count as current conformance |
| M06 | Review complete breadth subset and source-clock disclosure; inspect served viewport metadata and actual400%/mobile zoom behavior | Explain shown/total sector scope and comparison dates without invented values; retain magnification and all actions. D02's `maximum-scale=1`/`user-scalable=no` observation is an attributed source concern, not an executed F01 conformance failure |

Exact input blobs are in [CONSUMER_INPUT_RECEIPTS.json](evidence/source/CONSUMER_INPUT_RECEIPTS.json). The existing owners' reports are preserved at their pins; this note corrects only the consumer view of F01's current source and carries concrete retained obligations into its build/re-audit package.

## 6. D06 focused Terminal and Brain — exact consumer handoff

The existing D06 carrier is [Draft #10655](https://github.com/mastermindx-market-intelligence/macro/pull/10655), latest consumed source **d7d6b7ddcd950d7e9879bbf58c7e2e481b4708bf**. Its [Brain/shell handshake](https://github.com/mastermindx-market-intelligence/macro/blob/d7d6b7ddcd950d7e9879bbf58c7e2e481b4708bf/research/design_candidates/production_design_20261102/d06/BRAIN_SHELL_HANDSHAKE.md), [responsive audit](https://github.com/mastermindx-market-intelligence/macro/blob/d7d6b7ddcd950d7e9879bbf58c7e2e481b4708bf/research/design_candidates/production_design_20261102/d06/RESPONSIVE_AND_STATE_AUDIT.md) and [source delta](https://github.com/mastermindx-market-intelligence/macro/blob/d7d6b7ddcd950d7e9879bbf58c7e2e481b4708bf/research/design_candidates/production_design_20261102/d06/SOURCE_DELTA_20261103.md) are attributed consumer evidence. Root separately inspected relevant widget, rail and current shared-search source. D06's36 beta captures,75 specified-not-executed migration cases and16 retained Paper references are D06's records; F01 did not reproduce those observations.

The [independent nonauthor source-only review by mastermindxryan](https://github.com/mastermindx-market-intelligence/macro/pull/10655#pullrequestreview-5759912725) applies to the prior **61d6762cdd417b00aae879bd411a8bb20c50ff63** set and its71 cases. It does not approve later changed semantic artifacts, F01, native layout, QA01/RIG, Paper access, implementation or production. Its explicit scope/hold remains intact.

| Consumer issue | Candidate.4 resolution | Outstanding qualification |
| --- | --- | --- |
| Shared320+24 versus Terminal reader | Keep Terminal360 initial/300–520 requested width and incumbent mm.railW. Ordinary/native/tray/dossier/focus variants remain distinct | D06/Terminal/Options owners qualify effective fit without overwriting requested width;640px proposed price plot is not F01 primary-container math |
| Brain close and visible lifecycle | Actual Macro widget exposes close; typed Terminal interface is narrower. onClose is conditional focus restoration; ready/mounted/call success is not visible-state acknowledgment | Existing Brain/D14 and host owners bind actual served asset, callback lifetime, all close paths and failure/stale-owner behavior |
| Competing evidence and Brain | Proposed shared-shell suspension leaves evidence reachable; explicit reopen revalidates identity and access; no forced reopen | F02 shared-layer concurrence and existing-owner lifecycle proof. Focused Terminal is not automatically enrolled |
| Focus and Escape | Restore only when the closing/removed surface legitimately owns focus; no stealing later intent. Preserve nested Brain and chart priorities | D06's observed BODY/second-Escape discrepancies remain; current baseline is not target acceptance |
| Reader identity/history | Hover and Previous/Next share one current inspection cursor; Latest/invalidation have real owner semantics | No new pin/store. Exact historical Ask separately validates instrument/interval/bar/time basis/generation through Terminal/D14 |
| Return destination | Preserve accepted safe origin and named return versus browser Back; one observed Analysis roundtrip proves its href only | Full selection/scroll/focus restoration and all entry variants remain unqualified; symbol-only arrival can retain an older accepted origin |
| Company search current source | F01 read2ded360 ShellSearch/SymbolPicker/SearchModal/companySearchContext; preview/commit and company_query are retained | D07/Search owns listing/preview; Terminal owns accepted entry/return. End-to-end parity is unproved |

**Existing-owner next actions:** F02 responds to candidate.4's unchanged-versus-new clause table and shared focus/component semantics; D06 responds to its focused-reader exception, cursor correction and composition requirements; the existing Brain/D14/Terminal host owner qualifies lifecycle/context seams. These are scoped source/interface acknowledgments, not requests to implement, create another session, claim canvas access or waive a hold. D02/D08 can update their source mappings to the unchanged600/440/continuous geometry now, preserving their own effects and independent qualification.

The independent architecture advice is preserved in [F01_CONSUMER_CONTRACT_ADVISORY_20261103.md](evidence/review/F01_CONSUMER_CONTRACT_ADVISORY_20261103.md). It preceded D06's later explicit single-cursor correction; this current source adopts that correction instead of treating the earlier “committed versus hover” wording as an existing product contract. The advisory grants no ownership, admission or approval.
