# Prophet Save read recovery — 2026-11-05

## Change and user behavior

After an uncertain Save, the old dialog disabled “Check account list” permanently, even when the account owner explicitly permitted another read. Unexpected rejected or synchronous owner failures could also escape the handler. This repair preserves the uncertain-write hold and permits only another deliberate, authorized membership read.

The controller now checks the original account generation again before invoking the queued read. It re-enables the read control only when the owner returns the boolean capability `readRetryAllowed: true`. Unexpected failures display a generic English/Chinese message and keep that control disabled. A later “present” observation still explicitly says it does not prove the earlier Save. Closing and reopening preserves the hold; no automatic retry or second Save is introduced.

The existing material-UI evidence guard also passes against the full merge-base-to-working-tree templates/site diff, including this repair. Its exact invocation and result are retained in ui-evidence-gate.json and ui-evidence-gate.log.

Only the paired controller assets and their existing composition tests change. The account owner, hold identity, Save write path, styles, public/protected page, display source pair and historical cohort remain unchanged.

## Exact input and validation

Parent commit: `ec24a85de3fc91988ca5a6fb25a97384b1cf2ab5`.
Controller SHA256, both template and served copy:
`63364e5bf444b4ebcd3ca7689362b7f393a64ea0b5d9539445c14ba4631fa193`.

- The new regression cases reproduced **9 failures / 7 passes** against the preceding controller. The raw failing receipt and log are retained.
- The repaired composition and account-isolation suites passed **51 tests**. This includes explicit/absent/malformed read capability, repeated deliberate reads without a write replay, unexpected failures, same-user reauthentication, different-user transitions, and stale completion isolation.
- The actual controller and owned CSS/fonts passed **16 Chromium fixture cells**: widths 320/390, light/dark, EN/ZH, recoverable/unexpected outcomes.
- Each cell checked dialog bounds and document overflow, all controls at least44px tall, reduced motion, focus return and close/reopen behavior. Recoverable cells also exercised keyboard focus and Enter for the second read.
- All16 cells retained one Save write. Recoverable cells made two deliberate membership reads; unexpected cells made one. There were zero page errors, console errors or blocked requests. Status-text contrast was12.513–15.62.
- Original16 PNG crops and the complete observations are retained in `browser/`; the capture script uses the actual owned controller/CSS/fonts with a synthetic account-service boundary.
- Parent self-QA visually inspected four representative original captures across both widths, both languages, both themes and both outcomes. No clipping or unreadable hierarchy was observed. Exact image hashes are in `visual-review.json`.

This is **hermetic component proof**, with **no real account calls and no production acceptance claim**. Earlier full-page proof at39f792 remains historical evidence within its recorded scope; these new captures specifically cover the changed handler. The post-publication signed-in Save/readback/reopen and Sources/Plan/return journeys remain owed.

## CI coverage and measured calibration carried by the same publication

The already-published predecessor `f3c79cfed26286c25592e487939a59fa2dbfc7ec` registers four previously unrun suites in existing jobs. Its exact hosted contract-delta result found **no remaining unregistered-suite or trigger/exclusive-closure errors**. Its only three failures were the planner-weight ceilings associated with those intended registrations.

The intervening `ec24a85` commit adjusts exactly those three measured weight ceilings, as allowed by the existing gate. It changes no selected job IDs, job/pack ceilings, runtime/admission limits or estimator. The local canonical assertion passed; the subsequent hosted measurements on f3c79cf match the paired local calibration exactly. See the sibling `ci-weight-calibration-20261105/` packet and `hosted-predecessor-ci.json` here.

| Probe | Jobs before/after | Estimated weight before → after | Packs before/after |
| --- | --- | --- | --- |
| templates/index.html |137 /137|5912 →5918|10 /10|
| scripts/build_free_content.py |137 /137|5927 →5933|10 /10|
| engine/prophet/plan_book.py |131 /131|5668 →5674|10 /10|

These weights are planner estimates, not measured runtime seconds. The free-content job ceiling remains138.

## Evidence and custody

`source-binding.json` verifies the changed source hashes and unchanged published HTML/protected payload/board/gate. `package-manifest.json` binds all packet files except itself. `source.diff.patch` records the three-file repair. Red/green receipts and logs are copied unmodified.

The attended parent is the sole writer of the isolated checkout. Separate uncommitted Save edits in the prior integration checkout remain untouched and were not adopted; this fix was independently implemented against the actual account-owner contract. Native children supplied read-only CI/contract/evidence findings.

The containing commit is a publication candidate, not a merge, deployment, external approval or signed-in user acceptance. Current-head CI and release qualification must be read back after publication. See `CONTINUATION.md`.
