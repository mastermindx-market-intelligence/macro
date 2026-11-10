# Integration note

Root adopted the scope-recovery gate, exact family mapping and per-slice consumer proof. Subsequent source self-check corrected B04 to new-case revision 1, assigned V03/U02 to Plan and F03/F04/V04/OA-1C/OA-3 to prospective lineage, made the Plan→Watch edge conditional, and restored Pilot.P4’s residual log total-return wording. These corrections are incorporated in 04/05; the original review text below is retained as dated evidence. This appendix is an assigned reasoning review, not a formal GitHub approval or new release gate. The current consolidated decisions are in [04](../04_ARCHITECTURE_HARDENING.md), [05](../05_IMPLEMENTATION_MASTERPLAN.md) and [06](../06_FUTURE_ROUNDS.md).

---

# Options rounds 3–4 — acceptance and architecture review

**Review date:** 2026-11-10 UTC. **Reviewer:** `/root/options_acceptance_review`, an assigned, read-only native reasoning child. **Parent:** `/root`. **Scope:** inherited acceptance, design/source coverage, useful release sequencing, and custody boundaries. No application, Paper, remote source, runtime, worker, or release mutations were performed. The only writes are this review and its two companion analysis artifacts.

## 1. Decisive ruling

**The recovered architecture is a sound round-4 baseline, with explicit dispatch and acceptance gates.** It correctly preserves one programme, existing owners, distinct evidence/claim classes, immutable case revisions, and useful degraded states. The Paper candidate does not falsely call screenshots production transactions. Retain those decisions.

**It is not yet a row-complete whole-suite or full-parity implementation commission.** The original October 21 packet's 104 OPT task definitions and 130 OPR requirement rows have not been recovered. Their existence, counts, grouping and adoption are documented; their individual row text and full disposition are not. The final masterplan can be declared complete as an architecture baseline if it explicitly records this boundary, makes actual packet recovery the first Round 5 action, and gates any whole-programme/parity acceptance or unqualified packet-wide fanout. Independently bounded work whose original scope and dependencies have been recovered need not wait for unrelated missing rows.

The requested corrections are specific: add the attached qualified traceability projection, update held Plan/Matrix work from current source facts, distinguish case review from session review, explicitly bind retained deep surfaces, and put real consumer proof on each release slice. A second task hierarchy, persistence layer, review database, source cache, queue, or model authority is neither required nor justified.

## 2. Exact source identity and review limits

| Source | Pin / identity | Review use |
|---|---|---|
| Governing Mastermind | `9e6659c4a49ee6f11a6f6ee690d222ce81d67b09` | Compatible `mastermind.sol_skillpack.v1`, version 1.0.1, minimum bootstrap 1; same-pin review, reliability, reuse-first and session-review guidance read. No new admission or release authority inferred. |
| Candidate Macro PR | #10898, `626715ab73e3a0f9413c69faabd8a2a5030227de` | Parent-supplied canonical candidate identity. Local `01_MASTERPLAN.md`, `02_PAPER_DESIGN.md`, and `03_PAPER_MANIFEST.json` are the review inputs. |
| Original broad census | Macro `9a13c64bf69f782332afa29efb09fe48ee30b857`; Terminal `1c0bf028cf72539a4d3fcb17fa137ee474d764f9` | Original task, AC, research, supersession and Lab evidence. Their old statuses are dated observations, not fresh runtime verdicts. |
| Round-2 affected source read | Terminal `2fe2f02f07d1df8c855388bc556383cd74de44fd` | Original Paper build boundaries for Flow aggregates, Plan drafts, Investigation and receipts. |
| Current Terminal acceptance-document reread | `26c800c265d2cc627098955d186ddc8ef2886960` | Directly fetched `docs/OPTIONS_R1_PROGRAM.md` and `docs/OPTIONS_R2_ACCEPTANCE_COVERAGE_2026-10-22.md`; text matches the provided archive apart from one added final newline. Historical R2 proof remains explicitly pending in that document. |
| Canonical continuation | Macro `2aec75a534c26522642bd5dd432802760f5fdcfc`, `research/OPTIONS_INTELLIGENCE_CONTINUATION_HANDOFF_2026-10-11.md` | Direct read of exact D86 packet attestation and surrounding context. Original packet itself not recovered. |
| Current #804 delta | Held source head `27df56d997df0ae94a17b6b8e2d14867431bb394` | Parent's fresh source finding: v3 optional `option_plan`, admission, explicit New/Add/Save/reopen, exact-revision reader, `OptionsPlanResearchBridge` and `OptionsPlanSavedRevisionControl` already exist. This child does not recertify that diff or runtime acceptance. |

