# R8 — Independent Fabric review findings repaired

Same original sector-rotation assignment and Macro PR #9507. This is source-only Data OS integration, not a new market forecast, source-rights grant, vendor collector or deployment. Reviewed predecessor: `68784ed6ce2fcd415d97c63e24be1e245f3b7ac2`.

## Independent review and adjudication

The direct paid Fabric route was used for a NEW review of the changed R7 source, not a replay of the unavailable Executive request against aadf630 or of the older uncertain R5 worker. Stable run `rotation-r7-independent-68784ed6-20261017-c1`; original Web root/parent `rotation-intelligence-census-20261016-sol-c1`. The incumbent router selected Bailian/Qwen3.8-Max on Ubuntu3. Its original controller recorded lease, launch, terminal rc=0, retained stdout, process/usage receipts and transport cleanup. These are actual parent-side routing records; the worker did not select or launch another provider.

The retained 9,261-byte review has SHA-256 `7919356ddf76634818ba9fcd08167a47489529b2fc8b5a478e3179db5c4a083e`. It independently verified exact source blobs, ran the 30-method native adapter suite with 25 subtests, constructed a legacy-view witness, and returned CHANGES_REQUIRED with two Important findings and no Critical finding. The parent reproduced the material findings. The review task itself was accepted through the original Fabric ledger after validation; that is NOT source-code approval.

## Finding 1: legitimate legacy field absence

The incumbent native reader supports retained legacy views whose rows omit `source_receipt_id` entirely. The original R7 adapter incorrectly required that field unconditionally. The repair keeps `source_sha256` mandatory and treats the receipt-ID field as optional only when genuinely absent. Present-but-null, malformed or invalid IDs remain rejected. Matching a declared reference and its capture day remains mandatory.

The native end-to-end fixture now covers all thirteen invented instruments through the actual Archive, materializer and history reader, with modern raw-hash and receipt-ID selections plus the retained legacy artifact shape selected by raw hash. It verifies identical projected values and withheld PIT/decision authority. Raw payload bytes are not rewritten when the temporary legacy metadata/derived-view fixture is constructed. No actual retained market archive is read.

**Explicit conservative limit:** a legacy row without receipt ID cannot establish the mapping to a caller-supplied receipt-ID-only selector from the returned object alone. Such a projection remains refused with ROW_SOURCE_NOT_REFERENCED; no identity is fabricated and no silent selector fallback is added. Where the native reader can lawfully establish an unambiguous raw-hash-selected legacy history, that supplied history now works. A future need for receipt-only legacy projection requires the existing reader to carry the missing binding; it is not solved by weakening the consumer.

## Finding 2: future row tested at the correct boundary

The earlier future-date test changed the history end label and therefore stopped before the row-level FUTURE_OUTCOME_ROW guard. The new test retains a valid end label and appends a later EOD row, asserting the exact row-level refusal. Removing that guard now fails the intended test rather than surviving the suite. The original guard itself is unchanged.

## Executed verification

The repair uses an isolated copy of the exact previously tested public source under the original M2 evidence directory. No new source workspace, repository, scheduler or publication carrier is created.

- Before implementation: corrected native legacy fixture reached the adapter and reproduced 3 failures / 31 passes / 29 subtests, including an actual native thirteen-symbol legacy read accepted by the incumbent reader but rejected by the old adapter. An initial fixture-path error was corrected using the actual materializer-returned path; it is not counted as evidence of the product bug.
- After repair: actual native adapter/original-reader/original-history run **146 passed, 58 subtests passed**, exit 0, on M2 Python 3.14.7. There are **34 distinct adapter test methods**. Combined counts include the original reader-suite alias, not independent investment experiments.
- Three targeted mutations were caught: delete the origin-relative future-row guard; restore unconditional receipt-ID requirement; permit a present null receipt-ID as though absent. No unrelated import/syntax errors were counted as successful mutation detection.
- The source module and tests remain the only functional source changes. No native reader, raw collector, calendar, CI manifest, investment score or authority field is changed.

Exact tested SHA-256: module `1ff3a0e1caf7df84618a8b29df7345eba0f821e6f854124d14c0b8c932f4a341`; tests `a236eab76c783979b58d89cd36276ded04121b4e6d30291a979282f361c49768`.

M2 evidence: `/Volumes/Mastermind/research/rotation-intelligence-census-20261016-sol-c1/r8-review-repair/` contains red logs, native-green.log, native-regression.xml and review-repair-verification.json. The original R7 review bytes remain in `r7-native-review/fabric-independent-review-return.txt`.

## Release and broader mission boundary

R7's ci-gate, contract-delta and all twelve hosted packs had passed. This changed R8 source needs its own exact-head checks and independent repair review. It is not yet approved for merge merely because the prior review identified the fixes. Original platform-refused private-data reads, the uncertain R5 task, the unavailable old Executive review request and native Track A outcome gates remain separately preserved.

The already-retained source metadata establishes a common thirteen-instrument historical endpoint of October 9, 2026; the later BIL tail gap does not need to block a study deliberately ending there. Row-level integrity and actual value/rights/PIT qualification are still not inferred from metadata or synthetic fixtures. No real-data strategy, public recommendation, account allocation, deployment or trade is claimed.
