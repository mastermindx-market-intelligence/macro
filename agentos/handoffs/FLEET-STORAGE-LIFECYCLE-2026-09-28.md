---
workstream: WS:FLEET-STORAGE-LIFECYCLE
session: claude/internal-disk-agent-residue-20260928 (waves 1-4; wave 5 replayed on claude/fleet-storage-lifecycle-ws-20260928 after a sweeper race orphaned it)
model: opus
ended_because: blocked
mission: >
  Autonomous cleaning and triage of fleet storage: classify every disk pool, the worktree fleet and
  the PR queue, actually reclaim what can be reclaimed, and put what only the operator may decide
  in front of the operator. No device may run out of space.
state_before: >
  `research/WORKTREE_GC_POLICY.md` §9 recorded five pools and named `/Volumes/Worktrees` as holding
  9 ungoverned fleet worktrees with operator data as an aside. The internal data volume had never
  been censused. No `WS-` record and no handoff existed for storage lifecycle at all, so each
  session re-derived the same figures. Free space: internal 321 GiB / 83%, `/Volumes/Worktrees`
  130 GiB / 87%, `/Volumes/Mastermind` 757 GiB / 80%.
changed:
  - path: research/WORKTREE_GC_POLICY.md
    what: >
      Gained the non-git-bucket and `transfers` sections, the in-place pool-count correction
      (five→SIX null, six→SEVEN measured), the in-place retraction of the only-copy claim with the
      superseded sentence quoted and dated, four numbered receipt-reading rules, the
      `/Volumes/Worktrees` byte-attribution section (eighth pool), and the internal-disk section
      (ninth and tenth pools). 82,156 → 86,413 bytes at the last edit.
  - path: agentos/discoveries/DSC-TRANSFERS-HOLDS-A-195-GIB-OPERATOR-PHOTO-BACKUP-NOT-THE-ONLY-COPY.md
    what: >
      New record, and a RE-KEY: it replaced
      DSC-THE-TRANSFERS-POOL-HOLDS-THE-ONLY-COPY-OF-OPERATOR-PHOTO-DATA.md, which was deleted
      because its key asserted a claim that turned out to be false.
  - path: agentos/discoveries/DSC-A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED.md
    what: >
      Amended. The byte attribution was appended to `claim`, a new guidance item (0) inserted at the
      head of `so_what` ("Three things change" → "Four things change"), and `verified_by` extended
      with the `du` command rather than a session receipt path. 5,012 → 7,456 bytes.
  - path: agentos/discoveries/DSC-A-SCRATCHPADS-KEYED-CHECKOUT-CAN-BE-GONE-WHILE-ITS-SESSION-IS-LIVE.md
    what: New record (kind landmine) — the inverted scratchpad liveness signal.
  - path: agentos/discoveries/DSC-A-RUNNER-CHECKOUT-IS-87-PERCENT-GIT-STORE-SO-SPARSENESS-CANNOT-REACH-IT.md
    what: New record (kind constraint) — the 177.26 GiB runner stores and the 12% sparse ceiling.
  - path: agentos/workstreams/WS-FLEET-STORAGE-LIFECYCLE.md
    what: >
      New record. Storage lifecycle had no workstream; this one carries the four operator options in
      `needs_ceo`, the five `do_not_redo` entries that stop the null pools being re-measured, and
      the landmine list.