The local review inputs are bound by SHA-256 in `acceptance-coverage-gaps.json`. This review did not run product tests, inspect a signed-in production browser, reread live Paper nodes, establish current worker liveness, or lift any hold. Current source claims supplied by the parent remain distinguishable from this child's direct reads.

## 3. Complete requirement-family inventory

Counts below have different units. **Do not sum them into a completion percentage.** An execution task can serve several product assertions and historical commitments; a historical claim can preserve accepted work rather than commission new work.

| Family | Exact recovered count / IDs | Canonical source and meaning |
|---|---|---|
| Execution hierarchy | **35 rows:** G00–G01 (2), D01–D04 (4), F01–F04 (4), M01–M04 (4), V01–V04 (4), Q01–Q05 (5), N01–N03 (3), U01–U04 (4), R01–R05 (5). C00 remains the programme parent, not a 36th row in this table. | Macro `research/options_intelligence/2026-10-11-fable-completion/FABLE_EXECUTION_MASTERPLAN.md`, §5, at the broad census pin. October 31 amendment §5 maps later obligations back to these IDs. |
| Original OPT packet | **104 original tasks**, attested group ranges: 001–010 G; 011–025 D; 026–040 X; 041–053 M; 054–067 V; 068–082 P; 083–094 Q; 095–104 R. Later suffixes such as OPT-002a/002b are retained continuations, not permission to renumber the original 104. | Exact D86 attestation at the continuation pin. Original individual task text is unrecovered; no 104 fabricated CSV rows are supplied. Known later OPT references remain in AC/SUP evidence. |
| AC matrix | **60 exact assertions, AC01–AC60.** | Macro `research/options_intelligence/2026-10-31-fable-amendment/09_ACCEPTANCE_MATRIX.csv`, broad census pin. Contains capability, required witness, falsifier, source refs and original owner references. |
| R1 | W0 setup; **W1–W5 waves**, with named leaves W1A/B/C, W2A/B/C, W3A/B/C, W4A/B/C and W5—13 named implementation/proof leaves when grouped rows are expanded. The separate Design row is not an extra acceptance task. | Terminal `docs/OPTIONS_R1_PROGRAM.md`, current reread pin. Outcome is Sector Central → holding → expiry/strike → chart → matched change → save → watch → review, through release and live proof. Old wave-table labels must be read with later checkpoints and receipts. |
| R2 | **76 product requirements, P01–P76.** Grouped rows expanded without changing their original text. | Terminal `docs/OPTIONS_R2_ACCEPTANCE_COVERAGE_2026-10-22.md`, current reread pin. It explicitly retains `SPECIFIED_NOT_PRODUCTION_ACCEPTED` until authenticated P76 evidence. A passing P76 cannot create the held producers or discharge P74/P75 by itself. |
| Competitor/product requirements | **130 OPR requirements:** 112 competitor-referenced + 18 product; 11 competitor entries, all historically `NOT_ACCEPTED_AS_FULL_PARITY`. | D86 packet attestation and October 31 `04_RESEARCH_AND_VALIDATION.md`. **Exact OPR ID set and row text are unrecovered.** Do not assume a sequential OPR-001…130 ID scheme or invent requirements from competitor names. |
| Supersession | **123 rows:** numeric IDs 1–119 plus 59b, 59c, 66b and 73b. | Macro `research/options_estate/OPTIONS_SUPERSESSION_REGISTER_2026-10.md`, broad census pin. Historical rulings and retained commitments, not 123 new build tasks. |
| Scientific pilots | **Six pilots, P1–P6**, mapped through Q02–Q04 and AC27–AC35; Q01 and Q05 keep their separate method/held-family roles. | October 31 `04_RESEARCH_AND_VALIDATION.md`, original pilot records, and the masterplan §5.4. Registered targets, losses, horizons, blocks, costs and stage gates remain separate. |
| Research Lab | **Five connected lenses:** Chain, Volatility, Replay, Packages and Scenarios, under U03 and the original Lab programme. | Terminal `docs/options-research-lab/IMPLEMENTATION.md`, broad census pin, explicitly `MISSION_COMPLETE: false`. Positive qualified use cases are required, not merely five tabs or five unavailable messages. Original A–G programme obligations are inherited and must remain in the parent's full graph. |
| Paper candidate | **34 boards and 44 local state specimens:** 10 Product, 16 Responsive, 4 State atlases, 4 Build boards; state groups E01–E12, P01–P12, W01–W12, A01–A08. | Exact nodes in `03_PAPER_MANIFEST.json`; candidate design evidence only. Original 245-board inventory remains retained. |

