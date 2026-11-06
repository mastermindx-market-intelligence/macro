---
key: AN-OFFLOADED-SELF-UPDATING-CLONE-FREEZES-SILENTLY-UNDER-LAUNCHD
claim: >
  On M1 a manual storage offload on 2026-09-17 (`~/.local/lib/mastermind/storage-cleanup/offload_dir.py`,
  which neither `sweep.py` nor `storage_floor_guard.py` ever calls) replaced the fundamentals
  lane's engine clone `~/fund-engine-wt` and its source tree `~/fund-src` with symlinks into
  `/Volumes/STORAGE/Offloaded/m1-20260917/`. Under launchd, `/usr/bin/git -C <that path>` exits
  128 with `fatal: Unable to read current working directory: Operation not permitted` (TCC: a
  launchd job has no grant for the removable volume), while the lane's Python stages kept reading
  and writing fund-src through the same symlink. Unlike the 2026-08 ThetaData store wedge, where
  Python blocked forever, this variant does NOT hang: `ops/nightly_fund.sh` step 0 logged a
  generic `WARN: engine git update failed — using current code` and every nightly run since then
  "succeeded" on engine code frozen at `0fa09ade7` (2026-09-16), for six weeks. An interactive
  `ssh m1` session holds the grant, so the same git command run by hand returns `0fa09ade7` with
  rc 0, a false all-clear. Measured 2026-10-31 with a one-shot launchd job: git on the
  `/Volumes` copy rc=128, git on the internal-disk clone rc=0 (`24ae12d64`), and the `/Volumes`
  command over ssh rc=0.
falsifier: >
  A one-shot `launchctl bootstrap gui/501` job whose ProgramArguments run
  `/usr/bin/git -C /Volumes/STORAGE/Offloaded/m1-20260917/fund-engine-wt.rollback-moved-internal-20261031 rev-parse --short HEAD`
  exiting 0 (that rollback copy stays on the volume for exactly this check); or
  `readlink ~/fund-engine-wt` printing a `/Volumes/` path while, after
  `launchctl kickstart gui/501/com.mastermind.fund`, `/tmp/mm_fund_refresh.log` shows
  `engine at <current main sha>` with no `WARN: engine git update failed`.
so_what: >
  Never put a launchd lane's git checkout, or any path its `/bin` tools write, on `/Volumes`.
  Running `offload_dir.py` on a lane tree causes a silent lane outage; it is not a storage win.
  Verify any TCC fix with `launchctl kickstart`, never with a hand run over ssh. A self-updating
  clone must log the SHA it reached, because a bare failure WARN gets normalized as noise. Since
  mastermind-terminal PR #1190 both `ops/nightly_fund.sh` and `ops/nightly_cnhk.sh` WARN when
  their trees are `/Volumes/*` symlinks and log `engine at <sha> <date>` after the update.
  Before blaming code for a stale fundamentals symptom on M1, read that line first. Other
  directories under `/Volumes/STORAGE/Offloaded/m1-20260917/` have not been checked for the
  same exposure.
kind: landmine
verified_at: 2026-10-31
verified_by: "one-shot launchd probe on M1 2026-10-31 (git rc 128 on the /Volumes copy, rc 0 on the internal clone, rc 0 for the same /Volumes command over ssh); fixed by moving both trees back to internal disk and proven by a launchctl kickstart that reset the engine to 24ae12d64 = origin/main; guard and SHA logging in mastermind-terminal PR #1190"
scope:
  - mastermind-terminal:ops/nightly_fund.sh
  - mastermind-terminal:ops/nightly_cnhk.sh
confidence: verified
---

This is the fourth TCC incident on the data plane. It is the quietest one, because nothing
fails loudly. The lane's exit code stays 0, the Python stages publish, and `rsync OK` keeps
appearing in the log. Only the code doing the computing is stale. The controlled check is the
launchd-vs-ssh pair. A hand run inherits the terminal's grant and proves nothing about the job:

```
launchctl kickstart gui/501/com.mastermind.fund
grep -E "engine at|engine git update failed|external volume" /tmp/mm_fund_refresh.log | tail -3
```

The fix moved both trees back to the internal disk with a verified copy. Rollback copies are
kept at `/Volumes/STORAGE/Offloaded/m1-20260917/{fund-engine-wt,fund-src}.rollback-moved-internal-20261031`.

Not part of this defect: the US lane's `rsync OK — N fund.json` count fell from about 9971 to
about 5016 on 2026-10-21/22. That drop is intentional. mastermind-terminal commits `7cc1f2e07`
and `eb6af9f70` exclude `SS|SZ|BJ|HK|TO|V` from the US rsync, because the cnhk lane and the CA
staged publication now publish those names. Do not "restore" it.
