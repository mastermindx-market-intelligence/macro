# Skylit learning -> existing Mastermind sector and options intelligence

Date: 2026-09-10  
Accountable seat: Sol / ceo-sol  
Records operation: `skylit-integration-ruling-20260910-sol-001`  
Implementation candidate: `us-sector-participation-w1-20260910-sol-001`  
Capability state at this ruling: **SPEC_ONLY. No new product implementation or production proof.**

## 1. Executive ruling

Proceed beyond competitor research, but do not build a Skylit clone, a second Discover dashboard, or a new flow/rotation authority. The first independently useful capability is a **US Sector Participation Calendar inside the existing Sector Central page**. It answers: which sectors have broad participation, how has that changed, and which covered constituents support the observation?

Use the existing `sector-rotation-intelligence` program. The program key is established by `agentos/workstreams/WS-INSTITUTIONAL-PRODUCT-EXPERIENCE-V2.md`; its completed reference-design work is not being reopened. A new bounded US-SECTOR-PARTICIPATION workstream owns only the additive capability described here. Existing options-intelligence and market-structure programs retain options/positioning ownership.

The full destination remains broader than W1: participation -> relative leadership -> constituent evidence -> qualified options activity -> positioning scenarios -> price/contract investigation -> evidence-grounded Brain explanation -> monitoring and evaluation. W1 is a useful first vertical, not a reduction of that destination and not full Skylit parity.

Current Chairman direction in this conversation is to assess implementation and take leadership to move forward. Sol owns this product ruling, decomposition, adversarial acceptance and later release decisions. The publication of these records does not itself START a worker, admit an Executive Job, authorize a deployment, or qualify a model.

## 2. Outcome, value and moat

Primary persona: a discretionary market/sector researcher who needs to identify broadening or narrowing participation and investigate the underlying names without confusing it with a trade recommendation.

User job: in one existing workspace, compare sector participation across completed sessions, inspect the denominator and exclusions, understand the reference universe, and open the existing relevant research destination.

Machine job: expose the same dated, typed descriptive measurements the user sees, with method/version, observation clocks, quality and membership basis. W1's real machine consumer is the existing page's numerical view model; Brain admission is a later bounded integration, not an unused field claimed as intelligence.

Value thesis: better connected analysis and less reconstruction work, not a claim to own Skylit's private score. Proposed moat: coherent cross-asset/sector/theme evidence, explanations of why measurements changed, uncertainty that survives aggregation, correction-aware history, and measured research usefulness. No trading alpha is claimed by the thesis.

10/10 end-state: a researcher moves from an emerging participation change to the specific names, conflicting flow/positioning evidence, a dated explanation and a monitored research question. The system preserves where information is unavailable and later measures whether its discovery improved the user's process or an explicitly defined forecast target.

## 3. Evidence recovery and correction of prior chat

The prior deep-research answer said retrieval returned no inspectable source content. That blanket statement was incorrect: the conversation's tool returns contain complete published Skylit OpenAPI documents and pinned Mastermind source reads. Preserve those observations, while distinguishing documentation from authenticated live behavior.

The earlier engineering blueprint in the conversation was a proposal, not an approved architecture or source-owner release. In particular, its suggestion to begin with a new Discover workspace is superseded by the existing Sector Central integration in this ruling.

### Published numerical definitions recovered from the prior tool-returned schema

