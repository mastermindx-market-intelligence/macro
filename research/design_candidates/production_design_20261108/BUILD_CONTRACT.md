# Paper audit — implementation contract

Date: 8 November 2026. Scope: build specifications and native Paper candidates. This packet does not claim product implementation, installation, runtime admission, merge, deployment or release acceptance.

## Read this first

The design now puts the next useful action at the front of the journey. Detailed source, state and recovery rules live beside the designs and here. Preserve each existing producer, identity, route, permission boundary and persistence owner. A cleaner screen must not silently change the product.

Two primary personas guide this pass:
- The researcher needs to understand the observation, its comparison basis and limitations, inspect evidence, and return to the same context. Research order does not confer trading permission.
- The project owner needs to create an outcome, review a plan, understand what is actually running, and recover an interrupted interaction without duplicate effects.

Keep the existing shared Inter typography, neutral container edges, Noir and market palettes. AERLOR is a separate brand system. This packet does not standardize it into Mastermind.

## Exact source baselines

| Surface | Immutable baseline |
|---|---|
| Governing procedure and OS implementation | [Mastermind@5c3d388](https://github.com/mastermindx-market-intelligence/Mastermind/tree/5c3d3885234358aefb97ecdbc59be0864df14f8b) |
| Product implementation | [macro@338a108](https://github.com/mastermindx-market-intelligence/macro/tree/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd) |
| Existing programme assignment | [programme@6e186286](https://github.com/mastermindx-market-intelligence/macro/tree/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102) |
| Verified D05 builder package | [D05@078339e](https://github.com/mastermindx-market-intelligence/macro/blob/078339e5e77997a74a6d8679ac09d5bef89fb7af/research/design_candidates/production_design_20261102/d05/BUILDER_INSTRUCTIONS.md) |

The search index subsequently exposed a newer Macro default-branch SHA. It was used to locate files, not to replace these evidence pins. All semantic code checks in this packet were fetched at the stated immutable baseline. Re-pin affected code before production implementation; do not reinterpret a design fixture as current market data.

## 1. Intelligence Hub: review before research depth

Paper: [US desktop](https://app.paper.design/file/01M2VWK62FA5S4VVF6G7SBPE5J/p-3-0), board 86-0; [mobile](https://app.paper.design/file/01M2VWK62FA5S4VVF6G7SBPE5J/p-4-0), 1DO-0; [build map](https://app.paper.design/file/01M2VWK62FA5S4VVF6G7SBPE5J/p-2-0), 2P-0, delta 6YK-0.

### Resulting flow

Overview → review setups → research priorities → discovery/risks → sector signals/track record → specialist desks.

The hero states that two setups can be reviewed. Their cards immediately follow it, so the user does not first have to traverse a six-row research ranking. Specialist desks remain reachable and all six links fit on mobile. The ranking is still the original research order.

### Data and interaction

- Keep hub.command, opportunity_score, edge_remaining, stage, direction, entry_gate, price risk and timestamps. Do not invent a new ranking or readiness engine.
- Research is a display label. Preserve existing Command routes, fragments, stored links and engine contracts.
- Review setups scrolls to the setup section and moves keyboard focus to its heading. Use a heading target that is programmatically focusable without creating an extra tab stop.
- Inspect AXON opens the existing company inspector. A source link is a distinct action and appears only when its reference resolves. Missing evidence shows Source unavailable as neutral text.
- Back restores country, active tab, search, filters, selected company, scroll and focus. Opening or returning does not save a watch, thesis or case.
- Dated examples remain labelled design previews. The 27 September source fixture is not current data.
- Keep the six specialist desks and the deeper domain contracts. A shorter entry surface does not remove their features.

### Required product proof

Verify keyboard anchor behavior, explicit Back and browser history, no score/order drift, source-unavailable treatment, 320/390/768/1440 layouts, EN/ZH, light/dark, touch targets and long translations. This pass visually checked the edited English/light desktop and mobile candidates. The other variants were retained, not falsely marked revalidated.

## 2. Sector comparison: each number keeps its meaning

Paper: [Explore/compare](https://app.paper.design/file/01M6FAXA774QT1VRDMAG7DFQ2W/p-4-0), FB7-0; [company/save/build](https://app.paper.design/file/01M6FAXA774QT1VRDMAG7DFQ2W/p-3-0), ATF-0, B1V-0, BML-0. Current delta: GM1-0. Corrected plot: GMX-0.

### Model availability

FB7-0 previously showed large 14% and 17% values beside a state saying live model parity was unproven. Those primary cells now show — and Model unavailable. The percentages were removed from this current-claim treatment; no model was recalculated. The separate historical-prior rows remain.

Render a current model value only when the existing producer's qualification allows it. Missing, expired or incompatible inputs propagate to the primary cell, not merely its footnote. If the owner does not expose a sufficient qualifier, keep the value unavailable. Do not invent a confidence threshold in the frontend.

Historical priors are historical base rates. They are not substitutes for an unavailable current model and must retain their own basis and dates.

### Rank and score

[engine/sector_pulse.py](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/engine/sector_pulse.py) reads the source score and rank. Its archive-derived rank delta is historical rank minus current rank, so positive means the rank improved. Missing history remains null. [templates/si_workspace.js](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/si_workspace.js) counts the signs.

The plot and summary now say rotation score and improving/falling rank. The SVG axis and quadrant labels were also corrected. The 0–100 score axis no longer claims that 50 means benchmark parity. The plotted fixture coordinates and counts were preserved.

Retain score and pulse_rank_delta_5d in Methodology and the builder mapping. Rank change is ordinal; its sign count does not measure the size or acceleration of a market return. Do not blend it with 21-session return.

Required fixtures: positive return with falling rank; tied rank; missing history; disjoint observation dates. Plot, accessible description, counts and narrative must agree.

### Observation clocks and coverage

The company journey now says Member price dates unavailable. Its dated group snapshot and 20-session return window remain separate.

- Never infer a member price timestamp from a group timestamp or generation time.
- Use a shared clock only when all displayed rows share it; otherwise show the producer's row-specific dates.
- Price-history coverage is not native positive-volume coverage.
- Preserve Nasdaq, S&P and Russell source namespaces.
- Return difference versus group is arithmetic percentage-point difference.
- Preserve current-membership and sample-size limitations in the appropriate evidence detail.

### Company route and return

[templates/subsector_detail.html.j2](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/subsector_detail.html.j2) currently constructs the member destination using DETAIL.stock_base (fallback ../stock.html#) plus encodeURIComponent(member.ticker). Desktop rows and mobile cards use this owner. The verified D05 route matrix separately names the existing US, Canada, China and HK adapters.

D07's future canonical analysis route is an integration dependency, not an already proven installed binding. Resolve the listing with its native region/namespace. A same-ticker match is insufficient.

Required return context: stable listing identity; region; source namespace/universe; selected groups; filters; benchmark; window; snapshot; scroll; focus target. Use the existing navigation owner. Do not create another navigation store.

Required proof: open from the selected company row; return through explicit Back and browser history; resolve two listings sharing a ticker; show absent, ambiguous and inaccessible listing states without substitution or an accidental save.

### Watch, notes and navigation are independent

[WATCHLIST.md](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/WATCHLIST.md) records the existing owners:

| Object | Existing owner | What success certifies |
|---|---|---|
| Signed-in watch membership | templates/watchstore.js, WatchStore.symbols, selected list ID; existing Supabase watchlists/watchlist_symbols | That exact list contains the confirmed record |
| Signed-out watch membership | Existing local watch owner | A successful local persistence result |
| Notes | Existing device-local storage | That note's local write only; no cross-device sync promise |
| Return context | Existing navigation state | Restored selection/view, not a saved watch or thesis |

The Chinese success specimen now points to the watchlist and no longer bundles local notes/source context into one success paragraph. Unknown watch outcomes retain and reconcile the original operation. Watch success with note failure must be represented independently.

## 3. Mastermind OS: outcomes follow owner facts

Paper: [Projects](https://app.paper.design/file/01M3NRCX55B452A12819WNE1RH/p-H-0), MHD-0 and N8N-0; [Team progress](https://app.paper.design/file/01M3NRCX55B452A12819WNE1RH/p-J-0), QM6-0; [current builder map](https://app.paper.design/file/01M3NRCX55B452A12819WNE1RH/p-E-0), TMP-0 / XE7-0.

The 8 October snapshot is retained as history below the current map. It must not be interpreted as today's complete capability inventory.

### Project creation and planning

[ProjectPlanningJourney.tsx](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/projects/ProjectPlanningJourney.tsx) separates preview, publication, observed project, initial planning, result, keep/adopt and execution handoff. [App.tsx](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/App.tsx) rechecks the current binding and qualified launch conditions.

| Observed owner state | User-facing state/action | Guard |
|---|---|---|
| Publication pending | Creating project… | Keep original request |
| Project record observed | Project created · Plan the work | No Working claim |
| Planning admitted/running | Preparing your plan | Actual planning receipt |
| Plan result observed | Plan ready · Review plan | Preserve result identity |
| Plan adopted, execution not admitted | Ready to start · Start work | Current execution qualification |
| Result uncertain | Status needs checking · Check previous request | Reconcile original operation |
| Execution observed | Working | Actual current owner status |

The launch button now says Create project. Three compact state specimens cover created, plan-ready and uncertain outcomes. The consumer card does not carry enforcement notes; those belong in the contract.

Required proof: interruption after publication; repeated click while pending; prior plan retained on recovery; permission/binding change; create success without planning; adoption without execution. No duplicate project or request.

### Pause admission

[ProjectAdmissionPanel.tsx](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/admission/ProjectAdmissionPanel.tsx) and [project-admission.ts](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/admission/project-admission.ts) govern Pause new work / Resume new work. An open admission gate is not readiness, start authority or continuous supervision.

Show Pausing… → New work paused. Preserve running-work status separately. Unknown response → Check pause status. Resume requires the current pause token and current permission. Do not treat a historical receipt as current control state.

### Native Hermes conversation

[HermesNativePanel.tsx](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/hermes-native/HermesNativePanel.tsx) and its [closed contract](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/hermes-native/contract.ts) own local status, history, qualified create/send, original recovery and receipt reads. [THIN_NATIVE_OS.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/docs/hermes/THIN_NATIVE_OS.md) records candidate proof and separately retains the installed-release boundary.

New specimens: Continue on this Mac; Response not confirmed; Answer recovered.

- Show local connect only in the qualified desktop context. Remote clients show Open Mastermind on the Mac running Hermes without an enabled loopback-connect action.
- Unknown status describes uncertainty, not a guessed interruption cause.
- Check previous request reads the original conversation/request. It cannot automatically resend.
- Show Answer recovered only after the terminal receipt and original history read.
- Preserve read-only, capacity, unavailable and attention states. Sign-out clears private content.
- Local chat is not company dispatch or cancellation authority. The existing generic Office Send unavailable state was retained.

### Team and result lineage

[OrganizationWorkspace.tsx](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/organization/OrganizationWorkspace.tsx) and [organization.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/integrations/hermes_leadership/organization.py) project a verified Mission observation. Role charters and observed work are different.

Keep goal → team → role → work → result as an existing-owner projection. A role is not live enrollment; a reporting line is not an assignment. Returned evidence, review, acceptance and parent consumption stay distinct. If qualification is missing, show Team details unavailable while preserving project/work access. No new identity, scheduler, queue or lifecycle store.

## 4. Shared system and motion

Paper: [Start here](https://app.paper.design/file/01M312VSDSZFVT45674GDVJVZN/p-9-0), 47Q-0; [Utilities](https://app.paper.design/file/01M312VSDSZFVT45674GDVJVZN/p-7-0), 4NV-0 / 9VK-0.

The shared-system entry now presents destinations before lengthy source and hold details. Candidate status remains near the top. Existing acceptance and release holds were preserved.

Motion uses the house [Signal Ink contract](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/docs/ILLUSTRATIONS.md), not a new renderer:
- lib/illus.py produces the SVG.
- templates/illus.css controls draw, veil, endpoint and reduced motion.
- templates/illus.js owns reveal-once and evidence-dialog reopening.
- Real candles, crosshairs and zoom remain on the Terminal chart stack.

The new Paper storyboard shows draw, settled and missing-history states using an explicitly illustrative index. The HTML specimen embeds output and shared CSS/JS from the pinned implementation. It includes settled/missing controls, explicit specimen replay, reduced-motion handling and keyboard-accessible build notes.

Validation actually completed: renderer executed in Python; empty output is an honest null; both JavaScript blocks parse; native storyboard screenshots inspected. Browser execution did not complete: the browser policy rejected the inline data URL. No alternate browser or indirect hosted execution was used after that rejection. Browser playback, no-scroll-replay, reduced-motion rendering and responsive runtime checks remain an explicit integration gate.

## 5. Construction order and acceptance

| Phase | Buildable increment | Dependency / proof |
|---|---|---|
| 1 | Presentation-only Hub order and concise labels; OS truthful action labels | Existing data unchanged; route aliases and focus/return verified |
| 2 | Sector availability, clock and rank semantics | Exact producer fields and qualification; missing/tie/incompatible fixtures |
| 3 | Watch/note/return outcomes | Current selected-list owner and existing local-note/navigation seams |
| 4 | Project and native conversation states | Current principal/binding, original requests, native release qualification |
| 5 | Organization detail and result lineage | Genuine source-qualified Mission observation; no synthetic live workers |
| 6 | Shared illustration/motion integration | Allowed product-preview playback, reduced motion, nulls, no fake liveness |

For every feature, record four separate facts: implemented in source; tested candidate; installed consumer; accepted product path. A source SHA or a Paper screenshot alone is not all four.

The design pass has delivered native candidates, source-backed build rules, a census and retained-scope decisions. Production implementation is the future builder's scope, with the proof gates above. Do not clear unrelated holds, bulk-arm releases or duplicate existing owners.

## 6. Consolidation and retained work

- Preserve AI R10's compact conversation, source overlay and save/recovery contract; this pass found no reason to replace it.
- Preserve News R3's evidence/consensus framing and R2 states.
- Preserve Sector R3 depth and retained data families under R4.
- Preserve archived/rejected/study/canary boards as reference until their owners authorize and the native archive/delete capability allows removal.
- MASTERMIND PAGES emitted a file-too-large/data-loss warning on read. No modification was attempted after that warning. Its migration needs a dedicated capacity-safe split with stable links and a full retained-feature ledger; this pass does not claim that split.
- Keep AERLOR's independent hospitality design language.
- Refer to FILE_MAP.md for all 37 observed resources and the coverage level of each.
