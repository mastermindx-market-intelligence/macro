# Mastermind #1567 — independent semantic review of the deployment-helper candidate

**18 October 2026 UTC · Final frozen two-file candidate · Production deployment remains prohibited without separate current authorization**

## Disposition

**Pass for handoff of this bounded helper/test source candidate to the existing native owner and its remaining gates.** The reviewed control flow corrects the identified stop-before-copy, snapshot coverage/readiness, restoration, rollback-health and marker-ownership defects. Independent review exposed two additional classes of failure in the preceding candidate: misleading recovery completion with an unchanged active cohort but changed authority bytes, and a silent failed receipt scan admitting deployment. The final candidate addresses both; the retained controls distinguish the failures from the corrected behavior.

This disposition does not complete native test acceptance, qualify a production deployment, establish automatic recovery from every filesystem state, or accept delivered Risk Radar intelligence. A protected descendant under a newly introduced directory can deliberately leave restoration incomplete and the service stopped. Native runtime compatibility, real stop/lock behavior, exclusive release ownership, runtime-data effects and complete backend-to-user acceptance remain separate gates.

The independent reviewer read source, diffs and retained result records only. No first-party helper, test body, module, provider, model, scheduler or recovery operation was executed by this reviewer. No native tools, network or live application access were used. No source files were edited. Earlier accepted activation, dependency and settlement reports remain intact; #1586 retains the forward module and its tests.

## Exact source and evidence identities

All paths below are under `/workspace/scratch/da452a3ea08d/release_review/`. Each listed byte count and SHA256 was checked locally. The builder confirmed the final candidate was frozen, and its last delta was read before this disposition.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `candidate/scripts/deploy_code_to_vps.sh` — **H** below, 483 lines | 20,370 | `1ebfd44db982d73f7f9d507109fa3983ba65cc948e8afe9fe697589d712728a8` |
| `candidate/tests/test_deploy_provenance.py` — **T** below, 804 lines | 39,649 | `a4ed6d45ed39eec1aa92ac9d4aeb82219dcefc60e9632e7f27dd8b00f6bfb42a` |
| Unchanged `source/scripts/deploy_code_to_vps.sh` | 14,934 | `c158fc903121b8c4ad680049ded16000913393039944c6eec3a23d44ca376204` |
| Unchanged `source/tests/test_deploy_provenance.py` | 19,097 | `1bc5bf5e1980cb97fb8051d062e90e60536432b03782ff008cb31066f950bd3c` |
| `HELPER_CANDIDATE_REVIEWED_VERIFICATION_2026-10-18.json` | 8,506 | `dbfe8dc9ec6b5f70d060883b7e34e0ca285e09c6ae7f35dcb1372546d046a003` |
| Final `HELPER_CANDIDATE_MANIFEST_2026-10-18.json` | 4,688 | `213b6df3bf7e60732414cedf34b1eb88a932ec641b607f1966a4813bd5ce6569` |

The manifest binds the two changed first-party paths and the retained originals, red baselines, test driver and result records. The earlier manifest is retained separately as `HELPER_CANDIDATE_MANIFEST_PRE_REVIEW_2026-10-18.json`; it must not be used to identify the final candidate. The parent's prospective native base is `d65414e89ad3b930d84d614196a91d3cce8ba589`. This review did not use Git or independently re-establish native custody or an advancing branch identity.

## Control-flow assessment

