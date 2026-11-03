# F01 / F02 foundation interface — candidate concurrence

**Status: F02 concurrence recorded; joint candidate qualification remains open.** This source artifact responds to F01's [coordination request](https://github.com/mastermindx-market-intelligence/macro/pull/10630#issuecomment-6596927050). It does not record F01 acceptance of the clarifications below, an independent review verdict, a released foundation or permission to implement.

## Parties, versions and custody

| Item | Exact reference |
| --- | --- |
| Assignment | [Production Design package at `6e1862867193ec6486a22001a0e4fb515da20448`](https://github.com/mastermindx-market-intelligence/macro/tree/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102) |
| F01 candidate | [Draft #10645](https://github.com/mastermindx-market-intelligence/macro/pull/10645), source branch `design/f01-shared-shell-v1-20261103-c4`; [README at `34b4a52ddf9b56e6a1d3eed7816cbf5feed2d985`](https://github.com/mastermindx-market-intelligence/macro/blob/34b4a52ddf9b56e6a1d3eed7816cbf5feed2d985/research/design_candidates/production_design_20261102/f01/README.md), blob `4d41247aac8918858195e8b294a0ee09d4b98098` |
| F02 component contract | `F02-SYSTEM/1.0.0-candidate.2`, [immutable system contract at `c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82`](https://github.com/mastermindx-market-intelligence/macro/blob/c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82/research/design_candidates/production_design_20261102/f02/SYSTEM_CONTRACT.md) |
| F02 source/data contract | `F02-SOURCE-DATA/1.0.0-candidate.2`, [source and data contract at the same commit](https://github.com/mastermindx-market-intelligence/macro/blob/c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82/research/design_candidates/production_design_20261102/f02/SOURCE_AND_DATA_CONTRACT.md) |
| F02 token reference | [token-map.json at the same commit](https://github.com/mastermindx-market-intelligence/macro/blob/c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82/research/design_candidates/production_design_20261102/f02/token-map.json), Git blob `a7ec801d3b559cc64f4fd57141c32f63098c6461`; semantic specimen roles, not a new production CSS namespace |
| F02 design source | [Draft #10630](https://github.com/mastermindx-market-intelligence/macro/pull/10630), branch `design/f02-system-v1-20261102-c2`; [actual Paper Read me page](https://app.paper.design/file/01M312VSDSZFVT45674GDVJVZN/p-9-0) |

F01 owns global navigation, shell slots, context/search/account behavior and focused/public/internal shell composition. F02 owns shared component anatomy, presentation semantics and their evidence specifications. Domain owners retain data, entitlement, query identity, export and mutation contracts. Each author keeps its own source and Paper targets; this artifact makes no change to F01's branch, boards or the shared return ledger outside F02's row.

The latest F01 source baseline's [shared-shell.css at Terminal `3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/shared-shell.css), blob `d40551b54752c7d577b459ddfa2b5da1f4f6cbf9`, was read directly. Its 224/196/72px rail and 64/56px header rules agree with the values already inspected for F02. This is a bounded source comparison, not a claim about the currently deployed revision or every change between the two source baselines.

## Concurrence and precise responsive rules

F02 concurs with F01's proposed 224/196/72/0px rail, 64/56px header, 24/20/16px horizontal content gutters, one contextual evidence inspector, 320px dock, 24px dock gap and 640px minimum primary workspace. The following cutoffs and behavior remove ambiguity from those values.

| Effective CSS viewport width | Expanded navigation | Header | Content gutter on each side |
| --- | ---: | ---: | ---: |
| At most 600px | No rail | 56px | 16px |
| Greater than 600px and at most 860px | No rail | 56px | 20px |
| Greater than 860px and less than 1200px | 196px | 64px | 20px |
| At least 1200px | 224px | 64px | 24px |

The 600px content-gutter boundary is the existing F02 specimen boundary. It is distinct from the 860px shell-navigation boundary. The inequalities above deliberately cover fractional effective CSS widths such as 600.5, 860.5 and 1199.5px. This is a proposed clarification requiring F01 acceptance: the historical source uses literal `min-width:861px` / `max-width:1199px` for its middle class, so its behavior in fractional gaps is not asserted to equal this continuous rule. Header internal padding remains F01's composition responsibility; a content gutter is not automatically a header token. In the desktop shell, an explicitly selected compact rail is 72px. Neither F02 nor a consumer may automatically change the user's navigation preference to make a dock fit.

Let `C` be the **measured usable content width after the actual shell, local reserved chrome and both content gutters**. Dock only when `C − 320 − 24 ≥ 640`; equivalently `C ≥ 984`. Additional reserved local chrome reduces `C`. The width of an enclosing Paper artboard or a device label is not a substitute for this measurement.

| Viewport | Rail | Both gutters | Usable content C | Width if docked | Candidate presentation |
| ---: | ---: | ---: | ---: | ---: | --- |
| 320 | 0 | 32 | 288 | −56 | Full-width overlay; 288px underlying content when closed |
| 390 | 0 | 32 | 358 | 14 | Full-width overlay; 358px underlying content when closed |
| 768 | 0 | 40 | 728 | 384 | 440px overlay; complete underlying comparison remains available |
| 1024 | 196 | 40 | 788 | 444 | 440px overlay |
| 1280 | 224 | 48 | 1008 | 664 | 320px dock plus 24px gap |
| 1440 | 224 | 48 | 1168 | 824 | 320px dock plus 24px gap |
| 1600 | 224 | 48 | 1328 | 984 | 320px dock plus 24px gap |

These are calculated examples with no additional local reserved chrome. Native width studies supply editable geometric evidence; they do not prove browser reflow. Under this rule, a wide expanded shell first permits a dock at 1256px. The historical HTML specimen's 1280px media breakpoint is conservative supporting history, not the final measured-container rule. In the greater-than-860px / less-than-1200px class, a user-selected 72px rail first permits a dock at 1096px. Do not substitute either inferred viewport threshold for measuring the actual content slot.

At 600px and below, the evidence overlay occupies the full available viewport width and uses internal content padding. At the represented 768/1024px widths it is 440px wide, constrained to the available viewport. It must remain usable at smaller effective widths, browser zoom and increased text size. Evidence content scrolls vertically inside its own surface. A table may retain a deliberate local horizontal scroll region with all fields and an immediately reachable full-row evidence action.

## Interaction, preference and ownership boundary

| Concern | Required behavior and owner |
| --- | --- |
| Inspector identity | Domain-owned entity/row/field/observation identity remains exact. A new evidence selection replaces the existing contextual inspector; it does not stack evidence dialogs or silently write a saved object. |
| Overlay | Named dialog, visible Close action, initial focus, background made inert, contained Tab sequence and Escape/Close returning to the original trigger. Preserve table sort, filter, selected identity and local scroll. If the original row is no longer present, return to the named comparison heading and explain the change. |
| Dock | Nonmodal complementary region; do not trap focus or make the primary comparison inert. Preserve the same evidence identity and an explicit route back to the originating cell or row. |
| Responsive mode change | Preserve evidence identity and user context while changing presentation. F01 and the consuming component must reconcile focus/inertness when the surface changes between dock and overlay; no duplicate mounted inspector or hidden focused control. Browser proof remains required. |
| Other global layers | F01 owns search, account, navigation drawer and Brain layer arbitration. “One inspector” does not authorize a consumer to delete or duplicate the existing Brain singleton. Focused `/terminal` retains its incumbent chrome, chart tools, context handoff and return behavior. |
| Theme and market convention | Use semantic roles and the actual scope-specific source aliases. Preserve incumbent preference ownership until a reviewed migration exists. Language and price direction are distinct concepts; health, aggressor side and exposure do not change meaning when the language changes. |
| Public and internal shells | F01 decides the relevant shell. Public editorial keeps public navigation and reading measure; a shared component does not impose the investor rail. Operational/internal views retain their access and domain boundaries. |
| Source and writes | Opening, closing or switching evidence is read-only. Existing producer, entitlement, save request identity and confirmation belong to their current source owners. A design action does not create a new endpoint, storage key or grant. |

## Stable component and token consumption

The component vocabulary contains 21 roles. `SectionHeader`, `MetricValue`, `ChangeValue`, `FreshnessReceipt`, `DataRow`, `TableFrame`, `ChartFrame`, `Tabs`, `EvidenceTrigger`, `EvidenceInspector`, `StatePanel`, `Callout`, `DetailDisclosure`, `Action`, `SaveFeedback`, `TierGate` and `Icon` provide the portable shared anatomy. `VirtualizedDataInspector`, `CountLadder`, `LifecycleRail` and `DecisionRow / VerdictHero` retain domain-specific source semantics and are not globally qualified replacements.

These are design-contract names. The [source contract](SOURCE_AND_DATA_CONTRACT.md) maps them to actual Macro, Terminal and public estate owners. Do not invent corresponding imports or install a new foundation package merely because a role has a name. The [current native authority note](paper/CURRENT_DESIGN_AUTHORITY.md) identifies the latest export/capture and repair precedence. Participation fixture v3 changes synthetic records and does not rename the component contract.

The 20 original Paper color tokens remain an observed dark palette. The token map also identifies proposed light values and source-scope collisions, including `--sp-8`, `panel2` versus `panel-2`, financial figures versus code typography, and focused-chart versus shared-shell theme scopes. F01 may consume the semantic reference now for candidate composition; it must not globally alias tokens by spelling or overwrite focused-chart semantics.

## F01-facing defects and qualification conditions

No conflicting rail/header value was found in this bounded source check. The remaining material width/state risks are explicit:

1. Docking by a fixed viewport label instead of usable content can shrink the primary comparison below 640px when local chrome is present. Use the measured rule above and test actual expanded and selected-compact states.
2. A shell breakpoint, content-gutter breakpoint and dock decision are different decisions. Resolve the exhaustive 600/860/1200 cutoffs explicitly with F01 and review both sides and fractional values, including effective narrow width at 400% zoom. The historical integer media-query gaps must not be accidentally carried into a supposedly continuous contract.
3. Overlay-to-dock transitions and global layer arbitration need real focus/inertness proof. Native screenshots and adjacent instructions do not execute those behaviors.
4. The first native product and taste reviews found numeric alignment, fixture coherence, annual comparison visibility and missing width/state evidence. Repairs and final independent repaired-set review are in progress. No prior BLOCK finding is closed merely by this concurrence.
5. Joint freeze requires F01's final slot/navigation/preference contract, F02's exact final native artifact identity, affected consumer qualification and actual independent review evidence. F01 has not yet accepted this artifact's cutoff/transition clarifications. Formal RIG remains draft and needs actual admitted reviewer-class evidence and the designated authority verdict.

The next joint record should cite the two immutable source commits, precise versions, used roles, actual Paper targets, reviewed theme/locale/width/state coverage, any retained domain variant and all carried conditions. This concurrence may be used as a concrete input to that record. It is not a substitute for it.

