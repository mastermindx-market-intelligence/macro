# D08C source and baseline audit

All claims are scoped to the pins below. Source inspection proves implementation semantics at that revision; it does not prove activation, permissions, current private reference contents or successful production journeys.

## Canonical coordinates and owner verification

The [Chairman handoff](https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/handoffs/D08C-options-plan-review.md) and [common contract](https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/COMMON_SESSION_BRIEF.md) were consumed at one immutable programme SHA. The D08 owner is `mastermindx-3`, Draft PR #10649, branch `design/d08-options-integration-20261103`, inspected head `e89f527e3267b1d1dd27ac7507e9a25983c0c903`. Its frozen [D08-OPTIONS/1.0.0](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/research/design_candidates/production_design_20261102/d08/SLICE_INTERFACES.json) is a semantic design contract, not a released wire schema.

The D08C branch and existing PR comments were checked before creating a disjoint candidate. No separate existing D08C branch was found in that bounded discovery. This is a discovery observation, not a claim that all company work was exhaustively searched. The original held persistence carrier is Terminal #804, author `mastermindxryan`, branch `claude/iw2-g5-thesis-references-20261004`, inspected head `27df56d997df0ae94a17b6b8e2d14867431bb394`.

## Current Terminal implementation

Repository: `mastermindx-market-intelligence/mastermind-terminal`; protected source pin `2ded360882b9c721e690907ff363b553781fb920`.

| Source | Blob SHA where captured | Source-backed finding |
| --- | --- | --- |
| [OptionsWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/workspaces/OptionsWorkspace.tsx) | Source pinned by commit | Existing Options pane router and URL synchronization; Plan is not a new admitted `tab` value |
| [StructureView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/structure/StructureView.tsx) | Source pinned by commit | Root-scoped EOD structure, no polling, independent panel availability and stale-request protection |
| [structureTypes.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/structure/structureTypes.ts) | `51a27ed5fda25b62f766898ae6a53f0cf6c38a28` | Structure envelopes and panel field meanings |
| [OiChangePanel.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/structure/OiChangePanel.tsx) | `27966948fd0cebfaff2a285ae97ec78f9a3c984a` | Root/all scope and sortable OI-change detail |
| [optionsContractShortlist.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/optionsContractShortlist.ts) | `8d42da79f3e5bbda9ea236df93845824feb4900d` | Four-pin cap; exact identity distinct from source-list pin identity; observations copied without implicit refresh |
| [optionsPlanDraft.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/optionsPlanDraft.ts) | `1b02689501cd26226b61e7a5d3fa8f5868552f7b` | Detached 1–4-leg research draft; nullable authored assumptions; thesis/invalidation/horizon |
| [optionsPlanPayoff.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/optionsPlanPayoff.ts) | `cb68f58f3f64e3e586c7b775996209d177ca6a22` | Fixed expiry scenario grid; qualified response validation; focus view uses existing samples |
| [OptionsPlanPayoffPanel.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/options/OptionsPlanPayoffPanel.tsx) | `fb46e15b98e8221beb402f5558651a943b3f981f` | Incomplete/access/loading/unavailable/ready UI; edits clear obsolete numerical output |
| [OptionsPlanDraftEditor.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/options/OptionsPlanDraftEditor.tsx) | `e2b76e30ed12c12efa751d589b0820f7ae5c57aa` | Existing authored-input component to reuse |
| [expiry route](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/app/api/options/plan/expiry/route.ts) | `8aa0fb159c70bf5ab5ec4653857ab744ab6000a0` | Authenticated private/no-store proxy, reconstructed request, bounded bodies, 15-second upstream timeout; no persistence |
| [OptionsPlanInvestigationHost.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/options/OptionsPlanInvestigationHost.tsx) | `a6c5b16567f493ed4acb588e19d4123b4b751c59` | Visibility/focus host; leaves New, admission, Save and routing to incumbent Investigation owner |
| [InvestigationWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/workspaces/InvestigationWorkspace.tsx) | `4126bd73348aa3fdd95f31451e570ce089a631e7` | Incumbent journal, Save, revision and alert integration; protected composition lacks Plan admission/revision props |
| [investigationContracts.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/investigationContracts.ts) | `2060d5f8c92aa749ce1360a0dbd5c3a73bcf6e1f` | Protected closed manifest does not admit `option_plan` |
| [investigationJournal.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/investigationJournal.ts) | `a8b615342e0fbd8ceaec1e2d24c85fd4dc81d36d` | Same-owner pending custody and verified session retention before submission |
| [investigationSave.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/investigationSave.ts) | `a15205f61cb2ca00b0f084d4aee7a1e561d203c3` | Protected Save protocol; do not assume held-head retry semantics are already released |
| [investigations.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/investigations.ts) | `536b971c2b8205fdc44e7e0529c34b83a41f5df3` | Existing `apply_investigation_revision_v2` and `read_investigation_operation_v2` consumers |
| [investigations route](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/app/api/investigations/route.ts) | `df263ca7160c109ef70d302738b37ef9677cec93` | Availability gate, authenticated ownership, closed requests and private/no-store responses |
| [investigationWatch.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/investigationWatch.ts) | `ae67dc3e1eb873d86f250c2fb30222197ca533aa` | Price threshold and options-wall proximity previews; no generic condition evaluator |
| [investigationReview.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/investigationReview.ts) | `5a59c2bf1b9414c8e25a8348d2d68ddd5fe31cbd` | Saved revision, current evidence and owner firing/delivery status remain distinct |

