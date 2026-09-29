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
  main in **no** form. **`headRefOid` cannot detect this**: it reads `2ff0f92f` here, and it reads
  the merged head in the healthy case too, so the field is identical in both. The watcher, which
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
  discriminates is the **merged commit's file list** (`git show --stat <squash>`), or equivalently a
  `cat-file -s` on each artifact against `origin/main`. Third, the failure is fully recoverable and
  costs one PR: the branch ref survives the merge, so the orphaned commit is still fetchable and can
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

Four separate instruments agreed the work had shipped:

| instrument | what it said | why it could not know |
|---|---|---|
| `git push` exit code | `rc=0` | a push to a merged PR's branch is a legal push |
| `gh pr view … state` | `MERGED` | true of the PR, silent about which commits |
| `… mergedAt` | `2026-09-29T02:09:24Z` | true, and the same second as the lost commit |
| `… headRefOid` | `2ff0f92f4496` | this is the merged head — the correct value in the healthy case too |
| the armed watcher | `MERGED at 02:09:24Z` | it judged the PR's state, which was not in question |

Only the merged commit's **contents** disagreed, and only because they were checked.

## Why the replay was cheap

The late commit existed to fix an earlier sequencing error: the workstream record's `DSC:` citations
were hard `dangling-ref` validation errors against a main that did not yet carry those discoveries,
which is why the records and the handoff had been folded into one PR in the first place. The merge
that orphaned the commit also landed those discoveries — so on replay the citations resolved against
fresh `origin/main` with no special handling. The constraint that forced the bundling dissolved at
the moment the bundling failed.
