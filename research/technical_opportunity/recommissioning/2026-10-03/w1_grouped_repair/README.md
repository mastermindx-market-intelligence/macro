# W1 grouped repair — tested review artifact, not applied source

**Target:** existing Macro #7107 / `TOI-W1-EVIDENCE-CENSUS-V1` at `15e4dfb0c9ddc788127d0954fd7d92414eefdcbf`.
**State:** review candidate only. Actual source custody, branch adoption, independent review, Agent OS/current-base/hosted acceptance and W3 remain held.

[Patch](W1_GROUPED_REPAIR.patch) · [test and replay proof](PROOF.json) · [immutable source inputs](SOURCE_EXPORT.json) · [direct-source compatibility](CURRENT_SOURCE_COMPATIBILITY.json) · [candidate W1-to-W3 handoff](CANDIDATE_W1_TO_W3_HANDOFF.md).

The patch addresses the existing grouped repair, not a replacement project: preserve the pending AST-generated-ID validator, correct the duplicate fixture, retain independent first-class cardinality coverage, bind BandWidth to its numeric primitive as partial, preserve the original-occurrence fakeout definition as partial, reconcile 24 exact / 3 partial / 5 missing, and consume the closed original/Connors-RVOL reviews. A source-bound held handoff carries the current 22-slot Daily-first proposal and all remaining gates. Production indicator formulas and the other30 passport rows are unchanged.

## Verification

The unchanged committed-head baseline produced23PASS/3FAIL. The byte-preserved pending validator/tests produced27PASS/1FAIL. Adding regressions produced30PASS/7FAIL. The first grouped run produced34PASS/3FAIL because three old tests assumed the first passport was exact; they now select an actual exact row. No guard was weakened. Final **37PASS**, and all four W1 validatorsPASS.

The patch was applied to a fresh exact-source export with `git apply --check --whitespace=error-all`, then applied locally and replayed. All eight postimages matched; four validators and37tests passed again. Reverting generated-ID support caused2 failures; reverting the duplicate fixture caused1; disabling first-class cardinality caused2. The cases failed on targeted assertions/validation, not missing imports.

All16 directly cited engine-source blobs match current Macro main `f0e501324a5fca5541f57ef6f26bdf1133ec2d82`. This is source compatibility, not whole-repository merge or deployed proof. The live pending validator/test hashes and original exports remained unchanged. No market data/outcomes, engine import, fitted model, trial registration or production effect occurred.

## Matched preserved-preimage form

The [preserved-base patch](W1_GROUPED_REPAIR_FROM_PRESERVED.patch) expresses the SAME repair against the committed snapshot plus exactly the two preserved pending files. It leaves the pending validator untouched and contains seven changed paths. [The replay receipt](PRESERVED_BASE_REPLAY.json) proves clean application and identical postimages to the tested candidate. These are alternative input forms, not two repairs to apply sequentially.

Neither form may be applied to unknown/moved source. Actual source custody and exact preimage reconciliation remain required; the existing dirty worktree was never modified during either proof.

## Adoption boundary

Do not blindly apply this patch over the existing dirty worktree. It is expressed against the committed15e4dfb0 source; the first two paths already have preserved pending edits. The lawful custodian must first reconcile those exact preimages and other effects, reuse the validator byte-for-byte, and review the test-file delta against its preserved preimage. Then apply the remaining metadata changes on the SAME #7107 carrier, validate one immutable head and obtain changed-findings review and current release proof. No clean-writer release or ACK/START is inferred from this artifact.

Do not rerun the completed original20-passport or Connors/RVOL two-finding review. The deterministic selection is unchanged; its stale review-status text is corrected while current grouped-review acceptance remains false. Do not replace native formulas with these metadata statements or treat the proposed22-slot handoff as an executable manifest.

The code/test changes are delivered only inside the patch under this documentation directory. No application `scripts/`, `tests/`, registry or workstream file was modified by this publication. The original#7107 branch remains untouched.

A cumulative-checkpoint comment update was explicitly refused before dispatch during this continuation. It was not retried or moved to another tool/account. This independently requested patch publication is not a replacement checkpoint or a claim that the refused update succeeded. The last verified cumulative checkpoint remains comment5972996672 at its earlier07:34:22Z revision; read this immutable patch/proof as a later implementation-review result.
