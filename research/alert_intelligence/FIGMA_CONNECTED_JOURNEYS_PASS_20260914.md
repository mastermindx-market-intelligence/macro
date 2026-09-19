# Alert Center — connected Figma journey pass, 2026-09-14

**Design status: PARTIAL — editable primary-journey prototype exists. Expanded product/runtime status: SPEC_ONLY.** This is actual Figma canvas work, not another architecture proposal. It is not complete visual acceptance, a working application, a live signal feed, an activated monitor, or an email delivery result.

**Owner:** Sol, under Chris's current instruction to use the two supplied Figma files and continue without subagents. Architecture-to-design approval remains `DESIGN_ENTRY_RULING_20260914.md`; no new independent-review wait is introduced.

**Carrier:** Macro Draft PR #7135, `sol/alert-fabric-architecture-20260913`; read-before-record head `b5e86005af51dc37e6cf5513cf68a3488fff0174`. Existing implementation #7022 remains separate and untouched. Skillpack 1.0.1 was pinned at canvas pickup to Mastermind `2aa28559a857461fd674fae52d2904116b854891`.

## 1. File identity and working/reference decision

Chris supplied these exact two files. Both were read through native Figma tools before editing.

| Role | Figma file | Evidence at comparison |
|---|---|---|
| **Working** | `wvVt4GTPGMqnaPprVnbloU` — MastermindX — Alert Center V2 Canonical | Seven original pages; 35 local components; 212 instances; no original prototype reactions. Stronger reusable component and variable foundation for the new journey. |
| **Reference, untouched** | `EQlAQXIOdRdO63nMX2RK3u` — Mastermind Alert Center V2 — Canonical Ship Design | Eleven pages; 35 components; 192 instances; no original prototype reactions. Additional state, bilingual, and browser-comparison material remains useful reference. |

This is not a selection by modification date or the word Canonical. The component inventory, actual desktop/mobile compositions, variables and handoff material informed the choice. The reference file was not edited, deleted, renamed, or merged. No third file was created and no sharing/account setting was changed.

**New working page:** `33:222`, **07 — Alert Intelligence · Connected Journeys**.

