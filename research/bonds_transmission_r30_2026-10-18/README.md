# Bonds × Transmission R30 — design handoff

Status: **Paper design complete; runtime implementation and empirical forecast qualification remain separate work.**

This revision responds to the 18 October 2026 commission to replace the crowded Bonds R18–R25 and Cross-Asset transmission studies with a clear, advanced decision workflow. It belongs to the existing [Bonds × Forex programme #8147](https://github.com/mastermindx-market-intelligence/macro/issues/8147). Completion here is the R30 research/design deliverable, not closure of that programme or inheritance of production/model authority.

## Open the design

- [Bonds: four market workspaces and build references](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1H-0)
- [Transmission: mechanism, scenario, replay and saved-case workspaces](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1E-0)
- [Preserved pre-R30 studies](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1Y-1)

Each requested page starts at a new R30 navigation board, followed by a two-column sequence. The other session’s Forex page, p-1F-0, was not edited or moved. Its destination is an integration contract only.

## What changed

The daily product journey contains **eight routes**, replacing the previous collection of overlapping studies. Twelve detailed tool specimens, five implementation atlases, four responsive references and two navigation indexes complete the design package. These supporting references are not additional daily product destinations.

The default presentation uses the existing Mastermind light research tokens, Inter typography, a quiet sidebar, compact market status, and a clearly identified next decision. An optional mobile Chinese evidence sheet demonstrates the existing graphite dark tokens. No new global theme tokens were introduced.

Primary information is organized around the current state, its interpretation, and the next useful test. Calculations, source clocks, contractual details and method belong in focusable tooltips, popovers, drawers or mobile sheets. Builder acceptance text lives on the specification atlases. Main product headings were shortened and repetitive summary cards were consolidated.

## Continuous product journey

| Route | Question | Paper node | Primary next step |
| --- | --- | --- | --- |
| 01 · Bonds desk | Read the change; choose the next test. | 63GL-1 | 02 Curve · 03 Credit · 04 Capital |
| 02 · Curve & duration | Separate policy, term premium and sensitivity. | 63S3-1 | I02 Calculation · I10 Auction |
| 03 · Credit & issuer | Trace spread stress to financing obligations. | 63YS-1 | I05 Financing · I07 CDS · 05 Case |
| 04 · Capital competition | Compare the same buyer’s eligible alternatives. | 648A-1 | I06 Hedge · I08 Funding · 05 Case |
| 05 · Transmission | Inspect the proposed link and contrary evidence. | 64G1-1 | I03 Evidence · 06 Scenario · 07 Replay |
| 06 · Scenario | Change assumptions; retain confirmation and failure. | 64PQ-1 | I02 Calculation · I04 Monitor |
| 07 · Replay | Record the view before revealing outcomes. | 64WP-1 | I09 Filter · I11 Model · I12 Outcome |
| 08 · Saved cases | Review changed evidence and the next decision. | 670P-1 | Reopen case · I04 Monitor · I10 Check |

The eight routes share one saved case: its hypothesis, selected instruments, benchmark, currency and hedge assumptions, horizon, evidence cutoff and revision. A user should be able to start with an issuer, inspect competing sovereign alternatives, test the mechanism, change assumptions, compare historical failures, then return to the changes since the last review.

## Why the analytical structure matters

The motivating AI-credit/Treasury example is represented as a **contested transmission case**. Growth repricing, capital substitution, demand for safety, and funding stress are different mechanisms with different confirming evidence. A Treasury rally alone cannot establish which capital source moved or whether the move will continue.

Credit pricing, financing access and market functioning remain separate readings. Exact CDS conventions are inspectable. Issuer obligations use a clearly dated reported snapshot. Buyer comparisons retain mandate, duration, base currency and current hedge cost. The funding counterpath explicitly allows bonds to be sold when cash or collateral needs dominate.

The scenario workspace offers deterministic sensitivity and conditional continuation paths. Historical replay freezes what was known before revealing later outcomes. A likelihood percentage is withheld until its specific model, target, data vintages and performance are qualified. These are useful analysis paths with explicit evidential limits, not an empty promise of a forecast.

## Implementation package

- [Implementation and interaction contracts](implementation.md): I01–I12, common controls, navigation, keyboard/touch behavior and acceptance cases.
- [Data and model contract](data_contract.md): existing source owners, unresolved bindings, evidence identity, source clocks, monitor evaluation, replay admission and empirical qualification.
- [Research dossier](research.md): mechanism reasoning, contrary evidence and source register.
- [Migration map](migration.md): every preserved legacy board and its R30 replacement.
- [Validation record](validation.md): visual review, arithmetic checks, native-effect/inventory verification and limits.
- [Machine-readable manifest](manifest.json), [source register](sources.json), and [numeric fixtures](fixtures.json).
- [Editable JSX references](jsx/): current Paper exports with node IDs for all nineteen R30 boards.
- [Token snapshot](tokens.snapshot.json): only token names used by these references, copied from the observed existing token registry.

The JSX files are design references. They do not implement data fetching, calculation state, saved-case persistence, live monitoring, navigation or model inference. Runtime components must reuse existing platform owners and the accepted illustration/chart stack. Do not ship these fixed-width reference exports as a new parallel application.

## Readiness

| Area | R30 result |
| --- | --- |
| Product layout and information architecture | Specified and visually reviewed |
| Core tools and failure states | Native specimens plus implementation scorecards |
| Responsive behavior | 1440 desktop, 768 tablet, 390 mobile; light English and dark Chinese evidence reference |
| Data source investigation | Existing projection and dated read-only snapshot/vintage evidence recorded |
| Runtime integration | Pending: bind data, effects and canonical owners; no activation performed |
| Empirical prediction | Pending: no historical backtest, calibrated likelihood or profitability claim |
| Production delivery | No runtime code deployment, trade or live notification arming |

Use the R30 sequence and its contracts for implementation planning. Resolve the exact pending bindings in the data contract before making a feature appear current or activated.
