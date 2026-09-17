---
key: SYMLINK-ACL-OBSERVATION-IS-MANIFEST-ONLY-OPT-IN
question: >
  How should the release manifest observe the macOS ACL of a tracked symlink such as `vendor/macro`
  without weakening the shared filesystem security observer, whose default path-only behaviour opens with
  `O_NOFOLLOW` and refuses any non-file/non-directory object?
answer: >
  Keep the default path-only `has_macos_acl` exactly as it is — `O_NOFOLLOW`, refuses symlinks — and add ONE
  keyword-only opt-in, `allow_symlink=False`, whose use is a contract rather than a flag. It requires a
  caller-supplied `os.stat_result` whose `st_mode` is `S_ISLNK` (typed `FilesystemSecurityError` for None,
  non-`os.stat_result` or a non-link, raised BEFORE the Darwin gate and before any open); it rejects a
  caller-supplied `descriptor`; it requires the native `os.O_SYMLINK` to be a nonzero `int` (`bool`, `0`,
  missing and non-int all refuse, with no fallback); it opens exactly
  `O_RDONLY | O_SYMLINK | O_CLOEXEC | O_NONBLOCK` (no `O_NOFOLLOW`); it requires the `fstat`
  `(st_dev, st_ino)` to match the caller's identity AND the observed object to be `S_ISLNK`; it reads the
  ACL through the existing descriptor-bound helper; and it closes the descriptor on every path. Exactly one
  call site opts in — `release_manifest._has_acl(path, info)`, passing the already-validated `lstat` it took
  for the same object.
rationale: >
  The default refusal is a security property of the shared observer, not an inconvenience: every other
  caller benefits from "this can never silently observe what a link points at", and weakening the default to
  serve one release-manifest need would trade a fleet-wide property for a local convenience. A second public
  helper would instead mint a second contract to keep in step. The opt-in is therefore expressed so the
  symlink case is STRICTLY narrower than the default: the caller must already hold the `lstat` of the object
  it means to observe, the observer re-proves identity through `fstat` and link-ness of the OBSERVED object,
  and the `O_SYMLINK` open is owned by the observer rather than asserted by a handed-over descriptor.
  Validity is checked before the Darwin gate, so a malformed opt-in can never receive a silent ACL-free
  answer on a platform where the observation is inert. With no `O_SYMLINK` there is no fallback: the
  observation refuses instead of degrading into a fresh `lstat`, which is the exact substitution the
  contract exists to prevent. One call site keeps the blast radius one function wide and makes the exception
  auditable by grep.
alternatives:
  - option: Accept symlinks in the default path-only behaviour
    why_not: >
      It weakens a shared filesystem-security observer for every caller — including callers that never
      handle release manifests — to serve one manifest need. The default refusal is what makes the observer
      trustworthy, and a security default that yields to its first inconvenience is not a default.
  - option: Add a new public helper `has_macos_link_acl`
    why_not: >
      Closed duplicate: PR #748 proposed exactly that and was closed with its bytes never copied. A second
      public entry point means two contracts to keep in step, a new name for future callers to reach for by
      reflex, and a symlink-observer surface with no single obvious owner.
  - option: Fall back when `os.O_SYMLINK` is absent, zero or non-int
    why_not: >
      There is nothing to fall back TO. Without the native flag the observer cannot open the link itself, so
      any fallback observes something else — a fresh `lstat` or the link's target — which is precisely the
      substitution the identity contract exists to refuse. A zero-O_SYMLINK fallback would be a silent
      semantic downgrade.
  - option: Fall back to a fresh `lstat` inside the observer
    why_not: >
      Same defect one layer in: after the caller validated its own `lstat`, a fresh one can resolve a
      different object (retarget race), so the ACL observed would not be the ACL of the object the caller
      validated. Refusing is the only honest outcome.
  - option: Rebase onto current master to shed the ancestry question
    why_not: >
      Ancestry churn buys nothing: it rewrites review provenance for a source-only change and makes the
      reviewed head a different object than the reviewed bytes. The contract's correctness does not depend
      on its base, and a merge is a maintenance act, not a correctness act.
