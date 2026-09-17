---
key: INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583
claim: >
  Every Executive OS release manifest CREATE fails on a release tree that contains the tracked symlink
  `vendor/macro`: Mastermind `ops/executive_os/release_manifest.py` asks the shared macOS ACL observer
  about every walked object path-only, and `control_plane/fs_security.py::has_macos_acl` opens with
  `O_NOFOLLOW` and refuses any object that is neither a regular file nor a directory, so the symlink is
  re-raised as `ReleaseManifestError: cannot inspect release ACL: macro`.
falsifier: >
  A protected-master manifest CREATE succeeding on a tree containing `vendor/macro`. Concretely: export
  protected Mastermind with `git archive`, run the release-manifest CREATE against that export at the
  then-current pin, and read the exit code and the produced `.executive-release-manifest.json`. rc=0 with
  a `vendor/macro` entry of `type: symlink` flips this claim; the recorded RED (rc=1 at protected
  e878878c9a4ae2dd50a48d825e031e07e8211708) is the reproduction of it.
so_what: >
  No Executive OS release containing `vendor/macro` can pass the install manifest gate until the repair in
  Mastermind #757 lands. The installed control/relay therefore stay on release 4c148709 (AWAITING_CANARY,
  armed=false) and must NOT be restarted, and any session asked to install, restart, arm or re-run the
  Executive OS install ceremony reads this record, re-reads the current protected pin, and reports the
  refusal as a source-gate fact instead of retrying the ceremony.
kind: landmine
verified_at: 2026-09-17
verified_by: >
  `gh api repos/mastermindx-market-intelligence/Mastermind/contents/vendor/macro?ref=e878878c9a4ae2dd50a48d825e031e07e8211708`
  returns `{type: symlink, target: macro_src, size: 9, sha: 67c7d1aa15e255af2e662d8b4b385faf9714f06a}`, and
  the same read at #583's merge ref `7868e2c2727a8871f64f387de9ce00dc6a67cff9` returns
  `{type: symlink, target: macro_src}`. `gh api -H 'Accept: application/vnd.github.raw'
  repos/.../contents/ops/executive_os/release_manifest.py?ref=e878878c...` shows `_entries` at :65, the
  unconditional `if _has_acl(path):` inside the walk at :80, and `_has_acl` at :29-33 calling
  `has_macos_acl(path)`. `gh api -H 'Accept: application/vnd.github.raw'
  repos/.../contents/control_plane/fs_security.py?ref=e878878c...` shows `has_macos_acl` at :63,
  `O_NOFOLLOW` in its open flags at :90, and its typed refusal `macOS ACL object is not a file or
  directory`. Child-session receipts, NOT re-run by this fold: a live `install.sh` failure at
  2026-09-17T07:21Z, and a root RED proof on protected e878878c `release_manifest`+`fs_security` over a
  clean `git archive` export, rc=1.
scope:
  - mastermind
  - ops/executive_os/release_manifest.py
  - control_plane/fs_security.py
confidence: verified
---

## The failing call chain

`_entries` walks the release root with `os.walk(root, topdown=True, followlinks=False)` and, for every name
it sees, takes an `lstat`, validates ownership, and then calls `_has_acl(path)` BEFORE it classifies the
object. `_has_acl` is path-only and converts any `FilesystemSecurityError` into the manifest error whose
message is `f"cannot inspect release ACL: {path.name}"` — the `path.name` of `vendor/macro` is the literal
`macro` in the recorded receipt.

`has_macos_acl` opens the path with `O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK` and then requires the
opened object to be `S_ISREG` or `S_ISDIR`. A symlink satisfies neither, so the observation refuses instead
of silently reading an ACL. That refusal is correct behaviour for a shared security observer; it is simply
not survivable inside a release walk that is guaranteed to meet a tracked symlink.

## Why `vendor/macro` is always there

`vendor/macro` is a tracked symlink to `macro_src`. Its single introducing commit is `33eab84d`
(2026-06-23, "feat(macro-data): keep the vendored analyzer data fresh + staleness tripwire"), and it is
present at #583's merge `7868e2c2727a8871f64f387de9ce00dc6a67cff9`. The ACL walk in `_entries` is older
than #583 — it is already present at `0bdaf539` (#25, 2026-08-12, "Executive OS Phase 1C-A: secure launchd
supervisor") — so the defect is a property of any release tree carrying the symlink, and the recorded
receipt window is "every release cut since #583".

## Blast radius

The refusal happens at manifest CREATE, before any install step, so the failure is fail-closed and no
partial install can result. The operative consequence is that the Executive OS install path is blocked at
its source gate while the installed control/relay keep running the older healthy release `4c148709`
(AWAITING_CANARY, `armed=false`). Restarting that release is forbidden: it is the one healthy thing in the
lane, and a restart is not a repair.
