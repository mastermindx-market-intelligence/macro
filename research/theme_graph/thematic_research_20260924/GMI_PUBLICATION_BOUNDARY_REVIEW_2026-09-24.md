# GMI Meta-CEO - publication boundary and forward execution

Parent: gmi-thematic-research-meta-ceo-20260924-001, Macro #7886.
Date: 2026-09-24. This is source-qualified architecture/coordination, not a native implementation or release approval.
Protected procedure: Mastermind f1c070d733c4683b20bbbd9af8fae6c30dc38d84, compatible Skillpack 1.0.1/bootstrap 1. Current Chairman continuation preserves the existing Meta-CEO integration delegation. Incumbent source writers, R4, source rights and independent review remain controlling.

## 1. The useful outcome

Preserve a complete, bounded Technology economic explanation and its evidence through the existing private publication owner. Do not reduce the approved 50-row / 25-card / 100-relationship first-unit design merely because a small conditional-control object has a different allocation boundary. These counts remain the Technology packet's design bounds, not an assertion that every record at those counts is below a measured aggregate byte budget.

Consumes Technology's existing size question on #7793/comment5813422674. Its reported 28,150-byte and 52,230-byte synthetic dossiers are receiver measurements, not repeated real-data measurements by this review. The shared foundation remains #7870; no additional publisher, private store, version authority or domain writer is assigned here.

## 2. Exact source qualification changes the premise

Macro main inspected at 7ab5b531cceb9a5ade2a69e64c40c1728919bace:

- engine/research_vault/r2_store.py, blob 139fcbe8cf08945a2be1feaa0dca5428c818837b. The same complete blob is present on Technology #7891 head 60228b0feb470d42f49ee9d4eb67fbf03c702844.
- Lines 42-127 define a 16 KiB constant and separate strict/bounded/conditional capabilities. Bounded readers accept a caller limit.
- Lines 839-888: LocalStore._version_at limits reading an EXISTING conditional predecessor to 16 KiB.
- Lines 902-1020: LocalStore.put_bytes_strict_conditional checks that predecessor before writing the candidate, but does not reject a new candidate merely because len(data) exceeds 16 KiB. A successful first write can therefore leave an object that a subsequent local conditional comparison refuses.
- Lines 537-576: the inspected R2 conditional-write method does not apply that constant as a candidate-size check. This is a SOURCE-level backend asymmetry, not a claim about a live service's allowed size or permission to switch backend.
- engine/earnings_narrative/private_publication.py, blob 0ee93909693893f419f0109f9eba1994d94e2b46. Its existing architecture separates a small pointer from bounded, content-addressed manifests and records. Lines 42-47 declare pointer 16 KiB, manifest 8 MiB, record 2 MiB, context packet 512 KiB. Those are EARNINGS-specific bounds, not automatically approved GMI limits.
- The existing publication routine at lines 671-743 still uses ordinary pointer put and a best-effort prior-pointer restore. This source is not proof of an accepted CAS-fenced multiwriter publisher. Do not copy that restore path as a new GMI concurrency design; concurrent pointer correction stays with its incumbent owner.

Conclusion: 'the entire Research Vault cannot hold a dossier above 16 KiB' is not supported. The real question is which exact primitive and representation the accepted GMI adapter uses, including replay and supersession, and how its bounds apply consistently. Public reachability, a successful initial put, and source inspection do not qualify the private production path.

## 3. Actual local characterization and limits

The Meta-CEO executed selected LocalStore method bodies transcribed from the exact-ref source in a temporary local directory. Constructor/error classes were test scaffolding. This was NOT a full native-module test, source-file-byte-verification, remote R2 test, concurrency proof or production mutation. Synthetic repeated bytes, not issuer or private dossier content, supplied the size cases.

| Synthetic byte length | First conditional create into absent key | Second conditional write with matching predecessor |
|---|---|---|
| 16,384 | true; exact bytes present | succeeds |
| 16,385 | true; exact bytes present | predecessor oversize refusal |
| 28,150 | true; exact bytes present | predecessor oversize refusal |
| 52,230 | true; exact bytes present | predecessor oversize refusal |

All post-attempt bytes remained unchanged. A stale predecessor on the 16,384-byte control refused and preserved its bytes. Eighteen characterization assertions passed, zero failed. They demonstrate the selected-method behavior, not an accepted implementation fix.

Convenience reproducer: characterize_conditional_size.py, SHA256 3557775304ce3af847817db2ec699f559a25e4adb16786618baadb4c5228d469. Its receipt is supplied with the portable review package; neither is a replacement for native owner tests. Exact source pin, methods and the complete observations above make the finding recoverable without that package.

