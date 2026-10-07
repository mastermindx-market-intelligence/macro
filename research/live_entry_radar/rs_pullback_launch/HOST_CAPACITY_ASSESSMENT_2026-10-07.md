# Host capacity assessment — 2026-10-07

**Normal Macro and Terminal deployment is blocked by measured storage exhaustion. No safe, sufficient local recovery was established.** The next dependency is a bounded capacity action through the existing host/provider infrastructure owner, followed by fresh capacity validation and the normal deployment paths. This assessment neither performs nor approves cleanup, resizing, builds, restarts or deployment.

This is a synthesis of the completed read-only evidence supplied by root. No additional host, source, provider or runtime read was made for this assessment. The exact observations below retain their original scope and dates; they are not a fresh host census. Source delivery and prepared proof acceptance remain separate from installed execution. The parent commission remains open: Phase 1 NOT_ADMITTED, H1/H2/H3 NOT_TESTED, all authority false.

**Measured capacity and the actual blocker.** Root's block-allocation proof, process **44937, exit 0**, was recorded at **2026-10-07 13:12:58 UTC**. Its actual host-read interval was `1791378778792359925`–`1791378778827701717` UTC nanoseconds.

| Measurement | Exact observed value | Meaning and limit |
|---|---:|---|
| Root filesystem total, `statvfs` | 82,086,711,296 bytes | Filesystem accounting, distinct from the virtual disk and partition sizes. |
| Physical free space | 16,777,216 bytes | 16 MiB physical free; this is not the space reported allocatable to the normal filesystem caller. |
| Allocatable space | **0 bytes** | The decisive observed deployment constraint; actual updater writes also failed with ENOSPC. |
| Filesystem block size | 4,096 bytes | Allocated-byte budgets below use actual allocation or the stated 4 KiB-rounded estimate. |
| `vda` | 85,899,345,920 bytes | Exactly 80 GiB. |
| Root partition `vda1`, ext4 | 84,824,538,624 bytes | The root partition occupies the remaining disk tail after the allocated boot/EFI layout. |
| GPT usable sector range | 34–167,772,126; 512-byte sectors | `vda1` starts at 2,099,200 and has 165,672,927 sectors; its inclusive end is exactly 167,772,126. |
| Other device `vdb` | 499,712 bytes, ISO | Not an additional data volume. |

There is **no unallocated tail on the existing 80 GiB disk and no observed extra data volume**. The difference between disk, partition and filesystem accounting is not established usable growth space. No exposed DigitalOcean/droplet/volume-resize capability was found in the existing tool inventory, and no provider action occurred. Neither a resize plan nor a required new size or paid plan has been established.

The normal updater is `/usr/local/bin/macro-update`, SHA-256 `5020601b3dcac69a11fbbbd4ea8d99563e957734052c9961847af65a2c89b117`, on the existing three-minute cron and `/var/lock/macro-update.lock`. Its normal `fetch --depth 1 origin main` failed after **11:51 UTC** with ENOSPC involving `tmp_pack_Cf6wFt` and `shallow.lock`. There was no manual retry, deployment or restart in this assessment or the supplied capacity work.

The last supplied Macro checkout is `f1966d3fdae3f14f42c8e026958f74590d72f9fe`; the running process build is `7a1f9ad0a28973cdc9b261e80bfdf61f4eae9575`. The observed health HTTP 200 establishes that endpoint's liveness/version response, not installation of later source or the ability to deploy. The last supplied Terminal census remains `52b9107`, the legacy v1 source. Accepted merged Terminal v2 is `e963eefb3ac1984008caae922d6f43bfafa9d827`; the existing normal build script, SHA-256 `31d04362f041258524bbce1551befbae7322d2dd80a2f368cf6ae43c98de669f`, is the intended route when capacity exists.

**Candidate recovery is not a demonstrated build budget.** Two precisely identified classes have a combined allocated size of **249,626,624 bytes**. Their identification is useful, but neither was removed and neither is authorized for removal by this document.

| Candidate | Exact evidence | Allocated-byte budget and unresolved condition |
|---|---|---:|
| Failed-fetch orphan `/opt/macro/.git/objects/pack/tmp_pack_Cf6wFt` | Logical size 49,164,288; allocated size 49,176,576; inode 340022; regular file, mode 0444, not a symlink; mtime/ctime `1791374053280043679` ns. Tied to the actual failure log. `fuser` returned 1 with no handle at that census. | **49,176,576**. Any future removal would first require fresh lock/process/preimage reconciliation. A prior no-handle result is not permanent custody. |
| Loose objects also indexed in packs | `git prune-packed -n`, process **88388, exit 0**, identified **1,173** loose objects: 197,170,138 logical bytes and 200,450,048 allocated bytes. Index checksums and pack-trailer binding passed. Candidates span 222 packs totaling 26,345,814,640 bytes. | **200,450,048**. Object bodies were **not** verified. The 26.3 GB pack footprint is not reclaimable space from this operation. No prune was executed. |
| Combined candidate allocation | Sum of the two preceding allocated sizes. | **249,626,624**; a candidate sum, not a safe-removal or successful-recovery result. |

