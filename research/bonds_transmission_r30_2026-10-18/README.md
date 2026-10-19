# Bonds × Transmission — current R33 design and implementation handoff

**The requested native revamp and working offline reference are complete. R33 also builds the source publication and inspector needed to begin integration.** The design uses Mastermind light surfaces, eight focused workspaces, fifteen tool families and progressive detail. Production integration remains explicitly unproven.

## Open the current work

- [Bonds in Paper](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1H-0)
- [Cross-Asset in Paper](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1E-0)
- [Current working reference](r33/reference/index.html) — download and open the single HTML file locally.
- [R33 source integration](r33/implementation.md), [data contract](r33/data_contract.md) and [source interaction scorecard](r33/feature-scorecard.md)
- [Full R32 product contract](r32/implementation.md), [complete tool scorecard](r32/feature-scorecard.md) and [data/state extension](r32/data_contract.md)

Start with the START board at the top of either Paper page. S01 contains the source inspector and other overlays; S05 is the consolidated implementation map and scorecard. S06 holds curve, structure and financing depth. S07 holds buyer flows, conditional paths, typed draft returns, saved revisions and responsive states.

## Continuous product journey

| Workspace | Primary question |
| --- | --- |
| 01 Bonds desk | What changed, and what deserves attention next? |
| 02 Curve & duration | Which yield driver moved, and how does it affect price? |
| 03 Credit & issuers | Is spread repricing becoming a financing problem? |
| 04 Capital competition | Which alternatives can the same buyer actually own? |
| 05 Transmission | Which explanation fits, and which link is still missing? |
| 06 Outlook & scenarios | What could happen next, and what would change that view? |
| 07 Compare episodes | What was knowable then, and when did this path fail? |
| 08 Saved cases | What was retained, what changed, and which test is unresolved? |

The 21 owned current artboards remain eight routes, seven implementation atlases, four standalone responsive references and two START guides. Three mobile tools are embedded in S07. The 28 predecessor studies stay in the existing archive. The concurrent credit session's CDI boards and the protected Forex pages are outside this package.

## Analytical depth already implemented in the reference

The primary screen leads with a market read and next test. Source explanations, quote conventions, calculations and historical details open in tools.

Curve analysis separates policy, term premium, parallel sensitivity and compatible key-rate shocks. Structure includes fixed close levels, prior-only volatility distance, horizon conflict and curve participation. Credit analysis separates spread conventions, financing facts and actual contractual obligations. Cash timing preserves legal borrower identity, restrictions, draw eligibility, buffers and payment cutoffs.

Capital analysis compares buyer mandate, currency, duration and hedge. The transaction/revaluation lens distinguishes selling from price changes in holdings. The funding view covers financing demand, repo and cash supply without asserting unmeasured capital-flow arrows.

Outlook compares rate relief, supply pressure and funding interruption, with explicit confirmations and invalidations. Correlated indicators do not become independent probability votes. Case tools preserve typed additions, source periods, pending edits, conflict forms, Inspect/Remove/Undo and later event review. Replay separates what was knowable from subsequently revealed outcomes.

The full financial research, source bindings, falsifiers and contracts remain in the [R31 research](r31/research.md), [R31 sources](r31/sources.json) and [R32 implementation](r32/implementation.md).

## New in R33

The **Sources** inspector now works with a locally built capture from pinned Macro inputs. It exposes three concise readings first, then 22 searchable fields, selected origins, component clocks, raw values and missing evidence.

The same existing Macro builder now writes an additive companion JSON from its existing decision-workspace view model. The five-key hub contract remains unchanged. The companion records loaded-input fingerprints, component clocks, selected field lineage and a declared content digest.

The strict adapter preserves missing and invalid data, shows dated context honestly and leaves scenario/evaluator state unchanged. Broad HY spread, a calm funding proxy and selected label changes cannot become matched peer changes, admitted funding observations or a continuation probability.

The inspector supports local JSON import, pending/rejected states, explicit restore, search/focus restoration, Chinese mobile labels and optional dark theme. It makes no HTTP request and performs no real save or monitor action.

## Verification

| Verification | Result |
| --- | --- |
| Publisher + existing authority regressions | 239 passed; 49 deselected |
| Strict source-adapter checks | 40 passed |
| Rendered source-inspector journeys | 26 passed |
| Existing rendered core journeys | 65 passed on the final R33 HTML |
| R32 analytical model checks | 39 passed in the accepted baseline |
| Browser errors / HTTP(S) requests | Zero recorded |
| R33 Paper operations | 29 applied; 3 reconciled with no effect; none unresolved |

The final inspector includes an asynchronous import/restore race test. Native source, scorecard and START layouts were visually reviewed. The changed native exports preserve node IDs. The full self-contained reference builds from the immutable R32 baseline and contains its own licensed Chinese glyph subset.

See [validation](r33/validation.json), [publisher results](r33/verification/publisher-results.json), [adapter results](r33/verification/adapter-results.json), [source journeys](r33/verification/source-journey-results.json), [core journeys](r33/verification/core/journey-results.json) and the [native operation ledger](r33/native/effects.json).

## Implementation and source continuity

The source changes are limited to `scripts/build_macro_context.py`, `tests/test_macro_decision_publication.py` and this existing handoff folder. The current handoff stays on draft PR #9578 and its original branch. CI, DAG, render-input and production Bonds/Forex templates are not changed.

[R33 native exports](r33/native/) supersede the matching S01, S05 and START exports in the existing [native baseline](jsx/). S04 only moves on the canvas to clear the expanded S01. Unchanged R32 exports, contracts and tools remain applicable. The R33 reference itself is complete and requires no manual patching.

R31's repaired transient Forex attachment remains documented in its historical validation; R32 and R33 add no foreign attachment. The protected Forex work remains independent.

## Exact next integration action

The Macro owner should review and integrate the additive companion, then mount the adapter in the existing Bonds consumer under normal source review and repository checks. The status is **BUILT_NOT_PROVEN** until that actual production path is verified.

Qualified instrument observations, source availability clocks, matched peers and funding evidence must come from the existing owners before event evaluation is enabled. Terminal Investigation v2 owns admitted retention and exact reads; Terminal Alerts owns compound-rule admission, evaluation and receipts. Empirical likelihood additionally needs a defined target/horizon, point-in-time data, out-of-time validation, calibration and abstention.

This completes the requested mockup and implementation-ready reference scope. It does not claim a deployed feed, production forecasting, real retained case or active monitor.
