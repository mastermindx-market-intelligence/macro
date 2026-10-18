# Bonds × Transmission R30 + R31 — design handoff

**Status: Paper design and behavior specified. Existing runtime owners are identified; their bond-specific extensions, live data binding and empirical qualification remain implementation work.**

This is the continuous design handoff for the October 18, 2026 Bonds/Cross-Asset revamp and the user's authorized “great work, resume” continuation. It remains part of [programme #8147](https://github.com/mastermindx-market-intelligence/macro/issues/8147). The wider programme is not closed by this design delivery.

## Review the current mockups

- [Bonds page](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1H-0): four main workspaces, START guide and S02/S05/S06 implementation references.
- [Cross-Asset page](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1E-0): transmission, scenario, replay, saved cases and S01/S03/S04/S07 references.
- [Preserved predecessor studies](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1Y-1).

Start with the START board on each requested page. R31's deeper tools are in **S06 Structure & Financing** on Bonds and **S07 Flow Evidence & Case Continuity** on Cross-Asset. The main route entry actions and implementation map were updated to include them.

The set contains **eight product routes and fifteen core tools**. The **21 current artboards** comprise eight route designs, seven implementation atlases, four standalone responsive references and two navigation indexes. Three additional mobile tool specimens are embedded inside S07. They do not add product destinations.

## What R31 adds

| Capability | User decision | Native reference |
| --- | --- | --- |
| I13 Market structure | Is this a rebound or a confirmed change in trend? | 6B78-1 |
| I02 Curve shape | What if short and long yields move differently? | 6BZN-1 |
| I05 Reported obligations | Which financing dates are actually known? | 6BMD-1 |
| I05 Cash timing | What amount must arrive before the payment cutoff? | 6BRC-1 / 6E28-1 |
| I14 Buyer flows | Did holdings fall because of selling or revaluation? | 6C2T-1 |
| I14 Funding pipes | Can financing pressure challenge the proposed Treasury bid? | 6CZY-1 |
| I15 Save + compare | What will be retained, and what changed since that revision? | 6CEV-1 / 6CLB-1 |

The default desks remain light, spacious and aligned to existing Mastermind tokens. Deeper source, mathematical, contractual and implementation detail stays in tools and builder references. The dark Chinese view is an optional responsive specimen using existing graphite tokens. Global tokens were not changed.

### More analysis with fewer competing messages

The market-structure tool combines one chart, three time horizons, curve participation and explicit confirmation/invalidation levels. A five-day gain can remain in conflict with a weaker monthly trend. Volatility distance provides scale without pretending to be a probability.

The financing tools keep CoreWeave's dated annual reported principal separate from the exact-date synthetic Parent A scenario. They distinguish accessible cash, restricted funds, a selected operating buffer, eligible financing and settlement timing. The late-draw state preserves an earlier cutoff deficit even if projected closing cash later becomes positive.

The buyer-flow lens reconciles market-value holdings, transactions and revaluation. Its example shows AI-credit holdings falling despite net buying. The funding-pipes view then opens the dealer financing and money-fund allocation mechanisms that could challenge the initial market interpretation.

The retained-case tools show supported and excluded contents before saving. They separate a frozen revision from new evidence, preserve a draft during conflicts and explain partial success. This is part of reliable analysis: a reopened question must not imply that unsupported scenario inputs were retained.

## Continuous product journey

| Route | Focus | Main next tools |
| --- | --- | --- |
| 01 Bonds desk | Read the change and choose the next test | Curve / Credit / Capital |
| 02 Curve & duration | Policy, term premium and price sensitivity | I02 shape / I13 structure / I10 catalysts |
| 03 Credit & issuer | Spread stress and financing obligations | I05 financing / I07 CDS |
| 04 Capital competition | The same buyer's eligible alternatives | I06 hedge / I08 funding / I14 flows |
| 05 Transmission | Competing mechanisms and contrary evidence | I03 evidence / Scenario / Replay |
| 06 Scenario | Conditional paths and explicit assumptions | I02 shape / I05 cash / I04 monitor contract |
| 07 Replay | Point-in-time comparison and failure cases | I09 filters / I11 model / I12 outcomes |
| 08 Saved cases | Meaningful changes since review | I15 save + compare / I04 monitor / I10 next check |

The intended runtime carries one research question, instrument context, buyer perspective, horizon and evidence cutoff across these routes. Local drafts, complete retained cases and narrower question-only saves remain visibly different states.

## Implementation package

- [Current R31 interaction contracts](r31/implementation.md) and [action map](r31/action_map.json).
- [Current R31 data contract](r31/data_contract.md) and [pinned owner bindings](r31/source_bindings.json).
- [R31 research](r31/research.md), [primary sources](r31/sources.json) and [numerical fixtures](r31/fixtures.json).
- [R31 validation](r31/validation.md), [machine-readable checks](r31/validation.json) and [native-effect ledger](r31/native_effects.json).
- [Cumulative interaction inventory](interaction_contracts.json) and [current manifest](manifest.json).
- [Accepted R30 implementation baseline](implementation.md), [data/model baseline](data_contract.md), [research](research.md) and [migration map](migration.md).
- [Editable native JSX](jsx/) for all 21 current artboards, with node IDs and existing token bindings.

The original R30 validation and effect records remain preserved in the parent directory. Current R31 records explicitly identify the changes and the one repaired canvas-attachment incident.

## Exact runtime reuse

Source inspection located **Terminal Investigation v2** for retained research and **Terminal Alerts** for monitors. No parallel store is proposed.

The current Investigation service does not admit the complete bond/flow/scenario reference set. The current Alerts allowlist does not evaluate the arbitrary combined yield + credit + funding rule. Extend those existing owners before showing full-case retention or active compound monitoring. A question-only save must disclose excluded values; independent alerts cannot substitute for the conjunction.

The source inspection is pinned and read-only. It does not prove current production deployment or runtime acceptance. The JSX is reference markup, not a new application or a deployment artifact. Implement with existing components, source owners and the accepted illustration/chart stack.

## Verification and scope

All **29 R31 numerical checks passed**. All **21 current root positions** and page inventories were read back. The exports contain **3,893 unique node IDs**, with no duplicate or missing named R31 references. All used theme variables resolve; the existing global token hash remains cfd3d65c.

All **96 R31 native mutation responses** were observed. A newly returned responsive-container ID later resolved to a foreign Forex-reference navigation element; three own mobile specimens were temporarily attached there. They were moved back to the owned atlas, stale references were removed and the foreign navigation's original icon/text children were verified. The specified protected Forex page p-1F-0 was not mutated. See the precise scope record in R31 validation.

Runtime interaction/accessibility tests, live source binding, database changes, alert activation, historical backtesting, forecast calibration and deployment were not performed. The continuation paths remain conditional research designs until their specific data and empirical requirements are met.