| Phase | Source-supported behavior and failure boundary |
| --- | --- |
| Scope and no-op | H:19–50 requires a source directory/full expected SHA and rejects ambiguous/overlapping remote roots and invalid service text. H:117–122 requires existing physical canonical roots. H:125–136 combines a checksum dry-run with exact target health and active forward status before a no-op. The existing archive wrapper remains the clean-source owner; the helper itself does not reconstruct or attest the archive. |
| Recovery admission | H:154–162 initializes the attempt facts; H:265–280 installs one EXIT/INT/TERM recovery path before any service mutation. Recovery is enabled before initial stop, and possible tree mutation is recorded before forward rsync. A failure cannot be treated as proof that a modifying command had no effect. |
| Initial and recovery stop | `stop_service`, H:179–187, always issues `systemctl stop`, including after an earlier nonrunning observation, then requires `ActiveState=inactive|failed` and `MainPID=0`. This addresses a queued restart under the observed `Restart=always` policy. It runs before source replacement and again before rollback restore. An unverified recovery stop returns without restoring a potentially running tree (H:190–198). |
| Settlement and authority gates | H:303–330 refuses any observed WAL, any top-level `*.json` receipt entry regardless of type, and a nonzero receipt enumerator. `find -H` follows a command-line receipt-directory symlink consistently with scanning that directory; it does not filter out child symlink/directory entries. H:336–352 requires readable canonical US account/fill files and valid hashes while the configured service is stopped. No settlement recovery is invoked to clear these gates. |
| Snapshot coverage and readiness | H:354–391 creates a fresh snapshot below the protected, nonsymlink `.deploy_prev`, leaving prior snapshots intact. It copies the whole eligible receiver tree with the same `EXC` array used for transfer and restore, verifies the checksum dry-run, then captures provenance and optional tag preimages or explicit absence. Only successful completion sets `SNAPSHOT_READY=1`. |
| Live replacement and metadata | H:393–412 records possible mutation before checksum rsync with deletion. It atomically replaces the code SHA marker and passes the selected service identity to the existing optional Datadog helper. Failure in any of these steps uses the same recovery path. |
| Established cohort | H:282–292 records marker bytes and recognizes the active path through successful forward status. On that path H:417–420 and 474–476 require the marker to retain its identity; init and finalize are skipped. A historical cohort SHA does not have to equal the new code SHA. |
| Target verification | H:434–442 restarts and probes the target. `probe_health`, H:67–89, requires reasoning policy, scheduled runtime and the exact valid expected SHA. H:448–469 holds the canonical US outer book lock across account/fill comparison, conditional finalize and status. Only then, and after the active-marker check, is `RELEASE_COMMITTED` set. |
| Source restoration | H:199–231 requires a verified snapshot after possible mutation. It restores the same eligible tree with deletion/checksums, verifies it, then restores exact provenance/tag preimages or absence before restart. Any copy, comparison or metadata failure returns while the service remains stopped. When no tree mutation began, an incomplete snapshot is not used; unchanged old code can be restarted (H:232–234). |
| Recovery outcome | H:235–262 retains marker state and detects identity changes. The final-authority failure flag independently requires reconciliation even if marker bytes stayed unchanged. Old restart failure or required old health failure is incomplete. Verified recovery wording is explicitly limited to code rollback with runtime data retained. The deployment still exits unsuccessfully after its failed attempt (H:265–276). |

### Why full filtered restoration is materially stronger

The original helper synchronized the whole filtered archive but backed up a separately enumerated set of directories/files. The candidate removes that divergent list. A receiver-only eligible file deleted by the forward transfer is present in the snapshot; an eligible new file introduced by the failed release is absent from it and is removed during restoration. Existing tests inspect actual receiver-only `docs/obsolete.md`, changed `CLAUDE.md` and new `research/new.md` bytes, rather than just looking for a restore command (T:317–330).

The same exclusion array applies at every depth for forward copy, snapshot and restore (H:103–115, 154, 208–210, 367–369, 395–396). It protects excluded descendants from being rewound or removed as part of a whole-directory restore. The nested `.env` control checks that newer protected bytes survive (T:362–369). Checksum comparison addresses equal-size/equal-mtime content drift (T:412–424). This is an eligible-tree rsync preimage, not an image of every filesystem attribute or excluded runtime artifact.

## Independent-review counterexamples and their resolution

The following failures were identified from control flow, then reproduced by the builder before the final fix against helper SHA256 `c64b940d75a70db26eeed6af1305c2c0e7c924201026a45b69aaa8de2ebe483d`. The exact preceding helper and the same final test source are retained in `review_red_baseline/`. These are fixture failures, not alleged production incidents.

**1. An active marker could conceal residual authority changes.** With an established active cohort, target restart changes either account or fills. The final byte gate refuses release, but the old recovery logic compared only marker identity; unchanged marker bytes permitted a completion message while the changed authority bytes remained. Both controls failed their outcome assertions. The final candidate sets `FORWARD_VERIFICATION_FAILED` on any failed compare/lock/finalize/status operation (H:470–472), checks that flag during recovery (H:244–246), and reports code health restored with authority/state reconciliation still required (H:258–260). T:455–472 proves the historical marker is unchanged, the changed authority bytes are retained, source is restored, and the outcome is explicitly incomplete.

Retained red receipt: `HELPER_ACTIVE_COHORT_REVIEW_RED_2026-10-18.json`, **3,620 bytes**, SHA256 `e707a31ee264c2138c6448db9be559a8b8800e00185e6bca9c1d371dd2291594` — **two failed controls** before repair.

**2. A silent receipt enumeration failure could be called clean.** A conditional `find | grep` did not propagate the enumerator's status. Ordinary diagnostic output was already rejected by the outer exact-`clean` check, but a silent nonzero find admitted deployment in the added control. H:313–317 now captures and explicitly checks find status. T:581–590 verifies refusal before any source copy and a restart of unchanged old code.

Retained red receipt: `HELPER_RECEIPT_SCAN_REVIEW_RED_2026-10-18.json`, **1,576 bytes**, SHA256 `2c0049ac553fd7787f9c0e7d2832145f5a2aba8d9e02f9782720e1cb1c975b01` — **one failed control** before repair.

