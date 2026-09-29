---
workstream: WS:FLEET-STORAGE-LIFECYCLE
session: claude/internal-disk-agent-residue-20260928
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
  - "`du` over-counts APFS clones and hard links: the sum over `/` was 1917.93 GiB against `df`'s
     1501 used. Treat any `du` total as an upper bound and a ranking, never an attribution."
prs:
  - 8156
  - 8158
  - 8162
  - 8163
decisions:
  - DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM
discoveries:
  - DSC:A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED
  - DSC:TRANSFERS-HOLDS-A-195-GIB-OPERATOR-PHOTO-BACKUP-NOT-THE-ONLY-COPY
  - DSC:A-SCRATCHPADS-KEYED-CHECKOUT-CAN-BE-GONE-WHILE-ITS-SESSION-IS-LIVE
  - DSC:A-RUNNER-CHECKOUT-IS-87-PERCENT-GIT-STORE-SO-SPARSENESS-CANNOT-REACH-IT
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
