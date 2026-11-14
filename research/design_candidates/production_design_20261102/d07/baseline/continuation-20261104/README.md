# Served Company and Earnings journey evidence

Observed on 4 November 2026 UTC through the real beta and Terminal UI in the current available account context. The served build commit is unattested. The immutable source diagnostics retain their own explicit commits. Screenshots and DOM measurements establish this baseline's rendered states and actions. Final D07 visual acceptance remains open. [Capture identities](capture.json) · [Structured observations](observations.json)

## AAL article to selected call

The public article rendered its AAL identity, Q3 FY2026 call record, 22 October 2026 date, source-completeness material, 12 exact excerpts and 11 numeric receipts. Those counts and values are observed product content. Financial accuracy and underlying transcript rights were outside this UI observation. [Actual article](https://beta.mastermind-x.com/stocks/earnings/aal-2026q3-call-record.html)

| Step | Observed result |
| --- | --- |
| Read at 320×844 | Article iframe content width and scroll width both measured 309px. The date wrapped after `2026-10-`, with `22` on the next line. The title occupied four lines. The primary Terminal action stayed readable. [Capture](article-320.jpg) |
| Read at 390×844 | Article iframe width and scroll width both measured 379px. The date fit one line. Primary CTA measured 347×68.1875px and secondary CTA 347×41px. The secondary action is below D07's 44px house target. [Capture](article-390.jpg) |
| Activate the explicit AAL Terminal CTA | A new tab opened the exact AAL transcript URL with `pane=transcripts` and `tx=2026Q3`. The Company archive contained ten calls, and the Q3 FY2026 transcript dialog opened. [Actual destination](https://app.mastermind-x.com/terminal?sym=AAL&pane=transcripts&tx=2026Q3&utm_source=earnings_wire&utm_medium=organic_research&utm_campaign=company_intelligence) |
| Keyboard within the selected call | Initial focus was Close transcript. Tab moved to Search this call. Escape closed the transcript while the Company archive remained visible. Settled focus was BODY. An explicit fallback requires qualification when the opener is absent. |
| Observe settled URL and reload | The settled URL retained AAL and campaign context while `pane` and `tx` were absent. Reloading that settled URL showed no visible Company/transcript dialogs. The pane-removal time was sampled after Escape. This sequence does not isolate the removal to that keypress. The pinned MegaPane mount logic is a separate source explanation. |

The article's generic shell chart action used its existing active chart cursor. The explicit company CTA retained AAL. These are distinct navigation contexts. The transcript body was inspected in the live UI. Its text was excluded from the persisted screenshot set.

This observation closes the earlier inability to inspect the served article body for this route and current context. Guest, expired/revoked rights, another subject, missing retained revision, exact-passage anchoring, copy/digest and complete planner-to-claim return remain open. [Earlier dated observations](../OBSERVATIONS.md) · [Return contract](../../JOURNEY_RETURN.md)

## CN Forecast at its normal entry point

The route rendered all three annual EPS targets 2026, 2027 and 2028 with displayed averages 68.97, 72.76 and 76.46. Annual revenue targets displayed 180.26B, 189.28B and 198.80B CNY. The footer said `Consensus estimates · eastmoney · as of Nov 3, 2026`. Its source-clock interpretation remains constrained by the file-build finding. [Actual route](https://beta.mastermind-x.com/analysis?symbol=600519.SS&page=forecast) · [Desktop capture](cn-forecast-desktop.jpg)

| Step | Observed result and required follow-up |
| --- | --- |
| Open Actuals and estimates | The nine-period table initialized on its last page, labelled `2028 E–2028 E`. Expanding EPS showed Average 76.46, with Actual, High, Low and count unavailable. Preserve the farthest target and explain partial coverage. |
| Read at 390 and 320 | Body and scroll widths matched each viewport. The 390 table measured 355px wide. Forecast subview and statement controls measured 21px high. The EPS disclosure button measured 12×13px. These controls need the 44px house target while retaining density. [390 capture](cn-actuals-390.jpg) · [320 capture](cn-actuals-320.jpg) |
| Select Quarterly for EPS in Price target | Actual quarters Q1/Q2 2026 remained, with Q1 reported 21.76 and unavailable estimates/surprises. No quarterly-estimate-unavailable explanation appeared in the visible table or corresponding DOM text. Keep the actual history and state the estimate coverage. |
| Switch EN → ZH | The route and selected EPS quarterly mode survived the locale change. Opening Actuals and expanding EPS retained 2028 E and 76.46. The count label was `预测机构数`, which conflicts with the pinned producer's report-count semantics. [ZH capture](cn-actuals-zh-390.jpg) |
| Return through Company search | Browser Back recovered the Forecast route but returned the underlying page to its default Price target subview. The search's own restoration worked in the separate sequence below. |

A further 320px dark-theme scroll reached the final Net income row. Its bottom measured 574.8125px, above the visible bottom navigation at 772px, leaving 197.1875px clearance. The final rows measured 30.59375px high, below the current F02 candidate's 48px phone-row floor. The row is reachable in this fixture. Body and scroll width both remained 320px. Tab from the expanded EPS disclosure produced a BODY focus readback, which remains a bounded observation. Full keyboard/touch traversal, all-theme/locale parity, zoom, reduced motion and screen-reader qualification remain open. [Dark bottom-of-table capture](cn-actuals-dark-320-bottom.jpg)

One Price target click timed out at the browser input boundary. A fresh UI read showed that the requested selection had applied, so the click was not replayed. The subsequent Quarterly action used the reconciled UI. Locale and theme were restored to English/light and viewport emulation reset after the observations.

## Company search identity and return

| Step | Observed result |
| --- | --- |
| Enter `Alibaba` from the CN Forecast route | Search showed BABA/NYSE, 0241.HK/HKEX, 9988.HK/HKEX and 89988.HK/HKEX as separate listings. |
| Preview BABA | The current CN URL stayed in place. Preview showed BABA, Venue NYSE, Trading currency USD, and `Selected from “Alibaba”`, with an explicit Open Analysis action. [Capture](company-search-baba-preview.jpg) |
| Commit Open Analysis | Navigated to `/analysis?symbol=BABA&company_query=Alibaba`. BABA Overview retained NYSE/USD and the typed query. Price currency USD and statement currency CNY remained distinguishable. [Actual destination](https://beta.mastermind-x.com/analysis?symbol=BABA&company_query=Alibaba) |
| Browser Back | Returned to the exact CN Forecast URL. Search reopened with the query and selected BABA preview restored. |
| Preview 9988.HK | The CN URL remained. The preview showed the exact HK listing, HKEX and HKD. |
| Cancel, Forward, Back | Close company search dismissed the dialog. Forward returned to BABA Analysis. Back returned to CN Forecast with the search dialog closed. This is the observed cancellation behavior of the existing history marker. |

## Evidence limits and build requirements

Eight screenshots preserve the actual served baseline. Two phone captures use a native screenshot clip beginning below the global header. Dimensions and hashes are in the capture manifest. Browser observations are authored readbacks, with no claim of an automated assertion count or served commit attestation.

The same continuation executes 54 controlled source cases with 89 functional assertions and 24 input-integrity checks in the Forecast and Company search diagnostics. Those runs contain zero component-render assertions. A controlled React mount was blocked by npm E403 during dependency setup. Keep the normal-entry observations, controlled helper results and final reference acceptance as separate evidence classes. [Forecast diagnostics](../../checks/diagnostics/forecast/README.md) · [Search diagnostics](../../checks/diagnostics/company-search/README.md) · [Acceptance matrix](../../ACCEPTANCE.md)
