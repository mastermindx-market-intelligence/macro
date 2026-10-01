# Truthful plan-refusal receipt

The actual complete builder proof correctly refused HON/TRN/RBA on protective geometry but its existing `plan_not_built` group said every check passed. Admission is not evidence that plan construction/geometry/clock validation passed. This same-carrier correction changes only the existing EN/ZH fallback to **No entry plan is available — stand aside** / **暂无入场计划 — 暂时观望**. It preserves the code, classification priority, near flag, counts, names, gate logic, stop geometry, old plans and chronology. It does not invent a particular unobserved refusal cause.

The original 42-row full-builder receipt was reproduced exactly before the correction from the preserved board, its actual eight open names, and its actual fifteen new-plan names. Afterwards the complete receipt is identical except the two text values for the three `plan_not_built` names. No board/plan/ledger build was repeated and no original artifact was written. `recorded-receipt-comparison.json` records that narrow proof. The original preimage source is `308eff4a5e18dfdcb31ffbd0624169412aeac1aa`; earlier geometry receipts remain historical and are not restamped as a new source run.

Three new producer/template regressions failed before editing. **333 native tests passed** afterwards, covering existing receipt, plan, geometry, Arena, integrity, clock and reset consumers. Two stale test-harness assumptions were corrected without weakening assertions: the receipt environment now exposes the existing production `us_stance_projection` helper, and the layout-order assertion names the current plan-grid close marker rather than a retired comment. Every existing production function/class AST is unchanged; only the existing copy table and one explanatory comment differ.

## Visual proof boundary

Eight cases use the actual dashboard template and its unchanged shared dark/light styles with the recorded real refusal receipt; unrelated dashboard data uses the existing test fixture. The English/Chinese message and count/name parity pass at 390/1440 widths, with JavaScript disabled and no overflow. Screenshots and exact driver are included, and the dark-English/light-Chinese mobile outputs were visually inspected. This is not production, a new material design, or an authenticated/premium test. No live account/session is used; all requests are fulfilled locally or refused. Optional webfonts/favicon are unavailable in the fixture and fallback fonts are used. An earlier minimal component omitted the dashboard background and is not the accepted visual receipt; the complete existing template supplied the correct theme context.

## Release

Current Chairman continuation and Mastermind `aacf3df5a47ca37ce71cd47a3bd7caea81ad4cd2` govern this bounded same-operation amendment. #7254 remains DRAFT/HOLD. Exact-head CI, genuine independent full-PR review, integration, canonical publication and actual browser/payload proof remain distinct. This source change does not authorize any of them or complete the parent US availability recovery.

## Returned-source integration

After the copy correction, the existing repaired breadth/geometry/clock sources combine without manual conflict into `c748468aebd81340a241b97035f67327d9f9a5f7`. **518 tests across eleven suites passed**, with 6,447 Python source files unchanged. Current-main source composition is recorded separately; neither creates a production release. The existing visual-evidence checker returns0 for the exact amendment diff.

To reproduce visual evidence, use the existing `tests.test_prophet_whynot_receipts._page` helper with the actual preserved `refusal_receipts` result identified in `recorded-receipt-comparison.json`, save it as `receipt-page-fixture.html` next to a copy of `verify_receipt_page.mjs`, and set that verifier’s template/Playwright paths to the corresponding installed review environment. Its fixture changes only static locale/theme attributes, leaves page JavaScript disabled, and serves shared CSS locally. Do not reuse a real account, bypass a tier gate, or describe the resulting fixture as production.
