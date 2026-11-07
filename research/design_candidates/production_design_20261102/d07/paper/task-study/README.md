# D07 Phase 2A task studies

**Eight editable content and interaction studies · provisional · 3 November 2026.** These extend the Phase 2A research into concrete value, period, evidence and navigation states. Final shell composition remains gated on verified F01/F02 v1. D07 uses its existing Terminal file and its owned build-contract page. [Open the Paper page](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-11-0)

## Captured states

| Study | Paper board | Captured size | Task and evidence |
| --- | --- | --- | --- |
| A | `1NH5-0` | 320 × 973 | English dark historical revenue comparison, with 288px content. [Image](a320.jpg) · [Editable export](a320.jsx) |
| B | `1NII-0` | 390 × 973 | Same English task at 358px content. [Image](b390.jpg) · [Editable export](b390.jsx) |
| C | `1NJL-0` | 1008 × 735 | Financials at 664px with a 24px gap and 320px evidence region. Revenue FY2024 is selected. [Image](c664-evidence320.jpg) · [Editable export](c664-evidence320.jsx) |
| D | `1NMQ-0` | 1008 × 735 | The same table after selecting Revenue FY2025. Value, period, clocks and return destination change together. [Image](d664-selection.jpg) · [Editable export](d664-selection.jsx) |
| E | `1NPF-0` | 320 × 671 | Narrow evidence companion to D, retaining the FY2025 selection. [Image](e320-evidence.jpg) · [Editable export](e320-evidence.jsx) |
| F | `1NPG-0` | 390 × 973 | Chinese light historical comparison, matching B's values and dates. [Image](f390-zh.jpg) · [Editable export](f390-zh.jsx) |
| G | `1NR7-0` | 320 × 973 | Chinese light comparison at 288px content. [Image](g320-zh.jpg) · [Editable export](g320-zh.jsx) |
| H | `1NSA-0` | 320 × 508 | Complete five-view Financials chooser with current selection and close destination. [Image](h320-chooser.jpg) · [Editable export](h320-chooser.jsx) |

The heights show fit-content task fragments. A final mobile viewport will scroll through the content. Full shell chrome, fixed-footer clearance, safe-area integration and responsive interaction require later composition and browser qualification. The JSX is an exact Paper export and supplies editable design evidence. Product accessibility semantics and event handlers still belong to the authorized implementation phase.

## Source fidelity

**A, B, F and G reuse the historical R3 example.** The dated NVDA Q2 FY2026 result is 46.743 USD billion, published 27 August 2025. The prior management guidance midpoint is 45.000, issued 28 May 2025, with range 44.10–45.90. The comparison rounds to +3.9% against that midpoint. Analyst consensus remains unavailable. The separate Q3 FY2026 outlook is 54.0 with range 52.92–55.08. Source and calculation precede the detailed metric/comparator controls in the reading order. The current public projection's formatted value cannot serve as the raw production binding for this example. Earnings OS must qualify that input. [Retained R3 source captures](../../baseline/OBSERVATIONS.md) · [S12 source contract](../../SEMANTIC_TASKS.md)

**C, D and E use a labeled synthetic fixture.** Their data uses existing `StatementPeriodSet` fields and a partial `Fund` shape. The two annual periods have equal 12-month durations and the same explicitly synthetic comparison basis. Revenue is 100 million and 120 million USD. EPS retains a reported zero and an unavailable value. Filing date, statement acquisition and fund-file build are distinct fields. The source document and retained revision are explicitly unavailable. The fixture's `quarterly` value is null. A later Quarterly action must show the actual coverage state while preserving the Annual selection. [Fixture data](fixtures.json) · [Existing source types](../../checks/diagnostics/statements/sources/terminal/lib/fund.ts)

**H uses the actual Financials views.** Statements, Statistics, Revenue, Dividends and Compare map to the existing native page keys. The existing Analysis parser and navigation owner retain the listing and URL contract. H covers the local Financials level. The complete Company family chooser remains a separate composition requirement. The “Lab · Expectations” label in A/B/F/G preserves R3's study vocabulary and requires an owner-qualified native destination. [Exact route and family contract](../../ANALYSIS.md)

