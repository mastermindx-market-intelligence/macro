---
key: INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583
claim: >
  Every Executive OS release manifest CREATE fails on a release tree that contains the tracked symlink
  `vendor/macro`: Mastermind `ops/executive_os/release_manifest.py` asks the shared macOS ACL observer
  about every walked object path-only, and `control_plane/fs_security.py::has_macos_acl` opens with
  `O_NOFOLLOW` and refuses any object that is neither a regular file nor a directory, so the symlink is
  re-raised as `ReleaseManifestError: cannot inspect release ACL: macro`. Observed at protected
  `e878878c9a4ae2dd50a48d825e031e07e8211708` on 2026-09-17, BEFORE the repair merged as `8b231e82`; the
  claim is about the code as it stood at that pin.
falsifier: >
  A protected-master manifest CREATE succeeding on a tree containing `vendor/macro`. Concretely: export
  protected Mastermind with `git archive`, run the release-manifest CREATE against that export at the
  then-current pin, and read the exit code and the produced `.executive-release-manifest.json`. rc=0 with
  a `vendor/macro` entry of `type: symlink` flips this claim; the recorded RED (rc=1 at protected
  e878878c9a4ae2dd50a48d825e031e07e8211708) is the reproduction of it.
so_what: >
  CURRENT (2026-09-17 21:20Z UTC): the repair landed — Mastermind #757 merged to protected `8b231e82`
  (2026-09-17 19:54:58Z) — and the canonical install ceremony for installed generation
  `8b231e8267f09cfb002ed3e87bec14906dce1720` then COMPLETED SUCCESSFULLY (installer rc=0, verify ok), a
  state Sol ACCEPTED as UNARMED / STOPPED with the services kept stopped (option B). HISTORICAL: from the
  recorded RED until that merge, no release containing `vendor/macro` could pass the install manifest
  gate, so the installed control/relay stayed on prior generation `4c148709` (AWAITING_CANARY,
  armed=false), which this fabric never health-verified and must never call healthy or current. Any
  session asked to install, restart, arm or re-run the Executive OS install ceremony reads this record,
  re-reads the current protected pin and the accepted installed state first, and reports a source-gate
  refusal as a fact instead of retrying the ceremony. Restarting an installed release is never a repair.
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
  clean `git archive` export, rc=1. The later post-repair install of generation `8b231e82` and its
  ACCEPTED UNARMED / STOPPED state are carried from Sol ruling edge `1789680829.787409` — see the
  currentness section in the body; this records-only fold ran no host command.
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
partial install can result. HISTORICAL, as of the fold commit: the Executive OS install path was blocked
at its source gate while the installed control/relay kept running prior generation `4c148709`
(AWAITING_CANARY, `armed=false`). Do not carry a health verdict with that state: this fabric never
health-verified `4c148709`, and calling it "the one healthy thing in the lane" was an ungrounded claim
that this currentness repair removes. Restarting any installed release is forbidden either way — a
restart is not a repair.

## Currentness — 2026-09-17 21:20Z UTC (Sol ruling edge 1789680829.787409)

- The repair this record waited on landed: Mastermind **#757 merged to protected `8b231e82`**
  (mergeCommit `8b231e82`, parent `aacf3df5`, 2026-09-17 19:54:58Z) after Sol ACCEPTED/STOP.
- The canonical install ceremony then COMPLETED SUCCESSFULLY on 2026-09-17 21:20–21:21Z for installed
  generation `8b231e8267f09cfb002ed3e87bec14906dce1720`: installer rc=0, release manifest sha256
  `ec7231b0b826d2e6c829036b92ea59f6f6eee061fb95905007b5fdea20ff90e1`, tree
  `a6f21af86dbc018621c04126ae7e6579899aafaf`, 2303 entries, verify ok; installed `control.json` sha256
  `1676d78dce2715d54d64cbc73dd3b9c6c7d426da3270edf95d85795423a6b4f3`.
- Sol ACCEPTED that state as **UNARMED / STOPPED** and ruled (option B) that the services stay stopped.
  A relight is therefore NOT "pending", and `4c148709` is the PRIOR generation — its release directory
  remains on disk, intact — not a healthy or current release.
- Plist generations are not one vector: `control` / `worker.codex` / `backup` = `8b231e82`; the C1
  `sol-state-relay` plist is a separately owned generation (recorded at `4c148709`) because
  `install.sh` never writes it — see `DSC:EXECUTIVE-INSTALL-DOES-NOT-OWN-THE-C1-RELAY-PLIST`; MCP =
  `46bea208`.
- Next gate is HUMAN_AUTH / CREDENTIAL_READINESS (`provision-worker-auth.sh --verify-ready`, needing a
  reviewed credential kind, a company-workspace admin attestation class and the Chairman-owned
  `CREDENTIAL_EXPIRES_AT`). No credential, provider or ARM effect has occurred.