Required NEXT native characterization, not executed by this review: exercise the actual LocalStore with absent-key create, bounded/versioned read, identical replay, stale predecessor, conditional replacement and failure preservation at 16 KiB, 16 KiB+1 and the declared consumer sizes. Compare the contract with a controlled remote-adapter test double. Do not contact live R2 or read credentials to reproduce a local contract issue.

## 4. Meta-CEO product and architecture disposition

A. Keep the approved bounded Technology content scope. No silent truncation, smaller dossier masquerading as the full scope, or forced pagination contract change. A genuinely useful smaller release needs its own explicit product boundary, not an accidental storage workaround.

B. Do not raise a shared safety constant, select a different backend, switch to a permissive read/put, compress unbounded input, or omit the failing replay to get a green result. The source finding does not authorize any of those changes.

C. Select the existing-owner separation of bounded immutable data from small conditional publication control. Preserve content digests, lengths, source/correction identities, exact input generation and authoritative predecessor tokens. A composed dossier generation and an individual curation_revision are different identities: do not stamp many independent assertions with one invented assertion revision.

D. The shared publication/store owner must map this selection to its actual accepted adapter. Larger immutable data may use ONLY that owner's already-qualified immutable-artifact primitive, with an explicit GMI object and aggregate read budget. If its accepted path requires conditional semantics for every body and cannot support the declared object, a finite manifest-bound representation split is the alternative within the SAME publication owner. It is not permission for Technology to invent an index store, a second current pointer, a generic sharding service or a new identity grammar.

E. Publish immutable closure first; verify every required member and its exact digest/length; promote the small current control object only against its expected predecessor. A rejected predecessor is a conflict, not an unavailable store. An ambiguous promotion stays EFFECT_UNKNOWN on that same owner/carrier until readback; no blind retry or unconditional restoration of a stale pointer. Readers must not stitch different generations or substitute fixtures/public files for unavailable private input. Rights and dependent-prose filtering remain current vetoes even on a historical generation.

F. This closes the Meta-CEO product decision against shrinking content or widening the shared cap. It does NOT accept the unreturned T11a/private adapter, an unreviewed physical manifest contract, source permission or live publication. The next deliverable is one exact native field/primitive/budget map plus discriminating tests from the incumbent owner; Technology consumes that accepted result through its held T6/G5 path. Existing signed/exact/qualitative and company-first profile amendments remain separately reviewed.

## 5. Acceptance evidence owed by the existing owner

The implementation return should prove: consistent admissibility on first write AND identical replay; missing or corrupted member leaves the old complete publication intact; stale concurrent promotion cannot rewind current; exact generation pins both data and evidence; a correction updates dependent prose and figures together; source revocation does not leave derived content visible; oversized object, member count and aggregate-byte limits reject before uncontrolled allocation; small legacy consumers retain semantics; no raw object key or locator becomes a public URL; and a real permitted large-domain explanation survives the normal next publication.

Size tests alone are not privacy, source-use, successful deployment or user proof. No real production proof was performed here.

## 6. Independent execution and capacity

Semiconductor consumed the rights qualification direction in #7780/comment5814401358. That return explicitly says no new lane launched: reported mb slots occupied, m1 outside its window and mini2 without egress. H1 and the served-witness fixes remain queued; rights qualification is QUEUED_NOT_STARTED, not an executing research helper. This is attributed receiver evidence, not a new live host census.

Capacity pressure must go to WS:EXECUTIVE-CAPACITY-FABRIC through its existing owner/carrier. No new queue, runner, credential or host change is authorized. Do not move or duplicate STARTed/EFFECT_UNKNOWN work. Where a finite critical fix has not STARTed and the principal holds lawful custody/tools, existing ACTIVE_EXECUTION permits direct bounded completion after reconciling/removing only the unstarted local pending item; this is not a global switch back to principal-only labor. Independent review remains independent. Keep H1/reader-to-user proof ahead of optional breadth, and continue path-disjoint domain work.

## 7. Watcher and progress proof

An independent native task-list read now records GMI Meta-CEO Watch enabled with last_run_time 2026-09-24T12:43:58.458834Z. That proves a scheduled invocation was recorded, not successful GitHub access, a published parent ruling or notification delivery. Push/email flags are false in the observed native object. Keep the existing hourly parent role and one watcher; do not add a duplicate or silently assume child action authority.

The accepted A/B/C research and prior option-A/right-source rulings remain DO_NOT_REDO. This review changes parent architecture/coordination only. No product file, worker lifecycle, store setting, source registry, identity, membership, trade or deployment was modified.
