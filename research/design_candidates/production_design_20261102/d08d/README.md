# D08D — Options Futures & Equity Replay

**Candidate:** D08D/1.0.0 · 4 November 2026 · **Design and research only**

**Reference status: PARTIAL / BLOCKED_RETURN. RIG: draft; no approval receipt.** The research, retention, temporal, interaction, backend, build and acceptance contracts are supplied here. Responsive source studies support review. Dedicated editable Paper compositions and their immutable export freeze remain blocked by the published Paper action contract and the unreleased joint foundation. No product implementation or release is included.

## Product outcome

A researcher starts from a particular chart or Options selection, opens the appropriate replay reader, selects an actual historical observation, inspects its evidence and limitations, and returns to the same originating research state. The researcher can always answer **which instrument, which session, which observation, what was available, and what is missing**. Research navigation places no trade and creates no saved object.

The primary persona is an experienced equity/options researcher investigating an observed event. The secondary persona is a newer subscriber who needs a clear explanation of replay scope and access before encountering advanced depth, footprint and exposure controls. The first screen prioritizes identity, historical time, one useful chart, selection and return. Advanced controls remain reachable through named disclosures and the evidence inspector.

### Decisions to carry into D08

1. Keep the incumbent futures and IEX readers independent. D08-OPTIONS/1.0.0 supplies shared semantic handoffs, not a universal cursor or another replay engine.
2. Futures retain the closed `pair/interval/rows/expiry/mapping/at` grammar. Equity retains one optional `symbol`. Exact return and evidence selection must not be smuggled into new query parameters.
3. Display requested cutoff separately from the effective observation. IEX selection preserves nanosecond strings, native session/sequence and immutable artifact position. Millisecond formatting is not cursor identity.
4. Present historical context beside the instrument and beside the selected time. “Latest retained observation” never becomes a “Live” label. IEX archive acquisition does not establish contemporaneous knowledge.
5. Preserve access distinctions only when trusted evidence distinguishes them. The current page paywall, futures API access refusal and equity unpublished-feed response are different observed facts.
6. Extend existing D08/D06 navigation ownership to deliver exact restoration. Current `originNav` and company-search history helpers do not already provide the whole replay return protocol.
7. Retain `/dev/options-plan` as a production 404 and exclude it from customer navigation. Registry/projection admission remains with the incumbent owner/F03.

## Read this package

The package includes **52 capability entries** (25 RETAIN,21 IMPROVE,1 RELOCATE,5 BLOCKED_DATA,0 REMOVE), **76 future acceptance cases**,16 Gherkin scenarios,31 individually pinned source files,14 annotated supporting studies and the unchanged nine-image first-pass review freeze. These counts describe scope, not passing product tests or accepted Paper boards.

| File | Purpose |
| --- | --- |
| [SOURCE_EVIDENCE.md](SOURCE_EVIDENCE.md) | Immutable source pins, live observations, Paper references, producer seams and audit limits |
| [FEATURE_LEDGER.md](FEATURE_LEDGER.md) | Capability-by-capability retention and reachable destinations |
| [WORKFLOW_INTERACTION.md](WORKFLOW_INTERACTION.md) | Full journey, controls, route behavior, access/failure copy, focus and exact return |
| [TEMPORAL_BACKEND_CONTRACT.md](TEMPORAL_BACKEND_CONTRACT.md) | Native clocks, identity, validation, accounting, API boundaries and proposed owner extensions |
| [RESPONSIVE_SPEC.md](RESPONSIVE_SPEC.md) | Composition geometry, dark/light treatment, EN/ZH, chart alternatives, annotations and Paper construction packet |
| [BUILD_ROLLBACK.md](BUILD_ROLLBACK.md) | Existing modules, integration order, migration, performance and rollback |
| [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) | Discriminating acceptance cases and execution status |
| [acceptance.feature](acceptance.feature) |16 Gherkin scenario specifications, with no claimed execution or step implementation |
| [REVIEW_RETURN.md](REVIEW_RETURN.md) | Independent advisory findings, amendments, carried gates and exact successor actions |
| [studies/index.html](studies/index.html) | Local, static responsive-study gallery; illustrative data; no product behavior |
| [evidence/](evidence/) | Source hashes, live readbacks, original screenshots, Paper admission and artifact digests |
| [review/](review/) | Frozen product/visual finding records and post-freeze advisory consumption |

## Scope and ownership

The Chairman assignment authorizes this design/specification package. D08 owns Options integration and common navigation; D06 owns originating chart context; D08B owns exposure presentation; D08C owns plan/compare/review; D23 owns durable save/alert receipts. Existing Terminal/Quote Hub/IEX producer and access modules remain authoritative. This packet does not create a registry, scheduler, publisher, market calendar, auth provider, evidence store or general return-state store.

Source custody is restricted to `research/design_candidates/production_design_20261102/d08d/` on isolated branch `claude/d08d-options-futures-replay-20261104`. The branch starts at observed Macro main `df691495abb1c2ba8f61e5624126cb17ad14e056`. It does not edit sibling packets. Initial pickup and four-phase plan are recorded in [D08 #10649](https://github.com/mastermindx-market-intelligence/macro/pull/10649#issuecomment-6618905511).

### Inputs consumed

| Input | Exact identity / disposition |
| --- | --- |
| Protected Mastermind law | `910803421beca53ca25145392725ab2d84c7a8e9`; compatible bootstrap major 1 / skillpack 1.0.1 |
| Chairman handoff | `6e1862867193ec6486a22001a0e4fb515da20448` |
| Resolved common programme package | `b0d827361e7adc266079fa0501789fd005d0794c`; handoff/common brief unchanged from commissioning bytes |
| D08 interface | **D08-OPTIONS/1.0.0** at `d0516e1bad9cb5982d43d20c4167d0355cb70e2c`, PR #10649 |
| Terminal source audit | protected master `2ded360882b9c721e690907ff363b553781fb920` |
| Shared shell | F01-F02-SHELL/1.0.0-candidate.4 at `8926b16af4e0c3e5310cdb4cf057390ec04d18ff`; joint v1 unreleased |
| F02 specimen roles | candidate.2 token mapping at `f7c25c4b9870cff260c2a4b998be18d6c04d36d0`; no new production token namespace |

## DONE_WHEN and current evidence

The design outcome requires editable normal and exception compositions, a complete retention ledger, explicit temporal/source/return contracts, independent product/visual critique and an immutable reviewed artifact set returned to D08. Source existence, a paywall, a local study, CI or a URL alone cannot qualify that outcome.

This package establishes the source and live-access baseline and specifies the complete intended journey. It cannot establish entitled data behavior from the observed browser session. No new Paper file/page/artboard was created. `MM · Futures & Replay` remains a proposed destination with **null IDs**. Existing D08's denied empty board `1N2L-0`, D08B page `p-12-0`, D08C page `p-13-0` and unrelated GMI were not modified.

Success targets for a later commissioned usability study: identify historical scope and units without assistance; reach evidence for an explicitly chosen observation; distinguish a gap from zero liquidity; return to the original instrument/view/filters/selection without re-entry. Instrument these through the existing telemetry owner after consent and owner approval; no measured improvement is claimed here.

## Release boundary

Keep this package Draft and reviewable. The assignment forbids merge, Ready, un-draft, enqueue, held relabel and deployment. Route admission, Paper reference acceptance, code integration, deployment and real user-path acceptance remain separate stages. See [REVIEW_RETURN.md](REVIEW_RETURN.md) for the minimum evidence each remaining owner must provide.