Source: [Flowseeker published OpenAPI](https://docs.skylit.ai/flowseeker-openapi.yaml), specifically `ScoreComponents`, `TimeframeAggregate`, `FlowTradeScores`, `TopUnderlyingItem`, and the Market/Sweeps route descriptions. These are documented definitions observed in the September 10 research, not authenticated output-parity or backend-source proof.

- VWF is described mathematically as `sum(premium * flowScore) / sum(premium)`. Its name does not make this a contract-count-weighted measure.
- FIR is described as `100 * (bullish - bearish) / total_directional`.
- The aggregate composite is documented as `clamp(0.4*VWF + 0.35*SDF + 0.25*FIR, -100, 100)`.
- The per-trade schema relates `baseDirection` and `convictionMultiplier` to `flowScore`; exact feature coefficients, thresholds, clipping/rounding details and classification correctness remain unverified.
- FlowBonus is an unsigned 0-100 conviction field, not a second bullish probability.
- `TopUnderlyingItem.netPremium` is gross call premium minus gross put premium. The market interface separately carries directional fields. The screenshot's NCP-NPP measure must not be substituted with the gross difference or with OI-derived flow.
- The documented market-breadth API counts tickers by FIR, not by price above a moving average. Its sector-flow classifications are not proof of the screenshot's 50/10 price-rotation implementation.
- The sweep endpoint documents full-day reads with several intraday timeframe filters reserved, and population estimates distinct from returned capped rows. A visible parameter does not prove implemented filtering.

These corrections are useful research evidence. They are not a requirement to reproduce the weights in Mastermind, purchase a feed, invoke the API, or market a score as calibrated.

### What remains unknown and is NOT a W1 dependency

Skylit's precise price-rotation formula/universe, per-trade feature weights, trade-sign estimator, dealer signed-inventory reconstruction, projection model and forward validation, and Talon's LLM/provider configuration. No private code, proprietary corpus, participant identity, or live forecast advantage has been established.

The decision is independent implementation of the user job using appropriately permitted existing inputs. Do not scrape or copy proprietary implementation/assets, circumvent authentication, redistribute Skylit output, or make a paid/API commitment under this packet. Any later commercial data integration needs its own rights and budget decision.

## 4. Current source and capability ledger

Procedure pin: `mastermindx-market-intelligence/Mastermind@dd553d1b0b8eed9511da2d3d5ec02cc9cd8edca1`, protected master, Skillpack 1.0.1 / bootstrap 1. Loaded INDEX, COLD_START, COMMISSION_WAVE, WORKER_AVENUE_ROUTING, routing addendum, dialogue law, native hierarchy and CLOSEOUT at this pin.

Implementation archaeology pin: `mastermindx-market-intelligence/macro@11e145774d6193bf777ed1d355173a27c6ba693d`. Terminal reference pin: `ee320e390f9c09231a54e06c0e941f43875c198f`. Records may be based on a later main commit; these are the exact inspected implementation versions, not a claim they are perpetually current.

| Capability | Evidence in inspected source | Disposition |
|---|---|---|
| Breadth acquisition, identity repair, adjusted prices | `collectors/breadth.py`, blob `994f5a4e79dae1477ae7b7adb8000cb1677475dd` | Existing producer to extend; end-to-end production freshness not re-proven here |
| Sector membership and 50/200-session participation | Same collector `compute_sectors`; `data/breadth/constituents.parquet`, `_closes_cache.parquet`, existing sector_breadth output | Existing related capability; W1 20-session calendar NOT_BUILT in these inspected paths |
| Session reference | `lib/nyse_calendar.py`, blob `0ece6439ffe4b081ee7a268fe99b69e1de1216a3` | Reuse; no new calendar. Its documented conservative 17:00 ET settle expectation is not a real-time feed SLA |
| Existing Sector Central | `scripts/build_sector_central.py`, blob `b8d264582591d23cbc880ed2c7cb06cddfa8425f`; `templates/sector_central.html.j2` | Built host for W1, not a new product shell; live route/entitlement proof still required |
| Rotation events/fragmentation/velocity | `scripts/build_rotation_events.py`; existing rotation modules and canonical stores | Preserve classification/lifecycle. Flow receipts remain context; no alternative rotation event system |
| XPV2 reference design | WS-INSTITUTIONAL-PRODUCT-EXPERIENCE-V2; Macro PR6337, merge `8b303a58e8c0b807ef34d1913c4cacf5bb346e2d` | Reference objective done; reference-to-production capability SPEC_ONLY. This is not full R3C migration |
| Existing options estate | WS-ADVANCED-DATA-OPTIONS; Terminal Options Superintelligence and Market Structure Core records | Separate owning programs. Current data/authority gates are not waived by this research |
| New combined product described here | This ruling and W1 contract | SPEC_ONLY until real source, user journey and production proof exist |

Source links at the inspected pin:
[collector](https://github.com/mastermindx-market-intelligence/macro/blob/11e145774d6193bf777ed1d355173a27c6ba693d/collectors/breadth.py),
[calendar](https://github.com/mastermindx-market-intelligence/macro/blob/11e145774d6193bf777ed1d355173a27c6ba693d/lib/nyse_calendar.py),
[Sector Central builder](https://github.com/mastermindx-market-intelligence/macro/blob/11e145774d6193bf777ed1d355173a27c6ba693d/scripts/build_sector_central.py),
[reference workstream](https://github.com/mastermindx-market-intelligence/macro/blob/11e145774d6193bf777ed1d355173a27c6ba693d/agentos/workstreams/WS-INSTITUTIONAL-PRODUCT-EXPERIENCE-V2.md).

The source presence classifications above are not current production acceptance. No code execution, public browser or fresh market-data completeness proof occurred during this records ruling.

## 5. Frozen integration boundaries

1. **One product host:** add W1 inside `sector_central.html`, preserving the existing boards, embeds, links, controls and entitlement behavior. No new top-level Discover route or full XPV2 redesign.
2. **One input owner:** reuse breadth acquisition/identity/reference roster/adjusted-close cache and `lib.nyse_calendar`. No new vendor, collector, scheduled task, ticker map, calendar, or history database.
3. **One numerical method:** the new 20-session calculation is owned by the existing breadth path. The page consumes its result; JavaScript must not invent an alternative formula. Additive presentation packets are projections, not a second source of truth.
4. **Preserve existing meanings:** 50/200-day outputs, old sector/rotation scores, Act-Now classifications, Prophet rank/entry/size, graders and stored calls remain unchanged. New context must not enter a pre-existing grading signature through a whole-object hash or serialization side effect.
5. **Transparent history:** initial history is recomputed from the available adjusted-price cache using the selected reference roster. Label this as reference-universe reconstruction, not historic membership, original publication vintage or investable point-in-time replay.
6. **No source-law shortcuts:** current source custody, open-PR effects, runtime admission where applicable, rights, entitlement and publication gates remain binding. Technical read/write access is not source ownership.
7. **No premature trading authority:** descriptive values may help research. They do not buy, sell, rank Prophet candidates, change confidence, size risk, gate a trade, or train a model.

## 6. Implementation sequence and release gates

| Wave | Independently useful outcome | Existing owner / gate |
|---|---|---|
| W1 | US sector participation history with denominator/exclusions and constituent investigation in Sector Central | Bounded Macro builder; exact source preflight, one implementation PR, independent review, real publication/browser proof |
| W2 | Explainable relative-leadership map: recent change separated from the block rolling out of the lookback | Existing rotation producer; version a distinct descriptive method, never silently overwrite existing SPY-relative or cross-sectional coordinates |
| W3 | Qualified flow investigation: signed and gross premium separated; filters/date/contract selection survive drilldown | Existing options tape/classifier/UI program; actual sign/coverage and source-clock gates |
| W4 | Positioning interpretation: exposure units, sign assumptions, expiry scope, change attribution and proxy mapping | Existing Market Structure Core, not another dealer-inventory store |
| W5 | Brain and monitoring consume the same dated evidence and preserve contradictions | Existing Brain/context/alert/portfolio mechanisms; user control and existing authority ceilings |
| W6 | Separately preregistered predictive experiments and eventual promotion | Existing research/evaluation owners; target-specific point-in-time replay, execution assumptions, forward validation and promotion ruling |

Only W1 is selected for near-term source work. The other rows are sequenced scope, not worker assignments, Jobs, automatic follow-on authorization or release promises. W1 does not depend on discovering private competitor coefficients.

## 7. Source collision and side-effect findings

Current searches found no existing Skylit-named branch/PR/workstream in the searched scope. Keyword search is NOT complete source-custody clearance. The selected builder must use the current accepted source-continuity path over exact changed files, open PRs and any incumbent local work before editing.

Preserve current owners, notably Macro #7023 (China weekly member detail, including the shared `subsector_rotation_detail.html.j2`), #6990 recovery records, #7018 Canada opportunity map and #6832 predecessor, #6912 reference/dashboard changes, #7007 shared ticker-page work, and the existing options/market-structure writers. Do not touch their shared paths merely because the new feature is conceptually related.

`build_sector_central` runs a self-grader and writes payloads; `build_rotation_events` advances canonical event stores and shared alerts. A scratch output directory alone is not proof these invocations are side-effect-free. Diagnostic/fixture builds must isolate every writer and injected root. Real production invocation belongs to the existing deployment/publication owner, after source acceptance.

## 8. Routing and accountability

Sol owns scope, thesis and acceptance. Preferred implementation avenue: **Terra**, included-subscription coding capacity, because W1 is deterministic and bounded. Use one concrete capable source writer, not Fable by default. A finite CTO Sol non-author review is appropriate for source seams, history/null semantics and entitlement/side-effect checks; no recurring review campaign is commissioned here.

Actual placement belongs to the existing Secretary/Capacity bridge. The request must state `WAITING_CAPACITY / needs_placement` until an exact receiver exists. A Slack post is not pickup, START or an Executive Job. Receiver-specific continuation is registered through the existing lawful aggregate; no new watcher/control plane. Every material return requires a same-root Sol CONTINUE/repair/STOP ruling. No worker self-assigns W2 after W1.

## 9. Acceptance and exact next action

W1 acceptance requires actual inputs through the existing breadth/Sector Central path to the visible calendar, one selected cell and its correct constituents/destination; truthful current/old/missing states; dark/light, English/Chinese and desktop/mobile proof; unchanged protected boards and graders; actual entitlement and serving behavior; two independently observed publication versions or an equivalent named correction exercise through the owning path. Unit tests, CI, a docs merge and fixture screenshots remain distinct from production proof.

Immediate next action: place one W1 builder with the companion contract. Its first return is a finite preflight with exact source/consumer/CI/entitlement seams, input coverage/rights and source-custody proof. Sol resolves any real boundary conflict and issues the same-carrier source START clearance; do not ask the Chairman to allocate worker accounts. The builder then produces one vertical implementation PR and stops for independent review and release judgment. No more broad competitor research is needed to begin this path.