### Namespace rule

Preserve original IDs and qualify their namespace in every crosswalk. `R2.P09` is calendar charm; `Paper.S02/P09` is the leave-draft state; the original frozen-enrollment owner P09/#1182 is a different operation; `Pilot.P1` is a research study. Likewise, R1.W3 is not a Paper watch-state ID, and R2 session Review is not the case-assessment workspace. These are disambiguating references, not new runtime identifiers or a replacement task system.

### Supersession dispositions actually recovered

| Historical status | Count | Required treatment |
|---|---:|---|
| ACCEPTED_DO_NOT_REDO | 75 | Reuse scoped receipt/ruling; reopen only for a material invalidator. |
| HELD | 17 | Preserve original holder, scope and release condition. |
| SUPERSEDED_OBSOLETE | 17 | Do not rebuild the obsolete claim; preserve any explicitly retained remainder. |
| RETAINED_OPEN | 13 | Carry original commitment and owner/custody dependency forward. |
| UNKNOWN | 1 | Row 116 remains testimony pending its original runtime receipt. |
| CONFLICT | 0 | Do not resurrect resolved conflicts without new evidence. |

These counts describe the October 22 repaired register. For example, a later accepted Statistics consumer may supersede a dated claim that Statistics is unbuilt; the old row remains provenance and its particular remainder must be adjudicated against that later receipt. Do not refresh 123 statuses by inference from a new masterplan.

## 4. Corrections required in the round-4 baseline

### A. Scope recovery is a dispatch gate, not a fabricated completion claim

The current masterplan §12 and §13 correctly promises a complete inherited crosswalk, but the recovered originals do not yet support that claim for OPT/OPR. Record the gap explicitly. The exact packet is `TERMINAL_OPTIONS_FABLE_MASTERPLAN_PACKET_2026-10-21.zip`, **189,700 bytes**, SHA-256 prefix **`f08759dc8755000d`**; the full digest is not known from the inspected attestation. D86 reports `SHA256SUMS.txt ALL_OK` historically, not a new verification by this review.

Provided scratch files, their pinned source links, D86 and its surrounding context, bounded GitHub searches, and the parent's reported Library search did not recover the packet. No exact Downloads/archive/extracted-packet path or delivery URL was found in the inspected D86 context. This is an absence within those bounds, not proof that the packet is globally unavailable. Recover original bytes through known authorized provenance in Round 5; do not replay the historical refused census or perform a speculative host scan.

**Smallest repair:** make the final plan an explicitly bounded architecture baseline, attach the gap record, and require original-row reconciliation before a claim of full parity or an unqualified whole-packet implementation commission. Existing recovered slices can continue on their established scope.

### B. Update #804 and Matrix from current evidence; do not commission duplicate implementations

Round-2 Paper §5.2 and §8.3 describes the protected-master host at its dated pin as preparation-only. The parent has now read the held #804 head and found the actual v3 optional `option_plan`, admission, bridge, saved-revision controls and exact-revision reader. The round-4 work item must therefore be **compose, qualify and release the incumbent bridge when its original hold permits**, not build a new draft/Plan persistence adapter. Keep main-source availability, held-branch implementation, migration state, installation and live acceptance as separate fields.

Similarly, the parent reports a current Matrix reference adapter on main while #10866's source publisher remains pending. Missing publisher proof does not mean the adapter should be rebuilt. #10866 has both merge-intent and blocking labels; that is not release permission.

