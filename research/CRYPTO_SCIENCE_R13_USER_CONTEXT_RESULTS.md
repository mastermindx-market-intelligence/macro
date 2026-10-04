# Crypto / Vector R13 — source-qualified descriptive UI and mobile headline repair

Existing operation `crypto-vector-r2-20260926-sol-001`, WS:CRYPTO-INTELLIGENCE, Macro draft PR8050. Baseline `6812add52487ccbefc067d0850e8ebd4dcc8b3af`. Runtime-source candidate `684ce2965dab391c66bf551bbc6701d3f97f6c65`. This batch changes a pure builder projection and the actual Vector template. It does not change the Bitcoin allocation engine, flow calculation, collector, evidence store, trading thresholds or source data.

## 1. User capability delivered in the source candidate

The preceding R11/R12 work repaired evidence capture and descriptive flow, but the current Vector Derivatives Desk still displayed an annualized funding field whose settlement interval had not been established. Its older daily taker-share chip also bypassed the new elapsed-window and freshness context. The repaired flow result was present under the existing regime context owner but absent from the template.

R13 connects that existing result to one restrained card inside the current Derivatives Desk. The front read is source scope, a plain state explanation and a dimensionless buy-side share only when the input contract supports it. Coverage detail stays in a native keyboard-accessible disclosure instead of competing with the principal Bitcoin decision.

| Source situation | Displayed state | Percentage behavior |
| --- | --- | --- |
| Current, exact-scope, complete24h, finite valid share | Participation observed | Show the known share;62.5% is the controlled example |
| Valid zero buy-side share with measured selling | Participation observed | Show0.0%; zero remains an observed value |
| Complete window with no reported activity | No activity observed | Withhold percentage:0/0is undefined, not0%buying |
| Missing/invalid observations in required24h | Incomplete24-hour window | Withhold current share, not neutralize missing activity |
| Stale source flag or elapsed age beyond existing owner threshold | Stale observations | Withhold current share, retain inspectable timestamps |
| No usable context, wrong scope, malformed supported fields or future label | Activity unavailable | No invented current value or fallback to the old daily chip |
| Complete24h but incomplete72h, with an earlier gap | Participation observed | Preserve usable24h share; explicitly qualify72h and earlier history |

The disclosure shows observed and evaluated UTC labels,24/72hour label coverage and contiguous observation count. It says that aggregate OKX BTC derivatives are not Coinbase spot flow, and that absolute units, bucket finality and first-publication time remain unqualified. A complete set of timestamp labels is not proof that the data were historically available at those labels. The value is descriptive, not a confidence score, action or passive-absorption claim.

The legacy annualized funding number is withheld from this desk. The interface shows an em dash and **Settlement interval not established**, not an assumed annualized cost. Predicted/settled semantics and missing provider intervals are not solved by this presentation. The builder's old numerical leverage fields remain intact for compatibility; they are simply no longer consumed by these two template elements. No provider substitution, history splice or model resizing occurred.

## 2. The pure adapter does not become a second signal owner

`_derivatives_flow_view(regime)` consumes the existing `context_legs.intraday_cvd` dictionary. It does not read a data store, fetch a provider, compute CVD or change the accepted decision. The adapter imports the existing freshness threshold rather than defining another policy. It requires the known derivatives scope and display-only/nonqualified authority flags, complete-window/count agreement, valid clocks and an actual finite numeric share in[0,1]. Boolean share/count values are not accepted as measurements. UTC-naive labels are normalized only under this existing internal CVD contract; no generic provider timestamp semantics are inferred.

The source-scope verifier removes the added helper and its one view-model entry from the current builder and recovers the exact previous builder bytes. This proves existing computation, side effects and policy wiring were not silently rewritten. The collector, first-seen store, CVD engine, shared house style and prior scientific test source remain unchanged.

The production builder's main entry can update established research/model ledgers. It was NOT invoked for the UI experiment. Rendering uses the pure view, the actual Jinja template and a controlled fixture context only.

## 3. Full-page visual review caught a separate mobile defect

The first112state/browser checks passed for the new card, but full-page screenshot inspection exposed an inherited mobile headline problem. At390px viewport width, the336px inner hero was split into **42px of heading copy and270px of allocation rail**, plus the gap. Chinese heading characters stacked vertically. Page-wide overflow was false, so a scrollbar-only test missed a severe usability defect.

The cause is a specific CSS precedence conflict: the shared `body.page-vector .hero-read` desktop rule was more specific than the earlier page-local mobile rule and restored a two-column layout on small screens. The fix is a narrow same-specificity mobile rule AFTER the shared include, returning the hero to one full-width column at<=780px. The shared stylesheet and global tokens are unchanged.

A new focused source regression failed before the fix, then passed. The final browser proof also checks actual copy width and the allocation rail's vertical position at320/390/768px. Full-width headline copy and stacked allocation now pass; the final Chinese light screenshot was visually inspected. No previous market result or accepted model interpretation was changed to obtain this repair.

Original screenshots, renderer, browser receipts and the measured42px geometry are retained in `before_mobile_repair/`. The final112cases supersede their layout acceptance; initial and final runs are not added together to claim224distinct scenarios.

## 4. Verification on the real host

The initial seven R13 contract tests failed because the pure adapter and new template surface did not exist. After implementation, the existing frontdoor suite passed14tests. The mobile-style regression then produced its own failure and brought the frontdoor suite to15passing tests.

