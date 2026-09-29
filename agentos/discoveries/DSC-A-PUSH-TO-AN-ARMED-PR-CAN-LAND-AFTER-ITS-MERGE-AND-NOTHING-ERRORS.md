---
key: A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS
claim: >
  A commit pushed to a branch whose PR carries `merge-on-green` can land on the **far side of the
  merge**, and every instrument in the ship chain still reports success. Measured on PR #8163,
  2026-09-29: the sweeper merged it at **02:09:24Z** against head `2ff0f92f4496`; the follow-up
  commit `148c3fd95a53` (a workstream record plus its handoff) carries committer time **02:09:24Z**
  — the same second — so its push necessarily completed at or after the merge. The push returned
  **rc=0**. GitHub accepted it, did **not** reopen or amend the PR, and raised nothing: the branch
  ref `origin/claude/internal-disk-agent-residue-20260928` now points at `148c3fd9`, two commits
  ahead of what was merged, on a PR that reads `state=MERGED`. The squash `704d6b8ae995` contains
  **3 files / 195 insertions** — the wave-4 content only. The two files in the late commit reached
  main in **no** form. **Two PR fields are false friends here, not one.** `headRefOid` reads `2ff0f92f`,
  which is also the correct value on a healthy merge. And `gh pr view --json files` reports the
  **three merged paths**, not the five the branch touched — measured on this very PR — so the
  otherwise-obvious check "do the PR's files appear in the squash?" compares the merged head with
  itself and passes tautologically. Every field GitHub reports about a merged PR describes the
  merge, so **no single-PR read can detect this at all.** The watcher, which
  judged `state`/`mergedAt`/check rollup, reported `MERGED at 2026-09-29T02:09:24Z` and was correct
  about the PR and wrong about the work.
falsifier: >
  `gh pr view 8163 --json state,mergedAt,mergeCommit,headRefOid` returns
  `MERGED / 2026-09-29T02:09:24Z / 704d6b8ae995 / 2ff0f92f4496`, while
  `git log -1 --format=%H origin/claude/internal-disk-agent-residue-20260928` returns `148c3fd95a53`
  and `git log -1 --format='%ad' --date=iso 148c3fd95a53` returns `2026-09-28 19:09:24 -0700`
  (= 02:09:24Z). `git show --stat 704d6b8ae995` lists exactly three paths, none of them
  `agentos/workstreams/WS-FLEET-STORAGE-LIFECYCLE.md`;
  `git cat-file -s origin/main:agentos/workstreams/WS-FLEET-STORAGE-LIFECYCLE.md` fails while the
  same probe against the three wave-4 paths returns 86413 / 5420 / 4646. Disproved if a push landing
  after a merge is rejected, if it reopens the PR, if it appears as an additional commit on the
  merged PR, or if any of `state`, `mergedAt`, `mergeCommit`, `headRefOid`, the check rollup or the
  push's own exit code differs between this case and a clean merge — none did.
  The `files` half was measured directly as a positive control:
  `gh pr view 8163 --json files --jq '.files[].path'` returns three paths, byte-for-byte the same
  set as `gh api repos/<repo>/commits/704d6b8ae995 --jq '.files[].filename'`, so a checker built on
  that comparison reports success on a PR that demonstrably lost two files. The instrument that
  PASSES the control is local and costs no API call: paths from
  `git log origin/main..origin/<branch> --name-only --format=` (5 paths), then
  `git rev-parse origin/<branch>:<path>` against `git rev-parse origin/main:<path>` per path —
  which reports the three wave-4 files as byte-identical in main **despite the squash rewriting
  their commit**, and exactly the two wave-5 files as absent.
so_what: >
  **Arm LAST, never push to an armed PR.** The window between the sweeper deciding to merge and the
  merge completing is invisible from the session side, so any push into an armed PR can land on the
  wrong side of it. Push every commit the PR needs first, then `gh pr edit --add-label
  merge-on-green`. If a late push is genuinely required, disarm first — and per the standing
  disarm law that act owes a visible marker and ownership of the PR to merged-or-handed-back — then
  push, then re-arm. Second, and more general: **`MERGED` is a fact about a pull request, not about
  your bytes.** This repo's standing "verify it in main's bytes" rule is what caught it, and it was
  the *only* thing that could: every state field, the merge SHA, the head OID, the check rollup and
  the push exit code were all indistinguishable from success, and `headRefOid` is specifically a
  false friend because the merged head is the right answer in both cases. The instrument that
  discriminates must take its "intended" set from the **branch ref**, never from the PR: the branch
  survives the merge, so `git log origin/main..origin/<branch> --name-only` is what the PR was
  actually carrying, and a per-path blob comparison against `origin/main` is squash-tolerant
  because a squash preserves the tree even though it rewrites the commit. A `git show --stat
  <squash>` also discloses it, but only when checked against what you know you intended — compare
  it against `--json files` and it agrees with itself. **Be wary of automating this:** the first two
  hardenings of this session's own watcher were both wrong (one keyed on `files`, one on row
  cardinality), and only a positive control replayed against #8163 caught them. A verifier that
  cannot fail on a known failure is worse than no verifier, because its "all good" is trusted.
  Third, the failure is fully recoverable and costs one PR: the branch ref survives the merge, so the orphaned commit is still fetchable and can
  be replayed onto fresh main — and a citation that was a hard `dangling-ref` before the merge
  resolves cleanly after it, which is what made the replay simpler than the original.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  `gh pr view 8163 --repo mastermindx-market-intelligence/macro --json
  state,mergedAt,mergeCommit,headRefOid`; `git fetch origin main` then
  `git log -1 --format='%H %ad %s' --date=iso 704d6b8ae9953ed8949264d73b5b6f9a4d65dd36` and
  `git show --stat 704d6b8ae995` (3 files, 195 insertions); `git fetch origin
  claude/internal-disk-agent-residue-20260928` then `git log -3` on that ref (tip 148c3fd95a53,
  committer time 2026-09-28 19:09:24 -0700); `git cat-file -s origin/main:<path>` for each of the
  five intended artifacts (three present at 86413/5420/4646 bytes, two absent); the watcher log for
  #8163, whose final line is `MERGED at 2026-09-29T02:09:24Z` after three clean polls.