verified:
  - claim: "`/Volumes/Worktrees` is 93.5% operator personal data and the entire fleet is 6.5% of it."
    command: "du -sxk /Volumes/Worktrees/* /Volumes/Worktrees/.[!.]* (all 34 entries, files as well as directories)"
    result: >
      Documents 712.72 GiB (89.0%), Backups 36.08 (4.5%), six sized fleet/Sol trees 51.85 (6.5%) —
      of which 46.43 GiB is `sol-*` HUMAN-class, so at most ~5.4 GiB is agent-reclaimable on the
      whole 931 GiB volume. `.ADSPOWER_GLOBAL` = 0.00 GiB.
  - claim: "The 195.28 GiB photo tar is a BACKUP, not the only copy on this machine."
    command: "ls -ld + depth-1 ls -d */ + du -sh on /Volumes/Worktrees/Documents/Photos Library.photoslibrary; cat PREFLIGHT.txt in the 20260922-sol-001 reclaim dir"
    result: >
      Live library present at 247 GB with seven subdirs, and PREFLIGHT.txt lists that exact path as
      `protected=`. This RETRACTS my own earlier claim; the failure was REACH, not measurement — I
      searched ~/Pictures and /Volumes/Mastermind at depth ≤3 and reported the result as
      machine-wide.
  - claim: "The 09-26 reclaim operation's halted candidates left no duplicate operator data."
    command: "du -sk and find -type d on /Volumes/Mastermind/Offloaded/runner-fleet-resilience-worktrees-reclaim-20260922-sol-001"
    result: "284 K with no subdirectories at all — sources intact, partial targets genuinely cleaned."
  - claim: "A copy receipt's `destination_root` goes stale, so an absent path is not a failed copy."
    command: "cat Courses-appledouble-copy-receipt.json; test -d on its destination_root"
    result: >
      status COPIED_AND_HASH_VERIFIED over 655 files with a manifest_sha256, and the named
      destination directory does not exist. The hash is the evidence; the path is only where the
      bytes were when the receipt was written.
  - claim: "/private/tmp/claude-501 is 160.43 GiB and only 0.02 GiB of it is provably dead."
    command: "du -sxk /private/tmp/claude-501/* then per-key classification by transcript mtime (scratchpad/classify_scratchpads.py)"
    result: >
      473 keys. LIVE <2h 6 keys / 103.91 GiB (64.8%), RECENT <24h 7 / 0.17, IDLE 1–7d 60 / 22.21,
      COLD ≥7d 48 / 0.02, NO TRANSCRIPT 61 / 28.39 (undecidable), no project key 291 / 5.73.
  - claim: "A scratchpad's keyed checkout can be gone while its session is live."
    command: "test -d on the checkout the 81.24 GiB key names; stat on ~/.claude/projects/<same key>/938d17d6-….jsonl"
    result: >
      The checkout is absent; the transcript is 108.7 MB last written 2026-09-28 18:53, four minutes
      before measurement, by the active FINANCE INTELLIGENCE seat. The positional probe and the
      semantic one disagree, and the positional one would have authorized deleting 81.24 GiB.
  - claim: "87% of a CI runner checkout is the git store, so sparseness cannot reach it."
    command: "du -sxk on actions-runner*/_work and on runner-3's .git; ls -1 objects/pack/*.pack | wc -l; find -name '*.pack' -size +8G"
    result: >
      177.26 GiB over four runners. runner-3: checkout 66.34 GiB, `.git` 57.70, 136 packs / 57.20
      GiB vs 0.47 GiB loose. runner-2 holds two base-size packs (31.63 + 28.61 GiB). `_temp` is
      0.00 GiB. The sparse omit-set is 8.02 of 66.34 GiB = 12%.
  - claim: "PR #8162 merged and its text is in main's actual bytes."
    command: "gh pr view 8162 --json mergedAt; git show origin/main:research/WORKTREE_GC_POLICY.md | grep -n 'eighth pool'"
    result: >
      Merged 2026-09-29T01:54:06Z, squash d7ced5ac663b; the section is at line 824 of main's copy
      and the DSC amendment at lines 29/54/88.
  - claim: "MEMORY.md had already crossed the silent-truncation threshold."
    command: "wc -c on the index before editing"
    result: >
      24,904 bytes against a ~24,400 warn / 25,000 hard limit, up from 23,647 earlier in the same
      session because other seats append concurrently. Three over-long index lines were compressed
      to hooks (2,335 bytes reclaimed) with the verbatim originals archived to CATALOG.md first.
  - claim: "Wave 4 (#8163) is merged AND present in main's bytes."
    command: "gh pr view 8163 --json state,mergedAt,mergeCommit; git show --stat <squash>; git cat-file -s origin/main:<path>"
    result: >
      MERGED 2026-09-29T02:09:24Z, squash 704d6b8ae995, 3 files / 195 insertions.
      research/WORKTREE_GC_POLICY.md is 86,413 bytes in main with the new section at line 856 and
      the ninth/tenth pool figures at 865/892; the two new DSCs are 5,420 and 4,646 bytes.
  - claim: "Wave 5's commit was pushed AFTER that merge completed and reached main in no form."
    command: "git log -1 --date=iso 148c3fd95a53; git show --stat 704d6b8ae995; git cat-file -s origin/main:agentos/workstreams/WS-FLEET-STORAGE-LIFECYCLE.md"
    result: >
      Commit 148c3fd95a53 carries committer time 02:09:24Z — the same second as the merge — so the
      push landed at or after it. rc was 0, the PR read MERGED, headRefOid read the old head
      2ff0f92f (which is also the correct value on a healthy merge), and the armed watcher reported
      MERGED. Only the squash's file list disagreed: the workstream record and this handoff were
      absent from main. The branch ref survived, so the commit was replayed onto fresh main — where
      its DSC citations now resolve, because the same merge landed the discoveries it cites.
      DSC:A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS.