The [consumer integration document](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/docs/OPTIONS_PLAN_PAYOFF_CONSUMER_2026-10-24.md), blob `06c482a7f3594818b07a9c4b003602edac4ba34a`, distinguishes fixture evidence from authenticated persistence. `/dev/options-plan` is harness/inventory evidence assigned to D08D, not a shipping route or automatic production entry point. The existence of a component or a passing historical fixture does not prove its mounted product path.

## Original held persistence implementation

Read at Terminal #804 head `27df56d997df0ae94a17b6b8e2d14867431bb394`:

| File | Blob | Required future reuse |
| --- | --- | --- |
| `terminal/components/workspaces/InvestigationWorkspace.tsx` | `2cd4d2002cee8bc3fdc9fe01f2e35597287949ef` | Native Plan admission, embedded history and exact-revision interfaces |
| `terminal/components/options/OptionsPlanInvestigationHost.tsx` | `1038cc4bd9e79a62055a3ed7fbfe2d1148a52971` | Owner-controlled embedding and stale callback guards |
| `terminal/lib/investigationOptionPlanAdmission.ts` | `ebb5a5edfe6cdb0d999b37ae2693a280b4315407` | Local transfer only into fresh native draft; no ID, Save, storage or calculation side effect |
| `terminal/lib/investigationContracts.ts` | `7b47b0414f44d14df7ca349b9af60fe815f221c6` | `investigation_manifest.v3`, optional validated `option_plan`; explicit `scenario_capture` conflict |
| `terminal/lib/investigationSave.ts` | `e53914ca9fdfd22c1b869ebe1c2a0abd14e96d12` | Exact receipt and legacy uncertainty handling; only proved `not_applied` can enable a new owner attempt |

The PR's release hold `5989604142`, T03k refusal, unresolved-effect and exact-0030 conditions remain carried. No relabel, un-draft, replay, replacement carrier, merge or deployment follows from this design audit.

## Macro producer, independently located from the known endpoint

Repository `mastermindx-market-intelligence/macro`, pin `d0516e1bad9cb5982d43d20c4167d0355cb70e2c`.

| File | Blob SHA | Meaning |
| --- | --- | --- |
| [app/options_plan.py](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/app/options_plan.py) | `cf48c517712b3f7b432e0e08feaaaa16d5ce0487` | Existing expiry endpoint |
| [app/options_plan_source.py](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/app/options_plan_source.py) | `dc15914e1a31e75f8227639cca9ac0bd2a28c83e` | Exact identity and private installed-reference custody |
| [engine/options_plan_expiry.py](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/engine/options_plan_expiry.py) | `90adf0153e161f54c426438c231139894a3a789d` | Narrow Plan bridge, one root/expiry, entire-curve refusal |
| [engine/options_payoff.py](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/engine/options_payoff.py) | `fdda1b660dc13c5ed3dad4e53b0a8feba8c56fff` | Signed cost and extrema; piecewise-linear expiry payoff |
| [lib/options_source_receipts.py](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/lib/options_source_receipts.py) | `fa1b7e73c7384991af2a74acdee4b328c8317f5a` | Explicit narrow ordinary SPY/QQQ reference-term policy |
| [engine/options_nbbo_cohort.py](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/engine/options_nbbo_cohort.py) | `b84426de82c9d55caa26e9dd95092460be6dda1b` | Exact OCC identity; millistrike representability |
| [private consumer contract](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/docs/OPTIONS_PLAN_PRIVATE_CONSUMER_2026-10-24.md) | `61f8015e026683b93a65da3758945e10728a10e4` | Activation depends on accepted original source, installation and independent review |

Presence of generic scenario/Greeks functions in the engine is not admission to this endpoint. No installed observation, contract coverage, activation flag, live producer response or executable quote was inspected or changed.

## Route and context map

Canonical registry ID is `terminal:options`, `/options`, with the current shared shell and access owner. Preserve native panes `desk`, `tape`, `tide`, `0dte`, `largest`, `tickers`, `vol`, `gex`, `surface`, `structure`, `volatility`, `positioning`, `levels`, `prophet`, `statistics`; current default is Tape. Preserve existing labels/aliases including `vol`/screener and `gex`/prism, and the legacy leaders/radar→Discover and fundamentals→Analysis destinations. No pane is removed by this slice.

D08 common headings are Desk, Flow, Exposure, Structure, Volatility, Statistics and Prophet; Futures remains a separate destination. Plan, Compare and Review are contextual tasks under the incumbent host, not new admitted URL query keys. Local task state must use the existing host's validated behavior. Do not introduce `?tab=plan`, a serialized Plan in a URL, a new hash router or a second navigation registry. D08 owns any later route admission.

