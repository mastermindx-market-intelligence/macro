# QLedger publication-continuity witness implementation plan

**Mission:** Grey Deer / MAS-258 / Macro #8128 and #8648. The current Chairman-assigned Meta-CEO session is continuing the warning-delivery program. This is a new, source-only prerequisite for the existing QLedger publisher, not a production format transition.

**Operation:** `gd-native-publish-continuity-20261015`.
**Source base:** Macro `02d2c1b126af100bef3acf1a808fae1943f7bd3d`.
**Procedure:** Mastermind `78388ac29f7e54c9dfe7799a8e4769fb46d4aed6`, Skillpack 1.0.1/bootstrap 1.
**Existing specifications:** `research/QLEDGER_CONTINUITY_SOURCE_PLAN_2026-10-09.md`, `research/QLEDGER_CONTINUITY_IMPLEMENTATION_2026-10-09.md`; merged #8693. Held import preview #8756 and batching #8042 keep their own source custody and release gates.

## Product outcome and narrow scope

Risk-warning history must survive a storage repair before a normal nightly can reliably publish new observations. Splitting bytes into valid members does not itself prove continuity with the source previously accepted by the publisher. A candidate can have valid hashes and fit all limits while representing the wrong history or an unassigned transaction suffix.

Build two explicit read-only checks inside the existing native publication owner. They bind a candidate to exact Git objects and the already existing native operation receipt. They do not infer remote acceptance, issuer rights, quiescent writers, grants or release readiness from a caller's identifier.

## Design decisions

1. Reuse the accepted format, planners, Git reader and publication functions. Do not introduce a second schema, ledger, registry, scheduler, publisher, authorization plane or activation environment variable.
2. Preserve `engine.qledger_store._production_claims_binding` and the current CLI's hard-legacy selection byte-for-byte. Both new APIs are inert until a separately admitted caller uses them.
3. Initial conversion and subsequent native append/rebase are different proofs. A raw legacy source cannot be treated as an already native base when it exceeds the native base-member ceiling. Read it only through a new explicit immutable Git-source method capped by the existing logical/snapshot bounds; do not widen any member or Git publishing limit.
4. The source reader verifies raw Git commit/tree/member linkage, rejects symlink/non-file ancestors, checks the expected blob ID and its object hash/size, and returns an immutable exact byte snapshot. Hash-checked tree traversal reuses `_git_tree`; `ls-tree` text alone is insufficient. No lazy fetch or root discovery.
5. The conversion check requires a zero-byte canonical native base, exactly one append conversion transaction with the supplied stable transaction ID, and identical ordered raw logical bytes and digest to the explicit legacy Git object. Original malformed/duplicate/blank/Unicode rows are preserved, not parsed or re-registered. Native data already present in the purported legacy baseline is a conflict.
6. The native-operation check re-reads the exact accepted-tip native tree, uses the existing `rebase_native_pending` with a matching operation/lane/limits receipt, and requires its expected root to equal the named Git candidate. A valid-looking root carrying unknown rows, dropped history, a stale rewrite or a different transaction is rejected. It also runs the existing newly reachable object and size checks, including oversized deleted ancestors.
7. Neither check mutates a working tree, index, Git ref, source file, clock, notification or runtime job. Results explicitly report `effect=not_attempted` and `eligible_for_cutover=False`.

Rejected alternatives: copying raw claim IDs into a new dedupe store would alter existing semantics; exposing the current preview as a deployment action would confuse format fit with custody; turning on manifest discovery or an environment flag now would bypass the still-unproven production binding.

## Files and interfaces

- `engine/qledger_store_sources.py`: immutable `GitLegacyClaimsBlob` result and `read_legacy_claims_blob(repo, *, tree_oid, expected_blob_oid, limits)`. Reuse the existing verified raw-tree and Git-runner implementations. Returned bytes are not a writable plan or an admission grant.
- `scripts/ci/qledger_publication.py`: `check_legacy_conversion_candidate(...)` and `check_native_operation_candidate(...)`, composing existing `check_publish_candidate`, exact Git source adapters and native receipt/rebase checks. Return a bounded immutable witness with source/candidate identities and explicit scope limitations.
- `tests/test_qledger_store_sources.py` and `tests/test_qledger_publication.py`: extend the already enrolled suites. No new standalone runtime script or new test job.
- This plan/result record: retain source identities, red/green evidence, independent review and remaining cutover conditions.

## Implementation and verification