unverified:
  - claim: "`git gc` on a runner store would reclaim roughly the duplicate base pack (~28 GiB on runner-2)."
    what_would_verify: >
      A repack on a drained runner, measuring `.git` before and after. Not attempted: a
      `Runner.Worker` was live, and an aggressive repack on a 4-core box contends with the nightly's
      render budget. The 136-pack / two-base-pack shape is measured; the yield is an inference.
  - claim: "The 28.39 GiB of scratchpad keys with no transcript are dead."
    what_would_verify: >
      Nothing available established it, which is why they are classified UNDECIDABLE rather than
      dead. A transcript can be absent because it was rotated, archived, or written under a
      different project key.
  - claim: "The 61 no-transcript keys and 291 no-project-key entries contain no unique work."
    what_would_verify: "Content inspection of each. Not attempted; they were counted, not opened."
unresolved:
  - "All four `needs_ceo` options in WS:FLEET-STORAGE-LIFECYCLE remain undecided. No user input of
     any kind was received during this work, so nothing was deleted, moved, or armed."
  - "The three ratification gates (human_driven_roots deny-list, roots widening by subtree,
     lock-stamp fix) are unratified and were not touched."
  - "The 77.7 GiB of git-less verification trees have no owner and no reclaim path. The proposed
     convention — one reusable comparison tree per session, removed when the claim is filed — is a
     proposal, not a decision."
  - "PR #8163 was armed `merge-on-green` with a proven-live watcher and had not concluded when this
     record was written."
next_actions:
  - "Put the four `needs_ceo` options to the operator, recommending option 3 (runner repack) first
     because it is the largest reclaim and the only fully reversible one."
  - "Ratify the `human_driven_roots` deny-list before any other gate. It is purely protective and
     can delete nothing; every other gate is unsafe without it."
  - "On operator approval only: repack runner-2's store with its listener drained and no
     `Runner.Worker` live, measuring `.git` before and after, then runner-3."
  - "Adopt the one-comparison-tree convention for byte verification, so the 77.7 GiB does not
     regrow. No sweeper can reach a tree with no HEAD."
  - "Re-measure nothing in the `do_not_redo` list. Read
     `research/WORKTREE_GC_POLICY.md` §9 first; it now names all ten pools with their reclaimable
     figures."
