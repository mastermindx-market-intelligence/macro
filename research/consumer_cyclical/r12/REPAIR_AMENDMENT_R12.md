# Consumer Cyclical R12 — Narrow repair amendment after independent review

**Scope:** Consumer research/design on Macro #7804, not product implementation or shared-source enrollment.
**Reviewed predecessor:** `8bb5301e6bc5d661c75fc1b720048a21e0f9809f`.
**Independent review:** `cc-r12-independent-review-20260924-sol-001`, verdict REQUEST_CHANGES.
The review read seven frozen research inputs, not native application sources or all historical research. Its final output and process receipts are separately identified. The findings below are adjudicated rather than accepted blindly. Earlier research remains unchanged.

## 1. Select one delivery and subject path

For the NEW Consumer economic-change dossier, use the SAME shared POST `/api/themes/v1/research/query` and `/api/themes/v1/research/evidence` family, with a closed Consumer profile and a typed subject. This explicitly supersedes R6 section 8's direct new-dossier delivery through `/api/earnings/v1/records/{slug}` and R7 Task4's proposed Consumer ownership of changes to:
`engine/earnings_narrative/private_publication.py`,
`scripts/build_earnings_public_wire.py`,
`scripts/publish_earnings_private_store.py`, and `app/earnings.py`.

Those existing earnings components keep their own source/intake/delivery responsibilities. They are not deleted, bypassed or rewritten here. The NEW dossier consumes accepted shared GMI/Research Vault publication and reader contracts. R7 Task4 becomes qualification and cross-sector/next-run non-loss tests against that owner, not a second publisher or pointer.

For V1/V2 company-first presentation, select a **typed company subject on that same shared Consumer profile**. The existing ticker page is a mount for the common client, not a second API or public fallback. The alternative “reuse a separate company-serving route” is not selected. A company request must carry an owner-validated native company reference; no theme anchor is invented. An actual theme request remains a separately governed subject linked through accepted GMI relationships.

Working profile `consumer_cyclical` and content discriminator `consumer_economic_change.v1` are selected Consumer design names, NOT enrolled APIs. The shared owner must accept the exact typed subject/request/response contract before its integration task proceeds. Unsupported profile/subject returns an honest private refusal, not a Semiconductor payload or legacy GET fallback.

A design can name the binding task without pretending its future proof already exists. Native registration and source custody gate the relevant implementation; they do not require a second Chairman approval of this already commissioned research or completion of every neighboring program.

## 2. Select a reported-economics readiness policy

PLNT's single-event growth bridge and LTH's cash bridge do not require a management prior/actual/later-outlook triple. The shared Semiconductor B triple and witness gate remain unchanged.

Consumer reported-economics sections may be ready when their own source facts, context and derivations are qualified, even if optional management history is unavailable. Missing a required input suppresses only dependent calculations and their explanations. Incompatible or invalid inputs must never be coerced into a valid comparison. Actual issuer values that remain independently supported may still be shown by the native source reader.

When no requested calculation is qualified, the section is unavailable, not an empty ready object. A revised outlook is never passed as actual. A warning such as `definition_unqualified:<field>` cannot be ignored to produce a certified comparative badge.

## 3. Repair the research examples without creating a product adapter

The R12 standard-library reference is an original research example, with invented identities, dates, values and example.invalid locators. It imports no application modules, uses no network, and grants no native admission. It replaces R11's example behavior only; the original R11 bytes and their historical receipt remain at the reviewed commit.

Every derived numeric output now carries value text, unit, scale, sign convention, relevant intervals, exact per-result input references, original value text and declared display-rounding quantum. Computed values are exact arithmetic ON the reported values, not a statement that the underlying economics were measured exactly. Canonical derived decimals may strip trailing zeros; the original `0.30` remains `0.30` in its source input record. Ratios explicitly round to two decimal places.

The output is one per-result envelope. A missing fund-expense input leaves the total revenue change and other unaffected results available; the fund contribution result is unavailable with its missing input named. A missing asset-proceeds input leaves the supported pre-proceeds cash subtotal available but does not fabricate a reconciled total.

The numerical sentences are generated from the selected results, not copied from a stale example explanation. Counterevidence and a next observation are required. Literal forbidden-marker checks catch defined corruptions; they are NOT a semantic truth detector or a substitute for independent review. A source locator that resembles an instruction remains source text and never changes authority.

The invented calendar examples explicitly distinguish quarters, half years and years. An annual interval disguised as a quarter refuses. Equal day counts are NOT required: leap-year quarters remain valid. This reference does not implement the native fiscal-calendar owner, including 52/53-week periods and non-calendar year ends. Real LULU/other fiscal bindings must use that owner rather than copy the calendar-example function.

Distinct outlook-event IDs alone are insufficient. The examples require declared timezone-aware publication times and strict new-after-prior order. These invented timestamps are not reconstructed SEC availability, observed-system cutoffs or historical served-state proof. Missing clocks do not gain midnight or UTC defaults.