scope:
  - macro
  - .github/workflows/merge-on-green.yml
confidence: verified
---

## The shape of the miss

Six instruments agreed the work had shipped. Five of them are reads of the pull request, and
that is the point: a merged PR describes its merge, so no amount of PR-reading can see a
commit that arrived afterwards.

| instrument | what it said | why it could not know |
|---|---|---|
| `git push` exit code | `rc=0` | a push to a merged PR's branch is a legal push |
| `gh pr view … state` | `MERGED` | true of the PR, silent about which commits |
| `… mergedAt` | `2026-09-29T02:09:24Z` | true, and the same second as the lost commit |
| `… headRefOid` | `2ff0f92f4496` | this is the merged head — the correct value in the healthy case too |
| `… files` | the 3 merged paths | also frozen at the merged head, so it agrees with the squash tautologically |
| the armed watcher | `MERGED at 02:09:24Z` | it judged the PR's state, which was not in question |

Only the **branch ref** disagreed — it is the one surviving record of what the PR was carrying
— and only because it was checked.

## The discriminator's own failure mode: a STALE baseline, measured 2026-09-29

This record prescribed the branch-ref check and omitted one word, and the omission fails toward a
**destructive** remedy. `origin/main` is a **local ref**. The armed watcher for #8169 ran the
per-path comparison without re-fetching, so it compared the branch against a pre-merge `origin/main`,
found both paths absent, and exited `MERGED BUT NOT LANDED — replay the missing paths onto fresh
main`. Both files were byte-identical in `origin/main` the entire time (`14a58cd095ad`,
`3556e9757b09`, equal at my commit, at the squash `c4c1b09cbe4d`, and at `origin/main`). A session
obeying that instruction would have re-pushed content that had already landed.

So the check is: **`git fetch origin` FIRST**, then `git log origin/main..origin/<branch>`, then the
per-path blob comparison. On a MISSING verdict, re-fetch and re-run before believing it, and
cross-check against main's own bytes for a string only your commit introduced
(`git grep <needle> origin/main -- <path>`) — a positive hit there refutes a false alarm immediately.

**The general shape is worth more than the fix.** A verifier built to catch a silent loss will, if its
baseline can go stale, convert every ordinary merge into a false loss report — and the two verdicts
are indistinguishable from inside the verifier. Both of this program's verifier failures now share one
root: the comparison was right and the thing compared against was wrong (the first compared the merged
head with itself via `--json files`; this one compared against a stale ref). **Pin what a verifier
compares against, and make it prove that baseline is current before it reports.**

**The mechanism is worse than a forgotten fetch, and the sufficient fix is narrower than "fetch
first".** The watcher DID fetch — `git fetch origin main <branch>` — and that command **fatals**,
because GitHub **deletes the head branch on merge**: `fatal: couldn't find remote ref
claude/documents-pool-sweeper-blind-20260928`, confirmed by an empty `git ls-remote --heads origin
<branch>`. A fetch that aborts updates nothing, so `origin/main` stayed pre-merge; meanwhile the
stale local `origin/<branch>` still resolved, so every blob lookup succeeded and the comparison
looked healthy while running entirely on pre-merge data. **The merge's own success — deleting the
branch — is what broke the check that verifies the merge.** The helper swallowed the non-zero exit
(it returns `""` on any failure), so nothing surfaced.

Three requirements, not one: fetch `main` **alone** (bare `git fetch origin`, never bundled with the
branch ref); **check the fetch's exit status** instead of swallowing it; and treat the branch's
absence from the remote as the **expected** post-merge state — only `origin/main` has to be current,
since the branch side is read from the local ref you already have.

## Why the replay was cheap

The late commit existed to fix an earlier sequencing error: the workstream record's `DSC:` citations
were hard `dangling-ref` validation errors against a main that did not yet carry those discoveries,
which is why the records and the handoff had been folded into one PR in the first place. The merge
that orphaned the commit also landed those discoveries — so on replay the citations resolved against
fresh `origin/main` with no special handling. The constraint that forced the bundling dissolved at
the moment the bundling failed.