do_not_redo:
  - "The seven null pools are attributed and recorded. `/Volumes/Worktrees` (~5.4 GiB reachable of
     931), `transfers` (zero of 233.2), the non-git bucket (20.19 GiB, no landedness question),
     `/private/tmp/claude-501` (0.02 GiB of 160.43)."
  - "Retrofit-to-sparse as an ongoing lever: correctly gated it yields 0.0 GiB across the 27
     remaining FULL trees."
  - "Sparseness for the runner stores: the omit-set reaches 12% because 87% is `.git`."
  - "Deriving abandonment from ancestry: a squash rewrites the commit, so a merged branch's tip is
     not an ancestor of main. Real abandonment is 8–14%, not 79%."
  - "Re-litigating whether a wider `roots` alone frees space: +496 trees of reporting, +1 of
     deletion. The host-checkout belt is the binding constraint."
  - "Re-opening the only-copy question about the photo tar. It is settled: the tar is a backup, the
     live library is on /Volumes/Worktrees, and PREFLIGHT.txt lists it as protected."
danger_areas:
  - "Both copies of the operator's photo data sit on volumes the fleet writes to and sweeps, and
     NEITHER is on a backup device. The tar's name begins with three fleet-infrastructure words."
  - "Scratchpad liveness: the keyed-checkout probe is inverted. A scratchpad has no lock, no
     registry entry and no `git status`, so nothing refuses on your behalf there."
  - "Web/ChatGPT session roots are undetectable — no process, no shell, no reflog — so they are
     never auto-reclaimed, and a valid landed proof on one is NOT permission."
  - "The 527 human-driven SSD checkouts are protected today by a path-naming heuristic nobody chose.
     The repair that makes a wider `roots` work is the same commit that would delete them."
  - "An absolute-only `roots` list empties `rel_roots` and disables deletion entirely — fails
     closed, but silently, because the refusals land in `summary[\"errors\"]`, which is counted and
     never printed."
  - "Never `rm -rf`, move or rename `macro-main` or `Macro Dashboard`; the latter owns the whole
     worktree registry. Never bare `git stash`/`pop` — the stack is repo-global."
  - "Do not push to a PR that already carries `merge-on-green`. The window between the sweeper
     deciding to merge and the merge completing is invisible from here, so a late push lands on the
     far side of it with rc=0 and no change to any PR field. Push everything, THEN arm. `MERGED` is
     a fact about a pull request, not about your bytes — the discriminating instrument is
     `git show --stat <squash>`, never `headRefOid`."
  - "`du` over-counts APFS clones and hard links: the sum over `/` was 1917.93 GiB against `df`'s
     1501 used. Treat any `du` total as an upper bound and a ranking, never an attribution."