**Smallest repair:** replace generic “implementation missing” tasks with exact integration/proof deltas, link the held heads and source paths the parent verified, and preserve the hold. Existing code is a reuse input, not an acceptance receipt.

### C. An alias map does not prove deep-feature design or usability

The six-destination shell preserves the fifteen existing view keys and other entry points. That is necessary and valuable. It does not by itself upgrade or validate every retained deep surface. The new 34-board set emphasizes the principal SPY case; it does not contain complete new designs for Tide, 0DTE, Largest, Flow Surface, screener, ticker scan, Positioning, Levels, Structure, Statistics, all Prophet lanes, R2 quad/scanner/replay/session review, all Lab lenses, Futures or IEX replay.

**Smallest repair:** each retained feature receives an exact original board/source binding and one of: reuse without semantic change, adapt to shared shell, new design required, or explicitly held with owner/gate. Retained designs can be reused; there is no need to redraw 245 boards. But a general “More views” route is not evidence that these jobs remain discoverable, understandable or complete.

### D. Preserve distinct review, comparison and scenario meanings

O08 is an immutable **case assessment** after a supported condition firing. It does not satisfy R2 P59/P60's **session review**, completeness and open-to-close level journey. O10 compares matched books; O09 compares authored expiry assumptions. O07's deterministic expiry payoff does not satisfy P10/P69's local-linear exposure scenario, nor a pre-expiry valuation or prospective option outcome.

**Smallest repair:** bind each named action to its existing owner and exact domain. No universal Review object, global scenario model or common replay cursor should replace these different contracts.

### E. Degraded states preserve usefulness; they do not close promised positive cases

Paper E01 correctly leaves a useful aggregate when source children are absent; E09 preserves a saved reference when the original source cannot resolve; A06 keeps an exact table when 3D cannot render. These are required negative-path designs. They do not establish the requested child-print capability, durable original-book resolution, same-data 3D path, or U03's five positively qualified lenses.

**Smallest repair:** require both the admitted positive case and each relevant refusal/recovery case in the acceptance row. A held predictive family can remain unqualified without blocking descriptive work, but remains an inherited scientific obligation unless the decision owner revises scope.

### F. Put real consumer proof on every useful release

The masterplan's staged implementation table should not leave all production evidence to its final phase. Each independently useful slice must bind its source/build/migration/artifact identity to an authenticated consumer result and its material negative cases. R2 P76, P74 performance and P75 science are separate. Existing historical sign-in language identifies the missing proof, not a permanent human dependency if a currently authorized authenticated path is available.

**Smallest repair:** make per-slice release/consumer proof an exit edge, reuse existing scoped receipts where still valid, and keep final whole-suite acceptance as a separate reconciliation of outstanding obligations.

## 5. Family coverage and missing-proof map

