---
key: PACK-OBJECTS-OFF-FILESYSTEM-NEEDS-GIT-OBJECT-DIRECTORY
claim: >
  'git pack-objects <base>' with <base> on another filesystem does NOT write its output there:
  it builds tmp_pack/tmp_idx/tmp_rev inside the repository's OWN objects/pack, then dies
  renaming them across filesystems ("unable to rename temporary file ... Cross-device link" /
  "Invalid cross-device link", EXDEV, rc=128) and leaves the full-size temporary pack behind
  on the source disk. Off-disk consolidation only works when GIT_OBJECT_DIRECTORY points at an
  object directory on the target filesystem and the real store is read through
  GIT_ALTERNATE_OBJECT_DIRECTORIES.
kind: landmine
verified_at: 2026-10-19
verified_by: >
  strace -f -e trace=openat,rename on 146.190.142.17 (git 2.43.0), fixture repo on root
  (/dev/vda1) with base /mnt/terminal_storage/macro-git-maint-20261019/xdevtest/pk (/dev/sda):
  tmp_pack/tmp_idx/tmp_rev opened under the repo's .git/objects/pack, then rename(...) = -1 EXDEV.
  Reproduced on macOS git 2.46.1 between /dev/disk3s5 and /dev/disk12s1: plain run rc=128 with
  tmp_idx_*/tmp_pack_*/tmp_rev_* left in the source repo; the same command with
  GIT_OBJECT_DIRECTORY=<target>/objects GIT_ALTERNATE_OBJECT_DIRECTORIES=<repo>/.git/objects
  rc=0 with pack/idx/rev on the target. Macro PR #9666 test
  test_readme_recovery_pack_objects_writes_off_root pins the recipe.
scope:
  - macro
  - app/deploy/README.md
  - "VPS /opt/macro (146.190.142.17) and any host consolidating a Git store onto a second volume"
  - WS:MARKET-OS
confidence: verified
type: discovery
status: active
workstream: MARKET-OS
summary: >
  On 2026-10-19 the /opt/macro store (41 GiB on a full 77 GiB root) had to be consolidated
  with scratch on the 50 GiB /dev/sda volume. The obvious command -
  'git -C /opt/macro pack-objects --all --reflog /mnt/terminal_storage/x/pack' - looks like it
  writes to sda and does not. pack-objects writes temporaries with odb_mkstemp() in the
  repository's object directory and only renames them to <base> at the end, so the multi-GiB
  output lands on the full disk first and the final rename fails with EXDEV. The first
  production attempt (run2) was killed before its write phase once strace showed this; it would
  either have filled root (wedging the 3-minute pull, which needs root space to fetch) or died
  at the rename with a ~15 GiB tmp_pack stranded on root. Setting GIT_OBJECT_DIRECTORY to an
  object directory on sda moves the temporaries there, and GIT_ALTERNATE_OBJECT_DIRECTORIES
  keeps the real store readable; run3 used this and wrote only to sda.
evidence:
  - >
    VPS strace (git 2.43.0, fixture repo on /dev/vda1): openat(AT_FDCWD,
    ".git/objects/pack/tmp_pack_solCVE", O_RDWR|O_CREAT|O_EXCL, 0444), likewise tmp_idx_ityUtN
    and tmp_rev_g8FHNU, then rename(".git/objects/pack/tmp_pack_solCVE",
    "/mnt/terminal_storage/macro-git-maint-20261019/xdevtest/pk-fbe2c40f....pack") = -1 EXDEV
    (Invalid cross-device link); rc=128 "fatal: unable to rename temporary file".
  - >
    macOS repro 2026-10-19 (git 2.46.1, repo on /dev/disk3s5, base on /dev/disk12s1): "fatal:
    unable to rename temporary file to '.../objects/pack/pack-e4053065...pack': Cross-device
    link", rc=128, and tmp_idx_F6prpX tmp_pack_WTg5cM tmp_rev_NL1D1P left in the SOURCE
    repo's .git/objects/pack
  - >
    Same repro with GIT_OBJECT_DIRECTORY=<target>/objects and
    GIT_ALTERNATE_OBJECT_DIRECTORIES=<repo>/.git/objects: rc=0, prints
    e4053065902cd5e267f9e45c3a51826646c5f8a6, target holds pack/idx/rev and the source repo
    holds no tmp_* files. Also passed on the VPS with a fixture holding both packed and loose
    objects before run3 was launched
  - >
    Macro PR #9666 app/deploy/README.md recovery recipe carries the override, and
    tests/test_deploy_git_store_maintenance.py::test_readme_recovery_pack_objects_writes_off_root
    fails on the recipe text without it (negative control run)
falsifier: >
  On any host with two filesystems A and B: 'git init A/r && git -C A/r commit --allow-empty -m x
  && mkdir -p B/o/objects/pack && git -C A/r pack-objects --all B/o/objects/pack/pack </dev/null;
  echo rc=$?; ls A/r/.git/objects/pack'. If that prints a pack name with rc=0 and leaves no
  tmp_* files in A, the claim is wrong for that Git version. Then repeat with
  'GIT_OBJECT_DIRECTORY=B/o/objects GIT_ALTERNATE_OBJECT_DIRECTORIES=A/r/.git/objects' - if that
  fails, the remedy is wrong.
so_what: >
  Never point pack-objects' base name at another volume to "save space on the full disk": the
  bytes still land on the full disk.
  For an off-volume consolidation set GIT_OBJECT_DIRECTORY=<target>/objects and
  GIT_ALTERNATE_OBJECT_DIRECTORIES=<repo>/.git/objects, verify with a tiny repo first, and check
  that no tmp_pack_* appears in the source objects/pack once the write phase starts. If an
  attempt already died, delete the stranded tmp_pack_*/tmp_idx_*/tmp_rev_* in the source
  objects/pack - they are not referenced by any index. The Macro recipe is
  app/deploy/README.md "Recovery when it REFUSES for space"; the nightly
  macro-git-store-maintenance job deliberately repacks in place only when root has
  store-size + 3 GiB free and refuses otherwise.
related:
  - "DSC:VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED"
  - "DSC:VPS-PULL-CLONE-REFLOG-PINS-PACK-DUPLICATION"
  - "WS:MARKET-OS"
  - "WS:FLEET-STORAGE-LIFECYCLE"
---

`git pack-objects` takes a base name for its output, and it is natural to read that as "write
the pack here". It is not. The pack is built as a temporary file in the repository's own
object directory and renamed onto the base name at the end. On one filesystem that is an
atomic rename; across filesystems it fails with EXDEV, after the full pack has already been
written to the disk you were trying to spare, and the temporary pack is left behind.

This was found on 2026-10-19 while consolidating the 41 GiB `/opt/macro/.git` store from a
full root disk onto `/mnt/terminal_storage`. strace showed the first attempt writing its
temporaries under `/opt/macro/.git/objects/pack`, so it was stopped before its write phase.
The relaunch set `GIT_OBJECT_DIRECTORY` to an object directory on the target volume and read
the real store through `GIT_ALTERNATE_OBJECT_DIRECTORIES`, which moves the temporaries to the
target and makes the final rename local. The same behaviour reproduces on macOS with Git 2.46,
so it is Git's design, not a quirk of this host.
