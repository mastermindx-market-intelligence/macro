# Shared Shell R20 — interaction and composition review

Status: SOURCE REVIEW / NOT APPLIED TO PAPER / NOT PRODUCTION ACCEPTANCE.
Owner: existing WS:MARKET-OS and Macro PR #7949.
Parent mission complete: false.

## Purpose and scope

Give builders one understandable journey rather than a new route for every drawing. The user should receive a prepared comparison, inspect its evidence, and return to the same task without rebuilding filters or stepping through device variants.

This is a review of the existing design contract, not another page registry, router, state service, design-compliance ledger or executable navigation configuration. The existing product page registry, native workspace controllers, Terminal portal, identity, auth and WatchStore remain their respective implementation owners. No new route or public URL is authorized here.

The source baseline is PR #7949 at `8c13f60e295662418d048aa347b7038d2ce2dca8`. Its existing shared-design and first-adoption contracts remain applicable. Current protected procedure was read from Mastermind `3c35c5f8c4609c5bbaa4db424521facb6ad3757d`, INDEX blob `94d1af402598894372858793a5b1931019c5fa77`.

## Material new evidence

A fresh native read of file `01M2WGNCX9475G79JRKJTCM08P`, page `p-D-0`, reports 42 artboards and 6,515 nodes with token hash `bba69475`. A later organization pass has renamed and repositioned the existing boards and added `21H2-0`, “00 · SPEC · Shared Shell Journey + State Map.” This review did not author that organization or map. Stable node IDs, not display numbers or coordinates, identify the retained work.

The new map's builder rule correctly says that a STATE board is not automatically a product route and device/theme boards inherit the same semantic contract. Some arrows nevertheless contradict or obscure that rule. The table below makes those arrows explicit; it does not claim that the underlying controls are implemented.

Native evidence read this pass: the complete page inventory; map nodes `21HE-0` and `21HI-0`; the phone comparison tree `1JXM-1`; the desktop watchlist-dialog tree `1TPI-1`; the long-list tree `1VG1-1`; native renders of overview `TUD-0` and phone Sources inspector `1K11-1`.

Inactive-page null heights are unmeasured content-driven dimensions, not zero height or proof of clipping. The overview capture was resized by Paper to fit image limits; it is not a 390-pixel viewport proof.

## Corrections to the map

| Current shorthand | Clarification required | Reason |
| --- | --- | --- |
| `01 / 12 -> 05` | `01 -> 05` for the observed desktop market-selector example. Other origins require their own preserved context. | Frame12 / `10UM-0` is a builder contract, not an end-user overview. |
| `06 / 12 -> 13` | `06 -> 13` for the phone market sheet. | Specification text is not another navigable screen. |
| `12 -> 14` | `06 -> 14` from the overview's Review a breadth alert entry. Desktop-origin treatment remains a separate responsive requirement. | The prepared alert begins from the product overview, not the specification board. |
| `15 / 17 -> 16 / 18` | `15 -> 16` for Inspect Atlas on desktop; `17 -> 18` for Sources and method on phone. The default phone Evidence tab is not yet composed as its own reference. | Frame18 renders Sources & basis selected and offers Back to Evidence. It must not silently become the default evidence view. |
| `20 -> 21 -> 22 / 23 / 24` | `20 -> 21` is Review changes on desktop. Frames22,23,24 are phone/tablet/light treatments of the review state, not subsequent navigation steps. | Responsive adaptation is not user navigation. |
| `26 / 27 -> 29 / 30` | Frame27's local comparison query may reach its no-match state. Global Search26 cannot use the same empty-result meaning without its own search scope. | No companies in this prepared comparison is not no results across Mastermind. |
| `31 / 32 -> 33` | `10 -> 31` for the desktop research evidence inspector; `32 -> 33` for phone claim evidence. | Desktop and phone evidence inspectors are counterparts, not consecutive screens. |
| `40 -> 41 / 43` | `40 -> 41` only when a submitted save cannot be confirmed. Frame43 is a long-list dataset/layout variant of the chooser, not a save outcome. | Neither normal completion nor a large population should automatically route to an uncertainty state. |

## Proposed replacement text for the existing map

The following copy is ready for review against `21HE-0`. It was not written to that native node in this pass.

```text
USER ACTIONS — preserve the originating device and research context
01 -> 05: open the desktop market selector; close returns to the same overview.
06 -> 07: open global navigation; close restores its initiating control.
06 -> 13: open the phone market selector; close preserves the current market.
06 -> 14: review the prepared breadth rule; opening never enables an alert.
01 -> 15 / 06 -> 17: open the prepared company comparison with the same scope.
15 -> 16: inspect the selected company's Evidence view on desktop.
17 -> 18: open Sources and method on phone; default phone Evidence remains a gap.
20 -> 21: review changed readings; Keep current view retains the old snapshot.
15 -> 27: refine this comparison; Cancel retains the applied view.
27 -> 29 or 30: local-query no-match treatment, not global-search failure.
10 -> 31 / 32 -> 33: inspect a research claim on the same device.
32 -> 35: open the report outline; selecting a heading returns within that report.
38 -> 40: choose a watchlist for the exact selected security.
09 -> 09A: desktop chooser reference is PARTIAL, not build-complete.
40 -> 41: an uncertain save result; checking status must not submit again.

VARIANTS — NOT EXTRA CLICKS OR NEW ROUTES
01 / 06: desktop and phone overview treatments; 11 is the scrolled desktop state.
15 / 17 / 19: desktop, phone and light prepared-comparison treatments.
21 / 22 / 23 / 24: revision review on desktop, phone, tablet and light phone.
08 / 25: desktop and phone workspace directory.
10 / 32 / 34 / 36: desktop, phone, light and tablet research reading.
31 / 33: desktop and phone research evidence inspection.
37 / 38: desktop PARTIAL and phone selected-setup treatments.
40 / 43: compact versus long-list chooser; 43 remains PARTIAL.
00 and 12: builder specifications, never user destinations.
```

