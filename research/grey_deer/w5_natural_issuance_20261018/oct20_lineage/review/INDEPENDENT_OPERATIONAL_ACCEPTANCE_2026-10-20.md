# Independent W5 operational acceptance — 20 October 2026

Reviewer: `/root/w5_acceptance_oct20`. Assignment: independent review of the completed root lineage evidence, using local reads and standard-library hash/JSON/AST checks only. Root remains the acceptance and publication owner.

## Verdict

**PASS WITH SCOPE — the original first natural SPY issuance criterion is satisfied by the retained evidence.** The three finite ancestry, producing-source/preregistration, and warning-qualification facts left open in the [earlier partial handback](../../oct20_review/W5_FINITE_ACCEPTANCE_HANDBACK_2026-10-20.md) are now closed. No blocking defect was found in the [root operational acceptance](../ROOT_OPERATIONAL_ACCEPTANCE_2026-10-20.md).

Accept the operational fact: the approved Grey Deer prospective writer ran in a naturally scheduled nightly, produced one 30-row SPY batch, and that exact batch reached retained Git publication, without a relevant Grey Deer error warning in the complete retained engine-log scan or the complete annotation collection reported by its check.

This accepts the eventual first natural issuance on October 18. It does not establish that the first nightly after the October 14 source merge succeeded, erase the earlier CLOCK/BACKFILL refusals, or demonstrate dependable continuing cadence. Broader prospective grading, user delivery and predictive acceptance remain separate.

## Independently checked evidence

### 1. Source ancestry is sufficient

Both [source metadata](../PRODUCER_SOURCE_METADATA_2026-10-20.json) and the [lineage receipt](../VERIFIED_PRODUCER_LINEAGE_2026-10-20.json) bind producing checkout `5e3e1e9d2d97439d0546072b89e9f94d3e84f2fa` to approved merge `af468522ab6e97b4c15f00c701a5ad6ba6a960b5`. The compare result identifies the approved merge itself as merge base, with 1,020 commits ahead and zero behind. That establishes the required ancestor relationship from the retained API observation; no claim relies on the compare response containing every changed file.

This reviewer checked consistency between the two receipts. The GitHub ancestry query was performed by root, not independently repeated in this review.

### 2. Exact producing recipe and preregistration match

Independent local recomputation verified **all eight archived source files, totaling 262,139 bytes**, against the byte counts, SHA256 values, and Git blob identities in the lineage and retrieval records. These include the writer, nightly wrapper, shell enrollment, stage-1 module, two libraries, volatility module and preregistration.

A standard-library AST read recovered `PREREG_PATH` and `PREREG_BLOB` from the producing stage-1 source:

- `research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md`
- `49a68b5e9c6543d662044b0aa391c4b6e6e6052e`

The AST-derived `RECIPE_FILES` contains the same six source paths as the receipt. Sorting their independently computed Git-blob identities and appending the frozen preregistration blob reproduces **`9c8b7fe2f572b06b9253affd9a3ca7fb02b8f4d20e7723dd76b46538d235bb8c`**. The exact fingerprint function was inspected: it hashes actual file bytes from its repository root, rather than merely recording HEAD.

All **30** retained forward rows match that fingerprint and preregistration blob. All 30 configuration/horizon keys are distinct. There is one source session, `2026-10-16`, and one declared issuance timestamp, `2026-10-18T06:24:18+00:00`. The reviewer independently confirmed that `Y`, `realized_A`, `graded_at` and `grader_sha` are null in every row. These checks used the [retained JSONL](../../evidence/forward_log.snapshot.jsonl); no writer, grader or model was invoked.

### 3. Warning qualification closes the original criterion

The [complete-log scan receipt](../COMPLETE_JOB_WARNING_SCAN_2026-10-20.json) binds engine job **117575031870** to **4,482,863 bytes / 44,668 lines / SHA256 `8b0852ab26cf54a928f9c88be752621d6ebee546db60131176f1805f366b9702`**, matching the previously inspected engine-log identity. It declares a complete case-insensitive scan of that retained log, with three Grey Deer pullback references and no matching warning/error. The three references are writer/grader identity settings and the actual nightly invocation.

