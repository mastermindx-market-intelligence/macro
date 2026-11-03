# P00 independent technical assessment and disposition

## Source assessment

Reviewer: separate native agent /root/paper_contract_review. Scope: read-only architecture/adversarial judgment and source assessment of the existing Paper adapter. This was not a Fabric worker START, formal nonauthor GitHub approval, RIG acceptance or runtime admission.

The initial review identified the requested-tool contract changing during the guard getter as a concrete gap. Three offline reproducers exercised write_html, create_file and guarded get_jsx. They could dispatch on the original source after the chosen descriptor changed.

The reviewer independently reran those three reproducers after the repair. The observed repaired trace was catalog → get_basic_info → catalog, then TOOL_SCHEMA_CHANGED with zero requested dispatch.

The final assessment compared all five changed files to protected c57adacb338fe837c7d585f1e372c64d9b0118ec and found no remaining blocking correctness or capability regression:

- Requested descriptor and outgoing input profile are requalified after the getter.
- The new pre-dispatch catalog lookup lies outside the mutation exception handler, so failure remains refusal instead of fabricated EFFECT_UNKNOWN.
- Post-dispatch uncertainty and retry_allowed=false remain intact.
- Allowlists, file/snapshot/operation checks, sourceFileId stripping, token-delete prohibition and organization restrictions are unchanged.
- New bridge digest dfbf0b11c49a595610d1ac0e663d95f7291b500cb84d31ef8169bc3b909a2eaa matches the v21 candidate.
- Historical v2–v20 maps are unchanged; v20 remains 1a73ab002e89c87b489e8cee9f5c821530929a5b701eb0aaac7eed03a5a22ced.
- The documentation accurately separates source readiness, runtime release, account-app proof and the remaining non-atomic vendor boundary.

### Requested amendment

Add a regression for failure of the second catalog read after a valid guard. Implemented as test_catalog_failure_after_guard_refuses_before_mutation; it raises UPSTREAM_UNAVAILABLE and asserts the only vendor call was get_basic_info. The final available suite passed with that test.

### Limits and exact disposition

The reviewer inspected relevant test coverage and independently ran the original three reproducers, but did not independently attest the entire 164-test root run. That root run recorded 157 passed and 7 skipped because the dedicated mcp==1.30.0 SDK was unavailable. The full raw local result is test-results.txt.

No source review approval, protected release, installed v21 runtime or live v21 Paper acceptance is claimed. Formal review was not dispatched while the original carrier's Draft/HOLD restriction remained. The candidate was assessed as technically suitable for the existing owner's exact-head review/check process when admitted.

## Canary scope reassessment after owner correction

The latest #1011 correction (comment 6592856295) retracts a plan-based blanket write denial. The reviewer recommended reusing accepted v20 proof for P00's original mismatch, holding v21 live proof until its reviewed release/activation, and recording current-session write execution as not attempted/unproven.

A new v20 canary could prove only this exact session's accepted write if separately needed and admitted; it would not establish another account's entitlement, current C1–C4 mapping, or v21 behavior. P00 did not add a mutation solely to improve its delivery label.

## Evidence and return review

Reviewer: separate native agent /root/p00_evidence_review, with no inherited task history. Its first pass received only the user/business job, production-before observation, proposed-after claims and capability/task manifest, plus six allowlisted raw catalog/schema/metadata/readback/JSX/JPEG artifacts. Full return, source rationale and test explanation were withheld until its findings froze.

### Frozen first-pass findings

1. Catalog edit descriptors and compatible-tool list both contain exactly 16 tools; incompatible list is empty. All eight resource-contract descriptors match the actual catalog. No current-catalog capability loss was found.
2. Raw and normalized exact-file read agree on the real Hub identity. Original index, both QA artboards and the seven product pages are present. This is presence evidence, not a complete before/after content or route-preservation proof.
3. accepted_for_write, write_binding_ready, live_qualified_tools and bridge_access are compatibility/binding labels. They must not be represented as permission/admission/effect proof. The file-creation publication hold and parentId restriction must remain explicit.
4. JPEG and JSX agree, but the displayed v20/Ryan/e3ee36e/date content is historical QA content. A new read does not prove a new write, named-account identity or v21 behavior. The first-pass bundle did not independently establish the original owner's acceptance receipt.
5. Folder/move/archive/cross-file limits are stated correctly. Existing within-file node movement remains available as a source capability.
6. Website/source inspection, concrete repair/preservation tests, original-owner proof links and durable handoff/admission conditions required second-pass assessment; their omission from a deliberately blind first-pass bundle was not judged a failed implementation.

First-pass disposition: credible BLOCKED_RETURN capability/evidence handoff, not current write or production acceptance.

### Amendments and second pass

The return now states explicitly that preservation means P00's no-change footprint and capture-time presence, not exhaustive product regression proof. Its file-creation hold, current-session NOT_ATTEMPTED, v21 not-installed and BLOCKED_RETURN labels were retained. The reviewer then received the complete return, source/test evidence and exact owner references for the second pass.

Second-pass correction: the resource JSON initially described already-trimmed names as an enforced bridge constraint. The actual bridge checks only nonblank-after-trimming and trimmed length 1–500, and only for create_file/rename_resource; it forwards the supplied string. Both JSON and return now distinguish that rule from the recommendation to send trimmed names. No undocumented create_file normalization is claimed. This was a specification correction; no source change was needed.

Formal RIG remains not submitted. No product visual/taste approval is represented by the existing QA screenshot.

### Final second-pass disposition

The evidence reviewer found the complete return suitable as an honest BLOCKED_RETURN/PARTIAL handoff, with no additional source correctness blocker in the five-file diff. It recomputed all five candidate hashes and verified that all 19 preexisting runtime-generation entries remain unchanged, with only v21 added. It confirmed that the local log supports 164 run, 157 passed and seven SDK-dependent skips, and that the return does not turn those results into hosted success or formal approval.

The reviewer's necessary specification amendment was the file-name wording described above; the explicit preservation qualifier was also added. Both are in the finalized artifacts before manifest generation. The reviewer did not rerun the entire suite or independently retrieve the remote original-owner receipts. Its review followed the frozen blind first pass, then authorized full-return/source inspection. It performed no edits, Paper calls, publication or formal approval.

Final boundaries remain current-session write NOT_ATTEMPTED, v21 not installed, create_file publication HOLD, unsupported organization actions blocked, formal GitHub approval absent and RIG not submitted. The manifest is generated only after these review amendments are complete.

Focused final confirmation: after rereading the amended JSON, return paragraphs and review ending, the evidence reviewer confirmed all requested amendments were present and no necessary content amendment remained. Final disposition: the package accurately supports BLOCKED_RETURN/PARTIAL as a capability specification, evidence handoff and source candidate; it does not establish current write admission, installed v21 behavior, production acceptance or a completed F03 mutation dependency.