| Existing family | Paper / current implementation contribution | Remaining discriminating proof |
|---|---|---|
| G00–G01; AC01–05 | B01/B02 preserve programme and owner mapping. | Actual current custody/effects and any explicitly required admitted hierarchy start/return. Design/docs and a native reviewer do not prove the original hierarchy. |
| D01–D04; AC06–14 | Source-state patterns, truthful aggregate/known-subtotal displays; accepted natural Flow/Statistics scope retained. | Natural source→artifact→API→admitted consumer for changed path; exact availability/clocks, qualified premium/units, configured-to-displayed coverage, measured latency, retention/readback/corrupt/interrupted-write controls. |
| F01–F02; AC15–19 | O02, E01/E02/E03 and W12; existing aggregate projector/transport retained. | Typed child records and quote classification where promised; parent-child reconciliation; corrections; package completeness; measured-versus-proxy proof; original #6867 timing and all three transport planes under canonical session/calendar rules. |
| F03–F04/V04; AC20–24 | O05 maturity and inactivity presentation. | Original #9677 correction and #9682 expression lineage; lawful future activation; first eligible formation before outcome; prospective exact quote entry/exit and all attrition. No reuse of underlying success as option P&L. |
| M01–M04; AC51; R2 P06–24/P69 | O03/O10 and retained numerical reducers; new matched-subtotal case is coherent. | Actual selected model/domain/sign/units; alternative assumed books; local-linear versus repriced scenarios; finite attribution/residual controls. Endpoint hedge notional is not dealer inventory, turnover or price impact. |
| V01–V03; AC40/46–49 | O04/T01/M11; O07/O09; existing numerical payoff; held #804 bridge is a reuse input. | Exact-expiry/constant-tenor conventions, qualified model/fit and independent clocks; current admitted SPY/QQQ payoff domain; source-term identity; exact retained-reference installation and save/reopen; no unsupported fees/exercise/pre-expiry claims. |
| N01–N03 | 0DTE route retained; no complete new near-expiry workspace. | Natural near-expiry usefulness, source latency and exact last-trade/fixing clocks, half days/DST/AM–PM, deduplicated lifecycle and matching forecast horizon if any. |
| Q01–Q05; AC25–36 | O05/E11 distinguish accruing/inactive/unqualified. | Reuse concluded methods review; six pilot-specific causal cohorts and staged seals; actual study outcomes, costs, uncertainty and negative results; held dealer families stay independently gated. |
| U01–U02; AC37–49 | Principal case, explicit root-only handoff, Plan/Compare, saved revision and immutable assessment. | Real origin/selection/return under refresh; exact original/latest/comparable source distinctions; original operation reconciliation, CAS and account withdrawal; v3 Plan bridge integration on #804, not a new case store. |
| U03 | T02 and original Lab references; raw Chain/IV implementation exists in historical source. | Five connected **positive qualified** Chain/Volatility/Replay/Packages/Scenarios use cases. Source admission, retention and independently usable exact table must be real, not tabs around placeholders. |
| U04/R1 W5; AC53–55; R2 P72/P74/P76 | Representative EN/ZH desktop/tablet/phone and 44 state specimens. | Actual supported-browser interaction, both themes/languages, keyboard/touch/zoom, chart alternatives, source-bound performance and installed authenticated journeys. Font assignment and board counts cannot establish these. |
| R01–R04/C00 | B03 and source-bound acceptance plan. | Current applicable checks/review/release rules, migration and deployment identity, natural complete consumer, operational health and rollback on each slice. No blanket extra reviewer requirement beyond current governing policy/real controls. |
| R05; AC56 | Original context-audit successor preserved. | Original v2 charter/benchmark/limits/acceptance; no v1 cap widening, failed-census replay or invented successor control plane. |
| R1 W1/W2 | Accepted Sector→Exposure/chart/Back and Exposure Save/reopen receipts remain useful. | Preserve original roster/origin and relative-trend/holdings semantics. New Flow origin cannot replace the inherited Sector-origin journey. Changed paths need bounded regression; accepted unchanged work is not rebuilt. |
| R1 W3/W4 | Comparable volatility, watch/review and replay/scenario obligations remain. | Applied 0040 is not full live W3 acceptance; selected-event review and exact receipt/assessment path still need actual proof. W4C scientific gates remain separate. |
| R2 entire set | Incumbent shell/reducers/replay/scenario/surface/scan work plus selected new designs. | All 76 rows retain their own witness. P76 authenticated journey does not erase any producer or model dependency. |
| OPR/OPT | Counts/adoption and known later references recovered. | Original row texts and exact OPR IDs must be recovered and reconciled before whole-packet dispatch/full parity claims. |
| 123-claim register | Existing accepted, superseded, held and open rulings retained. | Current changes only for material later evidence; row 116 unknown and unassigned retained commitments must not be auto-closed. |

### R2 dependencies that must remain explicit

There are **15 explicitly HELD product requirements** in the current document: P17 velocity; P25 level-crossing alerts; P29 annual reference; P30–P31 intraday range cone/model explanation; P39 path to node; P48 scheduled open/close scans; P61 next-session setup; P62 sharing/export; P63–P67 bot delivery; P75 calibrated claims. P74 is separately partial/unprofiled and P76 is separately pending authenticated proof. All other mappings remain source/specification evidence in that ledger, not an automatic production-accepted set.

Existing Flow CSV controls do not automatically satisfy P62's rights-aware image/link sharing. A five-minute supported price watch does not satisfy P25's exposure level-crossing contract. A matched two-book delta does not satisfy P17's irregular-time velocity. These are useful concrete falsifiers for task packets.