The producing wrapper's warning calls were inspected. Its store, issue, grade and exception warnings all carry Grey Deer pullback tags covered by the scan's stated matching scope. This matters because the wrapper normally exits zero; rc=0 alone would not satisfy the criterion. This reviewer assessed root's complete-log receipt and did not reacquire or independently hash the raw native log.

Separately, the [parsed annotation receipt](../PARSED_ANNOTATIONS_2026-10-20.json) binds the exact engine job and check-run URL/id. The check head is the workflow head `b140360f39266c7ffb00dce2d8e118aba677436a`, correctly distinguished from the later pulled producing checkout. Actual array length, retrieved count and API-declared count are all **50**. Independent scanning of every field in all 50 objects found no match for any of `grey[\s_\-]*deer[\s_\-]*pullback`, `grey.?deer`, or `pullback`, case-insensitively. The collection contains 8 failures, 18 notices and 24 warnings; it is not represented as globally clean.

“Complete annotations” means all 50 reported by this check API. It does not assert unlimited GitHub retention or prove absence of every conceivable runtime error. The separately complete retained raw-log scan supports the original named-warning criterion. Later engine cancellation and whole-nightly failure remain unchanged.

## Limits that must survive publication

- **One operational invocation, one source session, one issuance batch.** Thirty correlated configuration/horizon rows are not 30 warnings or independent episodes. Independent episode N remains null.
- **No mature outcome evidence.** No calibration, incremental predictive value, preemptive warning skill, false-alarm burden, missed-damage improvement, recovery capture or capital-preservation result passes through this acceptance. Earlier failed predictive studies remain evidence.
- **No executable Friday-close claim.** Sunday issuance may comply with the captured before-next-open writer window, but cannot have informed a Friday-close action. Label-origin returns and implementable action returns remain distinct.
- **Unknown clocks remain unknown.** Input availability, first remote publication, first user display and actual execution time/price are not supplied by Git timestamps or buffered log emission.
- **No broader product or reliability acceptance.** The first writer event does not prove prospective grader maturation, ongoing schedule reliability, Macro/Terminal user display, action-policy integration or programme completion.
- **Earlier unreturned request remains unreturned.** The previous partial handback and its stalled read are preserved. The new root observations close evidence gaps; they do not retroactively complete or replay that request.

## Receipt identities and next action

| Reviewed receipt | SHA256 |
|---|---|
| VERIFIED_PRODUCER_LINEAGE_2026-10-20.json | `4af90e68656bd8a615bb3a7dc02d3698eeb4ff20cf40a4c8775d8ccbbf86b2d3` |
| PRODUCER_SOURCE_METADATA_2026-10-20.json | `99066f3f550ca3ac24ab1c20f9198933ff4fc052d6e925c0d8d521f3a7c25531` |
| PARSED_ANNOTATIONS_2026-10-20.json | `c6bee9d6de772ef315276382cffd3ebb759b565701225eaa8cbaad2b9f508891` |
| COMPLETE_JOB_WARNING_SCAN_2026-10-20.json | `c824095bc6f4dbd2544a6dea0793753700be732dc8279d38419ddca888a18f33` |

Root can publish the scoped first-natural-issuance acceptance in the existing programme record. Observe the existing writer/grader's genuinely new scheduled outputs and eventual mature outcomes under their existing owners; do not manufacture issuance or rerun the producer to strengthen this proof. Evaluate actual decision-availability and execution clocks before any actionable-performance claim.

**STOP — this independent review is complete.** All local checks completed with exit code zero. No remote call, first-party execution, source modification, provider invocation, model fit, CI rerun, service operation, new watcher or publication was performed by this review. Only this review file was written.

