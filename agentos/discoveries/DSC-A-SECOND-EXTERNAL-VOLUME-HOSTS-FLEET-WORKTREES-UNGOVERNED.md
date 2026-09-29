---
key: A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED
claim: >
  A SECOND external volume — `/Volumes/Worktrees` (`/dev/disk4s1`, 931 GiB, 801 used,
  **130 GiB free / 87%**) — hosts **9 fleet linked worktrees** owned by 4 distinct stores, and
  it is named by no `config/worktree_gc.json` root, by no figure in
  `research/WORKTREE_GC_POLICY.md`, and by none of the storage censuses run on 2026-09-26/27.
  Measured 2026-09-28: 6 owned by `Macro Dashboard`, 1 by
  `/Volumes/Mastermind/repos/Mastermind-r7-836`, 1 by
  `~/agent-tools/wsx-telemetry-support-20260906-1415/Mastermind`, and
  `sol-consumer-cyclical-7804` whose registration target is **GONE** and whose owning store is
  `/Volumes/mini2/Projects/MastermindX/repos/macro` — **another machine's volume**, so no store
  on this host can ever prune it. Newest-file ages 73–106 h. The **6 `Macro Dashboard` ones are
  in this clone's registry** (they appear in `git worktree list`) yet are unreachable by the
  sweeper for THREE independent reasons at once: no root covers the volume (all 7 relative
  roots are repo-relative session dirs, the 1 absolute root is `~/.codex/worktrees`); the path
  carries no repo-relative session-root segment so the host-checkout belt refuses it
  (`DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT`); and 4 of the 9 are `sol-*`
  HUMAN-class, which `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` never auto-reclaims. The volume
  ALSO holds the user's own `Backups`/`Companies`/`Documents`/`$RECYCLE.BIN` and the
  operator-protected `.ADSPOWER_GLOBAL`, so it must never be swept by path pattern.
  **The correctness worry that motivated this look is FALSIFIED.** exFAT folklore (no POSIX
  modes, no symlinks) does NOT hold here: the volume mounts through Darwin 25 **`fskit`**, where
  a direct probe creates an lstat-visible symlink and `chmod 755` reads back `-rwx------`; the
  repo's one tracked symlink (`collectors/marketdesk_extractor/feed.sh`) materialized as a real
  symlink in all 6 trees that carry it; and both owning stores set `core.filemode = false`, so
  even a mode-losing filesystem would produce no git dirt. There is no correctness defect on
  this volume — only a governance/reach one.
  **AMENDED 2026-09-28 — this record's own EMPHASIS was wrong, measured by bytes.** Top-level
  `du -sxk` over all 34 entries (files as well as directories) attributes the volume as
  `Documents` **712.72 GiB = 89.0%** and `Backups` 36.08 GiB = 4.5% — both operator personal data
  — against a total fleet footprint of **51.85 GiB = 6.5%** across 6 sized trees, of which
  `sol-macro-hottest-desk-strength-entry-20260923` (28.14), its sparse sibling (14.45) and
  `sol-consumer-cyclical-7804` (3.84) are **46.43 GiB of HUMAN-class that is never
  auto-reclaimed**. Agent-reclaimable on this entire 931 GiB volume is therefore at most
  **~5.4 GiB**. Inside `Documents` the three largest categories are the live photo library
  (246.65 GiB), a separate pictures tree (147.02 GiB) and a messaging archive (133.23 GiB);
  the operator's per-folder structure is deliberately not enumerated. `.ADSPOWER_GLOBAL` measures
  **0.00 GiB** — a marker, not a payload, and the operator veto on it stands regardless of size.
  So the governance gap named above is real and the SIZE framing it invites is not: the 87% fill
  is not a fleet problem.