verified_wave_6:
  - claim: "Granting Full Disk Access would free 1.81 GiB of the 201.13 GiB pool, not 201."
    how: >
      `worktree_gc.py --report` over the pool as a principal that can read `~/Documents`, then
      aggregated on the report's REAL size key `size_kb` (my first pass guessed `size_gib`/`gib` and
      printed every size as 0.00). 207 registrations = 203 directories + 4 already-gone checkouts.
      `DIRTY 68/95.43G · LOCKED 43/40.49G · UNPUSHED 57/27.01G · RECENT 11/13.12G · OPEN_PR 15/8.48G
      · ORPHAN 5/7.72G · LIVE_PROC 1/7.05G · SAFE_MERGED 3/1.81G · MISSING 4/0G`. This fired the
      third clause of `DSC:THE-SWEEPER-IS-TCC-BLIND-TO-THE-LARGEST-INTERNAL-WORKTREE-POOL`'s own
      pre-registered falsifier.
  - claim: "`DIRTY` here is genuine tracked work, not untracked junk — but the 8 landed ones are still not collectable."
    how: >
      `git status --porcelain` in all 68 DIRTY trees: 54 trees / 76.95 GiB carry tracked
      modifications (81% of the DIRTY bytes), 14 / 18.48 GiB are untracked-only, of which 8 /
      8.41 GiB are also landed. Those 8 remain uncollectable because untracked files have no commit,
      no ref and no remote, so neither `refs/salvage/*` nor `origin/main` can reconstitute them; the
      largest is 2.90 GiB of `mockups/evidence/…`, the class the 09-26 sweep destroyed. My probe's
      own verdict line claimed this refuted the program — it had tested LANDEDNESS and inferred
      RECLAIMABILITY, which is the inference that caused that incident.
  - claim: "All 43 LOCKED trees in this pool carry real seat text, so the :501 lock fix is worth far less here."
    how: >
      Lock reasons read from the report: zero matches for the SSD helper's content-free
      `mastermind-external-storage` / `initializing` stamps, against 282 of 285 on the SSD pool.
      Ceiling if `worktree_gc.py:501` is fixed: 17.01 GiB across 15 non-human locked trees, and only
      the subset that then proves landed-and-unoccupied would qualify.
  - claim: "The pool is large by COUNT, not fatness, so a population cap is its matching lever."
    how: >
      Size buckets over the 207: 181 trees under 1 GiB (already sparse) totalling 88.99 GiB, 6 at
      1–3 GiB / 13.73 GiB, and 16 FULL trees at ≥3 GiB holding 98.41 GiB (49%). Retrofit-to-sparse
      cannot reach the 181 that are already thin.
  - claim: "The floor guard monitors two volumes by construction and the fullest is neither."
    how: >
      `grep -c Worktrees` over the guard's whole log = 0; `main()` calls
      `free_gib(\"/System/Volumes/Data\")` on a literal then reads `pol[\"mount_point\"]`, with no
      iteration over mounts; `storage-floor.json` can express only `internal_floor_gib`. `df -k`:
      `/Volumes/Worktrees` 87% used / 130.3 GiB free, versus internal 83% and Mastermind 80%.
      Recorded as a third reach failure ON the existing
      `DSC:A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED` rather than as a new record —
      that DSC already carried the volume's census and the same 46.43 GiB HUMAN-class figure, so a
      new one would have duplicated it.
  - claim: "#8166, #8169 and #8170 are merged AND byte-identical in main; the exit-8 alarm on #8169 was false."
    how: >
      Branch-ref discriminator per PR. #8166: 3/3 paths identical, squash `37a8d10e6762`. #8170: 2/2,
      squash `8ca1ecf7c61e`. #8169: squash `c4c1b09cbe4d`, and its armed watcher exited 8
      (`MERGED BUT NOT LANDED`) — **a stale-baseline false alarm**, because it never re-fetched. After
      `git fetch`, both blobs are equal at my commit, at the squash and at `origin/main`
      (`14a58cd095ad`, `3556e9757b09`), and main's bytes contain strings only my later commits
      introduced. Fixed in both law files as a fetch-first requirement.
verified_wave_7:
  - claim: >
      The #8169 false alarm was NOT a missing fetch. The head branch is deleted on merge, so the
      combined `fetch origin main <branch>` fatals and refreshes NOTHING — including main.
    how: >
      `git ls-remote --heads origin claude/documents-pool-sweeper-blind-20260928` -> empty (deleted
      on merge). `git fetch origin main claude/documents-pool-sweeper-blind-20260928` -> `rc=128`,
      `fatal: couldn't find remote ref …`. The watcher's helper returns `""` on any failure, so the
      aborted fetch was invisible and the comparison ran on a pre-merge baseline. **The merge's own
      success is what broke the check that verifies the merge**, and the false verdict's prescribed
      remedy was to replay content that had already landed. Fixed in both law files and the landmine
      DSC as three requirements, not one: fetch `main` alone, check the fetch's exit status, and
      treat the branch's absence from the remote as the EXPECTED post-merge state.
  - claim: "The fix was re-run against the exact input that broke the old version."
    how: >
      Gen 2 on the #8169 branch: fetch `rc=128`, baseline stale, 2 paths reported MISSING, exit 8.
      Gen 3 on the same input: fetch `rc=0`, both blobs equal (`14a58cd095ad`, `3556e9757b09`),
      exit 0. A fix not re-run against its own failing case is a hypothesis.
  - claim: "#8171 is merged and all 6 paths are byte-identical in main."
    how: >
      Sweeper merged head `8d330725a5611f1343b9a66c33996fa91c05a021`; gen-3 verification returned
      `0 of 6 path(s) not byte-identical`, plus a path-scoped grep finding a string only this
      commit introduced in main's own `CLAUDE.md`.
  - claim: "The sweeper examines 224 of 789 registered worktrees — 28.4% — and never said so."
    how: >
      `python3 scripts/worktree_gc.py --no-sizes --no-gh --no-fetch` (report-only) against the real
      fleet, with the W9 patch: `reach: checked 224 of 789 registered worktrees · 565 outside
      configured roots and never examined · plus 9 unregistered found by scan`. Before W9 no
      human-readable output contained any number from which that could be derived — `in_scope` and
      `registered_total` went only into the JSON payload. **No verdict it printed was ever wrong;
      the report was simply unfalsifiable as a statement about the fleet.** Also: refusals were
      handled by exactly `if apply_summary["errors"]: return 1` — counted into an exit code and
      never printed, so `deleted=0 errors=688` with no messages was indistinguishable from a
      healthy run with nothing to do. 21 tests pass (16 existing + 5 new).