## 6. Recommended vertical release sequence

These are ordering labels for the existing task graph, not new issue IDs, permanent roles or lifecycle records. Source, custody and effect checks apply only to the next affected edge. Independent scientific and descriptive lanes can progress in parallel.

| Useful release | Existing tasks/assertions | Dependency and exact user result | Exit witness |
|---|---|---|---|
| **Observed investigation and return** | U01/U02/U03; R1 W1/W2/W3; AC37–44 | Reuse current aggregate Flow, qualified independent Exposure, accepted Exposure Save and supported watch/review owners. Child-detail absence uses E01; held exact Plan save need not block this slice. | User enters from Sector or Flow with correct transfer scope, inspects, saves exact supported evidence, reopens, arms supported condition, returns to an exact firing, and saves an explicit assessment revision; all source/effect/account failures remain truthful. |
| **Exact Plan and comparison continuity** | V03/U02; AC42–49 | Integrate the existing #804 v3 bridge and retained-reference/admission/history work on its original held carrier. Reuse current deterministic expiry engine. | Real admitted exact legs with authored assumptions calculate and compare, then save/reopen the exact revision; lost response, committed-but-unreadable, conflict and withdrawal prove one original operation. |
| **Exposure, retained Matrix and deep Lab** | D03/M/U03; AC52; R2 relevant map/scan/replay/surface/session-review rows | Existing Matrix adapter plus qualified source publisher/retention and original Research Lab owners; distinguish each temporal grammar. | Real qualified books, frozen scan/drill, retained replay/session review and connected Lab lenses; same data in table/2D/3D; 13k-contract/resource profile and authenticated R2 consumer evidence. |
| **Flow evidence depth and natural operation** | D01/D02/D04/F01/F02/N01; AC06–19 | Extend incumbent Flow publisher/API with child evidence only when actual source supplies it; complete original timing/transport repairs. | Aggregate and children reconcile; valid quote clocks/classification and unknown reasons; correction/package/withdrawal behavior; natural cadence and three-plane producer-to-browser proof. |
| **Volatility, mechanics and near-expiry depth** | V01/V02/M01–M04/N01–N03; AC40/51 | Qualified model, terms, calendar/fixing and source clocks; reuse accepted reducers and engines. | User can compare exact expiry/tenor and supported scenario assumptions, inspect limitations and uncertainty, and finish a useful natural near-expiry workflow within actual freshness. |
| **Prospective candidate and exact outcome** | F03/F04/V04; AC20–24 | Original correction + lawful activation + frozen first expression + prospective quote capture. | Candidate lineage and complete eligible/abstained/unavailable/matured denominator; actual scoped quote-ruler outcome, never implied fill or portfolio return. |
| **Scientific qualification and broader parity** | Q01–Q05/R05; AC25–36/56; R2 held requirements; recovered OPT/OPR | Original empirical/preregistration/rights/held-source gates and recovered scope. Observation accrual cannot be replaced by more workers or chat rounds. | Pilot-specific and family-specific tests/uncertainty/claim decisions; real additional producer/consumer proofs; row-complete adjudication through existing owners. |

Every row carries its own R01–R04 release/proof edge. Final C00/AC60 closeout reconciles all inherited obligations, retained exceptions and explicit scope decisions; it is not “the new case path works, therefore all Options is finished.”

## 7. Concrete remaining state and proof obligations

