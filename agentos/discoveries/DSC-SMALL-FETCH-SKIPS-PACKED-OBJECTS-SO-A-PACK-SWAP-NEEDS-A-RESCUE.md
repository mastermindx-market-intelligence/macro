---
key: SMALL-FETCH-SKIPS-PACKED-OBJECTS-SO-A-PACK-SWAP-NEEDS-A-RESCUE
claim: >
  A fetch whose pack is below transfer.unpackLimit is unpacked loose by unpack-objects, and
  unpack-objects writes no loose copy of an object that already exists in any local pack; it
  only freshens that pack's mtime. So after a consolidation snapshot, a later pull can make a
  reachable commit depend on an object that lives only in an old (snapshot) pack. If that
  object was unreachable when the snapshot was taken, the consolidated pack does not hold it,
  and retiring the old packs breaks the repository (fsck fails, the blob is unreadable).
  A pack swap on a live pull clone therefore needs a rescue step: before the old packs go,
  pack every object that the post-snapshot refs, reflogs and index need and that neither the
  consolidated pack, the post-snapshot packs nor the loose store holds.
kind: landmine
verified_at: 2026-10-19
verified_by: >
  Local fixture (git 2.46, macOS, Linux shims for flock/df/ionice): a shallow clone holds blob
  X only in a pack that also holds a deleted side branch; reflog expiry makes X unreachable;
  the consolidated pack, built with pack-objects --all --reflog --indexed-objects, omits X.
  A later upstream commit reuses X's content and is fetched with transfer.unpackLimit=1000.
  No loose X appears (checked by path), and the old pack's mtime moves. The swap with its
  rescue step then passes fsck and X reads back; with the rescue removed, fsck fails once the
  old packs are moved aside. Macro PR #9666's
  tests/test_deploy_git_store_maintenance.py runs the README rescue command, extracted from
  the README text, on the same construction, with the no-rescue falsifier run first.
  Production swap on 146.190.142.17 (2026-10-19, under the updater lock) ran the rescue:
  4,265 post-snapshot objects, 0 needing rescue.
scope:
  - macro
  - app/deploy/README.md
  - "VPS /opt/macro (146.190.142.17) and any live clone whose packs are swapped while pulls continue"
  - WS:MARKET-OS
confidence: verified
type: discovery
status: active
workstream: MARKET-OS
summary: >
  The 2026-10-19 recovery of /opt/macro built its consolidated pack off-root over about two
  hours while the 3-minute pull kept running, then swapped it in under the updater lock. The
  obvious swap (bridge the new pack in, delete the old packs, fsck) has a hole. Pulls that
  land after the snapshot are mostly small, so they are unpacked loose, and unpack-objects
  skips any object that already exists in a pack, as it should for a normal repository. If
  the object it skipped was unreachable at the snapshot (an old render's blob that a new
  render brings back, for example), only an old pack has it. Deleting the old packs then
  loses an object a live commit needs. The pull itself would not notice until a checkout or
  the next fsck.
  The rescue closes the hole without trusting timing. It marks post-snapshot packs .keep,
  bridges the consolidated pack in through objects/info/alternates, and runs
  pack-objects --revs --local --honor-pack-keep --non-empty with the post-snapshot tips and
  ^snapshot-tips, so only objects that nothing else holds land in a small local pack. The
  production run needed none, but the step is cheap (seconds) and the failure it prevents is
  silent.
evidence:
  - "Fixture assertion before the swap: X is absent from the consolidated pack's index (git -C <repo> show-index), and .git/objects/<xx>/<rest> for X does not exist after the transfer.unpackLimit=1000 fetch, so the fetch skipped it"
  - "Fixture with the rescue (test-swap-rescue.sh against vps-swap.sh): swap rc=0, 'X readable', final fsck ok, alternates absent afterwards. With the rescue block removed, fsck --connectivity-only fails after the snapshot packs are retired and the swap rolls back"
  - "Macro PR #9666 README rescue test: the command is extracted from app/deploy/README.md and run as written; without it fsck fails (falsifier runs first), with it fsck passes, the blob reads back, and the rescue pack overlaps neither the consolidated pack nor the post-snapshot pack"
  - "Production swap log ($M=/mnt/terminal_storage/macro-git-maint-20261019/swap/log, 2026-10-19 08:51:49Z-08:53:44Z): post-snapshot objects 4,265; rescue 0; retired 263 packs; fsck1 ok; fsck2 ok with the alternates bridge removed"
  - "Freshening fixture (git 2.46.1, 2026-10-19): with the old pack's .pack/.idx/.rev all set to 2026-01-01, a transfer.unpackLimit=1000 fetch of a commit reusing X moved only the .pack mtime (to the fetch time); .idx and .rev kept 2026-01-01 and no loose object for X was written. A .pack newer than its .idx therefore means freshened, not newly fetched"
falsifier: >
  Build the fixture: a repository where blob X exists only in pack P and is unreachable,
  then fetch a commit that contains X with '-c transfer.unpackLimit=1000'. If a loose object
  for X appears under .git/objects/<xx>/, unpack-objects does write duplicates and the claim is
  wrong for that Git version. Then move P aside and run 'git fsck --connectivity-only'. If it
  passes without X being anywhere else, the rescue is unnecessary.
so_what: >
  Never retire snapshot packs on a clone that kept pulling after the snapshot without a rescue
  step, and never rely on "the new pack plus the post-snapshot packs" being complete. Use the
  app/deploy/README.md recipe: .keep on post-snapshot packs, alternates bridge, the
  --honor-pack-keep rescue pack, then fsck with the old packs moved aside (not deleted) before
  anything is removed. The same hole exists for any tool that swaps packs under a live
  writer, including a hand-run 'repack -a -d' variant that builds outside the repository.
  The nightly macro-git-store-maintenance job does not have this problem: it runs
  'git repack' inside the repository, which sees every pack and loose object at write time.
related:
  - "DSC:PACK-OBJECTS-OFF-FILESYSTEM-NEEDS-GIT-OBJECT-DIRECTORY"
  - "DSC:VPS-PULL-CLONE-GROWS-ONE-92MB-PACK-PER-SITE-RENDER"
  - "DSC:VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED"
  - "DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK"
  - "WS:MARKET-OS"
---

Swapping a consolidated pack into a repository that kept fetching while the pack was built
looks safe: everything reachable at the snapshot is in the new pack, and everything fetched
since is in the new fetches. That second half is not true. Git does not store an object twice.
When a small fetch is unpacked loose and one of its objects already sits in an old pack, Git
just touches that pack and moves on. If the object was unreachable when the snapshot was
taken, the new pack left it out, so only the old pack has it.

On the Macro droplet that can happen whenever a render brings back content an expired render
once had. The 2026-10-19 swap included a rescue step for it. The step found 4,265 objects
added since the snapshot and none that needed rescuing. The fixture shows that without the
step, the same sequence loses a blob that a live commit points to.