Board numbers are presentation labels only. The paired IDs below and live native readback govern identification. This text does not create an implementation enum or replace the page registry.

## Exact anchors for the affected journeys

| Family | Retained native anchors |
| --- | --- |
| Overview and shell | `TUD-0` desktop; `UP4-0` phone; `10HS-0` scrolled desktop; `UJ4-0` desktop market sheet; `18GY-0` phone market sheet; `UQL-0` phone navigation |
| Prepared research | `1JLE-1` desktop comparison; `1JXM-1` phone comparison; `1K30-1` light; `1JR1-1` desktop Evidence; `1K11-1` phone Sources |
| Revised readings | `1KAF-1` notice; `1KFP-1` desktop review; `1KMI-1` phone; `1KO3-1` tablet; `1KQ7-1` light phone |
| Refinement | `1NLR-1` desktop refinement; `1NYN-1` held phone reservation; `1NZ0-1` dark no-match; `1O89-1` light no-match; `1NAV-1` partial global Search |
| Research reading | `VUD-0` desktop; `1Q4Y-1` phone; `1QF6-1` light; `1QTT-1` tablet; `1PU4-1` desktop Evidence; `1QE1-1` phone Evidence; `1QN9-1` phone outline |
| Setup and watchlists | `VIU-0` base Stocks; `1S66-1` partial desktop setup; `1SH3-1` phone setup; `1TPI-1` partial desktop chooser; `1UE1-1` phone chooser; `1V82-1` uncertain result; `1VG1-1` partial long-list chooser |
| Specifications | `21H2-0` new journey map; `10UM-0` guided-intelligence/scrolling contract |

## Do not promote unfinished drawings through relabeling

1. `1TPI-1` is currently named as a desktop chooser state, but its native dialog `1TX8-1` contains only `Choice heading`. List choices and the action region remain uncomposed. Its source qualification stays PARTIAL.
2. `1VG1-1` contains the header, retained security, local list search and two list-choice examples. There is no completed persistent destination/action footer in the inspected tree. Preserve its PARTIAL qualification even though the current layer name omits that word.
3. No-match boards `1NZ0-1` and `1O89-1` are 500px wide in the current native inventory. They can be component references, but their Mobile label is not proof of a 390px or 320px phone layout. Do not overwrite or resize their held scopes from this review.
4. `1NYN-1` has no children and is an explicit held reservation. It is not a functional mobile filter panel.
5. The missing phone default Evidence treatment, post-application revised-snapshot state and confirmed-save presentation must remain named gaps. Do not silently substitute Sources, the old snapshot, or Result uncertain for them.

## Prepared, immediately understandable interaction contract

Every primary action must name its next useful task. Carry the market, existing entity/listing identity, period, benchmark/evidence version and selected object through the incumbent owner; do not ask users to re-enter them. Optional refinement changes draft controls first. Applying commits the view change; cancelling discards only those draft controls.

Inspection stays beside the task on desktop and occupies the appropriate phone presentation on narrow layouts. Returning restores the original selected object, applied filters and same-document reading position. A new-tab return only promises what the existing URL/state owner can actually restore. Source inspection and theme switching do not create extra history routes by default.

Account/list membership checks stay distinct from market signals and quote freshness. The R18 read method is committed but not released; the R19 inline consumer remains a local partial candidate with three retained failing cases. A composed Frame41 is not proof that the production dialog or the inline consumer is working. No outbox entry, retry policy, active watchlist or holding is changed by this review.

## First-screen refinement recommendation

The current overview already gives the important distinction: “A strong index. A narrow market.” Preserve that conclusion and its two different concepts. A future permitted layout pass should avoid giving three nearby copies of the 3/11 participation fact equal visual priority. Keep the decisive fact beside the conclusion, then use the deeper scorecard and comparative chart to add new evidence rather than repeat the opening sentence.

Keep one dominant prepared research action at each decision point. The Sources inspector's “Where the +2.6 pp comes from” is a useful model: a direct answer, matched operands, and the limitation beside the calculation. Do not confuse more disclaimer text with more analytical depth. This is a proposed hierarchy refinement, not a claim that typography, comprehension or conversion improved in this pass.

## Verification and continuation

This review checked actual node identities, layer content, width metadata and two native renders. It did not click a production control, mutate Paper, test a browser, inspect a live account or validate an investment thesis. No award-level or production-readiness claim follows from it.

The next permitted native annotation action is a targeted correction of the existing map and truthful PARTIAL labels, preserving every board ID and layout. It must use the requested and currently permitted host/carrier; a source review does not clear an earlier native or platform refusal. Do not duplicate the map, create another Paper page or discard the organizer's grouping.

After the exact action gates clear, complete the missing high-value states before adding more decorative variants: default phone company Evidence, the held chooser action regions, and a truthful post-apply/post-check result. Then prove the full overview -> prepared comparison -> evidence -> exact-security action -> return path through existing frontend owners. Current R18/R19 code failures and #7129's persistence-before-rebind boundary remain separate release requirements.