1. **Selection/epoch:** prove wrong-root, wrong-account, expired entitlement, changed revision and late response invalidation before display. Return must restore row/filter/scroll/focus or explain withdrawal without selecting a neighbor.
2. **Source identity and clocks:** original, latest and comparable reads remain distinct; unknown first availability stays unknown; request/firing/build clocks cannot replace price/source clocks. Correction must not silently mutate the original saved baseline.
3. **Flow detail:** absent child records do not become six synthetic production observations. Estimated buy/sell coverage is not an at-ask premium partition. Qualified quote classifications need source clocks/method and reasons for unknowns; package and opening intent stay separate.
4. **Plan and save:** retain distinct 64-character Investigation horizon and 160-codepoint Plan research horizon through the actual v3 mapping. No silent truncation. Reconcile same operation on response loss, and retry only readback when commit is known. Do not add an independent draft store.
5. **Review:** freeze chosen firing before assessment; a later firing offers explicit switch. Readable outbox status is one of pending/deferred/sent/failed/suppressed; missing status is malformed, not an ordinary nullable state. The pending specimen covers one valid state, not all delivery outcomes. Trigger-stamp fallback has no invented exact firing ID.
6. **Text validation:** resolve codepoint versus native `maxLength` counting and preserve-input behavior for over-limit review notes. Paper A08 is a target; it does not prove the input currently accepts/displays the intended over-limit state.
7. **Usability at depth:** bind full controls and empty/error/help behavior for each retained specialized view, not only its navigation label. Cold readers must distinguish what was observed, modeled, authored and scientifically unqualified while reaching the detailed evidence quickly.
8. **Performance/accessibility:** use original meaningful targets and relevant source-bound populations; actual focus, table alternatives, zoom, touch and long-session/resource behavior. Reuse unchanged accepted evidence; do not repeat broad suites merely to increase a verification count.
9. **Research/sleeves:** two accruing Flow research books, eight broader Prophet taxonomy families, an exact option expression, a candidate and a live portfolio are different objects. Preserve independent formation/sample/outcome/maturity/authority fields; do not add a frontend composite confidence or infer trading authority from a user selection.

## 8. Custody, holds and accepted-work fences

| Boundary | Preserve in every affected packet |
|---|---|
| #804 | Source bridge exists on held head; parent reports release-hold receipt `5989604142` and Draft state. No duplicate persistence, silent host mounting, hold removal or source merge→live inference. |
| #10866 | Existing Matrix adapter/source publisher frontier, original writer, pending source/consumer proof. Merge-intent label does not erase `merge-blocked`. |
| #1248 / #1243 and Exposure shared paths | Refresh only current affected custody before overlapping workspace, Surface/Tape or ladder edits. Old author/idle age is not active liveness or release evidence. |
| #6867 | Source release described to original controller is distinct from broader producer/publication/browser proof. Preserve its remaining live acceptance obligations. |
| #9677 / #9682 | Campaign correction and frozen expression remain on original carriers. Source preparation is not lawful candidate activation or prospective outcome acceptance. |
| #8191 and historical failed census | Explicit verification-denial/retry fences remain; no cross-host/tool/provider replay. Packet recovery or a new plan cannot reset them. |
| #9808 | Original uncertain installer effect requires original-operation terminal evidence. A later matching/superseding install does not reconcile it. |
| AC50 / original P09 / #1182 | Separate dormant frozen-enrollment operation. Require exact original attempt pin and qualified terminal envelope; current runtime equality is insufficient. |
| #7328 / #8555 | Exposure Outlook/dealer predictive claims remain independently held or proposed; archival merge supplies no empirical promotion. |
| #8385 / #10390 | Reuse concluded method review/archive and accepted engineering design; neither supplies fitted calibration, empirical seals or final test outcomes. No redundant review commission absent invalidator. |
| D08D `p-2-0 / 1N2L-0`; adjacent #804 and company targets | Original Paper/custody holds unchanged. Design presence does not authorize a denied mutation or temporal-source replacement. |
| Applied migrations and accepted W1/W2 | Reuse scoped original receipts and source references. Do not rerun migrations or erase accepted Exposure Save because Exact Plan remains held. |
| Source-use permissions | Per-source/per-requested-use allow/deny/unavailable through current owner; do not invent a blanket license gate or expand private-use rights to export/bot redistribution. |

The earlier masterplan already preserves many of these correctly. The round-4 graph should carry them as dependencies/holds on the original actions, not recreate them as new tickets or blanket gates across independent work.

## 9. Roadmap for additional rounds