evidence:
  - "Mastermind #757, OPEN/DRAFT/HOLD-FOR-SOL at head f079f1ee14003dbcc12cfe7154c90c713eac3373 (read 2026-09-17 with `gh pr view 757 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid,mergeCommit,title`), chain e89382ee -> 90f6d146 -> f079f1ee, base b1498283."
  - "At f079f1ee, `gh api -H 'Accept: application/vnd.github.raw' repos/.../contents/control_plane/fs_security.py?ref=f079f1ee...`: `allow_symlink: bool = False` at :68; the typed opt-in refusals at :105-119 (a supplied descriptor rejected; None / non-`stat_result` / non-`S_ISLNK` identity rejected) raised BEFORE the `sys.platform != 'darwin'` gate at :122; the `O_SYMLINK` `type(...) is not int` and `<= 0` refusals at :137-145; the symlink flags `O_RDONLY | o_symlink | O_CLOEXEC | O_NONBLOCK` at :147-152 versus the default `O_NOFOLLOW` flags at :154-159; then the `fstat` identity check and the `S_ISLNK` observed-object check after the open."
  - "At f079f1ee, `release_manifest.py` defines `_has_acl(path, info)` at :30, passes `allow_symlink=stat.S_ISLNK(info.st_mode)` at :35, and is called with an already-taken `lstat` at :56, :82 and :162 — the file's only opt-in call sites."
  - "Root live proof at f079f1ee (child session, not re-run by this fold): GREEN create/verify with manifest sha256 049025007eeef3c0…, 2266 entries, `vendor/macro` recorded `{type: symlink, target: macro_src}`, plus a RED with the protected manifest."
  - "Hosted required `test` run 35215011646 SUCCESS (child-session run id)."
  - "Non-author exact-head review chain REQUEST_CHANGES(MEDIUM) -> REQUEST_CHANGES(LOW) -> APPROVE, record sha256 6bbb8c6115afa812… (child-session receipt)."
  - "Sol ACCEPTED/STOP edge 1789648278.066969: state SOL_ACCEPTED_BUILDER_RESULT / TERMINAL_BUILDER_STOP / BRANCH_WRITER_RELEASED from the seat / DRAFT-HOLD / BUILT_NOT_PROVEN. Ready and merge are Sol maintenance-only acts and the install ceremony is NOT authorized."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - control_plane/fs_security.py
  - ops/executive_os/release_manifest.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-17
---

## The contract in one table

| Condition | Default path-only call | `allow_symlink=True` call |
|---|---|---|
| Caller-supplied identity | optional (`expected_identity`) | REQUIRED, must be an `os.stat_result` with `S_ISLNK` |
| Caller-supplied `descriptor` | allowed | REFUSED (the observation must own its open) |
| Open flags | `O_RDONLY \| O_NOFOLLOW \| O_CLOEXEC \| O_NONBLOCK` | `O_RDONLY \| O_SYMLINK \| O_CLOEXEC \| O_NONBLOCK` |
| `os.O_SYMLINK` absent / zero / non-int | not consulted | REFUSED, no fallback |
| Identity re-proof | `fstat` `(st_dev, st_ino)` equals the pre-open identity | same, plus the observed object must be `S_ISLNK` |
| ACL read | existing descriptor-bound helper | same helper, same descriptor |
| Refusal type | `FilesystemSecurityError` | `FilesystemSecurityError` |

The strictness is the point: the opt-in cannot observe "whatever the link points at", cannot be driven by a
descriptor someone else opened with keys the observer did not choose, and cannot silently degrade on a
platform without `O_SYMLINK`. The validation also runs before the Darwin gate, so a non-Darwin caller with a
malformed opt-in is refused rather than handed a false "no ACL" answer.

## Reversibility

Source-only, nothing installed: revert is one commit and restores the pre-repair `fs_security.py` and
`release_manifest.py` bytes. No released artifact, installed host or ceremony depends on the change.

## What is NOT claimed

- #757 is DRAFT/HOLD-FOR-SOL. Its head is a reviewed source candidate, not a merged or released artifact;
  the install ceremony is not authorized by this decision.
- The decision says nothing about the health of the currently installed release beyond "do not restart it";
  see `DSC:INSTALLER-MANIFEST-REFUSES-TRACKED-SYMLINKS-SINCE-583`.