- [Working page](https://www.figma.com/design/wvVt4GTPGMqnaPprVnbloU/MastermindX-Alert-Center-V2-Canonical?node-id=33-222)
- [Desktop entry](https://www.figma.com/design/wvVt4GTPGMqnaPprVnbloU/MastermindX-Alert-Center-V2-Canonical?node-id=33-223)
- [Mobile entry](https://www.figma.com/design/wvVt4GTPGMqnaPprVnbloU/MastermindX-Alert-Center-V2-Canonical?node-id=38-150)
- [Chinese mobile entry](https://www.figma.com/design/wvVt4GTPGMqnaPprVnbloU/MastermindX-Alert-Center-V2-Canonical?node-id=47-255)

The old inaccessible `QO3CthsB5KzPVKdgfcVPMI` key is no longer a dependency. Do not ask Chris for these links again.

## 2. Capability added to the design

The primary experience can now be followed through native Figma click targets: a Prophet-first shared Now view, original and current evidence, a clearly simulated sign-in transition, a supported monitor request, effective digest/quiet-hour behavior, saved-awaiting-first-check confirmation, personal updates, correction and delivery history.

There are **33 editable artboards**, including language/theme/device variants—not 33 distinct product capabilities. All ten semantic compositions in the brief have at least an initial composition, but secondary behavior and the complete acceptance matrix are not finished.

The screens use the file's existing button/tab/evidence-row instances, local typography and variable collection, rather than flattened screenshots. Existing Macro navigation was retained and adapted to its light variables. Personal screens use a simplified editable reference to Terminal's existing AppShell/AppNav structure, not a newly proposed header family. The actual Terminal source remains the implementation owner; the Figma shell is not a pixel-perfect production capture.

Shared exploration and private notices remain distinct. Private task tabs and private notice drillback stay in the personal shell; an exit to shared context is explicit. Current Terminal remains dark-only. The new shared Macro light treatment uses white cards on the existing neutral canvas, restrained accent treatment and readable label overrides. CJK typography uses an available Noto Sans SC family without supplying font files.

## 3. Exact artboard inventory

| Node | Composition | Coverage |
|---|---|---|
| `33:223` | Shared Now | 1440, dark, EN |
| `33:314` | Original evidence | 1440, dark, EN |
| `33:379` | Current evidence / unavailable source | 1440, dark, EN |
| `35:55` | Monitor setup / effective account policy | 1440, Terminal dark, EN |
| `35:154` | Saved / awaiting first check | 1440, Terminal dark, EN |
| `35:232` | Monitors and coverage | 1440, Terminal dark, EN |
| `36:85` | Developing situation / qualification | 1440, dark, EN |
| `36:218` | Shared exploration | 1440, dark, EN |
| `36:362` | Personal Now | 1440, Terminal dark, EN |
| `36:476` | Notice and delivery History | 1440, Terminal dark, EN |
| `37:133` | Monitor entry / simulated sign-in | 1440, EN |
| `37:158` | Email return / simulated sign-in | 1440, EN |
| `37:183` | Immediate email | 640, EN |
| `37:201` | Daily digest | 640, EN |
| `37:223` | Explanation correction / shared context | 1440, dark, EN |
| `38:150` | Mobile Now | 390, dark, EN |
| `38:176` | Mobile original evidence | 390, dark, EN |
| `38:208` | Mobile monitor setup | 390, Terminal dark, EN |
| `38:232` | Mobile awaiting first check | 390, Terminal dark, EN |
| `38:254` | Mobile current evidence | 390, dark, EN |
| `41:171` | Personal original notice | 1440, Terminal dark, EN |
| `41:246` | Personal current evidence | 1440, Terminal dark, EN |
| `41:321` | Personal explanation correction | 1440, Terminal dark, EN |
| `42:347` | Personal exploration | 1440, Terminal dark, EN |
| `44:218` | Shared Now | 1440, light, EN |
| `47:255` | Mobile Now | 390, dark, ZH |
| `48:260` | Original evidence | 1440, light, EN |
| `48:326` | Current evidence | 1440, light, EN |
| `50:276` | Mobile original evidence | 390, dark, ZH |
| `50:311` | Mobile monitor setup | 390, Terminal dark, ZH |
| `50:336` | Mobile awaiting first check | 390, Terminal dark, ZH |
| `50:359` | Mobile current evidence | 390, dark, ZH |
| `55:291` | Unconfirmed email result | 1440, Terminal dark, EN |

`33:445` is the working/reference and prototype-scope annotation, not another app screen.

## 4. Saved prototype proof

Native Figma readback found **144 configured click targets**, including repeated task navigation and variant copies. This count is not a count of distinct features or tested user sessions. Every configured destination resolved to an existing root on the working page.

Six presentation starting points are registered. The following exact chains passed a readback check of the saved reaction graph:

| Flow | Verified configured chain |
|---|---|
| Desktop | `33:223 → 33:314 → 37:133 → 35:55 → 35:154 → 35:232 → 36:362 → 41:246 → 41:171` |
| Mobile EN | `38:150 → 38:176 → 38:208 → 38:232 → 38:254 → 38:176 → 38:150` |
| Mobile ZH | `47:255 → 50:276 → 50:311 → 50:336 → 50:359 → 50:276 → 47:255` |
| Light evidence | `44:218 → 48:260 → 48:326 → 48:260 → 44:218` |
| Immediate email | `37:183 → 37:158 → 41:171 → 41:246` |
| Digest and uncertainty | `37:201 → 41:321 → 36:476 → 55:291 → 36:476` |

This proves that the reaction paths are configured in the saved design. It is **not an interactive Present-mode click test**, keyboard/focus acceptance, browser integration, or proof that the proposed backend works. The mobile primary flow assumes the simulated private-workspace transition; real cross-app authentication is still an implementation proof obligation.

## 5. Visual and structural review

Rendered screenshots were inspected for representative new Now, original evidence, monitor setup, developing situation, personal evidence, light Now/evidence, EN/ZH mobile and digest compositions. They include nodes `33:223`, `33:314`, `35:55`, `36:85`, `38:150`, `41:171`, `44:218`, `47:255`, `48:260`, `50:311`, and `37:201`. This is representative screenshot review, not a claim that every variant received an exhaustive visual audit.

Repairs made during that review:

- Corrected horizontal auto-layout containers whose fixed one-pixel height hid the monitor-form content. Horizontal rows now use fixed width and automatic cross-axis height.
- Rebound inherited raw dark navigation paints in the new light frames; preserved the existing navigation composition.
- Reapplied Chinese native-instance text overrides after clone persistence, then confirmed them by screenshot and fresh text readback.
- Aligned the new Now row outer edges and removed eight measured two-pixel supporting-note overruns using local instance text treatment; original component masters were not edited.
- Replaced overly sparse personal evidence with paired comparison cards, a decisive qualification and separate read/email states.
- Corrected private-tab and private-notice destinations so they do not silently switch to the shared Macro shell.

The final saved-state check reported: **33 artboards; 144 configured targets; zero missing destinations; all six configured-path checks passed; zero measured text/frame/instance containment overruns at the check's one-pixel tolerance; no missing fonts; no untranslated English-only UI text in the five Chinese artboards.** These checks do not prove complete accessibility, every overlap/focus behavior, source correctness or live delivery.

All seven original pages remain. Their original totals remain **35 components and 212 instances**, matching the initial census. No writes were made to the reference file. No tokens, original component masters or original pages were globally replaced.

## 6. Scenario and effect boundaries

Every new screen is explicitly marked illustrative/prototype/sample. The ADBE transition is a synthetic, source-shaped example for the old-versus-current-reading contract; it is not a claim that the September 11 source actually showed that entry state. It must be replaced or bound to an accepted real producer example for implementation proof.

The AAPL example illustrates the retained source-stated contribution and the correction of an unsupported recurrence qualification. No source-derived price, consensus beat, organic-growth calculation, new return forecast or portfolio impact is invented. A correction of our explanation is not labeled a new market event.

No private customer records were used. Prototype Save/sign-in controls do not save an account, establish monitoring, request credentials or send an email. Email acceptance is not described as inbox delivery; an uncertain result does not offer a blind automatic retry. Settings shown are sample choices, not reads of Chris's account.

Figma operations that combined creation and links to new targets returned safe-to-retry failures; their actual absence was reconciled before smaller writes. Creation and reaction-authoring were then separated. This is an observed tooling workflow, not a generalized Figma API claim. No duplicate retry-created artboards remain.

The Code Connect read path reported a plan restriction. Native local components and variables remained usable; no upgrade, mapping publication or replacement library was attempted. Screenshot URL downloads failed DNS in the sandbox, so inline native screenshots were inspected. Temporary asset URLs are not retained as durable evidence links; use the stable file/node references above.

## 7. What is still unfinished

The new primary prototype is not the final design freeze. Several secondary controls remain visual-only: full source-document drilldowns, search/filter interactions, account notification editing, mobile secondary situation/monitor destinations, and some coverage/catalyst links. Do not present their presence as an implemented journey.

The full state and variant matrix also remains incomplete: desktop Chinese; mobile Situation/Explore/History and email variants; the remaining shared Macro light compositions; empty/no-match, permission-loss, save-failure, restored-source and other negative-state transitions. Current Terminal light remains intentionally out of scope, not unfinished work.

Actual Present-mode walkthrough, keyboard/focus behavior, contrast beyond the inspected palette pairs, long-content extremes and complete semantic parity still require design acceptance. The 144 saved targets are not a substitute for that review. All source/monitor/delivery infrastructure and production proof remain separate under the accepted architecture and existing owners.

## 8. Exact continuation

**Next primary action: finish the secondary evidence/settings/coverage interactions on page `33:222`, then complete the missing responsive, language and required-theme states against the same accepted brief.** Reuse the existing selected file and original component foundation; do not create another draft, ask for the two links again, restart architecture or wait for a subagent.

After those design paths and the complete scenario walkthrough are accepted, reconcile implementation #7022 against the accepted design/current source owners and its source-writer/release boundaries. No feature code, migration, provider setup, CI waiver, merge, deployment or live email activation is authorized by this design record. PR #7135 remains Draft. No worker or watcher was created by this pass.