| Round | Focus and concrete output | Completion boundary |
|---|---|---|
| **5 — Recover and reconcile full inherited scope** | Recover the exact October 21 packet and checksum manifest through known authorized provenance; map actual 104 OPT and 130 OPR rows to recovered execution/AC/R1/R2/SUP evidence, current owner, design disposition and next proof. Reconcile duplicates without renumbering or creating a second task plane. | Full row text/ID sets and unresolved scope have a verified source. If original recovery is impossible, obtain an explicit scope ruling from the existing decision owner; do not quietly replace it with a guessed list. |
| **6 — Finish depth and usability contracts** | Use the resulting gap map to bind retained boards or design precise missing deep states for scanner/quad/replay/session review, all Lab lenses, near-expiry, volatility, Prophet lanes, cross-product origins and temporal tools. | Each retained capability has a discoverable route, actual source domain, primary use case, meaningful failure/recovery and exact design target. No redraw of accepted unchanged work merely for uniformity. |
| **7 — Resolve source and operational release dependencies** | Qualify exact held Plan/Matrix/Flow integration deltas, installed references and current custody; bind schemas, rights, correction/availability clocks, budgets, rollback and per-slice consumer tests. | Every next release edge has a real available input/owner and discriminating proof plan, or a precise original gate. Source installation/production results remain separately recorded. |
| **8 — Adjudicate real capability and final commission** | Consume any newly available consumer/scientific evidence, perform affected usability/accessibility/performance review, reconcile acceptance rows and finalize bounded Fable/T3 packets on existing tasks. | Explicit useful release scope and remaining science/parity obligations; no full-suite claim from a successful showcase path. Dispatch remains the parent's authorized action, not this review. |

These rounds are a planning option, not newly commissioned workers or a promise that empirical observation horizons will mature within four more conversations. If a missing dependency is recovered earlier, the parent may close that issue without repeating an entire round.

## 10. Artifacts, validation and next parent action

Companion **`acceptance-traceability.csv` contains 294 actual recovered reference rows**: 60 AC, 76 R2, 35 execution tasks and 123 historical claims. It preserves original requirement text, original status/owner/evidence and exact source pin/path separately from Paper coverage, suggested release slice and next proof. Grouped R2 IDs are expanded while retaining the original group label and text. It is a documentation projection, not a new task/acceptance authority. There are no invented OPT or OPR rows.

**`acceptance-coverage-gaps.json`** records source identity, reviewed input hashes, exact counts, namespace distinctions, packet attestation/search bounds, first Round 5 recovery action and scoped dispatch gate.

Validation performed: parsed each original source with column-count checks; asserted 60/76/35/123 family counts, 294 unique qualified IDs, exact P01–P76 and AC01–AC60 sets, and exact supersession suffixes/status counts. Current R1/R2 fetched source blobs were compared with the local archive, accounting only for its extra final newline. No product test or live acceptance is claimed.

**Next parent action:** incorporate this traceability and the concrete corrections into the existing PR's round-4 baseline and dependency graph; bind current #804/Matrix findings from the parent's exact source reads; preserve the unrecovered-packet gate; save/read back the final canonical plan. This child assignment stops after the actionable review and artifact readback. It initiates no successor or dispatch.

## Pinned source links

- [Original execution task hierarchy](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/research/options_intelligence/2026-10-11-fable-completion/FABLE_EXECUTION_MASTERPLAN.md).
- [October 31 accepted planning crosswalk](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/research/options_intelligence/2026-10-31-fable-amendment/01_FABLE_MASTERPLAN.md) and [AC matrix](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/research/options_intelligence/2026-10-31-fable-amendment/09_ACCEPTANCE_MATRIX.csv).
- [Research/validation and 130-requirement inheritance](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/research/options_intelligence/2026-10-31-fable-amendment/04_RESEARCH_AND_VALIDATION.md).
- [Current-source R1 record](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/docs/OPTIONS_R1_PROGRAM.md) and [R2 coverage ledger](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/docs/OPTIONS_R2_ACCEPTANCE_COVERAGE_2026-10-22.md).
- [123-row historical supersession register](https://github.com/mastermindx-market-intelligence/macro/blob/9a13c64bf69f782332afa29efb09fe48ee30b857/research/options_estate/OPTIONS_SUPERSESSION_REGISTER_2026-10.md).
- [Canonical D86 packet attestation and original continuation](https://github.com/mastermindx-market-intelligence/macro/blob/2aec75a534c26522642bd5dd432802760f5fdcfc/research/OPTIONS_INTELLIGENCE_CONTINUATION_HANDOFF_2026-10-11.md).
- [Original Lab outcome and remaining frontiers](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/docs/options-research-lab/IMPLEMENTATION.md).