The directory and dangling-symlink receipt controls independently check reader-entry coverage (T:565–578). They do not substitute for the enumerator-error control.

## Explicit retained limitations

**Protected descendants can prevent automatic availability recovery.** The new control introduces `new_package/module.py`; simulated startup creates excluded `new_package/__pycache__/x.pyc`. Failed target health triggers restoration. The included module is removed and the protected cache survives, but its nonempty parent cannot be deleted and exact restore verification remains nonempty. The helper correctly reports incomplete restoration and leaves the service stopped (T:593–611; H:208–230). This is a verified conservative refusal with an availability cost. It is not evidence that the previous service was successfully restored, and no ad hoc cache deletion was added. The separate retained control is `HELPER_EXCLUDED_CACHE_REVIEW_CONTROL_2026-10-18.json`, **572 bytes**, SHA256 `f43a30f87f673fcca0e1aff7ab61c2e34aad96645064504dfce1dcd960259251`.

**Service stop and release exclusivity remain bounded.** The source checks the configured unit; it does not enumerate every detached process or acquire a lock between competing deployers. The retained live unit settings and data-namespace observations support the expected current path, but they are not an executed stop or proof of future exclusivity. The post-health US lock protects cooperating book writers; it does not serialize every regional/low-level writer. No global concurrency claim is accepted.

**Runtime effects are retained.** Target startup can perform queue quarantine, WAL recovery, evaluation or scheduled work; code rollback does not undo these. The current flag truthfully classifies a failed final authority check. A target-health failure can occur before that check, and regional books, queues, journals, NAVs and forward snapshots are not all compared by the helper. The scoped success message therefore does not certify unchanged runtime data or compatibility of every target-start effect with old code. An unknown marker transition is retained; old code can be restarted with reconciliation still outstanding. This does not make first initialization or pending activation atomic.

**The active-cohort guarantee has an observed-entry condition.** The explicit preservation branch depends on a valid marker identity and successful initial status. Existing-marker status failure is not a complete classification of pending versus temporarily unverifiable active state; it falls through the existing init/finalize path. Current upgrade qualification must retain successful evidence for the intended active cohort and the release-owner constraint. Arbitrary invalid/concurrently changing marker states remain outside this source acceptance. The reviewed forward module's preserve-active behavior remains supporting evidence, not permission to change its owner.

**No-op and metadata claims are narrower than a disk image.** The inherited no-op count discards directory-only dry-run entries (H:130–136); it is not a proof that every directory attribute matches. The snapshot/restore uses rsync archive/checksum semantics and explicit marker/tag preimages, without establishing every hardlink/ACL/extended-attribute or path-type permutation. The tested nonsymlink snapshot root and excluded-cache case do not qualify every directory-to-file/symlink transition. If the previous provenance marker is invalid or absent, rollback health uses the documented legacy branch without an exact prior-SHA requirement (H:67–89, 146–150).

**Lost replies remain uncertainty.** Possible partial source copy enters recovery; a failed snapshot response before mutation does not authorize use of that snapshot. A failed stop or restored restart response can leave actual remote outcome unknown and is reported incomplete. Simulated lost init/finalize responses retain marker state. EXIT/INT/TERM handling does not establish host-loss, SIGKILL, power-loss or arbitrary transport-interruption recovery; the attempt flags are in-process facts.

## What the tests establish and the next actual gates

The retained final receipt binds the exact final source pair and records **44 standalone cases passed, zero failed**. The builder used its standard-library driver to load the standalone test bodies; the five existing application-import tests and native owning pytest were not executed. The fixture uses real local **rsync 3.2.7, protocol 31** for filter/checksum/deletion behavior, and fake SSH, systemctl, curl, forward CLI, flock and sleeps (T:87–305; final manifest validation section). The fake booted commit is distinct from the on-disk marker. Fake flock supports invocation/order assertions, not actual contention evidence. This reviewer verified the receipt identities and test/control semantics and did not rerun them.

The implementation handoff explicitly retains unexecuted variants, including real stop/transport reply loss, a separate restored-restart failure, the complete path-type matrix, every health/no-op variation and global concurrent deployment behavior. Passing the exercised cases does not erase those limits. Broader first-run and direct-mark conditional defects remain with their existing owners and earlier reports.

The next admitted action is to transfer only the frozen helper and existing test-owner file into the parent's authorized native successor, rebind their bytes and current source/instructions/custody, and complete the native owning test gate. Production qualification then needs the actual final archive and receiver plan, effective environment and writer/stop/lock evidence, a usable recovery path for its particular introduced/excluded paths, compatibility and reconciliation of permitted startup effects, and real backend-to-user proof. **This review does not authorize production deployment, install #1567, or close the Risk Radar programme.**
