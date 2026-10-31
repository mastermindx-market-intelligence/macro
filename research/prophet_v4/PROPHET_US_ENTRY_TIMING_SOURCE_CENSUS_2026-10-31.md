# Census and source index — Prophet US V4 / Entry Timing

Use this appendix when opening a particular wave. These are source observations at the October 31 census, not new runtime jobs.

## Three compatible planning systems

Entry Timing W0/W1/W2 is the original measured P0. V4’s 30 wave IDs describe the recovery architecture. R6 B00–B28/Q01–Q24/D01–D12 are product, scientific and decision units; R7 S0–S6 plus Design integrates them across markets. The similarly named V4-B3, R6-B03, audit B-17 and R6-B17 have different meanings.

## All 30 V4 recovery waves

Source: [recovery workstream](https://github.com/mastermindx-market-intelligence/macro/blob/29cfb98b15d2f1a7d39489024c69e76fc46b6ff0/agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md). Columns for status and dependencies are transcribed from the 30 structured wave objects. The last column is an implementation or evidence direction.

| Wave | Recorded status | Depends on | Outcome | Reuse or remaining acceptance |
|---|---|---|---|---|
| 0A | done | — | Architecture freeze | Preserve #5832 |
| 0B | done | 0A | Post-freeze reconciliation | Preserve #5847 |
| A1 | done | 0A | Owed-session recovery | Preserve #6320 and Aug 24 source/reader receipt |
| A2 | in_progress | A1 | Settlement manifest | Resolve four-asset issuer and same protected reader, then liveness/rescue |
| A3 | todo | A1 | Atomic publication | Prove one committed and served unit including split-brain rejection |
| A4 | todo | A2, A3 | Fire-drill week | Ordinary settlement, outage and recovery over the required week |
| B1 | done | A1 | Canonical episode registry | Retain accepted canonical ID, generation and suppression history |
| B2 | in_progress | B1 | Correction integrity and B-17 | Adopt #10176 into private Lab when qualified; B-17 stays separate |
| B3 | in_progress | B1 | Four independent candidate axes | Prove actual consumers use all four axes, same B1 generation |
| B4 | in_progress | B2, B3 | Strategy-specific entry availability | Reconcile current identity, quote and geometry, then one user-facing verdict |
| B5A | in_progress | 0A | Operator Lab | Preserve commissioned API/shell; qualify remaining native Lab and entitlement checks |
| B5B | todo | B3, B4 | Authoritative Early Entry Desk | Use B5A plumbing after B3/B4; confirm authoritative desk on real data |
| B6 | todo | B2 | Radar full-RTH observation | Use Radar owner and existing full-RTH evidence; prove consumer observation |
| B7 | todo | B6 | Radar UI integration | Close Radar-owned W9 consumer after W4/W6/W8 |
| C1 | todo | B1 | All-candidate outcome ledger | Grade all cohorts with control joins, missingness and benchmarks |
| C2 | todo | C1 | Frozen V3 same-tape shadow | At cutover prove exact us_prophet_v3_legacy_shadow identity and same tape |
| C3 | todo | B5B | Operator decision receipts | Capture user decision vs subsequent outcome on the authoritative desk |
| D1 | done | 0A | Theme and identity census | Preserve #5859 scoped census |
| D2 | in_progress | D1 | GMI identity, PIT and rights | Adopt accepted GMI identity/PIT repairs; reconcile W3B current-use rights |
| D3 | todo | D2 | Consume accepted ThemeState | Join eligible GMI generation to Prophet by exact identity and cut |
| D4 | todo | D3 | Peer/transmission features | Use as-known group membership, leave subject out, control missingness |
| D5 | in_progress | B1 | Evidence families and trajectory | Reuse #6705, verify authenticated installed revision and clocks |
| D6 | todo | D5 | Earnings adapter breadth | Prove broader Earnings coverage; #6705 does not close this wave |
| D7 | todo | D5 | Other qualified adapters | One qualified family at a time; absent adapter emits no envelope |
| E1 | todo | B4, C1, D5 | Priority within availability lanes | Extend accepted Conditional Fusion within lanes, with missing-aware reasons |
| E2 | todo | E1, B7, C2, A4 | Primary experience and cutover | Reconcile #6817/selected design, prove serving, entitlement and rollback |
| E3 | todo | C1, E1 | Listwise shadow challenger | Same frozen cohort and incumbent comparison, research only |
| E4 | todo | E3 | Conditional challenger | Holdout conditional routing and calibration, research only |
| E5 | todo | D4, E3 | Temporal graph challenger | As-known canonical graph comparison, shadow only |
| E6 | todo | E3, E4, E5 | Promotion and V3 retirement | Qualified comparison and explicit retirement or retention ruling |

## All 29 R6 build units

[Full worker inputs, evidence, dependencies and release boundaries](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/research/prophet_v4/r6_fable_meta_ceo_handoff/effective/BUILD_PROGRAM.json). Descriptions below give the October application. They do not rewrite registered study law or R7 family-specific rulings.

| Unit | Existing objective | Completion focus |
|---|---|---|
| B00 | Bind and review the integrated master specification | Adopt current R6/R7 evidence and pin affected carrier |
| B01 | Complete owed-session and source-bound delivery | Four assets, protected reader and honest owed-session outcome |
| B02 | Preserve canonical episodes and qualify extra anchors | Natural B1 continuity, withdrawals and underwriting independent anchors |
| B03 | Deliver the lossless searchable opportunity field | Explain every record from universe through searchable field and featured cap |
| B04 | Bind the episode evidence dossier | Join accepted dossier evidence or explicit family absence |
| B05 | Close B4 source validity and mandatory-fact integration | Bind one real decision across B3/B4 owners and market session |
| B06 | Make policy capture and labels decision-clean | Separate policy labels, modeled execution, user visibility and economic returns |
| B07 | Ship the first research-to-watch journey | Complete watch/save/return against real user-state owner |
| B08 | Expand comparable event and expectation sources | Gate S source accepted within scope; production admission and Gate E still separate |
| B09 | Qualify group history and peer evidence | Current GMI rights, as-known group history and peer controls; preserve #7455/#7508/#7604 |
| B10 | Build qualified Early Leadership research comparisons | Prospective-only research, compare discovery and selection separately |
| B11 | Expose a qualified ranking/head challenger | Challenger stays in eligible lanes and shadow until adjudicated |
| B12 | Qualify genuinely earlier entry | Held-out timing delta and false-positive cost; no implied backfilled B4 calibration |
| B13 | Bind tactical management and original decisions | Version the entry/exit management decisions and original case |
| B14 | Deliver the Earnings research journey | Prove earned event/expectation/plan relationship and private Lab on actual data |
| B15 | Qualify Earnings models, entry and holding | No H42 economic comparison until corporate-action basis and study are eligible |
| B16 | Qualify a Cycle source-readiness pilot | Preserve closed NOT PILOT-READY result and held original #7868 diagnostic |
| B17 | Deliver funding and per-share Cycle dossiers | Original-equity, funding, dilution and milestone lineage via #8308 |
| B18 | Run failure-inclusive Cycle policy research | Include failures and delistings before treating Cycle results as informative |
| B19 | Qualify Cycle core/add/exit behavior | No add/hold/exit logic until B17/B18 and versions can support it |
| B20 | Build the shared flagship workspace and design system views | Shared workspace with signed-in usability, market-native data and approved reference |
| B21 | Integrate meaningful alerts and durable user actions | Read existing #9999 and #10062, suppress stale/unauthorized requests on real path |
| B22 | Deliver a truthful unified track record | All-cohort track record with controls, costs and missingness |
| B23 | Qualify reliability and operating budgets | Natural source-to-reader health, latency, refusal and operating cost under load |
| B24 | Expose coherent portfolio context across sleeves | Authenticated portfolio context with saved thesis and no new capital authority |
| B25 | Independent full-stack release adjudication | Independent source, statistics, security and user-path adjudication |
| B26 | Execute phased flagship cutover and rollback proof | Canary, rollback, cross-market isolation, V3 shadow and field/user parity |
| B27 | Disposition retained sleeves and instrument roadmap | Disposition the retained sleeves and instrument roadmap explicitly; keep spec-only where required |
| B28 | Accept US program scope and prepare market-native reuse | Record US capability matrix, limitations and residual dependencies; broader R7 acceptance separate |

## Research and decision index

Each linked docket entry contains its own population, inputs, controls, method, falsifier and downstream consumers. For Entry Timing start with Q01/Q02/Q03/Q04/Q15/Q18; check Q05/Q06/Q07 for sleeve dependency and Q24 for comprehension. Only a registered and eligible packet can open formal outcomes.

| Research | Question family | Serves |
|---|---|---|
| Q01 | Decision-time integrity and usable source history | B01, B02, B04, B06, B08, B16 |
| Q02 | Winner/loser and missed-opportunity attribution | B03, B06, B10, B22 |
| Q03 | High-recall expert union and independent origination | B02, B03, B10, B12 |
| Q04 | Same-origin daily/multi-day/intraday entry timing | B06, B12, B13 |
| Q05 | Group leadership, member selection and self-confirmation | B09, B10, B11 |
| Q06 | Comparable earnings and expectations | B08, B14, B15 |
| Q07 | Cycle proving-domain and economic-turn identification | B16, B17, B18 |
| Q08 | Funding, dilution and original-equity recovery | B17, B18, B19 |
| Q09 | Multi-head remaining opportunity and payoff timing | B10, B11, B15, B18 |
| Q10 | Ranking objectives and economic tradeoffs | B10, B11 |
| Q11 | Calibration, abstention and user-visible confidence | B11, B15, B18, B22 |
| Q12 | Context routing and behavioral fingerprints | B10, B11, B15, B18 |
| Q13 | Economic propagation and graph value | B04, B09, B11, B15 |
| Q14 | Specialist and qualitative evidence economics | B04, B08, B11 |
| Q15 | Execution realism, bars and latency | B05, B06, B12, B15, B19 |
| Q16 | Tactical and earnings management | B13, B15 |
| Q17 | Cycle core/add and milestone hold | B18, B19 |
| Q18 | Incumbent B4 policy calibration | B05, B06, B12 |
| Q19 | Feedback, attention and alert usefulness | B07, B21, B22 |
| Q20 | High-capacity representations and model vintage | B11, B15, B18 |
| Q21 | Feasible portfolio and correlated opportunities | B24, B25 |
| Q22 | Drift, degradation and safe model operation | B23, B25, B26 |
| Q23 | Later sleeves and instrument-specific expressions | B27, B28 |
| Q24 | End-to-end usability and decision comprehension | B07, B20, B21, B22, B25, B26 |

[Full research docket](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/research/prophet_v4/r6_fable_meta_ceo_handoff/effective/RESEARCH_DOCKET.json) · [Decision register](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/research/prophet_v4/r6_fable_meta_ceo_handoff/effective/DECISION_REGISTER.json) · [R7 intelligence rulings](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/research/prophet_v4/r7_program/intel/INTEL_DISPOSITION_2026-10-21.md) · [R7 source dispositions](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/research/prophet_v4/r7_program/source/SOURCE_DISPOSITION_2026-10-21.md). The original decision register is a preparation snapshot; use later scoped rulings on the same decision before re-opening it.

- **D01** Source-session validity and revocation
- **D02** Independent expert anchors and episode admission
- **D03** Real source histories and rights
- **D04** Distinct strategy, entry and holding versions
- **D05** Durable user decision/thesis mapping
- **D06** Economic margins, endpoints and formal-read law
- **D07** Source and model-vintage eligibility
- **D08** Fill, costs, latency and capacity assumptions
- **D09** Visual architecture and user comprehension
- **D10** Exact source custody, worker admission and independence
- **D11** Release, telemetry and safe rollback
- **D12** Final US capability and claim boundary

## Native PR snapshot

70 named Macro PR heads/states below were read directly. The link in the head column identifies the inspected commit; for a squash merge, use the PR’s merge commit for the bytes on main. Review depth varies. Only checks or reviews expressly identified in the brief have been qualified.

| PR | Native state | Inspected head | Scope |
|---|---|---|---|
| [#5370](https://github.com/mastermindx-market-intelligence/macro/pull/5370) | Merged 2026-08-11 | [f9b79cfef7](https://github.com/mastermindx-market-intelligence/macro/commit/f9b79cfef7f9bc69c71738d3b4d685ad0bd460a7) | feat(prophet-us): union admission on the EARLY-TURN starter tier (bake-off §A2) |
| [#6320](https://github.com/mastermindx-market-intelligence/macro/pull/6320) | Merged 2026-08-24 | [f126bfbc07](https://github.com/mastermindx-market-intelligence/macro/commit/f126bfbc079a2ef30badc91b46315479650d1a6b) | Prophet US 2026-08-14 PIT replay settlement |
| [#6840](https://github.com/mastermindx-market-intelligence/macro/pull/6840) | Merged 2026-09-20 | [c9a8de51c1](https://github.com/mastermindx-market-intelligence/macro/commit/c9a8de51c16d4ef4618ed5f501126aed80d68581) | HOLD-FOR-SOL: b2-0(prophet): freeze B-15..B-19 disposition matrix + correction/replay/mutation law |
| [#7356](https://github.com/mastermindx-market-intelligence/macro/pull/7356) | Merged 2026-09-20 | [0b747f7ea1](https://github.com/mastermindx-market-intelligence/macro/commit/0b747f7ea16403e878f772a2eff43fec069cd615) | feat(prophet): add conservative B3 candidate-state core |
| [#7506](https://github.com/mastermindx-market-intelligence/macro/pull/7506) | Merged 2026-09-20 | [08a08dd7c7](https://github.com/mastermindx-market-intelligence/macro/commit/08a08dd7c7bbf01292e8e3e962d11727fb7f6652) | fix(prophet): preserve B1 identity epoch in B3 state |
| [#7569](https://github.com/mastermindx-market-intelligence/macro/pull/7569) | Merged 2026-09-21 | [50939c0015](https://github.com/mastermindx-market-intelligence/macro/commit/50939c0015389a8872823669cde378ecb8bea1a1) | feat(prophet): add strategy-bound B4 entry availability core |
| [#7687](https://github.com/mastermindx-market-intelligence/macro/pull/7687) | Merged 2026-09-22 | [50ad128f3e](https://github.com/mastermindx-market-intelligence/macro/commit/50ad128f3e767475d4b179e6a2790b07f33b12be) | fix(prophet): keep optional structural overlay from deadlocking B4 |
| [#7180](https://github.com/mastermindx-market-intelligence/macro/pull/7180) | Merged 2026-09-26 | [7875f7335d](https://github.com/mastermindx-market-intelligence/macro/commit/7875f7335daaa06db990640120b92b0534c3a946) | fix(prophet): bind US picks to completed sessions and exact source |
| [#7187](https://github.com/mastermindx-market-intelligence/macro/pull/7187) | Merged 2026-09-20 | [80003197c0](https://github.com/mastermindx-market-intelligence/macro/commit/80003197c05d08598403e95c12743f447dabd231) | fix(prophet): preserve committed price panels and disclose screen dates |
| [#7457](https://github.com/mastermindx-market-intelligence/macro/pull/7457) | Merged 2026-09-20 | [123bb84b20](https://github.com/mastermindx-market-intelligence/macro/commit/123bb84b20176e64ec1cd6414aa66843a66dc437) | feat(prophet): surface leaders waiting for entry |
| [#7572](https://github.com/mastermindx-market-intelligence/macro/pull/7572) | Merged 2026-09-23 | [5e43db462b](https://github.com/mastermindx-market-intelligence/macro/commit/5e43db462b5ffa4912874c0be32549f8e26baeda) | feat(prophet): preserve every eligible candidate in a searchable view |
| [#7581](https://github.com/mastermindx-market-intelligence/macro/pull/7581) | Merged 2026-09-23 | [5bb4a6544a](https://github.com/mastermindx-market-intelligence/macro/commit/5bb4a6544ae436701d9da30d11802975b588e6d8) | feat(prophet): bind B4 runtime owner facts fail closed |
| [#7584](https://github.com/mastermindx-market-intelligence/macro/pull/7584) | Merged 2026-10-05 | [2e11f4c0dc](https://github.com/mastermindx-market-intelligence/macro/commit/2e11f4c0dc678d4ad9ca0b9d9135c0daf0f8abf4) | fix(prophet-live): require proven basis provenance |
| [#7738](https://github.com/mastermindx-market-intelligence/macro/pull/7738) | Merged 2026-09-24 | [b143e7000b](https://github.com/mastermindx-market-intelligence/macro/commit/b143e7000b6afa003a15a7f934f4aaf099968d42) | feat(prophet): add shadow B4 fillability and gap/velocity policies |
| [#7751](https://github.com/mastermindx-market-intelligence/macro/pull/7751) | Merged 2026-09-23 | [01de8a7d36](https://github.com/mastermindx-market-intelligence/macro/commit/01de8a7d36a8ce2e09242c167ca5869d1db34a20) | research(prophet): preregister B4 entry-policy calibration |
| [#6705](https://github.com/mastermindx-market-intelligence/macro/pull/6705) | Merged 2026-09-01 | [d5f162f0cb](https://github.com/mastermindx-market-intelligence/macro/commit/d5f162f0cb38d1a566e1ccb49472c80366bc015a) | feat(prophet): ship bounded D5 earnings intelligence |
| [#8670](https://github.com/mastermindx-market-intelligence/macro/pull/8670) | Merged 2026-10-11 | [29df1a715c](https://github.com/mastermindx-market-intelligence/macro/commit/29df1a715ce4a8f76900ff0f447dcbcd55f31ddc) | fix(prophet): separate source clocks from publication and fill proof |
| [#8762](https://github.com/mastermindx-market-intelligence/macro/pull/8762) | Merged 2026-10-11 | [a038753e0c](https://github.com/mastermindx-market-intelligence/macro/commit/a038753e0c50b777047d909823cdd5c8e7c6887a) | Prophet: add lossless early-observation discovery |
| [#8108](https://github.com/mastermindx-market-intelligence/macro/pull/8108) | Merged 2026-10-07 | [e4fe62ad0c](https://github.com/mastermindx-market-intelligence/macro/commit/e4fe62ad0cfe6d6201ac8103e673a3552eee5caf) | feat(prophet): journey reconciliation harness (release-integration proof tool) |
| [#8249](https://github.com/mastermindx-market-intelligence/macro/pull/8249) | Merged 2026-10-12 | [0b5348d8c6](https://github.com/mastermindx-market-intelligence/macro/commit/0b5348d8c616e13d120db0cd10be5dec29bb45ea) | Harden original Daily Brief and preserve independent quote clocks |
| [#8798](https://github.com/mastermindx-market-intelligence/macro/pull/8798) | Merged 2026-10-11 | [73a37ce16e](https://github.com/mastermindx-market-intelligence/macro/commit/73a37ce16e582477a1cc2c75b8c7565c81cd07ac) | fix(prophet): distinguish active setups from open entries |
| [#9921](https://github.com/mastermindx-market-intelligence/macro/pull/9921) | Merged 2026-10-21 | [7e0cf6c655](https://github.com/mastermindx-market-intelligence/macro/commit/7e0cf6c655632be9e75188db1982504450183a43) | fix(prophet): disclose validation_failed receipts — split the plan-not-built cohort by the intake's own failure record |
| [#9922](https://github.com/mastermindx-market-intelligence/macro/pull/9922) | Merged 2026-10-21 | [9fdaf51363](https://github.com/mastermindx-market-intelligence/macro/commit/9fdaf513631866a1f61f89bf7f5f6a38640ca50e) | docs(prophet): R7 end-to-end program records — continuation handoff, Agent OS workstream, orchestrator dispositions |
| [#9928](https://github.com/mastermindx-market-intelligence/macro/pull/9928) | Merged 2026-10-21 | [a99c8a027d](https://github.com/mastermindx-market-intelligence/macro/commit/a99c8a027dacda0f65b82ffa67c81250f5522e27) | prophet r7 records r2: Q06 Gate S acceptance records (F1), intel/regional dispositions, Stage 1 checkpoint |
| [#9933](https://github.com/mastermindx-market-intelligence/macro/pull/9933) | Merged 2026-10-21 | [3de9dad902](https://github.com/mastermindx-market-intelligence/macro/commit/3de9dad902374430371a00d9a7343217db036267) | prophet r7: named base_after_event receipt for formation-postdates-event clock refusals (Stage 1 product truth, step 2) |
| [#9935](https://github.com/mastermindx-market-intelligence/macro/pull/9935) | Merged 2026-10-21 | [7f6616b7bf](https://github.com/mastermindx-market-intelligence/macro/commit/7f6616b7bf2b3f31762bb95d130ee028309c82c0) | prophet lab: B04-A0 evidence dossier wrapper + closed reason map (A7–A12, 57 tests, CI-registered) |
| [#9936](https://github.com/mastermindx-market-intelligence/macro/pull/9936) | Merged 2026-10-21 | [f23b02479a](https://github.com/mastermindx-market-intelligence/macro/commit/f23b02479a01044df32b7b144ac4d6af680805b3) | prophet r7 records r3: INTEL done (B04-A0 + d06num), regional review reports, D06 proposal, checkpoint 05:1xZ |
| [#9945](https://github.com/mastermindx-market-intelligence/macro/pull/9945) | Merged 2026-10-21 | [b0f8eb3b8d](https://github.com/mastermindx-market-intelligence/macro/commit/b0f8eb3b8d33314b9f28b5a085cbf21d1e5dea59) | prophet r7 B05: same-read join between the B3 candidate projection and B4 Availability |
| [#9947](https://github.com/mastermindx-market-intelligence/macro/pull/9947) | Merged 2026-10-21 | [cfb8b81fa2](https://github.com/mastermindx-market-intelligence/macro/commit/cfb8b81fa2b432a117b69f4c5f4e1fb13974f498) | prophet r7 B23: journey latency acceptance — lab timing capture, lab serve, latency report (hermetic) |
| [#9951](https://github.com/mastermindx-market-intelligence/macro/pull/9951) | Merged 2026-10-22 | [4a47aac23e](https://github.com/mastermindx-market-intelligence/macro/commit/4a47aac23e13a13455a94ca3fae74f23db5daf4a) | prophet r7 B01: durable reconcile CLI refuses a caller-supplied recorded_at (writer clock only) |
| [#9954](https://github.com/mastermindx-market-intelligence/macro/pull/9954) | Merged 2026-10-22 | [7fa87f9bf4](https://github.com/mastermindx-market-intelligence/macro/commit/7fa87f9bf42492573ac3a743ff8bd9b0f7878cb6) | prophet r7 Wave A: a1 |
| [#9955](https://github.com/mastermindx-market-intelligence/macro/pull/9955) | Merged 2026-10-22 | [ff052167aa](https://github.com/mastermindx-market-intelligence/macro/commit/ff052167aa16b2463bc9f1468412806c9c1842e0) | prophet r7 Wave A: a3 |
| [#9956](https://github.com/mastermindx-market-intelligence/macro/pull/9956) | Merged 2026-10-22 | [31a61ba8ff](https://github.com/mastermindx-market-intelligence/macro/commit/31a61ba8fff3269e35d1653daa38202810871c38) | prophet r7 Wave A: a2 |
| [#9959](https://github.com/mastermindx-market-intelligence/macro/pull/9959) | Merged 2026-10-21 | [628cc4c69e](https://github.com/mastermindx-market-intelligence/macro/commit/628cc4c69ec1a561530ac700f862b102242c4770) | prophet r7: capture-only nightly B4 same-read decision-time stamps (F22) |
| [#9999](https://github.com/mastermindx-market-intelligence/macro/pull/9999) | Merged 2026-10-22 | [feb86035c3](https://github.com/mastermindx-market-intelligence/macro/commit/feb86035c339e8eb992a9636bfcc90d871e5e0ba) | prophet r7: B21 U2 — journey notifications pure producer half |
| [#10174](https://github.com/mastermindx-market-intelligence/macro/pull/10174) | Open Draft | [29cfb98b15](https://github.com/mastermindx-market-intelligence/macro/commit/29cfb98b15d2f1a7d39489024c69e76fc46b6ff0) | [Draft] Prophet V4 recovery: wave census and B17 frozen-input handoff |
| [#10176](https://github.com/mastermindx-market-intelligence/macro/pull/10176) | Open Draft | [228c25d376](https://github.com/mastermindx-market-intelligence/macro/commit/228c25d37617a7217c8f65f1613ade701a2fe01a) | fix(prophet): distinguish withdrawn episodes in private Lab reads (B2-1) |
| [#10180](https://github.com/mastermindx-market-intelligence/macro/pull/10180) | Open Draft | [943906af5c](https://github.com/mastermindx-market-intelligence/macro/commit/943906af5c0478e6bcf43f601b7f001fc30e0914) | [Draft] Prophet B2: recover B-17 frozen inputs and bounded cutoff replay |
| [#10202](https://github.com/mastermindx-market-intelligence/macro/pull/10202) | Open Draft | [2ea0bf0b21](https://github.com/mastermindx-market-intelligence/macro/commit/2ea0bf0b213242ff06472f18306dbdb059443fa9) | [V4-A2] Settlement manifest: exact served-byte projection and sentinel gates |
| [#10209](https://github.com/mastermindx-market-intelligence/macro/pull/10209) | Open Draft | [da3a04518f](https://github.com/mastermindx-market-intelligence/macro/commit/da3a04518f13695339ab54421e3894632d3b6ba4) | [PROPHET V4-A2][HOLD] Genuine UTC compute clock at private index writer |
| [#9634](https://github.com/mastermindx-market-intelligence/macro/pull/9634) | Open | [48adda3e4d](https://github.com/mastermindx-market-intelligence/macro/commit/48adda3e4d0d6acf2c60006775c2e565c1cca3a7) | fix(prophet): retain exact Turn Watch producer clocks |
| [#9610](https://github.com/mastermindx-market-intelligence/macro/pull/9610) | Open | [12966f1f25](https://github.com/mastermindx-market-intelligence/macro/commit/12966f1f25dbd03dbd6d9f4dddc0f00e5595d7f8) | fix(prophet): qualify early evidence and prospective universe coverage |
| [#7227](https://github.com/mastermindx-market-intelligence/macro/pull/7227) | Open Draft | [17987ce512](https://github.com/mastermindx-market-intelligence/macro/commit/17987ce512661e24d6fe69bc0ea18ee76e62e976) | [HOLD-FOR-SOL] Stage TURN WATCH v2 row evidence for idempotent retries |
| [#9495](https://github.com/mastermindx-market-intelligence/macro/pull/9495) | Open Draft | [0661c53d2a](https://github.com/mastermindx-market-intelligence/macro/commit/0661c53d2af2b3995163aef08e3b8ba285fc4e39) | Prophet: restore detailed opportunity cards and connected setup workspace |
| [#8444](https://github.com/mastermindx-market-intelligence/macro/pull/8444) | Open Draft | [6b45b8693f](https://github.com/mastermindx-market-intelligence/macro/commit/6b45b8693ff64c26dc4a8c0dcea4cbedffa810f0) | feat(prophet): compose shared coverage and truthful Plan relations |
| [#7264](https://github.com/mastermindx-market-intelligence/macro/pull/7264) | Open Draft | [214e0eda8c](https://github.com/mastermindx-market-intelligence/macro/commit/214e0eda8cea910a52aa592a1b7fdecc345748fc) | feat(prophet): native private-Lab earnings research view |
| [#9821](https://github.com/mastermindx-market-intelligence/macro/pull/9821) | Open | [cac29b2909](https://github.com/mastermindx-market-intelligence/macro/commit/cac29b29094f3e0bf403d01b715b067ad96f6820) | fix(prophet): revalidate profitability evidence before interpretation |
| [#9714](https://github.com/mastermindx-market-intelligence/macro/pull/9714) | Open | [a1511d63de](https://github.com/mastermindx-market-intelligence/macro/commit/a1511d63de8cb1d65287da95d5d6e9f9f49a0015) | fix(prophet): refuse lossy peer roster key normalization |
| [#9731](https://github.com/mastermindx-market-intelligence/macro/pull/9731) | Open | [4d40006d73](https://github.com/mastermindx-market-intelligence/macro/commit/4d40006d73d3a9e1306c2a2da110a3a90a946a90) | fix(prophet): qualify entry comparison basis before price conclusions |
| [#7734](https://github.com/mastermindx-market-intelligence/macro/pull/7734) | Open Draft | [f277be2adf](https://github.com/mastermindx-market-intelligence/macro/commit/f277be2adf5e295f6d5b23f1c520ac8b5fc27704) | feat(prophet-live): expose NBBO + session-open substrate for B4 policy |
| [#7772](https://github.com/mastermindx-market-intelligence/macro/pull/7772) | Open Draft | [2c198dd2cd](https://github.com/mastermindx-market-intelligence/macro/commit/2c198dd2cdcf359729dd9ec07f8a1e74f5b888d9) | research(prophet): add RQ1 point-in-time research matrix spine |
| [#7455](https://github.com/mastermindx-market-intelligence/macro/pull/7455) | Open Draft | [ebc7604b62](https://github.com/mastermindx-market-intelligence/macro/commit/ebc7604b624adb8452041d8240f7cda41733f167) | Lane C: closed-session subtheme leadership observations |
| [#7508](https://github.com/mastermindx-market-intelligence/macro/pull/7508) | Open Draft | [a24458aa90](https://github.com/mastermindx-market-intelligence/macro/commit/a24458aa90eeaffb6230d3da414bff3256a9ab9d) | DRAFT / HOLD: Lane D fail-closed stock entry context |
| [#7604](https://github.com/mastermindx-market-intelligence/macro/pull/7604) | Open Draft | [abcf15fad3](https://github.com/mastermindx-market-intelligence/macro/commit/abcf15fad369534eae73207e338913f2da96e8b4) | feat(prophet): measure emerging subtheme funnel gaps |
| [#8091](https://github.com/mastermindx-market-intelligence/macro/pull/8091) | Open | [410965bd24](https://github.com/mastermindx-market-intelligence/macro/commit/410965bd243d94e9f0e528e15f0c97df53fae732) | fix(prophet): capture prospective peer evidence inputs |
| [#8192](https://github.com/mastermindx-market-intelligence/macro/pull/8192) | Open | [07136c56ec](https://github.com/mastermindx-market-intelligence/macro/commit/07136c56ec6f8492067b468f90c6b4372ca649b4) | feat(prophet): release complete prospective capture and integrity verification |
| [#8004](https://github.com/mastermindx-market-intelligence/macro/pull/8004) | Open Draft | [f5898f9b0b](https://github.com/mastermindx-market-intelligence/macro/commit/f5898f9b0b90cb317ff1e225ae757406ae0ab558) | fix(prophet): bind episode security before issuer evidence |
| [#8308](https://github.com/mastermindx-market-intelligence/macro/pull/8308) | Open Draft | [446ffd0f10](https://github.com/mastermindx-market-intelligence/macro/commit/446ffd0f1062dd064c0716b576ceba7ce90acf2b) | [HOLD-FOR-SOL] feat(prophet): model Cycle funding and original-equity recovery |
| [#7868](https://github.com/mastermindx-market-intelligence/macro/pull/7868) | Open Draft | [3ad50f9d92](https://github.com/mastermindx-market-intelligence/macro/commit/3ad50f9d92d560a8375fd56a350243ee3aa99a93) | research(prophet-us r6/w3): Cycle (a) macro diagnostic pre-registration v3 (full-vintage store) |
| [#10062](https://github.com/mastermindx-market-intelligence/macro/pull/10062) | Open Draft | [af255c2fd7](https://github.com/mastermindx-market-intelligence/macro/commit/af255c2fd720da49c1432a7a2f0ee1132cf44301) | prophet r7: B21 U5 — drain stale-mandatory-fact guard + A2-N3 watchlist footnote |
| [#8325](https://github.com/mastermindx-market-intelligence/macro/pull/8325) | Open Draft | [604273045d](https://github.com/mastermindx-market-intelligence/macro/commit/604273045df4a277f0895093d8bebcd96a4e795f) | research: Prophet Timing State Engine audit and implementation masterplan |
| [#7929](https://github.com/mastermindx-market-intelligence/macro/pull/7929) | Open Draft | [e1a6524ecf](https://github.com/mastermindx-market-intelligence/macro/commit/e1a6524ecfcdfee0f0cad251e0d502f2660c32a7) | research: Market Tide C1 benchmark, source bridge, and complete-history guards |
| [#8531](https://github.com/mastermindx-market-intelligence/macro/pull/8531) | Open | [46597b3486](https://github.com/mastermindx-market-intelligence/macro/commit/46597b348649080720c9a012f4e5970420e5215b) | research(prophet): complete emergence + ignition audit and R6 handoff |
| [#8759](https://github.com/mastermindx-market-intelligence/macro/pull/8759) | Open Draft | [48ee616394](https://github.com/mastermindx-market-intelligence/macro/commit/48ee616394fa6af60e2a113927de762e6b5df498) | docs(prophet): CEO master direction and execution handoff (2026-10-10) |
| [#8363](https://github.com/mastermindx-market-intelligence/macro/pull/8363) | Open Draft | [69846be73b](https://github.com/mastermindx-market-intelligence/macro/commit/69846be73b624625add90823624630a740c1ed4f) | docs(prophet): harden Astra research takeover context and existing-plan map |
| [#8240](https://github.com/mastermindx-market-intelligence/macro/pull/8240) | Open Draft | [6d920952dc](https://github.com/mastermindx-market-intelligence/macro/commit/6d920952dc07731139cefc8a41cbd9bf92be5acf) | feat(prophet): compile source-bound Early Leadership evidence |
| [#7762](https://github.com/mastermindx-market-intelligence/macro/pull/7762) | Open Draft | [6011b83094](https://github.com/mastermindx-market-intelligence/macro/commit/6011b830943d694738866eb79d51b68e64cc51b9) | research(prophet): freeze north-star quantitative research architecture |
| [#7980](https://github.com/mastermindx-market-intelligence/macro/pull/7980) | Open Draft | [677565283f](https://github.com/mastermindx-market-intelligence/macro/commit/677565283ff5fe6d22a2d5345242132903177cd5) | docs(prophet): original-track product, recovery and scientific decisions |
| [#8271](https://github.com/mastermindx-market-intelligence/macro/pull/8271) | Open Draft | [7b19b87eb6](https://github.com/mastermindx-market-intelligence/macro/commit/7b19b87eb61d3b5d04197d2c5e346e0163f894d5) | feat(prophet-w3): add guarded post-floor validation report |
| [#7238](https://github.com/mastermindx-market-intelligence/macro/pull/7238) | Open Draft | [69d0b74b48](https://github.com/mastermindx-market-intelligence/macro/commit/69d0b74b483125ce198c3b56886b01f477902299) | research(prophet): checkpoint frozen-price loss and winner-retention replay |

## Discovery boundary

The bounded title screen of open Macro PRs with “Prophet” returned 62 at its observation. It includes adjacent markets and news work and misses PRs whose titles omit Prophet, including #10202. We augmented it with original-wave, R6, R7 and linked-carrier reads. This list is for overlap checking; inclusion is not a work order.

[#9610](https://github.com/mastermindx-market-intelligence/macro/pull/9610) · [#10235](https://github.com/mastermindx-market-intelligence/macro/pull/10235) · [#10174](https://github.com/mastermindx-market-intelligence/macro/pull/10174) · [#9821](https://github.com/mastermindx-market-intelligence/macro/pull/9821) · [#10209](https://github.com/mastermindx-market-intelligence/macro/pull/10209) · [#10176](https://github.com/mastermindx-market-intelligence/macro/pull/10176) · [#10180](https://github.com/mastermindx-market-intelligence/macro/pull/10180) · [#9634](https://github.com/mastermindx-market-intelligence/macro/pull/9634) · [#9731](https://github.com/mastermindx-market-intelligence/macro/pull/9731) · [#10062](https://github.com/mastermindx-market-intelligence/macro/pull/10062) · [#8444](https://github.com/mastermindx-market-intelligence/macro/pull/8444) · [#9495](https://github.com/mastermindx-market-intelligence/macro/pull/9495) · [#9714](https://github.com/mastermindx-market-intelligence/macro/pull/9714) · [#7734](https://github.com/mastermindx-market-intelligence/macro/pull/7734) · [#7772](https://github.com/mastermindx-market-intelligence/macro/pull/7772) · [#7762](https://github.com/mastermindx-market-intelligence/macro/pull/7762) · [#9422](https://github.com/mastermindx-market-intelligence/macro/pull/9422) · [#9369](https://github.com/mastermindx-market-intelligence/macro/pull/9369) · [#9294](https://github.com/mastermindx-market-intelligence/macro/pull/9294) · [#8759](https://github.com/mastermindx-market-intelligence/macro/pull/8759) · [#8714](https://github.com/mastermindx-market-intelligence/macro/pull/8714) · [#8495](https://github.com/mastermindx-market-intelligence/macro/pull/8495) · [#8240](https://github.com/mastermindx-market-intelligence/macro/pull/8240) · [#8531](https://github.com/mastermindx-market-intelligence/macro/pull/8531) · [#7264](https://github.com/mastermindx-market-intelligence/macro/pull/7264) · [#8192](https://github.com/mastermindx-market-intelligence/macro/pull/8192) · [#7499](https://github.com/mastermindx-market-intelligence/macro/pull/7499) · [#8363](https://github.com/mastermindx-market-intelligence/macro/pull/8363) · [#8271](https://github.com/mastermindx-market-intelligence/macro/pull/8271) · [#8325](https://github.com/mastermindx-market-intelligence/macro/pull/8325) · [#6871](https://github.com/mastermindx-market-intelligence/macro/pull/6871) · [#7963](https://github.com/mastermindx-market-intelligence/macro/pull/7963) · [#8141](https://github.com/mastermindx-market-intelligence/macro/pull/8141) · [#8308](https://github.com/mastermindx-market-intelligence/macro/pull/8308) · [#8091](https://github.com/mastermindx-market-intelligence/macro/pull/8091) · [#7018](https://github.com/mastermindx-market-intelligence/macro/pull/7018) · [#8303](https://github.com/mastermindx-market-intelligence/macro/pull/8303) · [#7288](https://github.com/mastermindx-market-intelligence/macro/pull/7288) · [#7980](https://github.com/mastermindx-market-intelligence/macro/pull/7980) · [#7868](https://github.com/mastermindx-market-intelligence/macro/pull/7868) · [#7399](https://github.com/mastermindx-market-intelligence/macro/pull/7399) · [#7248](https://github.com/mastermindx-market-intelligence/macro/pull/7248) · [#7385](https://github.com/mastermindx-market-intelligence/macro/pull/7385) · [#8004](https://github.com/mastermindx-market-intelligence/macro/pull/8004) · [#7851](https://github.com/mastermindx-market-intelligence/macro/pull/7851) · [#7684](https://github.com/mastermindx-market-intelligence/macro/pull/7684) · [#7779](https://github.com/mastermindx-market-intelligence/macro/pull/7779) · [#7604](https://github.com/mastermindx-market-intelligence/macro/pull/7604) · [#7286](https://github.com/mastermindx-market-intelligence/macro/pull/7286) · [#7303](https://github.com/mastermindx-market-intelligence/macro/pull/7303) · [#7168](https://github.com/mastermindx-market-intelligence/macro/pull/7168) · [#7174](https://github.com/mastermindx-market-intelligence/macro/pull/7174) · [#6996](https://github.com/mastermindx-market-intelligence/macro/pull/6996) · [#7254](https://github.com/mastermindx-market-intelligence/macro/pull/7254) · [#6801](https://github.com/mastermindx-market-intelligence/macro/pull/6801) · [#7218](https://github.com/mastermindx-market-intelligence/macro/pull/7218) · [#7238](https://github.com/mastermindx-market-intelligence/macro/pull/7238) · [#7066](https://github.com/mastermindx-market-intelligence/macro/pull/7066) · [#7043](https://github.com/mastermindx-market-intelligence/macro/pull/7043) · [#7059](https://github.com/mastermindx-market-intelligence/macro/pull/7059) · [#6990](https://github.com/mastermindx-market-intelligence/macro/pull/6990) · [#6264](https://github.com/mastermindx-market-intelligence/macro/pull/6264)

## New measurement of the retained origination receipts

I enumerated all 37 files in [the origination receipt directory](https://github.com/mastermindx-market-intelligence/macro/tree/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts). Two filenames carry the backfill prefix and are outside this calculation. Parsing all 35 run-numbered receipt bodies at the same pin yielded **31 distinct source sessions**, August 7 through October 29. The receipts report **1,678 admissions across runs and 674 originations**. All 674 listed plan IDs are distinct; in all 35 files the reported origination count matches both the ID-list length and the origination-record count. Sixteen identify a compressed source snapshot in the explicit snapshot-path field. The other 19 require separate provenance checks. Four source dates each appear twice: August 28, September 4, September 25 and October 2.

This census counts retained source acts. Admissions repeat across runs, some sessions lack a retained file, and some runs are manual. An origination has no implied protected delivery or fill. Do not divide 674 by 1,678 to infer trade conversion or coverage. The 35 files also cannot recover the B-17 pre-archive denominator. The most recent row is a ready specimen for tracing clocks through the protected reader.

| Run-numbered receipt | Source session | Admitted | Originated | Snapshot path recorded |
|---|---|---:|---:|---|
| [31292839484](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/31292839484-2-2be54ee76b7497cd.json) | 2026-08-07 | 30 | 2 | No |
| [31440972065](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/31440972065-1-ccc709560583c1f5.json) | 2026-08-10 | 35 | 25 | No |
| [31649984834](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/31649984834-1-f29436e0235c17b0.json) | 2026-08-12 | 53 | 25 | No |
| [31753425298](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/31753425298-1-4f26a3b5243dfde0.json) | 2026-08-13 | 51 | 27 | No |
| [32077948964](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/32077948964-1-dedc41050d307d52.json) | 2026-08-17 | 44 | 20 | No |
| [32207351396](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/32207351396-1-6db24618d5077872.json) | 2026-08-18 | 33 | 21 | No |
| [32246809547](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/32246809547-1-2959cbff4a3fc358.json) | 2026-08-19 | 42 | 12 | No |
| [32426513915](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/32426513915-1-e847b443109aeef2.json) | 2026-08-20 | 23 | 7 | No |
| [32534736736](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/32534736736-1-19a88744580416b8.json) | 2026-08-21 | 37 | 27 | No |
| [32786919396](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/32786919396-1-39ed2db50b37b043.json) | 2026-08-24 | 41 | 11 | No |
| [32908543584](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/32908543584-1-c0868a1641762eca.json) | 2026-08-25 | 41 | 9 | No |
| [33135155521](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/33135155521-1-0a0227052b506776.json) | 2026-08-27 | 32 | 13 | No |
| [33228310679](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/33228310679-1-82e3cab875c848a3.json) | 2026-08-28 | 34 | 3 | No |
| [33283677537](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/33283677537-1-d0d362b35fed3600.json) | 2026-08-28 | 37 | 13 | No |
| [33458443066](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/33458443066-1-2aff0728d78afb88.json) | 2026-08-31 | 25 | 11 | No |
| [33821174184](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/33821174184-1-8def85dd9bd13500.json) | 2026-09-04 | 36 | 4 | No |
| [33860741475](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/33860741475-1-7c2232aab4bf4c48.json) | 2026-09-04 | 35 | 20 | No |
| [34727280397](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/34727280397-1-6a380f4e29f25932.json) | 2026-09-11 | 30 | 20 | No |
| [35478395992](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/35478395992-1-3caa801ccdf482f2.json) | 2026-09-18 | 31 | 26 | No |
| [36241094249](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/36241094249-1-716c0da79512aceb.json) | 2026-09-25 | 39 | 22 | Yes |
| [36283591439](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/36283591439-1-c785c0ea24233464.json) | 2026-09-25 | 40 | 1 | Yes |
| [36832376691](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/36832376691-1-301762a6ad6845a4.json) | 2026-09-30 | 27 | 15 | Yes |
| [37122052286](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/37122052286-1-baa2eb14e257e22a.json) | 2026-10-02 | 54 | 29 | Yes |
| [37169452721](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/37169452721-1-59ac53c1bdfdf110.json) | 2026-10-02 | 55 | 1 | Yes |
| [37402815092](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/37402815092-1-80c672c79a8e66aa.json) | 2026-10-05 | 45 | 26 | Yes |
| [37558610387](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/37558610387-1-ed967d68adbc2fa7.json) | 2026-10-06 | 58 | 25 | Yes |
| [37716547994](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/37716547994-1-ea9a1a6412e6b7c7.json) | 2026-10-07 | 49 | 12 | Yes |
| [37873292221](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/37873292221-1-8bdf261a8ef953e5.json) | 2026-10-08 | 67 | 31 | Yes |
| [38661819472](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/38661819472-1-f04429104ba64d52.json) | 2026-10-14 | 72 | 38 | Yes |
| [39420247928](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/39420247928-1-b16040c9b350b1a7.json) | 2026-10-19 | 81 | 30 | Yes |
| [39585571282](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/39585571282-1-056fe334e49275fe.json) | 2026-10-20 | 87 | 34 | Yes |
| [39776286544](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/39776286544-1-3c9b1c1b41fcb43c.json) | 2026-10-21 | 78 | 23 | Yes |
| [39951371448](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/39951371448-1-8ae9156aabb387dc.json) | 2026-10-22 | 91 | 41 | Yes |
| [40090649378](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/40090649378-1-3cb2f40731fd0935.json) | 2026-10-23 | 76 | 13 | Yes |
| [41053380265](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/origination_receipts/41053380265-1-e65cf941e58ff2d8.json) | 2026-10-29 | 69 | 37 | Yes |

## Independent audit of W1 and parent adjudication

Paid Fabric census `prophet-us-entry-timing-w1-evidence-census-20261031-01`, under root `prophet-us-fable-meta-ceo-20260923-001`, returned terminal rc 0. Retained response SHA-256 `fa09d0aea7e68c2da48542d306061eb523d51e8aecca1d7ce0f74c400c6bcda0`. I checked the material findings against native GitHub jobs, the two disclosure objects and the actual PRs. The useful parts of the return are incorporated below; the complete worker narrative does not qualify for acceptance as written.

| Finding | Direct check and disposition |
|---|---|
| W0 source attribution | [#5289](https://github.com/mastermindx-market-intelligence/macro/pull/5289) and [#5304](https://github.com/mastermindx-market-intelligence/macro/pull/5304) are design and revision; [#5305](https://github.com/mastermindx-market-intelligence/macro/pull/5305) is the **Aug 9** receipt replay, merged August 11 10:01Z. [#5370](https://github.com/mastermindx-market-intelligence/macro/pull/5370) is the later union gate/display split. The specific W0 queue counter remains unidentified. Do not reopen the completed queue work on that account. |
| Original W1 bake | The authoritative later disclosure says the August 11 bake never ran. [Manual dispatch 31543112462](https://github.com/mastermindx-market-intelligence/macro/actions/runs/31543112462), created 22:36Z, was still recorded queued at read. The worker’s suggestion the Aug 11 board was never reconstructed conflicts with the explicitly labeled Aug 13 reconstruction in the [disclosure](https://github.com/mastermindx-market-intelligence/macro/blob/1c85878983323f9ab38fff56a15771166d0f8aeb/data/prophet/backfill_disclosures.json). Contemporaneous evidence and later reconstruction remain separate. |
| Operational recovery | [August 12 run 31649984834](https://github.com/mastermindx-market-intelligence/macro/actions/runs/31649984834): engine failed, publish and US ledger jobs succeeded, source receipt records 25 originations. [August 13 run 31753425298](https://github.com/mastermindx-market-intelligence/macro/actions/runs/31753425298): engine job 94656991904, publish 94689379837 and US ledger 94748629857 all succeeded; source receipt records 27 originations. [August 19 run 32310821528](https://github.com/mastermindx-market-intelligence/macro/actions/runs/32310821528): engine 96286569640, publish 96382099931 and US ledger 96429018409 also succeeded. The latter two runs ended cancelled overall. The worker’s “zero jobs” for Aug 13 and “first green US chain” on Aug 19 are contradicted by the jobs. Those three green steps do not prove exactly what a protected user saw. |
| W2 | The governing wave is TODO and this census found no accepted result satisfying both a held-out timing delta and false-positive cost for the frozen population. The worker’s stronger universal absence claim exceeds the discovery coverage. Carry the explicit proof gap and do not commission a replacement of a trial already registered. |