falsifier: >
  `mount | grep /Volumes/Worktrees` prints `exfat ... noowners ... fskit`; `diskutil info`
  confirms `File System Personality: ExFAT`. `os.listdir` + per-entry `.git` gitdir resolution
  yields 9 linked worktrees / 4 stores and flags the missing `mini2` registration.
  `git worktree list --porcelain | grep '^worktree /Volumes/Worktrees'` returns exactly 6.
  Reading `roots` out of `config/worktree_gc.json` shows none matches the volume. For the
  falsified half: `ln -s` in a temp dir there succeeds and `test -L` sees it; `stat -f '%Sp'`
  after `chmod 755` shows `-rwx`; `test -L <tree>/collectors/marketdesk_extractor/feed.sh` is
  true in the 6 trees that have it; `git config --get core.filemode` is `false` in both stores.
  Disproved by a legacy kernel-driver exFAT mount (no `fskit`) where those probes fail, by
  `core.filemode` becoming true, or by a root being added that covers the volume.
so_what: >
  Four things change. (0) **Do not propose fleet-GC work as a remedy for this volume — it
  cannot help.** The byte attribution at the end of the claim puts operator data at 93.5% and the
  whole fleet at 6.5%, ~90% of that HUMAN-class, so no roots widening, sweeper arming, lock-stamp
  repair or population cap can move its 87% fill — there is almost nothing there to reclaim. The
  risk runs the OTHER direction: only ~130 GiB is free, and every fleet worktree planted here
  consumes the operator's remaining headroom for a photo library that is still growing. The
  operator questions are whether the fleet should plant worktrees on this volume at all, and that
  **neither copy of the photo data is on a backup device**
  (`DSC:TRANSFERS-HOLDS-A-195-GIB-OPERATOR-PHOTO-BACKUP-NOT-THE-ONLY-COPY`). Attribute a volume's
  bytes before characterizing what fills it, and report the fleet's SHARE, not merely its
  presence — an entry count and a governance gap are not a byte attribution.
  (1) **Governance reach is bounded by VOLUME discovery, not by the roots
  list.** A volume literally named `Worktrees` held 9 fleet trees that no root, no census and no
  sweeper had ever seen, and 6 of them were sitting in a registry we read all day — so
  registry-visible is not the same as governable, and a fleet-wide storage figure is incomplete
  until mounted volumes have been enumerated. (2) **Do NOT migrate or "repair" these trees for
  filesystem reasons** — that premise is falsified, and acting on it would move live checkouts
  for nothing. The real hazards are the 87% fill, the permanently unprunable `mini2`
  registration, and the user data + AdsPower payload sharing the volume, which together mean
  this volume is REPORT-ONLY for any automated sweeper. (3) **Never reason about filesystem
  capability from version-free folklore.** "macOS exFAT has no symlinks or modes" is true of the
  legacy kernel driver and false under Darwin 25 FSKit; probe the mount, and check
  `core.filemode` before predicting git dirt at all, since a store that disables it cannot
  report a mode change no matter what the filesystem drops.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  mount/diskutil on /Volumes/Worktrees (exfat, fskit, noowners); os.listdir + per-entry gitdir
  resolution (9 linked worktrees, 4 stores, 1 registration GONE owned by /Volumes/mini2);
  `git worktree list --porcelain` (6 present in this clone's registry); direct ln -s + chmod
  probe in a temp dir on the volume (symlink and exec bit both honoured, probe removed);
  `git ls-files -s` (1 tracked symlink, 72 exec-bit files) and `core.filemode = false` in both
  `Macro Dashboard/.git/config` and this store; and for the 2026-09-28 amendment, top-level
  `du -sxk` over all 34 entries of /Volumes/Worktrees plus one level of Documents (712.72 GiB /
  89.0%; fleet 51.85 GiB / 6.5%; .ADSPOWER_GLOBAL 0.00 GiB) -- re-derive with
  `du -sxk /Volumes/Worktrees/* /Volumes/Worktrees/.[!.]*`, not from a session receipt path
scope:
  - macro
  - scripts/worktree_gc.py
  - config/worktree_gc.json
  - research/WORKTREE_GC_POLICY.md
confidence: verified
---
