---
key: RESTORING-A-SNAPSHOT-INDEX-BLINDS-GIT-DIFF-TO-SAME-SIZE-EDITS
claim: >
  Copying a saved index file over `.git/index` - what
  `scripts/ci/options_signal_nightly.sh`'s `oip_restore_locked_index` does to restore a locked
  tree snapshot - gives `.git/index` an mtime NEWER than the working-tree files it describes,
  which defeats git's "racily clean" safeguard and makes a SAME-SIZE content change invisible
  to `git diff` (worktree-vs-index). Git only re-hashes a cached entry when the file's mtime is
  not older than the index's; with the index newer, it trusts the cached stat, and size is the
  only field a same-size edit changes. Measured on this repo: a same-size payload rewrite was
  missed 1 time in 40 (`rc=0`, `git diff` empty, while the file on disk held v2), and a
  different-size rewrite was missed 0 times in 40. This is the mechanism behind the
  intermittent `test_locked_broad_snapshot_blocks_late_index_writer` failure (2/40 solo, 5%) -
  the lock is working; the comparison used to prove it is what goes blind.
falsifier: >
  In a scratch repo: commit a file, `cp .git/index /tmp/snap`, rewrite the file with content of
  IDENTICAL byte length, `cp /tmp/snap .git/index`, then `git diff --quiet -- <file>`. The claim
  is disproved if `git diff` reliably reports the change (non-zero exit) across ~40 trials, or
  if it also misses a DIFFERENT-size rewrite at a comparable rate (which would mean the cause is
  not the stat cache's size field). `git update-index --refresh` before the diff, or comparing
  with `git diff --cached`/`git hash-object`, must make the miss disappear - if it does not, the
  mechanism is something else.
so_what: >
  Never prove "a writer was blocked" or "a tree is clean" with a worktree-vs-index comparison
  taken after a snapshot index has been restored - the proof can pass on a tree that was
  actually modified. Use a content-based check instead: `git diff --cached`, `git hash-object`
  on the file, or an explicit `git update-index --refresh` first. `--cached` comparisons are
  content-based and unaffected, so the blast radius is worktree-vs-index reads only; the
  publisher's own `git add`/replay path does not rely on the blind comparison. A test that
  asserts a late writer was refused must not use `git diff` as its only witness.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  40-trial same-size vs different-size falsifier loop (1/40 vs 0/40 violations) plus
  scripts/ci/options_signal_nightly.sh oip_restore_locked_index; symptom is
  tests/test_options_signal_episode.py::test_locked_broad_snapshot_blocks_late_index_writer
  failing 2/40 in isolation.
scope:
  - macro
  - scripts/ci/options_signal_nightly.sh
  - tests/test_options_signal_episode.py
confidence: verified
---

## What breaks

`oip_restore_locked_index` restores a locked-roots snapshot by copying a saved index file back
over `.git/index`. That is a file copy, so the restored `.git/index` carries a *fresh* mtime,
newer than the working-tree files it describes.

Git's stat cache treats an entry as "racily clean" only when the file's mtime is **not older**
than the index's mtime; in that case it re-hashes the content to be safe. When the index is
newer than the file, git skips the re-hash and trusts the cached stat data. The cached stat
includes size but not content, so:

- a **different-size** edit still shows up (size mismatch forces the comparison),
- a **same-size** edit does not (nothing in the cached stat disagrees).

## Why it looks like a lock failure

`test_locked_broad_snapshot_blocks_late_index_writer` asserts that a late writer cannot modify a
locked tree, and witnesses that with a worktree-vs-index `git diff`. When the stat cache goes
blind, the diff comes back empty — which the test reads as "the writer was blocked" or, depending
on the assertion's direction, fails to detect a write that did happen. Either way the *lock* is
not what failed. Measured 2/40 in isolation (5%).

## What not to conclude

This does not mean the publisher can silently commit a stale tree. The `git add` / replay path
compares content, and `--cached` diffs are content-based and unaffected. The exposure is confined
to worktree-vs-index reads used as evidence.