The Terminal target's `package-lock.json` blob `d860c936` and `package.json` blob `47164687` match the live versions, so the normal script skips `npm ci` for that target. `node_modules` and public-data staging use hardlinks on the same device, `64769`; they are not an additional roughly 7.2 GB copy.

| Normal Terminal budget component | Bytes | Interpretation |
|---|---:|---|
| Staged source content, rounded to 4 KiB blocks | 103,071,744 | Excludes directory metadata. |
| Current `.next` output | 119,349,248 | A measured existing output used as a build-size baseline, not a guarantee of the next compiler peak. |
| Source plus current-output baseline | **222,420,992** | Does not include fetch, prebuild `build_data_coverage.py`, directory metadata or compiler/transient peaks. |
| Current `.next.bak` | 119,316,480 | Retained until after build validation; not credited as space available before a successful build. |
| Candidate sum minus baseline | **27,205,632** | Only this much remains even if both candidate classes were lawfully recovered. It is not a proven margin for the excluded work. |

The measured Macro source delta from `f1966d3fdae3f14f42c8e026958f74590d72f9fe` to the accepted Split `f2` release has positive M2 ancestry, three commits and **7,235 new blobs totaling 746,685,551 logical bytes**. Current M2 storage for that measurement is **36,901,663 bytes**, or **37,148,955 bytes for all measured objects**. Neither compressed local storage figure proves the server's fetch-pack size, fetch temporary allocation or the peak against a moving `main`.

Consequently, the evidence supports **insufficient proven build margin**, not a numerical claim that the next build must consume exactly a particular peak. Adding uncertain cleanup estimates to uncertain compressed transfer estimates would not establish a safe deployment budget.

**Whole-pack reclamation was tested and yielded no candidates.** These negative findings are stronger than a filename or size survey and must survive the handoff.

| Completed read-only comparison | Result |
|---|---|
| Index cost census, **11258, exit 0** | 233 version-2 indexes; 42,548,156 index bytes; 29,768,780 OID-table bytes. |
| Pairwise comparison, **18773, exit 0** | No equal OID sets and no pack's set wholly covered by a single other index. |
| Union comparison, **20998, exit 0** | 1,488,439 entries; 887,086 distinct OIDs; 438,818 shared and 448,268 exclusive OIDs. Every pack has at least five exclusive OIDs. **Zero whole packs covered by the other packs.** Witness SHA-256 `4b7ccfa7c53f0e514ae99c5af38102fdc46d7b1f9ece059af11c490308215fdb`. |
| Other-pack union plus actual loose filenames, **32928, exit 0** | Compared 13,923 actual loose filenames. Of 448,268 exclusive OIDs, 1,162 have a loose filename and 447,106 have no alternate representation in this comparison. Every pack has at least four uncovered OIDs. **Zero candidate packs and zero reclaimable pack bytes under this test.** Runtime 7.62 seconds; peak RSS 60,404 KiB. |

The strongest comparison's host-read interval was `1791378402259494621`–`1791378407970291372` UTC nanoseconds. Its witness SHA-256 is `0e507c6640945e5bff3fe2d6cd5a59d1776220c244b1fa63362887090bd96705`.

Index format, sorted OIDs, fanout, offsets and checksums; pack header/count/trailer; and stat stability checks passed. **Pack object-body content was not verified.** The loose-file comparison checks actual filenames, not reconstructed object bodies. No witness file was written to the host. The witness digests identify the bounded comparison output; they are not retained whole-pack body evidence. None of these results supports calling all packs redundant, pruning whole packs, or claiming that a full Git integrity/reachability audit occurred.

**Other occupied space has no established disposable owner scope.** Six inactive `.1` logs occupy **185,659,392 allocated bytes**. Estimated compression gain is **161–167 MB**, not measured recovery. The existing logrotate policy already uses `compress`, `delaycompress` and `rotate 4`; forcing rotation can retire `.4` history and carries `copytruncate` loss risk. No justified content-preserving emergency protocol was established, so these logs are not added to an approved recovery budget.

Both **4 GiB swap files are active and used**. Terminal public data occupies **6,517,993,472 bytes**, `node_modules` **739,110,912 bytes**, and combined cache **966,656 bytes**. Those directory names do not establish disposable content. Macro automatic GC is disabled; the census found **233 packs, 700 files, three refs all at `f196` and three reflogs with 1,287 transitions each**. Preserve the recorded history. No aggressive GC, repack, prune, reflog expiry, forced log rotation or unrelated application cleanup occurred or is proposed as a proven remedy.

