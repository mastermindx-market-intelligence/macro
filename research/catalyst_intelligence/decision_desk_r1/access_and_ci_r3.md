# Decision Desk R3 — access action and complete CI ownership

**2026-10-20 · Original PR #9611 · Draft/HOLD · Source parent de824d8360b91ff44aca2930ac045d1bc6b14bfb.** The containing commit identifies this candidate. No native source admission, independent review, merge, deployment or production acceptance is asserted.

## Two concrete changes

The access-required Decision Desk now has a bilingual **Check access / 查看访问权限** action. Anonymous users are sent through the existing `MDXAuth.open('signin')` owner. Signed-in users without the required access, or a host where that sign-in port is absent, navigate to the existing same-origin `/plans.html`. The action never transports a case identifier, source payload or credential, never reads WMN on its own, and is inert after disposal or suspension and on an invalid route. Server-side entitlement remains unchanged. The standalone component without an access callback preserves its existing behavior.

The actual hosted failure on the parent was `biocatalyst-serving` in code run **39441884896**, job **118695764178**. Its aggregate ownership assertion recognized seven older Bio jobs but omitted the already-declared, separate `biocatalyst-decision-desk` job. The candidate failed one test with 278 passes; the CI base replay passed all 277. The uncounted file was `tests/test_biocatalyst_decision_desk.py`, not an absent or skipped execution target.

The repair explicitly counts that eighth lane, checks its real Python 3.12 / Node 20 / four-minute contract and actual pytest command, and retains complete and non-duplicated ownership across all lanes. Every older job keeps its existing timeout and test set. No CI workflow, permission, runtime, source-admission or deployment setting was changed. Eight corruption witnesses reject a missing frontend job, missing command, absent Node setup, wrong Node/Python versions, changed timeout, duplicate ownership and a missing legacy page test. Each witness first accepts the real manifest, so an always-failing guard cannot pass.

## Verification actually executed

| Layer | Result and scope |
|---|---|
| Hosted regression reproduction | Parent CI candidate: 278 passed / 1 failed; tested base: 277 passed. Exact source/run/job identities in `ci-regression.json`. |
| Local guard red/green | The original assertion reproduced the missing frontend file; repaired real-manifest check plus eight corruption witnesses: 9 passed. |
| Complete failing logical job | **287 passed, 14 warnings**, 227.35s, exit 0 (Studio PID 37586). This runs all eight test files named by the real `biocatalyst-serving` job. |
| Existing component | 89 JavaScript checks passed. |
| Host lifecycle | 23 JavaScript checks passed, including three new access-action cases. |
| Focused page/component/hydration | 39 pytest checks passed; wrappers overlap the JavaScript counts. |
| Controlled actual-page browser | **15 behaviors, 16 EN/ZH × dark/light × 320/390/768/1440 layouts, eight actual CJK font checks**, zero page errors. Existing MDXAuth/API seams are explicitly synthetic, not live entitlement. |
| Canonical anonymous browser | **24/24 rest/hover/focus states** at 2026-10-20T15:30:37Z; all PNG hashes/bytes checked; zero console errors and failed responses. |
| Style/source guards | Visual evidence, added design tokens, runtime styles, source-claims and diff checks passed. No new palette or runtime stylesheet was introduced. |

These layers overlap; their counts are not a unique-test total. The local JavaScript runtime is Node 26.5.0; hosted Node 20 has its separate execution verdict. A new candidate needs new hosted CI. The full repository test suite was not run on this partially sparse checkout.

The first local full-job run could not supply the omitted ClinicalTrials fixtures and used a pytest directory beneath the group-writable SSD ancestor. That produced setup failures and security-test refusals. Fourteen original fixture files were restored byte-for-byte, and the existing hardened path checks were tested beneath an already safe, user-owned temporary cache instead of weakening them or changing SSD permissions. A remaining sponsor-map failure was traced to the omitted `data/baskets/membership.json`; restoring its exact HEAD bytes resolved it. The final full logical job then passed. These are test-environment repairs, not new data, identity admission or altered production authority. The fourteen warnings are inherited duplicate OpenAPI operation identifiers and were not suppressed.

The browser's initial sign-in spy diagnostic accidentally returned the assigned callback to Playwright, which invoked it once with no argument. The harness was corrected to a statement block; no production authentication flow was changed to satisfy that artifact. It now observes one actual sign-in request from the button and no research fetch.

## Evidence and visual assessment

Canonical evidence folder: `mockups/evidence/biocatalyst-decision-desk-access-r3/`.

- `manifest.json`, `smells.json`, PNGs and three-key `EVIDENCE.yml`: current anonymous page and real access-button hover/focus.
- `anonymous-asset-provenance.json`: exact data-free staged asset bytes and canonical theme emission.
- `synthetic-host/verification.json` and two selected screenshots: actual rendered host with controlled test auth and retained owner/API fixtures, not native or paid-account proof.
- `source-hashes.json`: current product/test bytes; `ci-regression.json`: exact hosted defect and repair scope.

Root inspected the dark English desktop and focused light Chinese mobile captures. The new action uses the existing neutral button, has a visible complete focus outline, and fits the mobile width. Dark remains a restrained canvas; light retains its white research surface. This is principal inspection, not independent visual acceptance.

## Current product frontier and design references

A fresh read of Paper file `01M2WGNCX9475G79JRKJTCM08P`, page `p-20-0`, confirms the same ten Decision Desk boards (776 nodes). Relevant retained targets include primary signals `6HNW-0`, setup detail `6I4R-0`, source conflict/withheld case `6IP4-0`, and advanced research beneath the signal `6J09-0`. The condition-saving specimen `6INF-0` remains a supporting workflow, not the primary product. No Paper content or active page was changed, and a board inventory is not visual acceptance of the complete implementation.

The target remains useful catalyst interpretation, issuer impact, same-subtheme context, market incorporation and conditional research scenarios. This release slice still consumes the existing WMN milestone contract; it does not manufacture those deeper estimates from missing data. The separate R10/#9662/#6712 and Codex native-adoption owners retain their sources and the DataOS #9617 dependency. No native worktree was modified here.

Independent host/source review remains unreturned. The Session Bridge and Executive reader reported `backend_unavailable`; no reviewer or queue execution was fabricated. The connected Browser tab read reported `ERR_PROXY_AUTH`, so the live acceptance step needs that connection restored to the authenticated Mastermind tab. Current unit/browser fixtures are not a substitute for that step. The existing merge-queue-pilot authority check explicitly reports `inactive_base_context` on this main-targeted PR; its red mark is not repaired by weakening an unrelated authority rule.

Next: consume this candidate's exact CI and independent review; obtain the qualified native Company/DataOS cut through the existing owners; prove a real entitled source-change/correction journey before any release-hold removal. All Draft/HOLD boundaries remain.
