---
key: BLOBLESS-CLONE-OBJECT-LOOKUP-ON-AN-UNKNOWN-SHA-LAZY-FETCHES
claim: >
  On a promisor (blobless) clone - `remote.origin.partialclonefilter=blob:none`, which
  every macro checkout under Macro Dashboard/.git is - `git cat-file -t|-e`, `git
  show`, and `git rev-parse --verify` on a 40-hex id that is not a local object do not
  fail fast: git assumes a missing promisor object and attempts a lazy fetch from
  origin, paying a network round-trip (`fatal: remote error: upload-pack: not our ref
  <sha>`) and hanging for the fetch timeout (>= 15 s locally; 40 s+ on the ubuntu1 lane
  clone). `GIT_NO_LAZY_FETCH=1` restores the instant "could not get object info".
falsifier: >
  `perl -e 'alarm 15; exec @ARGV' git cat-file -t
  0000000000000000000000000000000000000001` in a blobless checkout returning "Not a
  valid object name" in under a second, or `git config --get
  remote.origin.partialclonefilter` printing nothing.
so_what: >
  Never feed an unverified 40-hex (a sha from a packet, a PR field, a sibling's
  message, or a guess) to a git object command on a fleet clone - look it up by ref
  (`git ls-remote origin <branch>`, `git log -1 --format=%H <ref>`) or prefix the
  command with `GIT_NO_LAZY_FETCH=1`. A lane that probes shas in a loop without it
  reads as hung; the S5 study-runner packets carry this as a standing constraint.
kind: landmine
verified_at: 2026-10-04
verified_by: >
  Local worktree intraday-dislocation-reclaim-f27801 (git 2.46.1, partialclonefilter
  blob:none): `perl -e 'alarm 15; exec @ARGV' git cat-file -t 0000...0001` -> remote
  error "upload-pack: not our ref", killed by the alarm at 15 s (rc=142); same with
  `cat-file -e`. `GIT_NO_LAZY_FETCH=1 git cat-file -t 0000...0001` -> "fatal: git
  cat-file: could not get object info" in 0 s (rc=128).
scope: [macro]
confidence: verified
---

## Detail

The hang is the promisor machinery working as designed: an object id that is not in
any local pack is indistinguishable from a blob the clone deliberately omitted, so
git asks origin for it before concluding it does not exist. The cost is only visible
on an id that cannot exist (typo, fabricated, or a squash-rewritten tip), which is
exactly the id a session is most likely to probe while verifying a merge.