The broader invocation initially had438passes and one failure: the old OKX bilingual-markup test still searched for the removed daily taker-chip anchor. It was not disabled. After checking source custody, the test was repointed at the actual new hourly-context markup while preserving both languages, the existing contrarian long/short caveat, technical details demoted to their tooltip, and the code-level display-only invariant. It now also confirms55.0from the qualified view is used instead of the99%legacy sentinel. The existing five-test OKX suite passed.

**Final broad result:439passed,49warnings.** This is the existing combined Crypto/Vector/storage/science invocation, not every test in the repository. Python compile, Jinja parse, source-scope claim checking and git difference checks passed. The forward-only design ratchet reports zero blocking findings; its25,426preexisting estate findings remain nonblocking, not resolved by this slice. The visual-evidence gate passed without a waiver or new validation owner.

### Actual generated-template browser matrix

Seven source states ×320/390/768/1440pixels ×EN/ZH ×light/dark = **112distinct final cases**. The browser opens the real Derivatives Desk, focuses its nested source disclosure and presses Enter. It verifies:

- correct state and value, including valid0.0%versus unavailable/no-activity;
- one canonical verdict, unchanged60%synthetic model allocation and retained chart container;
- the unsupported1234.5annualized-funding and98.7%legacy-daily-flow sentinels never appear in the desk;
- keyboard disclosure,>=44pxtarget,>=14pxexplanatory text, no page-wide or nested card overflow;
- full-width mobile hero and vertically stacked allocation, not just an absence of scrollbars;
- no page JavaScript exceptions in this matrix and successful use of the repository's Inter400/700font faces, with all six copied font-file hashes checked.

Process59901completed with exit0. The original run20399had also completed, but its evidence predates the mobile repair and missing-font fixture correction. Both are retained with their actual source identities.

### Canonical visual evidence

The unchanged existing `capture_page_evidence.py` captured **16/16final states**: desktop/mobile ×EN/ZH ×light/dark, each at rest and actual browser focus. The synthetic review route opens the outer desk initially and adds a fixture-only content-security policy restricting network to the local fixture. Those two initialization differences are explicit; this is not a deployed default route. Process79035exit0. The16PNGdigests and dimensions are checked, and representative full desktop/mobile images were viewed.

The separate112case harness starts a temporary loopback server, blocks all non-loopback traffic and shuts down its server before exit. Canonical font/assets were copied only to the external fixture directory; no font binaries, credentials or raw market-data files are published. The earlier fixture's missing fonts and optional resource failures remain in its retained receipt. The final proof also records unavailable or blocked resources; this is not a claim of complete production network parity, authenticated Brain behavior or a live-data route.

## 5. Source identity, prior evidence and review limits

The read-only verifier checks all112final cases,16canonical image states,14state snapshots, mobile geometry, font identities, source hashes and the exact builder restoration described above. All57recorded input identities,18gate files,137prior research artifacts and the absent real response-observation files remain unchanged. The earlier frontdoor file is an exact byte prefix of the appended tests. The separately repointed bilingual test is explicitly changed and is covered by the full439-test run; it is not falsely claimed byte-identical.

This is same-session executable and visual verification, not independent researcher approval. The market fixtures are illustrative, not current Bitcoin prices, allocations or forecasts. None of the rejected/weak R1–R10 strategies is promoted by improving this display.

Two platform holds remain distinct. The prior retention-design effect is still denied and was not attempted again. During R13, an additional two-test append for general nonscalar-flag fuzzing and direct real-CVD composition was refused before dispatch. Tail readback confirms it was not applied; neither test was retried, moved, counted or silently replaced. Generalized nonscalar-fuzz coverage and that extra composition test therefore remain unproven. The tested internal scalar contract and the independently planned browser states are narrower. A later optional combined diagnostic print was also refused; it was not retried. Already-started browser/capture/regression processes were reconciled through their existing handles, and the separately planned read-only receipt verification completed normally.

Current protected Mastermind pin:dd73150b9459bcbead43d7c2934fa6b95d7ce592; INDEX94d1af402598894372858793a5b1931019c5fa77; compatible Skillpack1.0.1/bootstrap1. Same M2 Studio Direct carrier and operation. Main336cd635has no relevant template/builder/frontdoor movement since R12custody9b613935. An incremental517openPRcensus found only8231/8182updated after the prior publication; neither touched the initial three targets, and their file lists were separately checked for the later bilingual-test repair. No reset, force, rebase or concurrent writer displacement.

## 6. Disposition and next boundary

**BUILT_NOT_PROVEN on the live route.** The repaired descriptive data contract now reaches the actual Vector UI, unsupported annualized funding is withheld, and a severe mobile headline layout issue is corrected and browser-checked. The broader scientific/product mission remains incomplete.

Independent code/science review, the held retention-capacity work, source-semantic qualification, admitted prospective collection and deployed user-task proof remain required. Current exact-head CI must be consumed after publication; earlier R12fences success does not transfer to this source. No worker is claimed dispatched, no new review/forecast/store plane is created and no automatic wake is implied.

The next useful phase is exact-source review and production-route qualification of this integrated source-to-consumer path while the storage owner resolves its separate retention gate. Do not rerun the preceding market studies, reapply the fixed price guard, substitute unqualified flow history or turn the new descriptive card into a trading signal.