The ratio guard is evidence-based, not a blanket ban on percentages above 100. Withhold the ratio if its denominator is nonpositive or its declared display-rounding envelope includes zero. If the invented inputs explicitly declare exact precision and other contributions offset one another, an 800 percent change ratio can be valid; the interpretation states what it measures and why it can exceed 100. Display quantum is not statistical measurement uncertainty or a confidence interval.

Malformed research cases receive named refusals. Unused imports were removed. No production schema, formula registry, source archive, rights system or generic period service is added by these changes.

## 4. Preserve the correct valuation normalization

The reviewer proposed changing R9/R10's stationary illustration. That recommendation is rejected.

The defined metric is `M = enterprise value / next-period NOPAT`. Under the stated stationary assumptions:
`M = (1 - g/R) / (r - g)`.

At zero growth, value is `NOPAT/r`, so M equals `1/r`, not 1. The proposed denominator `(1-g/r)` gives `r*M`, a different normalized measure. At r=10 percent, g=0 and NOPAT=100, value is1000 and M=10. The proposed replacement would give1 and mislabel the unit of the ratio. R9 explicitly defines the next-period profit denominator; no formula correction is warranted.

This remains a hypothetical identity with strong assumptions, not any issuer's fair value or an investment recommendation.

## 5. Complete the review inputs and separate proof levels

The initial reviewer delivery omitted companion maps and generated receipts. They were already in saved packages but were not supplied to that worker; this is a review-delivery gap, not proof they never existed.

The complete continuation package includes:
- R6 evidence companion, blob `cdab90b867e16b36ff08fd6a678d4547308cec95`;
- R7 review/delivery map, blob `58c26b787da834f92efb82363daecc631e034367`;
- R10 integration map, blob `6b69882a3bf9cc43b686ddfdd41475606258334c`;
- attributable independent-review receipt, baseline counterexamples, revised example outputs and verification receipt.

The counts reconcile: the 32 R6 requirements are INCLUDED in the earlier148; add10 R7 delivery requirements and16 R10 integration requirements to get174, not206. All174 remain unexecuted product obligations. The research tests do not discharge native-source, API, browser, rights or investment proof.

Constant-authority tests are valid regression/mutation guards: changing a required literal false can make them fail. Test counts must not be described as counts of independent financial guarantees. The review body enumerates18 findings (3H,9M,6L); its footer's6-medium count is inconsistent, so the actual finding IDs control this disposition.

Historical native pins are evidence of what was inspected. Before an implementation action, the worker must verify the exact affected source group and accepted interface version, then perform a material compatibility comparison. No blanket claim that every old blob is current; no ancestry-only rebase or universal re-review when unrelated paths move.

## 6. Consume the newer shared decisions, with qualifications

Shared-owner comment `5809602368` explicitly answers Consumer request `5809073104`; it is no longer “no direct answer consumed.” Shell ruling `5808986207` permits one guarded `_basket_intelligence_mounts.html.j2` seam outside #app, with separately owned partials and serialized integration. Neither gives Consumer a new shared writer.

At shared head `70fde3c79956bba5b9c4e2365a97b4e4b3b1c3ef`, the SEC-family rationale is corrected in `config/theme_sources.yml`, blob `1073ca1e9841dc95084a57b4577d159e74f9d211`. It now distinguishes approved factual inputs, short excerpts and original interpretation from whole expressive documents, third-party material, branding and dataset redistribution. The specific inaccurate rationale is addressed in source; actual use-specific and deployed enforcement proof remains open.

At that same head, `guidance_history.py`, blob `e5f90c43efb25a2b8fd1ae18e274e548ef84a966`, emits the missing-definition limitation. Consumer must honor it. This is source presence on a Draft/unmerged branch, not a native test or live acceptance claimed by this session.

Consumer's standard descriptive paid dossier consumes R4's existing positive-only entitlement-store-outage grace, bounded by the actual smaller configuration and the86400-second cap from last successful positive observation. Failed refresh cannot renew it; fresh negative entitlement, authentication failure and invalidation cannot use it. Source-rights withdrawal remains an independent veto. No second auth policy or promise of instantaneous cross-host revocation is introduced.

## 7. Exact next boundary

The repair candidate is ready for targeted independent re-review of these changed decisions and original research examples, not another full sector review. Final reviewer disposition is separate from this immutable amendment.

An eventual implementation packet must carry these selected decisions and the exact remaining owner binding tasks. Do not demand future production proof as a condition for beginning its producing task; do not treat an accepted design as that proof. Real source admission, Consumer profile registration, qualified private delivery, all three positive cases and governed theme-to-company/browser acceptance remain mandatory before calling the first vertical delivered.

The R8 native-code staging denial remains untouched. An optional native fabric ledger-recent read was separately blocked in R12 and not retried; no ledger outcome write is claimed. The original independent review completed on its original carrier with exit0, STOP_REVIEW and unchanged input hashes. No hidden worker, watcher, product implementation, source admission, Fable build dispatch, merge or deployment follows.