prs:
  - 8156
  - 8158
  - 8162
  - 8163
  - 8166
  - 8169
  - 8170
  - 8171
  - 8172
decisions:
  - DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM
discoveries:
  - DSC:A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED
  - DSC:TRANSFERS-HOLDS-A-195-GIB-OPERATOR-PHOTO-BACKUP-NOT-THE-ONLY-COPY
  - DSC:A-SCRATCHPADS-KEYED-CHECKOUT-CAN-BE-GONE-WHILE-ITS-SESSION-IS-LIVE
  - DSC:A-RUNNER-CHECKOUT-IS-87-PERCENT-GIT-STORE-SO-SPARSENESS-CANNOT-REACH-IT
  - DSC:A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS
---

## The one thing a successor should read first

Ten pools were byte-attributed across three volumes. **Seven are null, and the bytes were never
where the remediation program was looking.** The two external volumes turned out to be mostly the
operator's own data (93.5% and 84%); the session scratchpad pool turned out to be 64.8% live with
0.02 GiB provably dead; and the single pool with a real, bounded, reversible lever — **177.26 GiB of
CI runner git stores, 87% of each checkout being `.git`** — is the one nobody calls a worktree and no
policy document named.

Before proposing any storage work here: attribute the target volume, state your instrument's REACH,
and report the reclaimable SHARE beside the pool size. Seven times in this triage an instrument
returned a clean, plausible number with no error while answering a different question than the one
asked — `df /` (first row, not which volume fills), the HUMAN-class screen (name prefix, not marker
anywhere), `is_git` (a `.git` child, not "is this a git store"), landedness (ancestry, not the
merged PR), the pool census (`is_dir()`, which hid a 195 GiB FILE that was 84% of its pool), the
absence search (two locations reported as "nowhere on this machine"), and scratchpad liveness (the
keyed path, which is inverted). None of them errored. That is the failure mode to expect.

**Wave 6 added two more, and both are about the ASKER rather than the question.** The eighth: the
fleet GC's `roots` were right and its config was `armed`, but the launchd principal running it cannot
READ `~/Documents` (TCC), so every hand census saw the 201 GiB pool and every automated sweep did not
— 16 remediator faults and 73 escalations, unread. The ninth: `storage_floor_guard.py` asks each
volume it knows whether it is above its floor, correctly, but it has exactly two hardcoded subject
slots and the fleet has three volumes — the fullest being the one absent. Both print a clean number.
**Neither states its reach, and that is now the single most repeated defect in this program: an
instrument that reports per-subject health while never reporting its subject COUNT is
indistinguishable from one with full coverage.** Print `checked N of M` beside every verdict.

**Wave 6 also failed in the other direction, which is worth as much.** The landed-bytes verifier this
program wrote to catch a silent loss raised a *false* loss on #8169, because it compared against a
local `origin/main` it had not refreshed — and its prescribed remedy was "replay the missing paths",
i.e. duplicate work that had already landed. Both of this program's verifier defects share one root:
the comparison was correct and the thing compared against was wrong. **Pin what a verifier compares
against, and make it prove that baseline is current before it reports.**
