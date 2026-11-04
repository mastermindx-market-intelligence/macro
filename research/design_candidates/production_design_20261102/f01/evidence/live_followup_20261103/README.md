# Actual beta follow-up — Company return, directory and mobile shell

**Observed:** 2026-11-03 to 2026-11-04 UTC through the connected Chrome browser. These are current-beta baseline observations and direct captures, not implementation or execution of F01's proposed 86 acceptance specifications. The served build was not attested to a source commit.

## Findings and product implications

| Path / condition | Actual observation | Design implication / existing specification |
| --- | --- | --- |
| NVDA Company Financials → Earlier periods | Exact origin `/analysis?symbol=NVDA&page=statements`; table2016–2021; `fin-active-panel.scrollTop=107`; focus on Earlier periods | Domain-owned period and scroll are working context, separate from the URL |
| Open current chart → focused Terminal | Actual Terminal URL carries `from=macro`, the exact encoded `ret` origin and `symbol=NVDA`; visible Back to Analysis control; focused dark presentation | Preserve the existing return carrier and focused variant; do not add a parallel return store |
| Back to Analysis | Exact origin and selected Financials/Statements restored; table became2022–2026; prior inner scroll disappeared; active element BODY; EN/light restored | URL return succeeded, full working-context return did not. H01/H02 remain proposed NOT_RUN acceptance cases, and future owner work must separately prove period/scroll/focus restoration |
| Command+K from desktop All tools control | Existing native modal dialog opened with focus in Find a page or tool… | Bounded actual keyboard-open evidence only |
| Unfiltered query `options` |12 distinct matches: four platform destinations, seven learning pages and one options-profit calculator; exact hrefs retained in OBSERVATIONS.json | F's prior All destinations /4 label was wrong. F now depicts the separately proposed four-item Options & futures facet. No matching learning/calculator destination may be removed |
| Same open directory resized1440→320 | Query and input focus retained; dialogx10/y10/300×880 at viewport320×900; scrollWidth=clientWidth298 | A useful current mobile baseline; not a measurement of the proposed native320×960 board |
| Reverse Tab and Escape after resize | First reverse Tab reached Close inside modal; second returned BODY. Browser-level focus could not be disambiguated. Escape closed the dialog and left BODY when the original desktop invoker had disappeared | Full trap remains unqualified. The missing visible-invoker fallback is a bounded observation relevant to N07. Do not infer a trap defect from the restricted browser diagnostic failure |
|390×844 ZH light global navigation | Native modal, six jobs, five market links, All tools, Terminal and Brain present. Close and ordinary rows44px high; footer settings30px. Escape closed and returned focus to Open navigation. No document-wide horizontal overflow | Main global journey survives locale/mobile change. Footer target and full accessibility still need actual owner qualification |
|390×844 ZH dark Company picker | All seven Company groups reachable with Financials selected; `role=dialog`, `aria-modal=true`; category rows76px, close36px. Focus remained on underlying Financials trigger after opening; Escape closed and returned/remained there | Local capability survives, but dialog entry/focus and close target require owner attention. Static/native acceptance remains separate |
| Viewport metadata | `maximum-scale=1, user-scalable=no` on Analysis and Terminal | Recorded accessibility obstacle; not a completed400%-zoom or assistive-technology test |

The live route, query, selected labels, scroll/focus observations and DOM measurements are retained in [OBSERVATIONS.json](OBSERVATIONS.json). The sequence used ordinary visible controls and observed locators. A transient stale URL immediately after chart entry was reconciled with the subsequently loaded Terminal URL; it is not reported as a route failure. English/light and the original browser viewport were restored, and all opened navigation/local dialogs were closed. No account, saved object, holding, watchlist or alert was modified.

## Direct captures

| Capture | Exact subject |
| --- | --- |
| [01-company-earlier-periods.png](01-company-earlier-periods.png) | Company before chart entry,2016–2021 window |
| [02-terminal-return-control.png](02-terminal-return-control.png) | Direct1000×650 clip of Terminal chart/header and named return; excludes the private watchlist |
| [03-company-after-return.png](03-company-after-return.png) | Returned Company view,2022–2026 window |
| [04-directory-options-320.png](04-directory-options-320.png) | Actual unfiltered directory at320px |
| [05-mobile-zh-light-navigation.png](05-mobile-zh-light-navigation.png) | Actual ZH light global drawer |
| [06-mobile-zh-dark-company-picker.png](06-mobile-zh-dark-company-picker.png) | Actual ZH dark local Company page picker |

PNG bytes are direct unedited browser captures. Private Terminal watchlist DOM was intentionally not retained. No production fix, data-source validation, complete keyboard trap, IME, screen-reader, zoom, permission, expired-authentication, stale-request, save or Brain callback proof is claimed.