- [ ] Add source-reader and conversion contract tests; observe expected failures before implementation.
- [ ] Implement explicit immutable legacy-source reading and source-to-conversion witness. Test ordered duplicate and malformed bytes, wrong expected source, corrupt or symbolic Git tree, wrong baseline, omitted/reordered/different contents, and oversized newly introduced ancestry.
- [ ] Add native operation integration tests; observe expected failures before implementation.
- [ ] Compose actual accepted/candidate Git snapshots with existing operation receipts and rebase. Test remote prefix + local suffix, already-applied retry, different IDs/payloads/lane/limits, stale rewrite, wrong accepted tree, candidate differing from HEAD, and no changes to the index/ref/worktree.
- [ ] Run existing source/protocol/native/publication and binding suites as needed for changed dependency closure, then existing CI-path/import guards. Do not rerun financial replays or historical grading.
- [ ] Obtain one independent bounded Fabric review of the final exact diff; keep its original root/parent/run and adjudicate findings.
- [ ] Publish the source candidate through the normal Git workflow of this new managed operation, bind hosted CI/review to its exact head, and preserve the remaining production gate. No admin bypass or merge-on-green.

## Review focus

The important adversarial questions are: Can a substituted source object masquerade as the accepted history? Can a format-valid candidate hide removed, reordered or injected raw occurrences? Can the caller swap a native receipt's root/lane/limits and still pass? Can an oversized intermediate Git object escape after final-tree deletion? Can any proof API turn this caller-provided identity into runtime/cutover authority? Tests should attack all five.

## Recovery and release boundary

This source workspace was freshly admitted by `mmx-workspace` at `/Volumes/Mastermind 2/agent-workspaces/macro/web/gd-native-publish-continuity-20261015`; only these new changes belong to this operation. Ordinary Studio shell Git is the selected source carrier for this new work from the start; no old refused typed-Git operation, checkpoint mutation, Terminal wiring or raw-ledger distribution request is replayed here.

The heartbeat fixes #8835 and #9070 have already merged and will not be reimplemented. The actual QLedger cutover still requires the current original publisher's accepted-tip provenance, explicit disposition of retained failed tails and first-issued clocks, mixed-version writer fencing, independent release acceptance and a successful natural, non-skipped nightly. These checks supply narrower mechanical evidence only. Warning PR #8132 and the earlier held Terminal work retain their distinct permission/source gates.

## Executed source result — first candidate

The immutable legacy Git source reader and both publication-continuity APIs are implemented. Production selector `engine/qledger_store.py`, protocol, native mutation implementation, and every pre-existing publication function (including the CLI) are unchanged. AST/source comparison verified that only the new witness class/APIs and imports were added to the publisher. No original claims, private data, source clocks, live writers or old refused actions were accessed or changed by execution.

Red/green evidence: 17 new source-reader cases initially failed because the API was absent; one temporary corruption fixture initially hit its own Git-created read-only file and was corrected to make the intended test-only corruption, then failed on the absent API. The source suite passed 91 cases after implementation. Twenty-one new conversion/native integration cases failed on the absent APIs, then the publication suite passed 67 cases. The combined existing QLedger, all bypass-reader, protocol, source, native mutation/binding/integrity and publication suites passed **756 tests in 48.03 seconds**, no failures. Existing script-import pinning passed **11 tests**. `git diff --check` is clean. The curated CI closure check is separately in progress; full hosted CI and independent review are still owed.

Independent review was submitted through the installed M2 Fabric adapter as `gd-native-publish-continuity-review-20261015-01`, original root and assigning parent `gd-native-publish-continuity-20261015`. The normal router admitted Qwen3.8-max/Bailian on Ubuntu3, with a granted existing pool lease. Packet SHA256 `70bb3009e548ed172e7b239c0da8e81360266c0d88d7577925d9cbd53c0a9ef0`; it contains the frozen four-path diff, exact file hashes, design and relevant unchanged owners. At this checkpoint execution/return is still pending, not accepted. The reviewer has no modifying, financial-data, publication or deployment scope.

The named consumer benefit is a separately checkable link from the original accepted QLedger Git history to a storage-conversion candidate, and from an accepted native prefix to only the declared pending operations. This narrows the unsafe gap before normal Risk Radar nightly issuance can resume after a proper cutover. It does not itself recover withheld historical tails, authenticate a remote accepted tip, switch production storage or deliver a user warning.

Next: adjudicate the independent return, apply any in-scope repair with a failing regression first, finish CI integration/hosted tests and exact source publication. The source-only check can be released independently of activation; actual native storage remains held until the existing QLedger/publication owner resolves the original tail and writer/cutover conditions. Mission completion remains false.