The bounded `/var/lib` classification, processes **23421 and 25491, both exit 0**, totals **4,676,976,640 allocated bytes**. The three large Macro service areas account for **4,157,808,640 bytes**: biocatalyst 3,125,481,472; market-memory 671,416,320; live 360,910,848. The first had an observed activating service and running timer, and the others had active timers. These are active public/state owners, not unidentified caches. Apt accounts for **212,090,880 bytes**, of which **212,029,440** are lists, not cached package archives. Remaining classification includes Codex state, package database and other small areas; `.tmp` or cache naming does not prove inactivity. No application bodies, databases or credentials were read, and no cleanup owner was identified. The classification is not permission to reclaim those bytes.

**Evidence records and custody.** The paths below are original root-owned evidence locators. This assessment used the completed evidence supplied in its compiled brief; it did not reopen these host records or claim a fresh verification of them.

| Record | Exact retained identity |
|---|---|
| Block allocation proof | `/private/tmp/rs-pullback-host-block-allocation-1791378778116809000.json`; **4,540 bytes**; SHA-256 `2f61194a42479343392e76279825b0a42573782211a5fa72378c419179350e10`; process 44937. |
| Read-only prune-packed manifest | `/private/tmp/rs-pullback-host-prune-packed-readonly-1791376858020410000.json`; **623,990 bytes**; SHA-256 `71f84a1c017c274edf89808a95c1a2696e90bfc90b6f8ebb09cae5822820a4cd`; process 88388. |
| Pack-set comparisons | Processes 11258, 18773, 20998 and 32928, all exit 0; exact witness digests and the strongest read interval above. No host-written witness or body-verification claim. |
| `/var/lib` classification | Processes 23421 and 25491, both exit 0; allocation/classification evidence only. |

**Delivery state at the supplied evidence cutoff.** Repository delivery is not blocked by the host disk. Macro **#8636** merged at **13:35:32 UTC**, squash `3781c8c7c4f80007d8d74231e83ec4fbca82e29c`; all 13 accepted files were exact in post-merge process **93194**, and the remote branch was deleted. This is source delivery, not a host installation claim.

Split **#8625**, release `f2`, and Terminal **#843**, release `e963`, are already merged. Their prepared installed proofs are independently accepted but **UNEXECUTED**. Macro **#8623** v3 remains held until the paired v2 proof. Terminal **#844** at `a826` has a separate required-run failure: run **37622577138** failed the mobile 1-second-versus-3-day case in all three attempts; the desktop repair and tablet cases were green. Its artifact download succeeded through the ordinary existing GitHub owner, and diagnosis was ongoing. No mobile repair, completed browser proof or capture defect is inferred here. Storage remediation would not itself resolve that independent gate.

**Next dependency and verification sequence.** The evidence supports escalation of the concrete capacity requirement through the existing infrastructure owner. There is no confirmed resize plan or exposed provider mutation capability, and no safe sufficient local cleanup was established. A new scheduler, duplicate host or alternative deployment platform would create another path without solving this owner dependency.

After a separately authorized capacity action, the existing owners should:

1. Reconcile the actual action and target, then measure fresh virtual-device, partition and filesystem sizes and allocatable bytes. A provider-side disk change alone does not prove guest partition/filesystem growth or usable build space. Preserve the original zero-space record alongside the new observation.
2. Establish a sufficient budget for the exact then-current normal Macro fetch and Terminal build, including temporary fetch allocation, staging, retained rollback output, prebuild work and compiler peak. The 222,420,992-byte baseline is evidence to build on, not the capacity requirement by itself. No size or price is selected in this assessment.
3. Observe the existing Macro updater with its normal lock and intended source. Reconcile any remaining failed fetch state against fresh process/lock/preimage evidence; do not treat a capacity increase as proof that the old orphan or lock can be removed blindly. Verify the resulting checkout, running process source and relevant exact installed blobs; a health 200 alone remains insufficient.
4. Run the existing normal Terminal deployment path for the accepted target, retaining its staging, validation and rollback behavior. Verify the actual installed source/build; source merge and hardlink setup are not build success.
5. Only after the required exact sources are installed, execute the already independently accepted paired v2 and Split installed proofs through their reviewed owners/carriers, preserving actual read clocks, stdout, failures and source bindings. Keep these synthetic conformance results scoped; they do not establish historical provider availability, market outcomes or admission.
6. Resolve the independent Terminal mobile gate through its existing case owner and preserve the three failed attempts. Reconcile the held v3 delivery dependency separately from storage and from the v2 installed proof.

No step in that future sequence was performed by this assessment. It records a real capacity blocker, useful negative recovery evidence and the next dependency without converting a potential cleanup, accepted script, source merge or liveness response into a deployment result.

This draft belongs in the existing Macro `research/live_entry_radar/rs_pullback_launch` research/handoff path under root's persistence custody. Applicable protected procedure pin is `a2c93f1d5280f285751107543645154e9b20eb8f`; supplied canonical handoff source is `3781c8c7c4f80007d8d74231e83ec4fbca82e29c`. No new infrastructure owner, state store or cadence is introduced. Only this cloud draft was written; read custody is released when its size and digest are returned.