On B→C, preserve validated same-origin return context: original node/lens/vintage, selected row, filters, focus and scroll where still valid. If the target disappeared, disclose a named fallback to the originating view. Never carry credentials, payloads or Save intent in return metadata. Actual holdings navigation remains D22-owned.

## Structure source and advanced capability

`StructureView` uses `flowGet` keys `max_pain:ROOT`, `oi_time:ROOT` and `oi_change:ROOT`; cross-root `oi_change` loads lazily when selected. It resets on committed root change, checks root consistency and suppresses late wrong-root responses. Its panels include OI by strike, OI by expiry, 18-month calls/puts history, put/call history, max-pain intrinsic curve, max pain by expiry and sortable root/all OI change. Keep each panel's own availability and basis; a missing panel does not blank the rest.

The data are nightly EOD and reported OI is nondirectional, generally t−1. Existing staleness is computed after more than three Eastern weekdays; that is not a complete exchange-holiday calendar. Display source dates, not a “LIVE” badge. Preserve the distinction between report date, position session and retrieval time.

## Paper baseline and exact custody

Verified file: **Terminal `01M3NSZGE8JWN2EZCSF0DT05RM`**. Direct Mastermind Paper is the single carrier. Live catalog `03cb81e960dab705b21b0695f3886d39c4792df629a6419163efef52338182e4` returned tool-scoped write acceptance. Each edit used a fresh exact-file guard and stable operation ID. A guard/token hash is not a document revision or approval.

| Page | Baseline | Representative inspected boards |
| --- | --- | --- |
| `p-2-0` | Structure / exposure references | Retained; shared D08 integration `1N2L-0` is held and untouched |
| `p-3-1` | Plan, 12 boards | `FS4-0` desktop dark EN; `HEB-0` phone dark EN; other theme/locale/tablet variants retained |
| `p-4-1` | Save/watch, 15 boards | `L6U-1` three verification outcomes; `KWI-1` whole-case Save; `LCO-1` phone |
| `p-5-1` | Review, 20 boards | `L94-1` saved reopen; `LLG-1` evidence→decision; `NUB-1` included prints; `NZE-1` linked package |
| `p-6-1` | Scenarios, 20 boards | `G9Q-0` main; `GZU-0` phone assumptions; `HBR-0` model requirements; theme/locale siblings retained |
| `p-7-1` | Compare, 4 boards | `KD8-0`, `KG5-0`, `KJ2-0`, `KLZ-0` |
| `p-P-1` | Build contracts, 12 boards | `G6A-0` Plan/watch/review; `LIJ-1` capture/verify/reopen; held unfinished boards retained |

Before images show useful analytical depth and explicit Save uncertainty. Weaknesses are long phone chains, dispersed task hierarchy and some modeled-value presentations that exceed the currently admitted expiry path. The new candidate reorganizes that depth; it does not delete the predecessor pages or infer their approval.

The new disjoint candidate page is `p-13-0`; exact boards and the separate D08C Read me page are recorded in `DESIGN_MANIFEST.json`. No old board, global token, file or folder was renamed/moved/deleted. Final organization into the proposed “MM · Options Plan & Review” location remains F03-owned; proposed names were not treated as discovered IDs.

## Verification limits

### Final foundation refresh

F01 [#10645](https://github.com/mastermindx-market-intelligence/macro/pull/10645) was refreshed at `abfecf1efc452383fe720cb3ea2016ad8d7088e0`; its [joint candidate.4](https://github.com/mastermindx-market-intelligence/macro/blob/abfecf1efc452383fe720cb3ea2016ad8d7088e0/research/design_candidates/production_design_20261102/f01/JOINT_SHELL_SYSTEM_CONTRACT.md) has whole-document blob `653d93bbce70a2515d677ecdb76bb21edfab750c`. §§2–5 are byte-identical to the original consumed candidate.4. Status/binding text now records F02's policy concurrence and later F01 implementation, while retaining PARTIAL / REQUEST_CHANGES / RIG draft. That separate F01 implementation does not authorize D08C product changes.

F02 [#10630](https://github.com/mastermindx-market-intelligence/macro/pull/10630) was refreshed at `c985c24e2558dbd4211d34e7bac2e62e50506ba3`. The token-map blob remains `a7ec801d3b559cc64f4fd57141c32f63098c6461`; no D08C token migration is needed. F02 reports policy concurrence and a scoped 31-board freeze, with its original Chinese-comparison effect and complete-set gate still held. These are attributed owner statuses, not D08C approval of that native set. Formal foundation release, actual Brain/host and focused-consumer qualification remain gates. Exact refresh metadata is in `verification/foundation_refresh.json`.

The live beta route produced an access-verification failure. Source plus Paper inspection therefore support design and contract decisions, not normal-data browser proof. Native advisors performed read-only reasoning; their historical test references are not rerun evidence. The synthetic oracle is the only calculation newly executed by this package. Independent artifact critique is recorded separately and is not a formal RIG receipt.