## Interaction requirements represented by the studies

| Transition | Required identity and state | Current evidence |
| --- | --- | --- |
| Read A/B/F/G and choose source | Keep listing, Q2 FY2026, revenue, reported currency/unit, actual source and prior-guide identity together. Show formula and both source clocks. | The action is visible. Its historical-guidance evidence destination still needs a separate state. E is the synthetic Financials companion. |
| C → D by selecting FY2025 | Replace the evidence content with the newly selected field and exact period. Preserve the table, cadence, current local view and complete available-history access. | Selected border, value, period, annual dates, filing/acquisition clocks and named return action agree across the two captures. |
| D → E at narrow width | Preserve the selection through the existing shell's inspector mode change. One modal owns focus and scroll. | E retains D's evidence text. Executable resize, inertness and focus transfer remain unverified. |
| Close evidence or use its return action | Restore focus to the invoking Revenue FY cell when it remains available. If its context disappeared, focus a labeled status and preserve the previous selection for recovery. | Close and subject-named return controls are visible. Keyboard and actual focus restoration remain unverified. |
| Open H, then close or choose a view | Close restores Financials / Statements. Choosing a view uses its real page key and retains the selected listing. | All five choices, current state and close destination are visible. Open/close behavior remains a test requirement. |
| Change cadence, open complete history, switch statement type or choose chart | Preserve actual source cadence, period inventory, accounting family, currency and selection validity. A missing period has a scoped coverage state. | The entry controls are retained. Complete-history and annual-to-interim transition compositions remain open. |
| Open Brain from selected evidence | Apply the joint candidate's proposed single-layer behavior only after D06 supplies the acknowledged lifecycle. Preserve evidence identity and owner-qualified attachment/save semantics. | This remains a source proposal pending F02/D06 qualification. |

## Static quality checks and correction

The internal review inspected all eight JPEG/JSX pairs and rechecked C/D/H after the selected-text correction. It found the historical comparison, synthetic field selection, narrow evidence companion and five-view chooser consistent with their source contracts. This review had author context and carries no formal independent reviewer-class or RIG receipt.

The numeric check initially measured `--mx-light-link` on `--mx-light-panel2` at approximately 4.447. Five selected text nodes now use the existing `--mx-light-ink-link` role. Their exact nodes, original export hashes and applied operation are recorded in the capture receipt. The subsequent program checks all 249 text-bearing elements, including 28 inline spans, against a minimum 4.5 ratio without rounding the threshold. It also checks 62 explicit control minimum heights, eight image/export pairs, preserved text/value identities, comparison arithmetic and operation/retention records. All **433 static checks pass**. The minimum measured text pair is **4.737883**. The script executes zero UI interactions. [W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) · [Executable checks](../../checks/verify-task-study.py) · [Results](../../checks/task-study-results.json)

Visible control heights meet the 44px house minimum in these exports, with phone choice/source/return rows at 48px where represented. Full accessibility qualification still requires semantic controls, keyboard order, screen-reader names/state, focus visibility, touch operation, zoom and reflow. These conditions remain in the main responsive acceptance matrix. [Responsive requirements](../../RESPONSIVE.md)

## Persistence and exact scope

The direct Paper carrier observed one ready response and 65 applied responses across 66 unique recorded operations. The final working indicators were released on the exact edited boards. The token content hash remains `55dd37b7`. The original build-contract board retains 11 children. The nine original R3 IDs remain present, and the R3 phone predecessor `1D9K-0` still has zero children. The new studies have their own owned targets. [Capture and digest receipt](capture.json) · [Operation responses](operations.json) · [Native inventory](inventory.json)

The primary continuation is to consume the verified F01/F02 v1 release, then compose and qualify the full historical-source, cadence, complete-history and Company navigation journeys using these retained task states. Preserve exact source and Paper identities when freezing the independent review packet. [Current D07 handoff](../../CONTINUATION.md)
